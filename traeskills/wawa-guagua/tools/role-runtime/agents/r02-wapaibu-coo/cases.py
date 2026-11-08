# -*- coding: utf-8 -*-
"""R02 案例库（T8）：案例夹具与领域经验包的确定性登记与校验。

目录结构对齐 r06 样板：
  cases/<case_id>/
    case.json                  案例卡
    semantic_layer.json        术语 → 事实表（大写蛇蛇命名）
    experience/good_summaries.md、priority_rules.md、thresholds.json
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from skills import _common as c

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CASES_DIR = os.path.join(_AGENT_DIR, "cases")

_REQUIRED_CASE_FIELDS = ["case_id", "artifact_type", "required_gates",
                         "scope_boundary"]
_REQUIRED_SEMANTIC_FIELDS = ["case_id", "facts", "terms"]
_REQUIRED_XP_FILES = ["good_summaries.md", "priority_rules.md",
                      "thresholds.json"]


def _case_dir(case_id: str) -> str:
    return os.path.join(_CASES_DIR, case_id)


def list_cases() -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not os.path.isdir(_CASES_DIR):
        return out
    for name in sorted(os.listdir(_CASES_DIR)):
        p = os.path.join(_CASES_DIR, name, "case.json")
        if os.path.isfile(p):
            try:
                data = c.load_json(p)
            except (OSError, ValueError):
                data = {"case_id": name, "artifact_type": "",
                        "summary": "案例夹具损坏"}
            out.append({"case_id": data.get("case_id", name),
                        "artifact_type": data.get("artifact_type", ""),
                        "summary": data.get("summary", "")})
    return out


def get_case(case_id: str) -> Dict[str, Any]:
    d = _case_dir(case_id)
    out: Dict[str, Any] = {"case_id": case_id, "exists": os.path.isdir(d)}
    cj = os.path.join(d, "case.json")
    sl = os.path.join(d, "semantic_layer.json")
    if os.path.isfile(cj):
        out["case"] = c.load_json(cj)
    if os.path.isfile(sl):
        out["semantic_layer"] = c.load_json(sl)
    xp_dir = os.path.join(d, "experience")
    if os.path.isdir(xp_dir):
        out["experience_files"] = sorted(os.listdir(xp_dir))
    return out


def validate_case(case_id: str) -> Dict[str, Any]:
    d = _case_dir(case_id)
    checks: List[Dict[str, Any]] = []
    if not os.path.isdir(d):
        return c.result([c.ck(False, f"案例 {case_id} 不存在", "structure",
                              "CRITICAL")], gates=[], terms=[], facts=[],
                        threshold_count=0, next="先建案例目录")
    cj = os.path.join(d, "case.json")
    sl = os.path.join(d, "semantic_layer.json")
    for f, req in ((cj, _REQUIRED_CASE_FIELDS),
                   (sl, _REQUIRED_SEMANTIC_FIELDS)):
        if not os.path.isfile(f):
            checks.append(c.ck(False, f"缺 {os.path.basename(f)}", "files",
                               "CRITICAL"))
            continue
        data = c.load_json(f)
        for k in req:
            checks.append(c.ck(k in data,
                               f"{os.path.basename(f)}.{k}", "fields",
                               "CRITICAL" if k not in data else "OK"))
    case = c.load_json(cj) if os.path.isfile(cj) else {}
    sem = c.load_json(sl) if os.path.isfile(sl) else {}
    for g in case.get("required_gates", []):
        if not str(g).strip():
            checks.append(c.ck(False, "required_gates 存在空门禁", "gates",
                               "CRITICAL"))
    terms = list(sem.get("terms", {}).keys()) if isinstance(sem.get("terms"),
                                                            dict) else []
    checks.append(c.ck(len(terms) >= 1, f"术语 {len(terms)} 个", "terms",
                       "HIGH" if len(terms) < 1 else "OK"))
    xp_dir = os.path.join(d, "experience")
    for f in _REQUIRED_XP_FILES:
        checks.append(c.ck(os.path.isfile(os.path.join(xp_dir, f)),
                           f"experience/{f}", "experience", "HIGH"))
    th_file = os.path.join(xp_dir, "thresholds.json")
    threshold_count = 0
    if os.path.isfile(th_file):
        try:
            xp = json.load(open(th_file, encoding="utf-8"))
            threshold_count = len(xp)
            checks.append(c.ck(threshold_count >= 1,
                               f"经验包阈值 {threshold_count} 条", "thresholds",
                               "HIGH" if threshold_count < 1 else "OK"))
        except (OSError, ValueError):
            checks.append(c.ck(False, "experience/thresholds.json 损坏",
                               "thresholds", "HIGH"))
    return c.result(checks, gates=case.get("required_gates", []), terms=terms,
                    facts=list(sem.get("facts", {}).keys())
                    if isinstance(sem.get("facts"), dict) else [],
                    threshold_count=threshold_count,
                    next="案例包齐套后挂进技能经验增强")
