# -*- coding: utf-8 -*-
"""S11 产品工作流：discovery / prd / priority / acceptance / briefing /
experience / run / audit。

这是 R07 从「10 个校验模块」升级为「5 条工作流 + 1 个经验门」的入口：
  - 单条工作流先过自己的确定性门禁，产出独立 JSON 包；
  - `run` 一条命令跑指定工作流或全链，产出各包 + workflow_manifest.json；
  - `audit` 只读复核哈希、门禁与交接回链。

角色边界不变：只交产品工件，不写对外报告（报告归 R01）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from . import _common as c
from pm_workflows import common as wc
from pm_workflows import runner
from pm_workflows.runner import FILES, _BUILDERS

NAME = "workflows"
DESC = "产品工作流：discovery/prd/priority/acceptance/briefing/experience/run/audit"
ACTIONS = {
    "discovery": "W1 访谈→job story→机会树→假设→POC",
    "prd": "W2 八段 PRD + 用户故事 + 不在范围 + 红队 premortem",
    "priority": "W3 机会分/RICE/ICE→backlog→路线图→发布说明",
    "acceptance": "W4 Given/When/Then→边界/失败态→测试→发布门禁",
    "briefing": "W5 项目理解→选项/利弊→建议→归档",
    "experience": "G 经验门：L0/L1/L2 + 写回状态机",
    "run": "一条命令跑指定工作流或全链",
    "audit": "只读复核工作流产物",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for name, help_txt in ACTIONS.items():
        if name == "audit":
            au = act.add_parser(name, help=help_txt)
            au.add_argument("--dir", required=True, help="run 输出目录")
            continue
        if name == "run":
            rn = act.add_parser(name, help=help_txt)
            rn.add_argument("--input", required=True, help="工作流束 JSON")
            rn.add_argument("--out-dir", default=None)
            rn.add_argument("--flow", default="all",
                            help="all 或 discovery/prd/... 或逗号分隔")
            rn.add_argument("--html", default=None, help="可选：渲染单文件 HTML")
            rn.add_argument("--html-title", default="R07 产品工作流")
            continue
        pa = act.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
        pa.add_argument("--out-dir", default=None)
        pa.add_argument("--html", default=None)


def _base_dir() -> str:
    try:
        from core.base.workspace import role_workspace
        base = role_workspace(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:  # noqa: BLE001
        base = os.path.join(os.getcwd(), "workspace")
    return base


def _out_dir(args) -> str:
    d = getattr(args, "out_dir", None) or os.path.join(
        _base_dir(), "artifacts", "workflows")
    os.makedirs(d, exist_ok=True)
    return d


def _payload(action: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """单条工作流：输入既可以是裸输入，也可以是 {stage: input} 包络。"""
    if isinstance(data.get(action), dict):
        return data[action]
    return data


def run(args) -> Dict[str, Any]:
    action = getattr(args, "action", None)
    if action == "audit":
        out = runner.audit(args.dir)
        out["artifact_path"] = os.path.join(args.dir, "workflow_manifest.json")
        return out

    if action == "run":
        data = c.load_json(args.input)
        out_dir = _out_dir(args)
        manifest = runner.run(getattr(args, "flow", "all"), data, out_dir,
                              html=getattr(args, "html", None),
                              html_title=getattr(args, "html_title", "R07 产品工作流"))
        g = manifest.get("gate") or {}
        return {
            "ok": bool(manifest.get("ok")),
            "artifact": "workflow_manifest",
            "artifact_path": os.path.join(out_dir, "workflow_manifest.json"),
            "grade": manifest.get("grade"),
            "checks": g.get("checks", []),
            "gate": g,
            "manifest": manifest,
        }

    if action not in _BUILDERS:
        return {"ok": False, "error": f"未知工作流：{action}",
                "checks": [c.check(False, f"未知工作流：{action}", "action")]}

    data = c.load_json(args.input)
    pack = _BUILDERS[action](_payload(action, data))
    out_dir = _out_dir(args)
    path = wc.write_json(os.path.join(out_dir, FILES[action]), pack)
    if getattr(args, "html", None):
        from pm_workflows import render
        render.write_html(args.html, f"R07 {action} 工作流",
                          f"stage={action}", [(FILES[action], pack)])
    return wc.emit_pack(pack, path)
