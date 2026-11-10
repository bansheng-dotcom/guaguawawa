# -*- coding: utf-8 -*-
"""S12 AI 图片生成与编辑（Nano Banana Pro 裸接口适配）。

能力来源：AI Hive OpenAPI 的 `public_model_nano_banana_pro`（文生图 / 参考图 / 图片编辑），
脚本以 vendor 方式随仓库分发（`vendor/aihive/imagegen.py`，上游 Marketplace Skill
nano-banana-pro v1.0.0）。

本模块**不自己发 HTTP**，只做「确定性外壳」：
  - probe   ：探测脚本 / requests / API Key 是否齐备（不联网、不扣费）；
  - preview ：把将执行的命令拼出来（脱敏，永远不打印 Key）；
  - generate：真实调用需 --yes；默认 COST_FIRST；单次 batch 上限 4（超出要 --allow-batch）；
  - task    ：查询已有任务（需要网络）。

纪律：缺依赖或 Key 时返回 status=blocked，绝不假装生成成功；超时保留 taskId 供后续查询。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from . import _common as c

NAME = "aihive"
DESC = "AI 图片生成与编辑（Nano Banana Pro）：probe/preview/generate/task"

MODEL = "public_model_nano_banana_pro"
MAX_BATCH = 4
_ROLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VENDOR_SCRIPT = os.path.join(_ROLE_DIR, "vendor", "aihive", "imagegen.py")
_CONFIG_PATHS = [os.path.expanduser("~/.ai-hive/config.json")]


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _script() -> Optional[str]:
    env = os.environ.get("AIHIVE_SCRIPT")
    for p in (env, _VENDOR_SCRIPT):
        if p and os.path.isfile(p):
            return p
    return None


def _api_key() -> Optional[str]:
    if os.environ.get("AI_HIVE_API_KEY"):
        return "env"
    for p in _CONFIG_PATHS:
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and data.get("api_key"):
                return p
        except (OSError, ValueError):
            continue
    return None


def _has_requests() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("requests") is not None
    except Exception:  # pragma: no cover
        return False


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    act.add_parser("probe", help="探测脚本/依赖/API Key（不联网）")

    pv = act.add_parser("preview", help="只拼命令，不执行")
    pv.add_argument("--prompt", required=True)
    pv.add_argument("--image", nargs="*", default=None, help="参考图路径，可多张")
    pv.add_argument("--batch", type=int, default=1)
    pv.add_argument("--param", nargs="*", default=None, help="模型参数 key=value")
    pv.add_argument("--output-dir", default=None)
    pv.add_argument("--routing", default="COST_FIRST",
                    choices=["COST_FIRST", "SPEED_FIRST", "SUCCESS_FIRST"])

    g = act.add_parser("generate", help="真实生成（需 --yes）")
    g.add_argument("--prompt", required=True)
    g.add_argument("--image", nargs="*", default=None)
    g.add_argument("--batch", type=int, default=1)
    g.add_argument("--param", nargs="*", default=None)
    g.add_argument("--output-dir", default=None)
    g.add_argument("--routing", default="COST_FIRST",
                   choices=["COST_FIRST", "SPEED_FIRST", "SUCCESS_FIRST"])
    g.add_argument("--no-download", action="store_true", help="只提交不下载")
    g.add_argument("--yes", action="store_true", help="确认会产生费用并执行")
    g.add_argument("--allow-batch", action="store_true",
                   help=f"允许 batch > {MAX_BATCH}（费用按倍增长）")
    g.add_argument("--timeout", type=int, default=600)

    t = act.add_parser("task", help="查询任务状态（需网络）")
    t.add_argument("--task-id", required=True)
    t.add_argument("--yes", action="store_true", help="确认执行网络查询")


def run(args) -> Dict[str, Any]:
    if args.action == "probe":
        return _probe()
    if args.action == "preview":
        return _preview(args)
    if args.action == "generate":
        return _generate(args)
    if args.action == "task":
        return _task(args)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    script = _script()
    key = _api_key()
    req = _has_requests()
    checks = [
        _ck(bool(script), f"vendor 脚本可用（{script or '未找到'}）", "aihive.script"),
        _ck(req, "requests 已安装（pip install requests）", "aihive.deps"),
        _ck(bool(key), f"API Key 已配置（{key or '缺失：AI_HIVE_API_KEY / ~/.ai-hive/config.json'}）",
            "aihive.key"),
    ]
    ready = all(x["ok"] for x in checks)
    return c.result(checks, ok=True,
                    status="ready" if ready else "blocked",
                    verdict="PASS",
                    model=MODEL,
                    script=script,
                    command_hint="python agent.py aihive generate --prompt '...' --yes",
                    next=("配置齐备：可 preview 后 generate（会产生费用）" if ready
                          else "先补齐缺项；缺 Key 时不会联机、不会扣费"))


def _build_cmd(args) -> List[str]:
    script = _script() or _VENDOR_SCRIPT
    cmd = [sys.executable, script, "generate",
           "--prompt", args.prompt,
           "--batch", str(max(1, int(args.batch))),
           "--routing", args.routing]
    if args.image:
        cmd += ["--image", *args.image]
    if args.param:
        cmd += ["--param", *args.param]
    if args.output_dir:
        cmd += ["--output-dir", args.output_dir]
    return cmd


def _preview(args) -> Dict[str, Any]:
    checks = [_ck(bool(args.prompt.strip()), "prompt 非空", "aihive.prompt"),
              _ck(1 <= int(args.batch) <= MAX_BATCH,
                  f"batch 在 1..{MAX_BATCH}（实际 {args.batch}）", "aihive.batch")]
    if args.image:
        missing = [p for p in args.image if not os.path.isfile(p)]
        checks.append(_ck(not missing, f"参考图均存在（缺 {missing or '无'}）", "aihive.image"))
    return c.result(checks,
                    command=" ".join(_build_cmd(args)),
                    model=MODEL,
                    note="按脚本实时价格扣费；确认后加 --yes 执行 generate",
                    next="先跑 preview 核对，再 generate --yes")


def _generate(args) -> Dict[str, Any]:
    script = _script()
    key = _api_key()
    checks = [
        _ck(bool(script), "vendor 脚本可用", "aihive.script"),
        _ck(_has_requests(), "requests 已安装", "aihive.deps"),
        _ck(bool(key), "API Key 已配置", "aihive.key"),
        _ck(bool(args.prompt.strip()), "prompt 非空", "aihive.prompt"),
        _ck(bool(args.yes), "已确认费用（--yes）", "aihive.confirm"),
    ]
    batch = max(1, int(args.batch))
    if batch > MAX_BATCH:
        checks.append(_ck(args.allow_batch,
                          f"batch={batch} > {MAX_BATCH} 需 --allow-batch", "aihive.batch"))
    if args.image:
        missing = [p for p in args.image if not os.path.isfile(p)]
        checks.append(_ck(not missing, f"参考图均存在（缺 {missing or '无'}）", "aihive.image"))

    if not all(x["ok"] for x in checks):
        return c.result(checks, ok=False, verdict="FAIL",
                        status="blocked", model=MODEL,
                        next="补依赖或 Key 后重试；被拦截时未发起任何网络请求")

    cmd = _build_cmd(args) + (["--no-download"] if args.no_download else [])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return c.result(checks, ok=False, verdict="FAIL", status="timeout",
                        next="任务可能已在服务端创建，用 aihive task --task-id <id> 继续查")
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    task_id = None
    m = re.search(r"taskId\s*=\s*(\S+)", out)
    if m:
        task_id = m.group(1)
    files = [ln.strip() for ln in out.splitlines()
             if re.search(r"\.(png|jpe?g|webp)\b", ln, re.I) and os.sep in ln]
    ok = proc.returncode == 0 and (bool(files) or args.no_download)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    status="done" if ok else "error",
                    model=MODEL, task_id=task_id,
                    files=files[:20],
                    returncode=proc.returncode,
                    stdout_tail=out[-1500:],
                    next=("可交给 R08 做落地页素材，或交 R10 继续精修" if ok
                          else "保留 taskId 后查询；失败原因见 stdout_tail"))


def _task(args) -> Dict[str, Any]:
    script = _script()
    checks = [_ck(bool(script), "vendor 脚本可用", "aihive.script"),
              _ck(_has_requests(), "requests 已安装", "aihive.deps"),
              _ck(bool(_api_key()), "API Key 已配置", "aihive.key"),
              _ck(bool(args.yes), "已确认执行（--yes）", "aihive.confirm")]
    if not all(x["ok"] for x in checks):
        return c.result(checks, ok=False, verdict="FAIL", status="blocked")
    proc = subprocess.run([sys.executable, script, "task", "--task-id", args.task_id],
                          capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace")
    return c.result(checks, ok=proc.returncode == 0,
                    verdict="PASS" if proc.returncode == 0 else "FAIL",
                    status="done" if proc.returncode == 0 else "error",
                    task_id=args.task_id,
                    stdout_tail=((proc.stdout or "") + (proc.stderr or ""))[-1500:])
