# -*- coding: utf-8 -*-
"""一人公司 · 角色运行时公共层（Role Runtime）。

给 R01~R20 的 `agent.py` 提供三件公共能力，避免 20 份重复实现（META-001 反模式 #8）：

1. `bootstrap()`   —— 把仓库根 / agents 根注入 sys.path。
2. `emit(...)`     —— **证据出口**（2026-11-15 起）。执行角色不再自己出报告，
                      只把本次技能的真实 result 落成 `result.json` + `evidence.json`，
                      交给 R01 解读后统一出具唯一报告（core/report/report_flow.py）。
3. `log_event(...)` —— 结构化运行日志，按角色分文件落盘到 `workspace/logs/<role>.jsonl`。

为什么改：过去每个角色各有报告模板/引擎（REP-001 五段式、内核 spec、v2/v3 批量线），
同一次执行能产出 20 种版式、20 套口径。收敛后「报告」只有一个作者（R01），
执行角色只对**数字与证据**负责。

设计纪律：
    - result 落盘失败不静默：写 `EVIDENCE_FAILED.md` 并返回 ERROR 日志。
    - 证据内容全部来自本次 result，不注入任何演示数字。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
_REPO = os.path.dirname(_AGENTS)

from core.base.workspace import default_root  # noqa: E402

LOG_DIR = os.path.join(default_root(), "logs")


def bootstrap() -> None:
    """把仓库根与 agents 根加入 sys.path（幂等）。"""
    for p in (_REPO, _AGENTS):
        if p not in sys.path:
            sys.path.insert(0, p)


bootstrap()

from core.base import protocol  # noqa: E402


# --------------------------------------------------------------------------- #
# 结构化日志
# --------------------------------------------------------------------------- #
def log_event(role: str, event: str, payload: Optional[Dict[str, Any]] = None,
              level: str = "INFO") -> str:
    """按角色分文件写一行 JSON 日志，返回日志路径（失败也不抛）。"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, f"{role}.jsonl")
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "role": role, "level": level, "event": event,
            "payload": payload or {},
        }
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# 证据出口（唯一职责：把 result 交给 R01，不出报告）
# --------------------------------------------------------------------------- #
def emit(role: str, name: str, title: str, result: Dict[str, Any],
         skill: str, action: str, intent: str, out_dir: str,
         md_name: str = "result", html_name: Optional[str] = None,
         input_path: Optional[str] = None,
         report_slug: Optional[str] = None,
         dataset: Optional[List[Dict[str, Any]]] = None,
         data: Optional[Dict[str, Any]] = None,
         **legacy: Any) -> List[Any]:
    """执行角色的出口：落 `result.json` + `evidence.json`，返回 data Port。

    与旧签名兼容（md_name/html_name/dataset/data/legacy 全部接受并忽略渲染语义），
    但**不再生成 HTML/MD 报告**：报告由 R01 在 core/report/report_flow.py 里统一出具。

    兼容字段（dataset/data/report_slug）只记录在 evidence 里供 R01 取用：
    PRD 类角色的内容在输入不在 result，R01 仍能从 evidence.data 拿到。

    :return: [Port("result.json", "data")] —— 交给 R01 的唯一产物。
    """
    os.makedirs(out_dir, exist_ok=True)
    result = result if isinstance(result, dict) else {"ok": True, "value": result}
    result.setdefault("skill", skill)
    result.setdefault("action", action)
    result.setdefault("role", role)
    result.setdefault("intent", intent)

    result_path = os.path.join(out_dir, "result.json")
    payload = {
        "role": role, "name": name, "title": title,
        "skill": skill, "action": action, "intent": intent,
        "ok": bool(result.get("ok")),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "result_file": os.path.basename(result_path),
        "input_path": input_path,
        "has_data": bool(data),
        "dataset_rows": len(dataset or []),
        "legacy_kwargs": sorted(legacy) if legacy else [],
    }
    try:
        with open(result_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        payload["result_hash"] = hashlib.sha256(
            json.dumps(result, ensure_ascii=False, sort_keys=True,
                       default=str).encode("utf-8")).hexdigest()[:16]
        with open(os.path.join(out_dir, "evidence.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        if data is not None:
            with open(os.path.join(out_dir, "input.json"), "w",
                      encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:  # 证据落盘失败必须可见
        tb = traceback.format_exc()
        try:
            with open(os.path.join(out_dir, "EVIDENCE_FAILED.md"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(f"# 证据落盘失败 · {role}\n\n- 技能：`{skill}/{action}`\n"
                        f"- 异常：`{type(exc).__name__}: {exc}`\n\n```\n{tb}\n```\n")
        except OSError:
            pass
        log_event(role, "evidence_failed", {**payload, "error": str(exc)},
                  level="ERROR")
        return [protocol.Port("EVIDENCE_FAILED.md", "artifact", "text/markdown")]

    log_event(role, "evidence_emitted", payload)
    return [protocol.Port("result.json", "data", "application/json")]


# --------------------------------------------------------------------------- #
# 一次技能执行的便捷封装（供新增角色与回归脚本使用）
# --------------------------------------------------------------------------- #
def run_and_capture(role: str, name: str, title: str, skill: str, action: str,
                    intent: str, out_dir: str, run_callable,
                    input_path: Optional[str] = None,
                    md_name: Optional[str] = None) -> Dict[str, Any]:
    """执行 run_callable() 拿到 result，落 result.json + evidence.json 并返回。"""
    result = run_callable()
    if not isinstance(result, dict):
        result = {"ok": True, "value": result}
    emit(role=role, name=name, title=title, result=result, skill=skill,
         action=action, intent=intent, out_dir=out_dir,
         md_name=md_name or "result", input_path=input_path)
    return result


# 兼容旧名（外部脚本/回归可能还在用）
run_and_report = run_and_capture


# --------------------------------------------------------------------------- #
# 统一元命令：`report` / `test` / `logs`
# --------------------------------------------------------------------------- #
def _role_dir(role: str) -> str:
    for name in sorted(os.listdir(_AGENTS)):
        if name.startswith(role + "-") and os.path.isdir(os.path.join(_AGENTS, name)):
            return os.path.join(_AGENTS, name)
    raise FileNotFoundError(f"找不到角色目录：{role}-*")


_META_HELP = """\
用法：
  python agent.py report <skill> <action> --input <file> [--intent <一句话意图>]
      ↑ 跑技能并把 result 落成证据（不再出报告；报告由 R01 统一出具）
  python agent.py test                 # 跑本角色 tests/（pytest 绝对路径）
  python agent.py logs [--n 5]         # 查看本角色最近运行日志
"""


def handle_meta_command(argv: List[str], role: str) -> Optional[int]:
    """在角色 CLI 解析前拦截统一元命令；不匹配则返回 None 交回原 CLI。"""
    if not argv:
        return None

    # 全员 LLM 网关：默认关闭；开启且通过 schema 校验时接管，否则原样放行。
    try:
        from .prompt_gateway import maybe as _llm_maybe
        _llm_res = _llm_maybe(role, argv)
    except Exception:  # noqa: BLE001
        _llm_res = None
    if _llm_res is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        print("__AGENT_RESULT__ " + json.dumps(_llm_res, ensure_ascii=False))
        return 0 if _llm_res.get("ok", True) else 1

    cmd = argv[0]
    if cmd not in ("report", "test", "logs"):
        return None

    from shared.role_profiles import get as get_profile
    profile = get_profile(role)
    role_dir = _role_dir(role)
    if role_dir not in sys.path:
        sys.path.insert(0, role_dir)

    if cmd == "test":
        import pytest
        tests_dir = os.path.join(role_dir, "tests")
        if not os.path.isdir(tests_dir):
            print(json.dumps({"ok": False, "error": f"{role} 无 tests/ 目录"},
                             ensure_ascii=False))
            return 2
        return int(pytest.main([tests_dir, "-q"]))

    if cmd == "logs":
        n = 5
        if "--n" in argv:
            try:
                n = int(argv[argv.index("--n") + 1])
            except (IndexError, ValueError):
                n = 5
        path = os.path.join(LOG_DIR, f"{role}.jsonl")
        records: List[str] = []
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                records = [ln.rstrip("\n") for ln in f if ln.strip()][-n:]
        print("\n".join(records) if records else f"（{role} 暂无日志）")
        return 0

    # report <skill> <action> --input FILE [--intent TEXT]
    rest = argv[1:]
    if len(rest) < 2:
        print(_META_HELP)
        return 2
    skill, action = rest[0], rest[1]
    input_path = None
    intent = f"{skill}/{action} 例行执行"
    if "--input" in rest:
        i = rest.index("--input")
        if i + 1 < len(rest):
            input_path = os.path.abspath(os.path.join(role_dir, rest[i + 1]))
    if "--intent" in rest:
        i = rest.index("--intent")
        if i + 1 < len(rest):
            intent = rest[i + 1]

    import argparse as _argparse
    from skills import SKILLS  # 角色目录已在 sys.path，故可直接导入
    mod = next((m for m in SKILLS if m.NAME == skill), None)
    if mod is None:
        print(json.dumps({"ok": False, "error": f"未知技能 {skill}"},
                         ensure_ascii=False))
        return 2

    if hasattr(mod, "run"):
        ns = _argparse.Namespace(action=action, input=input_path)
        result = mod.run(ns)
    else:  # r07 风格：动作函数(input_data)
        fn = getattr(mod, action, None)
        if not callable(fn):
            print(json.dumps({"ok": False, "error": f"未知动作 {action}"},
                             ensure_ascii=False))
            return 2
        data = {}
        if input_path and os.path.isfile(input_path):
            with open(input_path, encoding="utf-8-sig") as f:
                data = json.load(f)
        result = fn(data)
    if not isinstance(result, dict):
        result = {"ok": True, "value": result}

    out_dir = os.path.join(default_root(), "artifacts", role, "evidence",
                           f"{skill}-{action}")
    res = run_and_capture(role=role, name=profile["name"],
                          title=profile["title"], skill=skill, action=action,
                          intent=intent, out_dir=out_dir,
                          run_callable=lambda: result, input_path=input_path,
                          md_name="result")
    print(json.dumps({
        "ok": bool(res.get("ok")), "role": role, "skill": skill, "action": action,
        "verdict": res.get("verdict"), "checks": len(res.get("checks") or []),
        "evidence": os.path.join(out_dir, "result.json"),
    }, ensure_ascii=False))
    return 0 if res.get("ok") else 1


__all__ = ["bootstrap", "emit", "log_event", "run_and_capture", "run_and_report",
           "handle_meta_command", "LOG_DIR"]
