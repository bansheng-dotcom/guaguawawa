# -*- coding: utf-8 -*-
"""S01 产品发现与 JTBD：jobstory / discover / interview 三条真实门禁。

设计原则（对齐 L01 工具实体层「真实手脚」）：
- 每个判据都是确定性可复算的，不接受「只要字段存在就算过」；
- 失败项一律落为 sev=BLOCKER 的结构化 checks，供 harness/报告/SARIF 消费；
- 阈值统一来自 experience/thresholds.json（T9 外置），不在代码里写死业务口径。
"""
from __future__ import annotations

from typing import Any, Dict

from ._common import check, is_blank, load_thresholds, make_result

NAME = "discover"
DESC = "产品发现、JTBD 与用户访谈验证"
ACTIONS = {"jobstory": "校验 Job story（情境/动机/期望结果三段式）",
           "discover": "校验发现计划（问题/人群/时机/假设/验证）",
           "interview": "校验访谈脚本（时间盒/Mom Test/记录字段）"}

# 四段式访谈时间盒：开场 / 暖场 / 核心 / 收尾
_INTERVIEW_BANDS = ("opening", "warmup", "core", "wrapup")
_MOM_TEST_RULES = ("no_pitching", "listen_ratio_80_20", "ask_why_deep")
_NOTE_FIELDS_MIN = 4


def _validate_jobstory(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Job story 三段式：When[situation] I want[motivation] so I can[outcome]。"""
    checks = []
    keys = load_thresholds().get("discovery", {}).get(
        "job_story_keys", ["situation", "motivation", "outcome"])
    missing = [k for k in keys if is_blank(input_data.get(k))]
    for k in keys:
        checks.append(check(not is_blank(input_data.get(k)),
                            f"Job story 缺少 {k} 段" if k in missing
                            else f"Job story 具备 {k} 段", k))
    if is_blank(input_data.get("outcome")):
        checks.append(check(False, "缺少 outcome（期望结果）无法验收", "outcome"))
    # 反向门禁：job story 不得写成功能清单
    text = " ".join(str(input_data.get(k, "")) for k in keys)
    checks.append(check(len(text.strip()) >= 8, "Job story 语义长度不足（<8 字符）",
                        "semantics"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "discover", "jobstory", checks, mode="job_story")


def _validate_discover(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """发现计划门禁：问题/人群/时机 + 承重假设 + 验证计划（禁止只有问题描述）。"""
    checks = []
    for field, label in (("problem", "问题"), ("segment", "目标人群"), ("why_now", "时机")):
        checks.append(check(not is_blank(input_data.get(field)),
                            f"发现计划缺少{label}（{field}）" if is_blank(input_data.get(field))
                            else f"发现计划已定义{label}", field))

    risk_types_allowed = set(load_thresholds().get("assumption", {}).get(
        "risk_types", [])) or {"value", "usability", "viability", "feasibility",
                               "ethics", "gtm", "strategy", "team"}
    assumptions = input_data.get("assumptions") or []
    valid_assumptions = []
    for idx, a in enumerate(assumptions if isinstance(assumptions, list) else []):
        rt = (a or {}).get("risk_type", "") if isinstance(a, dict) else ""
        if rt in risk_types_allowed:
            valid_assumptions.append(rt)
        else:
            checks.append(check(False,
                                f"假设 {idx} 的 risk_type 不在八类风险内: {rt!r}",
                                "assumption"))
    checks.append(check(bool(valid_assumptions), "发现计划缺少可归类的承重假设",
                        "assumption"))

    plan = input_data.get("validation_plan") or []
    valid_plan = 0
    for idx, step in enumerate(plan if isinstance(plan, list) else []):
        step = step if isinstance(step, dict) else {}
        if all(not is_blank(step.get(k)) for k in ("hypothesis", "method", "metric")):
            valid_plan += 1
        else:
            checks.append(check(False,
                                f"验证计划 {idx} 缺 hypothesis/method/metric 三要素",
                                "validation"))
    checks.append(check(valid_plan >= 1, "缺少可执行的验证计划", "validation"))

    risk_types = sorted(set(valid_assumptions))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "discover", "discover", checks,
                       assumption_count=len(valid_assumptions),
                       risk_types=risk_types,
                       validation_count=valid_plan)


def _validate_interview(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """访谈脚本门禁：四段式时间盒 + Mom Test 三规则 + 记录字段。"""
    checks = []
    sections = input_data.get("sections") if isinstance(input_data.get("sections"), dict) else {}
    band = {}
    total_minutes = 0
    for name in _INTERVIEW_BANDS:
        cfg = sections.get(name) if isinstance(sections.get(name), dict) else {}
        minutes = cfg.get("minutes", 0)
        if isinstance(minutes, (int, float)) and minutes > 0:
            band[name] = int(minutes)
            total_minutes += int(minutes)
        else:
            checks.append(check(False, f"访谈脚本缺少 {name} 段的有效时长", "section"))
    checks.append(check(25 <= total_minutes <= 45,
                        f"访谈时间盒 {total_minutes} 分钟不在 25~45 分钟区间",
                        "timebox"))

    rules = input_data.get("mom_test_rules") if isinstance(input_data.get("mom_test_rules"), dict) else {}
    for rule in _MOM_TEST_RULES:
        checks.append(check(rules.get(rule) is True,
                            f"Mom Test 规则 {rule} 未显式开启", "mom_test"))

    fields = [f for f in (input_data.get("note_fields") or []) if isinstance(f, str) and f.strip()]
    checks.append(check(len(fields) >= _NOTE_FIELDS_MIN,
                        f"记录字段不足 {_NOTE_FIELDS_MIN} 个（当前 {len(fields)}）",
                        "note"))
    for required in ("biggest_pain", "desired_outcome"):
        checks.append(check(required in fields, f"记录字段缺少 {required}", "note"))

    ok = all(c["ok"] for c in checks)
    return make_result(ok, "discover", "interview", checks, sections_band=band)


# 历史名称兼容（harness 注册的是 _validate_interview）
_validate_interview_script = _validate_interview


def discover(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_discover(input_data)


def jobstory(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_jobstory(input_data)


def interview(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_interview(input_data)
