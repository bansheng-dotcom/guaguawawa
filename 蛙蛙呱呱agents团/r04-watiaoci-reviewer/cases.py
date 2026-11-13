# -*- coding: utf-8 -*-
"""R04 案例库（T8）：landing-acceptance（落地页交付独立验收）
与 harness-audit（门禁强度审计：STRENGTH-001/007 触发与修复后复评）。

cases.py 提供：list_cases / load_case / validate_case（案例结构门禁）
与 CLI（list / validate）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_CASES_DIR = os.path.join(_HERE, "cases")

_REQUIRED_META = ["case_id", "display_name", "description", "default_question"]
_REQUIRED_SEMANTIC = ["artifact_type", "terms", "gates", "boundary"]
_REQUIRED_EXPERIENCE = ["good_summaries.md", "priority_rules.md", "thresholds.json"]


def cases_dir() -> str:
    return _CASES_DIR


def list_cases() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not os.path.isdir(_CASES_DIR):
        return out
    for name in sorted(os.listdir(_CASES_DIR)):
        if name.startswith(".") or name == "artifact-reject":  # artifact-reject 是草案/SOP文档配套，核心基准包含 harness-audit 和 landing-acceptance
            continue
        meta_path = os.path.join(_CASES_DIR, name, "case.json")
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            continue
        out.append({
            "case_id": meta.get("case_id", name),
            "display_name": meta.get("display_name", name),
            "description": meta.get("description", ""),
            "default_question": meta.get("default_question", ""),
            "dir": name,
        })
    return out



def load_case(case_id: str) -> Dict[str, Any]:
    for row in list_cases():
        if row["case_id"] == case_id or row["dir"] == case_id:
            path = os.path.join(_CASES_DIR, row["dir"])
            with open(os.path.join(path, "case.json"), encoding="utf-8") as f:
                meta = json.load(f)
            with open(os.path.join(path, "semantic_layer.json"), encoding="utf-8") as f:
                semantic = json.load(f)
            out = dict(meta)
            out["case_dir"] = path
            out["semantic_layer"] = semantic
            return out
    raise KeyError(f"案例不存在：{case_id}")


def validate_case(case_id: str) -> Dict[str, Any]:
    errors: List[str] = []
    ok = True
    try:
        case = load_case(case_id)
    except (KeyError, OSError, ValueError) as exc:
        return {"ok": False, "case_id": case_id, "errors": [f"案例不可加载：{exc}"]}
    case_dir = case["case_dir"]
    for k in _REQUIRED_META:
        if not str(case.get(k) or "").strip():
            errors.append(f"case.json 缺必填元信息：{k}")
    semantic = case.get("semantic_layer") or {}
    for k in _REQUIRED_SEMANTIC:
        if k not in semantic or semantic[k] in (None, "", [], {}):
            errors.append(f"semantic_layer.json 缺区段：{k}")
    for fname in _REQUIRED_EXPERIENCE:
        if not os.path.isfile(os.path.join(case_dir, "experience", fname)):
            errors.append(f"experience/ 缺文件：{fname}")
    steps = case.get("steps") or []
    if not steps:
        errors.append("case.json 缺 steps（T8 厚度：步骤+期望+算例数字）")
    for i, st in enumerate(steps):
        if not str(st.get("skill") or "").strip() or not str(st.get("action") or "").strip():
            errors.append(f"steps[{i}] 缺 skill/action")
        if "expect" not in st:
            errors.append(f"steps[{i}] 缺 expect（手工算好的断言数字）")
    if errors:
        ok = False
    return {"ok": ok, "case_id": case.get("case_id", case_id), "errors": errors,
            "steps": len(steps),
            "cartridges": [c.get("name") for c in case.get("cartridges", [])]}


def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R04 案例库")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="列出全部案例")
    vp = sub.add_parser("validate", help="校验案例结构")
    vp.add_argument("case_id")
    args = ap.parse_args()
    if args.cmd == "list":
        print(json.dumps(list_cases(), ensure_ascii=False, indent=2))
        return 0
    v = validate_case(args.case_id)
    print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
