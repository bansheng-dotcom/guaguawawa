# -*- coding: utf-8 -*-
"""R02 harness 确定性验证器（S4）：21 个动作全量可跑，加 verify 综合门禁。

标准：跑 PASS 退出码 0；跑 FAIL 退出码 1（供外部系统确权消费）。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from skills import _common as c
from skills import (s01_schedule, s02_capacity, s03_handoff, s04_retro,
                   s05_process, s06_knowledge, s07_portfolio)

_VALIDATORS: Dict[str, Tuple[str, str, Callable[[Any], Dict[str, Any]]]] = {
    "wbs": ("schedule", "WBS 结构门禁", s01_schedule._wbs),
    "sprint": ("schedule", "冲刺排期", s01_schedule._sprint),
    "critpath": ("schedule", "关键路径", s01_schedule._critpath),
    "check": ("capacity", "容量负载", s02_capacity._check),
    "delegate": ("capacity", "派工包", s02_capacity._delegate),
    "split": ("capacity", "超大任务拆分", s02_capacity._split),
    "package": ("handoff", "交接包", s03_handoff._package),
    "accept": ("handoff", "验收", s03_handoff._accept),
    "trace": ("handoff", "审计轨迹", s03_handoff._trace),
    "postmortem": ("retro", "事故复盘", s04_retro._postmortem),
    "grade": ("retro", "复盘打分", s04_retro._grade),
    "action": ("retro", "行动项闭环", s04_retro._action),
    "sop": ("process", "SOP 门禁", s05_process._sop),
    "waste": ("process", "流程浪费", s05_process._waste),
    "meeting": ("process", "会议门禁", s05_process._meeting),
    "digest": ("knowledge", "技能化门禁", s06_knowledge._digest),
    "entry": ("knowledge", "知识条目", s06_knowledge._entry),
    "search": ("knowledge", "知识检索", s06_knowledge._search),
    "status": ("portfolio", "项目群状态", s07_portfolio._status),
    "plan": ("portfolio", "执行编排", s07_portfolio._plan),
    "graph": ("portfolio", "图谱门禁", s07_portfolio._graph),
}


def run_validator(name: str, path: str) -> Dict[str, Any]:
    entry = _VALIDATORS.get(name)
    if entry is None:
        return {"ok": False, "error": f"未知验证器 {name}"}
    skill, usage, fn = entry
    try:
        data = c.load_json(path)
    except (OSError, ValueError) as e:
        return {"ok": False, "error": f"加载 {path} 失败：{e}"}
    result = fn(data)
    bad = [x for x in result.get("checks", [])
           if not x.get("ok") and x.get("sev") in ("CRITICAL", "BLOCKER", "HIGH")]
    out = {"ok": bool(result.get("ok")),
           "skill": skill,
           "usage": usage,
           "pass_count": len([x for x in result.get("checks", []) if x.get("ok")]),
           "fail_count": len([x for x in result.get("checks", []) if not x.get("ok")])}
    if bad:
        out["violations"] = [f"{x['dim']}: {x['msg']}" for x in bad[:3]]
    out["harness_result"] = result
    return out


def verify(data: Any) -> Dict[str, Any]:
    """综合验证：给定 work_breakdown + team，串起 WBS→排期→容量全链门禁。"""
    checks: list = []
    th = c.load_thresholds()["schedule"]
    checks.extend(s01_schedule._validate_items(data.get("work_breakdown", []),
                                               th))
    spr = s01_schedule._sprint(data)
    checks.extend(spr.get("checks", []))
    cap = s02_capacity._check({"team": data.get("team", [])})
    checks.extend(cap.get("checks", []))
    ok = all(x.get("ok") for x in checks)
    return {"ok": ok, "checks": checks, "sprint_end": spr.get("end_date", ""),
            "overloaded": cap.get("overloaded", []),
            "next": "全链通过后冻结排期"}


# --------------------------------------------------------------------------- #
# CLI（2026-11 补）：此前本文件是纯库，无 __main__，
# `python harness.py package --input x` 什么也不做且退出码 0 —— 典型的假绿：
# 一个不执行的脚本和一个通过的门禁，退出码是一样的。
# 现在补上 CLI 与非 0 退出码，与其余 18 个角色一致。
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(
        prog="r02-harness",
        description="R02 确定性验证器 CLI：跑单个门禁或综合 verify。"
                    "退出码 0=通过 / 1=不通过 / 2=输入或环境问题。",
        epilog="示例：python harness.py package --input examples/handoff.json",
    )
    ap.add_argument("action", choices=sorted(_VALIDATORS) + ["verify"],
                    help="门禁名（与 agent.py harness 一致）")
    ap.add_argument("--input", required=True, help="输入 JSON 路径")
    ap.add_argument("--json", action="store_true", help="只输出 JSON（不打印摘要）")
    args = ap.parse_args(argv)

    if not hasattr(sys.stdout, "reconfigure"):
        pass
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if args.action == "verify":
        try:
            data = c.load_json(args.input)
        except (OSError, ValueError) as e:
            print(f'{{"ok": false, "error": "加载 {args.input} 失败：{e}"}}')
            return 2
        out = verify(data)
    else:
        out = run_validator(args.action, args.input)

    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        # 与其它角色一致：单行 __AGENT_RESULT__ + 人读摘要
        print("__AGENT_RESULT__ " + json.dumps(out, ensure_ascii=False))
        if out.get("error"):
            print(f"[harness] {args.action}: ERROR {out['error']}")
            return 2
        bad = out.get("violations") or []
        print(f"[harness] {args.action}: ok={out.get('ok')} "
              f"pass={out.get('pass_count')} fail={out.get('fail_count')}")
        for v in bad:
            print(f"  - {v}")
    if out.get("error"):
        return 2
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(_cli())
