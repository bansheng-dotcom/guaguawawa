# -*- coding: utf-8 -*-
"""T7 对抗评审：确定性 adversarial reviewer。

对齐 data-analysis-report-agent 的 report-text-adversarial-reviewer：
独立语境（不继承生成逻辑/隐藏推理）、低温（确定性等价最小温度）、
只收 bounded unit_packet + 契约 + 校验链，不收完整 material pack，
返回 verdict + checks + issue list + 三个 route-back 类别之一。

三个失败类别（route-back）：
  evidence_does_not_support_conclusion -> react   （回去重算/补证据）
  expression_title_or_line_fit         -> writer  （回去改写/删建议）
  no_report_value                      -> controller（丢弃该产出单元）

这是「对抗性」的关键：不给生成过程写解释性判断，只做可复现的确定性挑战。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple

from skills import _common as c

# 结论可能所在的文本键（这些字段里的内容会被当作「读者可见结论」挑刺）
_CONCLUSION_KEYS = ("conclusion", "verdict", "decision", "note", "summary",
                    "insight", "text", "recommendation", "advice", "finding",
                    "reason", "result_note", "message", "answer")

# 因果动词：结论里点名「驱动/原因」就必须有 decompose/attribution 证据
_CAUSAL_RE = re.compile(
    r"导致|造成|引起|主因|驱动|因为|归因|源于|拉低|推高|贡献了|使.{0,6}(下降|上升|下滑|增长)"
    r"|\btrigger\b|\bcause\b|\bdrive\b"
)
# 归因分解证据键：必须是「拆解/贡献」的结构化证据，而非 total_change/dimension 这类总量字段。
# 否则「只知道总量变化、没拆出贡献」也会被误判为有归因。
_DECOMPOSE_KEYS = ("segments", "contribution", "contribution_pct", "items",
                   "drilldown", "root_cause", "driver", "attribute")

# 未授权建议触发词（决策建议默认禁止，除非显式 advice_authorized）
_ADVICE_RE = re.compile(r"建议|应该|应当|须尽快|must|should|建议你")

# 禁用词 / 例证辞（对齐 harness.BANNED_WORDS + good_summaries 替代表）
_BANNED = ["需要关注", "很可能", "可能存在问题", "整体趋势良好", "后续需要跟进",
           "有待进一步分析", "这一现象值得重视", "可能吧", "大概也许", "差不多就行", "TODO"]

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _flatten_nums(obj: Any) -> List[float]:
    """递归收集一个对象里所有数值（含嵌套），用于「数值可追溯」校验。"""
    out: List[float] = []
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _flatten_nums(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _flatten_nums(v)
    return out


def _conclusion_texts(obj: Any) -> List[str]:
    """收集「读者可见结论」文本：优先 _CONCLUSION_KEYS，退而求其次所有字符串。"""
    texts = _walk_strings(obj)
    keyed = [str(obj.get(k)) for k in _CONCLUSION_KEYS
             if isinstance(obj, dict) and isinstance(obj.get(k), str)]
    return keyed or texts


def _walk_strings(obj: Any) -> List[str]:
    out: List[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _walk_strings(v)
    return out


# 元说明字段：note/msg/message 里常写「算法阈值/公式说明」（如 "≥0.6"、"×1.4826"），
# 这些不是「从数据里引用却无法追溯」的结论指标，证据边界检查必须排除它们。
_NON_EVIDENCE_KEYS = ("note", "msg", "message", "runtime_ms", "note_text", "hint")


def _evidence_texts(obj: Any) -> List[str]:
    """证据边界检查用的读者可见文本：排除元说明字段，只挑真正的结论/数字引用。"""
    out: List[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in _NON_EVIDENCE_KEYS:
                continue
            out += _evidence_texts(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _evidence_texts(v)
    return out


def _referenced_decimals(texts: List[str]) -> List[float]:
    """结论文本里出现的带小数点的数值（视为「引用过的具体指标」，需可追溯）。"""
    nums: List[float] = []
    for t in texts:
        for m in _NUM_RE.findall(t):
            if "." in m:
                nums.append(float(m))
    return nums


def review_packet(packet: Dict[str, Any],
                  check_value_utility: bool = True) -> Dict[str, Any]:
    """对一个 bounded unit_packet 做确定性对抗评审。

    packet = {run_id, skill, action, question?, result, data_ref?, semantic?,
              contract_checked?}
    check_value_utility=False 用于「元信息/指南类」动作（guide/list/backend），
    其产出是选型提示词而非数据分析结果，不做「量化事实」价值判断。
    """
    run_id = packet.get("run_id", "")
    skill = packet.get("skill", "")
    action = packet.get("action", "")
    result = packet.get("result", {}) or {}
    data_ref = packet.get("data_ref")

    checks: List[Dict[str, Any]] = []
    issues: List[str] = []

    # 1) 契约符合（T6）
    contracted = True
    if skill and action:
        try:
            import contracts
            r = contracts.validate_output(skill, action, result)
            contracted = r["ok"]
            if not contracted:
                issues += [f"契约不符: {', '.join(r['errors'][:5])}"]
        except Exception:
            contracted = True  # 无契约登记的动作不在此门禁
    checks.append(_ck(contracted, "契约符合（JSON Schema）", "contract"))

    # 2) 证据边界：引用的小数指标必须可追溯到 result 或 data（排除 note 元说明）
    texts = _conclusion_texts(result)
    evidence_texts = _evidence_texts(result)
    result_nums = [round(x, 4) for x in _flatten_nums(result)]
    data_nums: List[float] = []
    if data_ref and os.path.exists(data_ref):
        try:
            data_nums = [round(x, 4) for x in _flatten_nums(c.load_csv(data_ref))]
        except Exception:
            data_nums = []
    traceable = set(result_nums + data_nums)
    untraceable = [d for d in _referenced_decimals(evidence_texts)
                   if round(d, 4) not in traceable]
    if untraceable:
        issues.append(f"结论引用 {len(untraceable)} 个无法追溯的小数: "
                      f"{sorted(set(untraceable))[:8]}")
    checks.append(_ck(not untraceable, "结论数值可追溯（不超过数据边界）", "evidence_boundary"))

    # 3) 因果升级：点名驱动必须有归因分解证据
    has_causal = any(_CAUSAL_RE.search(t) for t in texts)
    has_decomp = any(k in result for k in _DECOMPOSE_KEYS)
    if has_causal and not has_decomp:
        issues.append("结论点名因果驱动，但没有 decompose/attribution 证据")
    checks.append(_ck(not (has_causal and not has_decomp),
                      "驱动声明有归因分解支撑", "driver_decomposition"))

    # 4) 建议授权：决策建议默认禁止
    has_advice_word = any(_ADVICE_RE.search(t) for t in texts)
    authorized = bool(result.get("advice_authorized")) or \
                 packet.get("advice_authorized")
    if has_advice_word and not authorized:
        issues.append("含决策建议但未授权（advice_authorized 缺失）")
    checks.append(_ck(not (has_advice_word and not authorized),
                      "决策建议已授权", "advice_gate"))

    # 5) 禁用词
    hits = [b for t in texts for b in _BANNED if b in t]
    if hits:
        issues.append(f"禁用语: {sorted(set(hits))}")
    checks.append(_ck(not hits, "无禁用词/例证辞", "banned_words"))

    # 6) 报告价值：至少一个非平凡量化事实（元信息类动作豁免）
    #    「诚实阻断/降级」产出（status=blocked/degraded）不是装饰：它正确报告了
    #    「做不到」，本身即有价值，故豁免量化事实要求（与元信息类动作同）。
    blocked = str(result.get("status", "")).lower() in ("blocked", "degraded", "scaffold")
    if check_value_utility and not blocked:
        nums = [x for x in _flatten_nums(result) if abs(x) > 0]
        has_value = bool(nums) and len(result) > 1
        if not has_value:
            issues.append("无量化事实，疑似装饰性产出")
        checks.append(_ck(has_value, "有报告价值（非装饰）", "value_utility"))
    else:
        checks.append(_ck(True, "元信息/诚实阻断类产出，量化价值豁免", "value_utility"))

    ok = all(x["ok"] for x in checks)
    # 失败类别 → route-back
    category = ""
    if not ok:
        for name in ("evidence_boundary", "driver_decomposition"):
            if not next((x for x in checks if x["check"] == name))["ok"]:
                category = "evidence_does_not_support_conclusion"
                break
        if not category:
            if not next(x for x in checks if x["check"] == "value_utility")["ok"]:
                category = "no_report_value"
            else:
                category = "expression_title_or_line_fit"

    return {
        "run_id": run_id,
        "manifest": f"{skill}/{action}",
        "execution_temperature": 0.0,
        "context_isolation": {
            "sees_full_material_pack": False,
            "sees_writer_hidden_reasoning": False,
            "input_scope": ["unit_packet", "contract", "data_ref"],
        },
        "verdict": "PASS" if ok else "FAIL",
        "failure_category": category or None,
        "checks": checks,
        "issues": issues,
    }


def _ck(ok: bool, msg: str, name: str) -> Dict[str, Any]:
    return {"ok": ok, "check": name, "msg": msg, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser("review", help="对抗评审：对技能产出做确定性挑战")
    p.add_argument("--result", required=True, help="待评审的技能产出 JSON")
    p.add_argument("--skill", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--data", default=None, help="数据 CSV（用于数值可追溯校验）")
    p.add_argument("--run-id", default="")


def run(args) -> Dict[str, Any]:
    result = c.load_json(args.result)
    packet = {"run_id": args.run_id, "skill": args.skill, "action": args.action,
              "result": result, "data_ref": args.data}
    review = review_packet(packet)
    review["exit_code"] = 0 if review["verdict"] == "PASS" else 1
    return review