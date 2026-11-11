# -*- coding: utf-8 -*-
"""一人公司 · 角色运行时公共层（Role Runtime）。

给 R01~R20 的 `agent.py` 提供三件公共能力，避免 20 份重复实现（META-001 反模式 #8）：

1. `bootstrap()`   —— 把仓库根 / agents 根注入 sys.path，修掉「异构 cwd 下
                      `ModuleNotFoundError: No module named 'agents'`」这类历史故障。
2. `emit(...)`     —— 与旧 `core.report_bridge.emit` **签名兼容**的报告出口，
                      内部改走《DSH-SOP-REP-001》商业决策报告引擎
                      （五段式 + 三级归因 + 护栏熔断 + 阶梯灰度）。
3. `log_event(...)` —— 结构化运行日志，按角色分文件落盘到
                      `agents/workspace/logs/<role>.jsonl`，替代 print 当日志。

设计纪律：
    - 报告失败**不静默**：写 `REPORT_FAILED.md` 说明失败原因与堆栈摘要，
      并返回 ERROR 日志，绝不假装产出成功。
    - 报告内容全部来自本次 result，不注入任何演示数字。
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
_REPO = os.path.dirname(_AGENTS)

from core.workspace import default_root  # noqa: E402

LOG_DIR = os.path.join(default_root(), "logs")


def bootstrap() -> None:
    """把仓库根与 agents 根加入 sys.path（幂等）。"""
    for p in (_REPO, _AGENTS):
        if p not in sys.path:
            sys.path.insert(0, p)


bootstrap()

from agents.shared.report_engine import emit_role_report  # noqa: E402
from core import protocol  # noqa: E402


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
# 报告出口（签名兼容 core.report_bridge.emit）
# --------------------------------------------------------------------------- #
def emit(role: str, name: str, title: str, result: Dict[str, Any],
         skill: str, action: str, intent: str, out_dir: str,
         md_name: str, html_name: Optional[str] = None,
         input_path: Optional[str] = None,
         report_slug: Optional[str] = None,
         **legacy: Any) -> List[Any]:
    """把一次技能真实运行结果，渲染成 REP-001 双格式报告，返回 Port 列表。

    :param role: 角色 id（r01..r20）
    :param name: 角色名（蛙全局…），仅用于日志
    :param title: 角色职称，仅用于日志
    :param result: 技能 run() 的原始返回（必须是真实执行结果）
    :param skill/action: 本次技能与动作，用于报告标题与可复现命令
    :param intent: 任务意图，进报告标题
    :param out_dir: 产物目录
    :param md_name: 产物前缀（如 coo_report → coo_report.md / .html）
    :param html_name: 兼容旧签名，忽略（HTML 名与 md_name 同名）
    :param input_path: 本次输入文件绝对路径，用于计算 SHA256 供复算
    :param legacy: 兼容旧调用（specialist/chart_dir/data/doc_type/pdf 等），忽略
    :return: [Port(.md), Port(.html)]
    """
    os.makedirs(out_dir, exist_ok=True)
    slug = report_slug or md_name
    payload = {
        "skill": skill, "action": action, "ok": bool(result.get("ok")),
        "out_dir": out_dir, "md_name": md_name,
        "ignored_legacy": sorted(legacy) if legacy else [],
    }
    try:
        files = emit_role_report(role, result, skill, action, intent, out_dir,
                                 input_path=input_path, report_slug=slug)
        payload.update({"html": os.path.basename(files["html"]),
                        "md": os.path.basename(files["md"])})
        log_event(role, "report_emitted", payload)
        return [
            protocol.Port(md_name + ".md", "report", "text/markdown"),
            protocol.Port(md_name + ".html", "report", "text/html"),
        ]
    except Exception as exc:  # noqa: BLE001  报告失败必须可见，不得静默
        tb = traceback.format_exc()
        fail_md = os.path.join(out_dir, "REPORT_FAILED.md")
        with open(fail_md, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                f"# 报告出具失败 · {role.upper()} {name}\n\n"
                f"- 技能：`{skill}/{action}`\n"
                f"- 意图：{intent}\n"
                f"- 异常：`{type(exc).__name__}: {exc}`\n\n"
                "## 说明\n\n"
                "本次技能已真实执行，但报告渲染未通过 REP-001 门禁。"
                "请按下方堆栈修复后重跑，禁止把本文件当作交付物。\n\n"
                f"```\n{tb}\n```\n")
        payload.update({"error": f"{type(exc).__name__}: {exc}"})
        log_event(role, "report_failed", payload, level="ERROR")
        return [protocol.Port("REPORT_FAILED.md", "report", "text/markdown")]


# --------------------------------------------------------------------------- #
# 一次技能执行 + 报告的便捷封装（供新增角色与回归脚本使用）
# --------------------------------------------------------------------------- #
def run_and_report(role: str, name: str, title: str, skill: str, action: str,
                   intent: str, out_dir: str, run_callable,
                   input_path: Optional[str] = None,
                   md_name: Optional[str] = None) -> Dict[str, Any]:
    """执行 run_callable() 拿到 result，落 result.json + 双格式报告并返回结果。"""
    result = run_callable()
    if not isinstance(result, dict):
        result = {"ok": True, "value": result}
    result.setdefault("skill", skill)
    result.setdefault("action", action)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{skill}.json"), "w",
              encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    emit(role=role, name=name, title=title, result=result, skill=skill,
         action=action, intent=intent, out_dir=out_dir,
         md_name=md_name or f"{role}_report", input_path=input_path)
    return result


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
  python agent.py test                 # 跑本角色 tests/（pytest 绝对路径）
  python agent.py logs [--n 5]         # 查看本角色最近运行日志
"""


def handle_meta_command(argv: List[str], role: str) -> Optional[int]:
    """在角色 CLI 解析前拦截统一元命令；不匹配则返回 None 交回原 CLI。"""
    if not argv:
        return None
    cmd = argv[0]
    if cmd not in ("report", "test", "logs"):
        return None

    from agents.shared.role_profiles import get as get_profile
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

    out_dir = os.path.join(default_root(), "reports", role,
                           f"{skill}-{action}")
    res = run_and_report(role=role, name=profile["name"],
                         title=profile["title"], skill=skill, action=action,
                         intent=intent, out_dir=out_dir,
                         run_callable=lambda: result, input_path=input_path,
                         md_name="report")
    print(json.dumps({
        "ok": bool(res.get("ok")), "role": role, "skill": skill, "action": action,
        "verdict": res.get("verdict"), "checks": len(res.get("checks") or []),
        "report_html": os.path.join(out_dir, "report.html"),
        "report_md": os.path.join(out_dir, "report.md"),
    }, ensure_ascii=False))
    return 0 if res.get("ok") else 1


__all__ = ["bootstrap", "emit", "log_event", "run_and_report",
           "handle_meta_command", "LOG_DIR"]
