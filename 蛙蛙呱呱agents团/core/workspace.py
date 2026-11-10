"""共享工作区：让 20 个 Agent 通过文件系统读写同一个状态。

对应 Anthropic 「Shared-State」协作模式：没有中心路由，各 Agent 直接
读/写 workspace；由「事件流 + 任务卡」承载交班，由文件锁保证单写者。

布局：
    workspace/
      events.jsonl      # 只追加事件流（审计 + 追溯）
      tasks/<id>.json    # 任务卡
      artifacts/         # 各 Agent 的实际交付物（csv/md/json…）
"""
from __future__ import annotations

import json
import os
import time
import tempfile
from typing import Any, Dict, List, Optional


def _atomic_json(path: str, value: Any) -> None:
    """UTF-8 原子替换 JSON 文件，避免读到半写内容。"""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.workspace-', dir=parent, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


from . import protocol
def _append_utf8(path: str, text: str) -> None:
    """Append one UTF-8 record and flush it durably as one write operation."""
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)



class Workspace:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.events_path = os.path.join(self.root, "events.jsonl")
        self.tasks_dir = os.path.join(self.root, "tasks")
        self.artifacts_dir = os.path.join(self.root, "artifacts")
        for d in (self.tasks_dir, self.artifacts_dir):
            os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 事件
    # ------------------------------------------------------------------ #
    def emit(self, event: protocol.Event) -> None:
        with self._lock(self, "events"):
            _append_utf8(self.events_path, event.to_line() + "\n")

    def events(self, agent: Optional[str] = None, type_: Optional[str] = None
               ) -> List[Dict[str, Any]]:
        if not os.path.exists(self.events_path):
            return []
        out: List[Dict[str, Any]] = []
        with open(self.events_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                if agent and e.get("agent") != agent:
                    continue
                if type_ and e.get("type") != type_:
                    continue
                out.append(e)
        return out

    # ------------------------------------------------------------------ #
    # 任务卡
    # ------------------------------------------------------------------ #
    def task_path(self, task_id: str) -> str:
        return os.path.join(self.tasks_dir, f"{task_id}.json")

    def create_task(self, task: protocol.Task) -> str:
        with self._lock(self, "tasks"):
            _atomic_json(self.task_path(task.task_id), task.to_dict())
        self.emit(protocol.Event.now("core", "task_created", task.task_id,
                                     {"owner": task.owner, "title": task.title}))
        return task.task_id

    def read_task(self, task_id: str) -> Optional[protocol.Task]:
        p = self.task_path(task_id)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return protocol.Task.from_dict(json.load(f))

    def update_task(self, task_id: str, patch: Dict[str, Any],
                    event_type: str = "note") -> Optional[protocol.Task]:
        t = self.read_task(task_id)
        if t is None:
            return None
        for k, v in patch.items():
            # 端口字段统一规范化：允许上游传 dict，存回时转成 Port 对象
            if k in ("inputs", "outputs") and isinstance(v, list):
                v = [protocol.Port(**x) if isinstance(x, dict) else x for x in v]
            setattr(t, k, v)
        with self._lock(self, "tasks"):
            _atomic_json(self.task_path(task_id), t.to_dict())
        self.emit(protocol.Event.now(t.owner, event_type, task_id, patch))
        return t

    def set_status(self, task_id: str, status: str,
                   note: str = "") -> Optional[protocol.Task]:
        return self.update_task(task_id, {"status": status},
                                "task_finished" if status == "done" else "note")

    def list_tasks(self, status: Optional[str] = None) -> List[protocol.Task]:
        out: List[protocol.Task] = []
        if not os.path.exists(self.tasks_dir):
            return out
        for name in sorted(os.listdir(self.tasks_dir)):
            if name.endswith(".json"):
                with open(os.path.join(self.tasks_dir, name), encoding="utf-8") as f:
                    t = protocol.Task.from_dict(json.load(f))
                if status is None or t.status == status:
                    out.append(t)
        return out

    # ------------------------------------------------------------------ #
    # 产物路径
    # ------------------------------------------------------------------ #
    def artifact(self, *parts: str) -> str:
        return os.path.join(self.artifacts_dir, *parts)

    # ------------------------------------------------------------------ #
    # 运行可观测性：只追加 runlog，记录输入哈希/耗时/退出码，供 harness 门禁
    # ------------------------------------------------------------------ #
    def log_run(self, agent: str, entry: Dict[str, Any]) -> None:
        path = os.path.join(self.root, "runlog.jsonl")
        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        try:
            with self._lock(self, "runlog"):
                _append_utf8(path, json.dumps(entry, ensure_ascii=False) + "\n")
        except (PermissionError, OSError):
            pass

    def runlog(self, n: int = 10) -> List[Dict[str, Any]]:
        path = os.path.join(self.root, "runlog.jsonl")
        if not os.path.exists(path):
            return []
        out: List[Dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out[-n:]

    # ------------------------------------------------------------------ #
    # 单写者文件锁（跨进程），用 O_EXCL 建锁文件 + 超时重试
    # ------------------------------------------------------------------ #
    class _lock:
        def __init__(self, ws: "Workspace", name: str, timeout: float = 5.0):
            self.path = os.path.join(ws.root, f".{name}.lock")
            self.timeout = timeout

        def __enter__(self):
            deadline = time.time() + self.timeout
            while True:
                try:
                    fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, str(os.getpid()).encode())
                    os.close(fd)
                    return self
                except FileExistsError:
                    if time.time() > deadline:
                        raise TimeoutError(f"等待锁超时: {self.path}")
                    time.sleep(0.05)
                except (PermissionError, OSError):
                    return self

        def __exit__(self, *exc):
            try:
                os.remove(self.path)
            except OSError:
                pass
            return False