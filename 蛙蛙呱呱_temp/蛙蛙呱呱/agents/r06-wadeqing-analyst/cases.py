# -*- coding: utf-8 -*-
"""R06 案例库（T8）：case 目录下的可复用「业务语义 + 阈值 + 边界」资产。

对齐 data-analysis-report-agent 的 `cases/<case-id>/` 设计：
    cases/<case-id>/
      case.json             # 案例元信息：id/display_name/description/semantic_layer/data_input/default_question
      semantic_layer.json   # 业务语义层：grain + fields(role/business_name/unit/meaning/quality_rule) + 业务术语 + 分析边界
      experience/
        good_summaries.md   # 好结论范例 + 禁用词替代表
        priority_rules.md   # 结论优先级规则
        thresholds.json     # 业务阈值（critical_low/impact_min_pct 等）

case 是「跨请求可复用」的业务知识，不是硬编码在技能里；`experience/` 是跨 case 的通用
分析与写作规则。harness 会做确定性结构校验，缺关键字段即 FAIL。
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
    """加载案例（case.json + semantic_layer.json + experience 路径）。"""
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
    """案例结构门禁：case.json + semantic_layer.json 确定性校验。"""
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
        grain = sem.get("grain") or {}
        grain_default = grain.get("default")
        checks.append(_chk(True, f"grain.default={grain_default or '(未定义，非必填)'}",
                           "structure", "OK"))
        fields = sem.get("fields") or {}
        names = []
        for fname, f in fields.items():
            role = f.get("role")
            bname = f.get("business_name")
            checks.append(_chk(bool(role), f"字段[{fname}] 有 role", "structure",
                              "HIGH" if not role else "OK", field=fname))
            checks.append(_chk(bool(bname), f"字段[{fname}] 有 business_name", "structure",
                              "HIGH" if not bname else "OK", field=fname))
            if role not in {"dimension", "metric", "attribute"}:
                checks.append(_chk(False, f"字段[{fname}] role 非法 {role!r}",
                                   "structure", "HIGH", field=fname))
            names.append(fname)
        for k in ["business_terms"]:
            checks.append(_chk(k in sem, f"semantic_layer 含 {k}", "structure",
                              "HIGH" if k not in sem else "OK"))

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
    """合并阈值：跨 case 全局阈值 + 指定 case 的业务阈值（case 覆盖同名键）。"""
    base = c.load_thresholds()
    if case_id:
        d = _case_dir(case_id)
        tp = os.path.join(d, "experience", "thresholds.json")
        if os.path.exists(tp):
            case_t = c.load_json(tp)
            # 去掉说明性键，只保留数值业务阈值
            merged = dict(base)
            for k, v in case_t.items():
                if isinstance(v, dict):
                    merged.setdefault(k, {}).update(v)
                elif k not in ("_comment", "desc"):
                    merged[k] = v
            return merged
    return base