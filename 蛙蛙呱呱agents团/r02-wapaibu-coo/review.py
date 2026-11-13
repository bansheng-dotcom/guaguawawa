# -*- coding: utf-8 -*-
"""R02 对抗性评审（T7）：五个确定性挑战，砍空话、砍无主之责、砍无授权建议。

挑战清单（R02 视角）：
  1. contract         输出违背已注册契约 → 契约违规（BLOCKER，回 writer）
  2. ownership_gate   委派/交接/行动项里出现无主之责（owner 缺失）→ BLOCKER，
                      回 writer 补责任人
  3. vague_gate       空话黑词（尽快/持续关注/后续跟进…）→ BLOCKER，回 writer
  4. advice_gate      无授权的建议/应当/必须 → BLOCKER，回 writer 要授权
  5. value_utility    无任何量化事实 → FAIL，回 writer 补数据
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import contracts
from skills import _common as c

CATEGORY_TO_ROUTE = {
    "contract_violation": "writer",
    "missing_owner_or_due": "writer",
    "vague_expression": "writer",
    "unauthorized_advice": "writer",
    "no_quantitative_value": "writer",
}

_SKIP_KEYS = {"checks", "sha", "fingerprint", "package_id"}


def _walk_strings(obj: Any, path: str = "$",
                  skip: bool = False) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    if skip:
        return out
    if isinstance(obj, str):
        out.append((path, obj))
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            out.extend(_walk_strings(x, f"{path}[{i}]"))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_walk_strings(v, f"{path}.{k}", k in _SKIP_KEYS))
    return out


def _has_owner_bearer(obj: Any) -> bool:
    """是否含 owner 承载结构（packages/action_items/subtasks 等）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("packages", "action_items", "subtasks", "schedule_items") \
                    and isinstance(v, list) and v:
                return True
            if _has_owner_bearer(v):
                return True
    elif isinstance(obj, list):
        for x in obj:
            if _has_owner_bearer(x):
                return True
    return False


def _missing_owner(obj: Any, path: str = "$") -> List[str]:
    out: List[str] = []
    if isinstance(obj, dict):
        th = c.load_thresholds()["review"]
        for k in th["owner_fields"]:
            v = obj.get(k)
            if v is not None and (isinstance(v, str) and not v.strip()):
                out.append(f"{path}.{k} 为空")
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out.extend(_missing_owner(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            out.extend(_missing_owner(x, f"{path}[{i}]"))
    return out


def _has_quant(result: Dict[str, Any]) -> bool:
    found = False

    def scan(x: Any, skip: bool) -> None:
        nonlocal found
        if found or skip:
            return
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            if float(x) not in (0.0, 1.0):
                found = True
        elif isinstance(x, str):
            if any(ch.isdigit() for ch in x):
                found = True
        elif isinstance(x, list):
            for e in x:
                scan(e, skip)
        elif isinstance(x, dict):
            for k, v in x.items():
                scan(v, k in _SKIP_KEYS)

    scan(result, False)
    return found


def review_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    """packet = {skill, action, input, result, advice_authorized?}"""
    skill = packet.get("skill", "")
    action = packet.get("action", "")
    result = packet.get("result", {}) or {}
    th = c.load_thresholds()["review"]
    issues: List[Dict[str, Any]] = []

    # 挑战 1：契约
    if skill in contracts.CONTRACTS and action in contracts.CONTRACTS[skill]:
        errs = contracts.validate_output(skill, action, result)
        if errs:
            issues.append({"challenge": "contract", "category": "contract_violation",
                           "severity": "BLOCKER",
                           "detail": "；".join(errs[:3]) + (f"（共 {len(errs)} 处）"
                                                            if len(errs) > 3 else "")})
    # 挑战 2：无主之责
    if _has_owner_bearer(result):
        missing = _missing_owner(result)
        if missing:
            issues.append({"challenge": "ownership_gate",
                           "category": "missing_owner_or_due",
                           "severity": "BLOCKER",
                           "detail": "委派/行动项存在无主之责：" + "；".join(missing[:3])})
    # 挑战 3：空话黑词
    vague_hits = [f"{p}:「{v[:20]}」" for p, v in _walk_strings(result)
                  if c.has_any(v, th["vague_words"])]
    if vague_hits:
        issues.append({"challenge": "vague_gate", "category": "vague_expression",
                       "severity": "BLOCKER",
                       "detail": "空话黑词：" + "；".join(vague_hits[:3])})
    # 挑战 4：无授权建议
    if not packet.get("advice_authorized"):
        advice_hits = [f"{p}" for p, v in _walk_strings(result)
                       if str(v).strip().startswith(tuple(th["advice_words"]))]
        if advice_hits:
            issues.append({"challenge": "advice_gate",
                           "category": "unauthorized_advice", "severity": "BLOCKER",
                           "detail": "未经授权的建议措辞（需 advice_authorized）：" +
                                     "；".join(advice_hits[:3])})
    # 挑战 5：量化价值
    if not _has_quant(result):
        issues.append({"challenge": "value_utility",
                       "category": "no_quantitative_value", "severity": "HIGH",
                       "detail": "产出无任何量化事实（COO 产出必须带数字）"})

    blocker = [i for i in issues if i["severity"] in ("BLOCKER", "CRITICAL")]
    verdict = "FAIL" if issues else "PASS"
    if issues and not blocker:
        verdict = "FAIL"  # HIGH 也回炉：R02 产出必须过全部挑战
    out: Dict[str, Any] = {
        "skill": skill, "action": action, "issues": issues, "verdict": verdict,
        "issues_count": len(issues),
    }
    if verdict == "FAIL":
        cat = issues[0]["category"]
        out["category"] = cat
        out["route"] = CATEGORY_TO_ROUTE.get(cat, "writer")
        out["challenge"] = issues[0]["challenge"]
    return out
