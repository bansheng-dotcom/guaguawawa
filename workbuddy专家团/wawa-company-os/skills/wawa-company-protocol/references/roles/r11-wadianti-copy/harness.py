# -*- coding: utf-8 -*-
"""R11 的确定性验证器层（harness）。

把「内容门禁」做成可独立运行、返回 exit code 的确定性校验。每个 validator 读
输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，`ok=false` 时返回码非 0。
这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py article  --input article.json
    python harness.py probe    --skill localize
    python harness.py plan     --input plan.json
    python harness.py runlog --n 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import _common as c  # noqa: E402
from skills import (s01_topic, s02_seo, s03_hook, s04_copy,  # noqa: E402
                    s05_voice, s06_pr, s07_platform, s08_localize)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "brief": (s01_topic, "_validate_brief"),
    "plan_topic": (s01_topic, "_validate_plan"),
    "keyword": (s02_seo, "_validate_keyword"),
    "audit": (s02_seo, "_validate_audit"),
    "hook": (s03_hook, "_validate_hook"),
    "outline": (s03_hook, "_validate_outline"),
    "article": (s04_copy, "_validate_article"),
    "script": (s04_copy, "_validate_script"),
    "guide": (s05_voice, "_validate_guide"),
    "edit": (s05_voice, "_validate_edit"),
    "ad": (s06_pr, "_validate_ad"),
    "press": (s06_pr, "_validate_press"),
    "adapt": (s07_platform, "_validate_adapt"),
    "publish": (s07_platform, "_validate_publish"),
    "term": (s08_localize, "_validate_term"),
    "review_localize": (s08_localize, "_validate_review"),
}

_PROBE = {"localize": s08_localize._probe}

_GATE_HELP = {
    "brief": "选题卡门禁", "plan_topic": "内容规划门禁",
    "keyword": "关键词表门禁", "audit": "AEO 就绪度审计门禁",
    "hook": "钩子标题门禁", "outline": "提纲立场门禁",
    "article": "文案终稿门禁", "script": "脚本类门禁",
    "guide": "品牌语调指南门禁", "edit": "清洁终稿门禁",
    "ad": "广告文案门禁", "press": "新闻稿门禁",
    "adapt": "多平台改写门禁", "publish": "发布清单门禁",
    "term": "术语表门禁", "review_localize": "审校记录门禁",
}


def _grade(checks) -> str:
    if not checks:
        return "EMPTY"
    if all(x.get("ok") for x in checks):
        return "PASS"
    if any(x.get("sev") == "BLOCKER" and not x.get("ok") for x in checks):
        return "FAIL"
    return "WARN"


def run_validator(cmd: str, path: str, **kw) -> dict:
    if cmd not in _VALIDATORS:
        return {"ok": False, "grade": "FAIL",
                "checks": [{"ok": False, "msg": f"未知门禁 {cmd}", "dim": "existence",
                            "sev": "BLOCKER"}]}
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL", "path": path,
                "checks": [{"ok": False, "msg": f"文件不存在 {path}", "dim": "existence",
                            "sev": "BLOCKER"}]}
    mod, fn = _VALIDATORS[cmd]
    data = c.load_json(path)
    out = getattr(mod, fn)(data, **kw) if kw else getattr(mod, fn)(data)
    checks = out.get("checks", [])
    out["grade"] = _grade(checks)
    out["gate"] = cmd
    return out


def probe(skill: str) -> dict:
    """重依赖能力探测：如实降级（ok=true + status=ready/blocked），不是门禁。"""
    if skill not in _PROBE:
        return {"ok": False, "grade": "FAIL",
                "checks": [{"ok": False, "msg": f"未知探测目标 {skill}",
                            "dim": "existence", "sev": "BLOCKER"}]}
    out = _PROBE[skill]()
    out["gate"] = f"probe:{skill}"
    out["grade"] = "PASS"
    return out


# --------------------------------------------------------------------------- #
# plan：复用 plan_schema.json
# --------------------------------------------------------------------------- #
def validate_plan(path: str) -> dict:
    with open(os.path.join(_HERE, "experience", "plan_schema.json"),
              encoding="utf-8") as f:
        schema = json.load(f)
    data = c.load_json(path)
    checks = []
    for k in schema["required_fields"]:
        checks.append(c.ck(k in data, f"计划含必填字段 {k}", f"plan:{k}",
                           "CRITICAL" if k not in data else "OK"))
    step = data.get("content_step")
    if step not in schema["content_step_enum"]:
        checks.append(c.ck(False,
                           f"content_step={step!r} 不在枚举 {schema['content_step_enum']}",
                           "plan:content_step", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"content_step={step}", "plan:content_step"))
    for key, field in (("deliverables", "deliverables_required"),
                       ("acceptance_criteria", "acceptance_criteria_required"),
                       ("stop_condition", "stop_condition_required")):
        node = data.get(key)
        if isinstance(node, dict):
            missing = [f for f in schema[field] if f not in node]
            if missing:
                checks.append(c.ck(False, f"{key} 缺子字段：{missing}",
                                   f"plan:{key}", "CRITICAL"))
            else:
                checks.append(c.ck(True, f"{key} 子字段齐备", f"plan:{key}"))
        else:
            checks.append(c.ck(False, f"{key} 缺失或非对象", f"plan:{key}", "CRITICAL"))
    ok = all(ch.get("ok") for ch in checks)
    return c.result(checks, ok=ok,
                    grade="PASS" if ok else "FAIL",
                    next="内容计划合规，可执行" if ok else "计划不合规：补齐字段再执行")


# --------------------------------------------------------------------------- #
# runlog
# --------------------------------------------------------------------------- #
def validate_runlog(n: int = 5) -> dict:
    from core import workspace as ws_mod
    w = ws_mod.Workspace(os.path.join(_ROOT, "workspace"))
    rows = w.runlog(int(n))
    return c.result([c.ck(True, f"读取最近 {len(rows)} 条 runlog", "runlog",
                          **{"rows": len(rows)})],
                    ok=True, rows=rows, count=len(rows), grade="PASS",
                    next="runlog 正常")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.py", description="R11 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name, help_txt in _GATE_HELP.items():
        pa = sp.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    pr = sp.add_parser("probe", help="重依赖能力探测（localize）")
    pr.add_argument("--skill", required=True, choices=sorted(_PROBE))
    pl = sp.add_parser("plan", help="内容计划门禁（plan_schema）")
    pl.add_argument("--input", required=True)
    rl = sp.add_parser("runlog", help="读取最近 n 条 runlog")
    rl.add_argument("--n", type=int, default=5)

    args = p.parse_args(argv)
    if args.cmd == "plan":
        out = validate_plan(args.input)
    elif args.cmd == "runlog":
        out = validate_runlog(args.n)
    elif args.cmd == "probe":
        out = probe(args.skill)
    else:
        out = run_validator(args.cmd, args.input)

    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
