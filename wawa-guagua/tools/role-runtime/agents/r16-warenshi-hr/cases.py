# -*- coding: utf-8 -*-
"""R16 案例库（T8）：case 目录下的可复用「人事语义 + 门禁 + 边界」资产。

对齐 R07/R08/R10/R11/R12/R13/R14 案例设计，但把语义换到「人事 artifact」：
    cases/<case-id>/
      case.json               # 元信息：case_id/display_name/description/default_question
      semantic_layer.json     # 人事语义：artifact_type + terms + gates + boundary
      experience/
        good_summaries.md     # 好结论范例
        priority_rules.md     # 取舍/优先级规则
        thresholds.json       # 业务阈值

case 是跨请求可复用的人事知识，不硬编码进技能。harness 做确定性结构校验。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from skills import _common as c

_CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")


def _case_dir(case_id: str) -> str:
    return os.path.join(_CASES_DIR, case_id)


def list_cases() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not os.path.isdir(_CASES_DIR):
        return out
    for name in sorted(os.listdir(_CASES_DIR)):
        p = os.path.join(_CASES_DIR, name, "case.json")
        if os.path.exists(p):
            d = c.load_json(p)
            out.append({"case_id": name, "display_name": d.get("display_name", name),
                        "description": d.get("description", ""),
                        "default_question": d.get("default_question", "")})
    return out


def load_case(case_id: str) -> Dict[str, Any]:
    d = _case_dir(case_id)
    case = c.load_json(os.path.join(d, "case.json"))
    sem_path = os.path.join(d, case.get("semantic_layer", "semantic_layer.json"))
    sem = c.load_json(sem_path) if os.path.exists(sem_path) else {}
    exp = os.path.join(d, case.get("experience_dir", "experience"))
    return {
        "case_id": case_id,
        **case,
        "semantic_layer": sem,
        "experience": {
            "good_summaries": os.path.join(exp, "good_summaries.md"),
            "priority_rules": os.path.join(exp, "priority_rules.md"),
            "thresholds": os.path.join(exp, "thresholds.json"),
        },
    }


def _chk(ok: bool, msg: str, dim: str, sev: str = "OK", **ev) -> Dict[str, Any]:
    d = {"ok": ok, "msg": msg, "dim": dim, "sev": sev}
    d.update(ev)
    return d


def validate_case(case_id: str) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    d = _case_dir(case_id)
    if not os.path.isdir(d):
        return {"ok": False, "case_id": case_id, "grade": "FAIL",
                "checks": [_chk(False, f"案例目录不存在 {case_id}", "existence", "CRITICAL")]}

    case = c.load_json(os.path.join(d, "case.json"))
    for k in ["case_id", "display_name", "description", "default_question"]:
        checks.append(_chk(bool(case.get(k)), f"case.json 含 {k}", "structure",
                          "CRITICAL" if not case.get(k) else "OK", field=k))

    sem = c.load_json(os.path.join(d, case.get("semantic_layer", "semantic_layer.json")))
    if not sem:
        checks.append(_chk(False, "semantic_layer.json 缺失或为空", "structure", "CRITICAL"))
    else:
        checks.append(_chk(bool(sem.get("artifact_type")),
                           f"artifact_type={sem.get('artifact_type', '?')}", "structure",
                           "HIGH" if not sem.get("artifact_type") else "OK"))
        terms = sem.get("terms") or []
        checks.append(_chk(isinstance(terms, list) and len(terms) > 0,
                           f"术语表 {len(terms) if isinstance(terms, list) else 0} 条",
                           "structure", "HIGH" if not terms else "OK"))
        gates = sem.get("gates") or []
        checks.append(_chk(isinstance(gates, list) and len(gates) > 0,
                           f"门禁 {len(gates) if isinstance(gates, list) else 0} 条",
                           "structure", "HIGH" if not gates else "OK"))
        boundary = sem.get("boundary") or []
        checks.append(_chk(isinstance(boundary, list) and len(boundary) > 0,
                           f"边界 {len(boundary) if isinstance(boundary, list) else 0} 条",
                           "structure", "HIGH" if not boundary else "OK"))

    exp = os.path.join(d, case.get("experience_dir", "experience"))
    for f in ["good_summaries.md", "priority_rules.md", "thresholds.json"]:
        p = os.path.join(exp, f)
        checks.append(_chk(os.path.exists(p), f"experience/{f} 存在", "structure",
                          "HIGH" if not os.path.exists(p) else "OK"))

    ok = all(x["ok"] for x in checks)
    grade = ("PASS" if ok else
             "FAIL" if any(x["sev"] == "CRITICAL" and not x["ok"] for x in checks)
             else "WARN")
    return {"ok": ok, "case_id": case_id, "grade": grade, "checks": checks}


def resolve_thresholds(case_id: str = None) -> Dict[str, Any]:
    base = c.load_thresholds()
    if case_id:
        d = _case_dir(case_id)
        tp = os.path.join(d, "experience", "thresholds.json")
        if os.path.exists(tp):
            case_t = c.load_json(tp)
            merged = dict(base)
            for k, v in case_t.items():
                if isinstance(v, dict):
                    merged.setdefault(k, {}).update(v)
                elif k not in ("_note", "desc"):
                    merged[k] = v
            return merged
    return base
