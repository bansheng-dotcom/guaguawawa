# -*- coding: utf-8 -*-
"""R10 的确定性验证器层（harness）。

把「视觉设计门禁」做成可独立运行、返回 exit code 的确定性校验。
每个 validator 读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，
`ok=false` 时返回码非 0。这是 R04 蛙挑刺做硬门禁复核的可调用入口。

除 16 个设计门禁外，另含 plan（复用 plan_schema.json）与 runlog。

用法：
    python harness.py logo       --input logo.json
    python harness.py probe      --skill imaging
    python harness.py verify     --logo logo.json --vi vi.json
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
from skills import (s01_imagegen, s02_logo, s03_uiux, s04_brand,  # noqa: E402
                    s05_motion, s06_imaging, s07_media, s08_transcribe,
                    s09_render)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "prompt": (s01_imagegen, "_validate_prompt"),
    "style": (s01_imagegen, "_validate_style"),
    "logo": (s02_logo, "_validate_logo"),
    "favicon": (s02_logo, "_validate_favicon"),
    "screen": (s03_uiux, "_validate_screen"),
    "ux": (s03_uiux, "_validate_ux"),
    "vi": (s04_brand, "_validate_vi"),
    "token": (s04_brand, "_validate_token"),
    "motion": (s05_motion, "_validate_motion"),
    "prototype": (s05_motion, "_validate_prototype"),
    "edit": (s06_imaging, "_validate_edit"),
    "media": (s07_media, "_validate_media"),
    "transcribe": (s08_transcribe, "_validate_transcribe"),
    "poster": (s09_render, "_validate_poster"),
}

_PROBE = {"imaging": s06_imaging._probe,
          "media": s07_media._probe,
          "transcribe": s08_transcribe._probe}

_GATE_HELP = {
    "prompt": "生图提示词门禁", "style": "风格探索门禁",
    "logo": "Logo 设计门禁", "favicon": "图标变体门禁",
    "screen": "屏幕设计门禁", "ux": "可用性评估门禁",
    "vi": "品牌视觉身份门禁", "token": "设计令牌门禁",
    "motion": "动效规格门禁", "prototype": "交互原型门禁",
    "edit": "图像工程任务单门禁", "media": "媒体处理任务单门禁",
    "transcribe": "转写任务单门禁", "poster": "宣传图契约门禁",
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


def verify(logo: str = None, vi: str = None) -> dict:
    parts = {}
    if logo:
        parts["logo"] = run_validator("logo", logo)
    if vi:
        parts["vi"] = run_validator("vi", vi)
    ok = all(v["ok"] for v in parts.values()) if parts else False
    return {"ok": ok, "parts": parts, "verdict": "PASS" if ok else "FAIL"}


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
    step = data.get("design_step")
    if step not in schema["design_step_enum"]:
        checks.append(c.ck(False,
                           f"design_step={step!r} 不在枚举 {schema['design_step_enum']}",
                           "plan:design_step", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"design_step={step}", "plan:design_step"))
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
                    next="设计计划合规，可执行" if ok else "计划不合规：补齐字段再执行")


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
    p = argparse.ArgumentParser(prog="harness.py", description="R10 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name, help_txt in _GATE_HELP.items():
        pa = sp.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    pr = sp.add_parser("probe", help="重依赖能力探测（imaging/media/transcribe）")
    pr.add_argument("--skill", required=True, choices=sorted(_PROBE))
    v = sp.add_parser("verify", help="综合门禁（logo+vi）")
    v.add_argument("--logo", default=None)
    v.add_argument("--vi", default=None)
    pl = sp.add_parser("plan", help="设计计划门禁（plan_schema）")
    pl.add_argument("--input", required=True)
    rl = sp.add_parser("runlog", help="读取最近 n 条 runlog")
    rl.add_argument("--n", type=int, default=5)

    args = p.parse_args(argv)
    if args.cmd == "verify":
        out = verify(args.logo, args.vi)
    elif args.cmd == "plan":
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
