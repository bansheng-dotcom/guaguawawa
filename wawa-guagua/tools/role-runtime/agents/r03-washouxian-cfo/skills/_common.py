# -*- coding: utf-8 -*-
"""R03 八个技能模块的共享基础：JSON 读写、轻量 JSON Schema 校验、结果输出。

约束：纯标准库。技能之间不互相 import，只依赖 _common；阈值统一走
experience/thresholds.json（T9 阈值外置，改口径不改代码）。
与 r01/r02/r06/r07/r08 保持同一套 _common 契约。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def emit(data: Dict[str, Any]) -> None:
    """以单行 JSON 输出结果，供编排器以子进程方式消费。"""
    print("__AGENT_RESULT__ " + json.dumps(data, ensure_ascii=False))


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_json(path: str, data: Any) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    _makedirs(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _makedirs(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# 轻量 JSON Schema 校验器（子集，支撑 contracts.py 的确定性契约）。
# --------------------------------------------------------------------------- #
def _typename(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def validate_schema(instance: Any, schema: Any, path: str = "$") -> List[str]:
    errs: List[str] = []
    if not isinstance(schema, dict):
        return errs
    if "enum" in schema and instance not in schema["enum"]:
        return [f"{path}: 值 {instance!r} 不在枚举 {schema['enum']}"]
    t = schema.get("type")
    if t == "object":
        if not isinstance(instance, dict):
            return [f"{path}: 应为 object，实际 {_typename(instance)}"]
        for k in schema.get("required", []):
            if k not in instance:
                errs.append(f"{path}.{k}: 缺必填字段")
        props = schema.get("properties") or {}
        for k, sub in props.items():
            if k in instance:
                errs.extend(validate_schema(instance[k], sub, f"{path}.{k}"))
        if schema.get("additionalProperties") is False:
            for k in set(instance) - set(props):
                errs.append(f"{path}.{k}: 未声明字段")
        return errs
    if t == "array":
        if not isinstance(instance, list):
            return [f"{path}: 应为 array，实际 {_typename(instance)}"]
        it = schema.get("items")
        if isinstance(it, dict):
            for i, x in enumerate(instance):
                errs.extend(validate_schema(x, it, f"{path}[{i}]"))
        return errs
    if t == "string":
        if not isinstance(instance, str):
            return [f"{path}: 应为 string，实际 {_typename(instance)}"]
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: 长度 {len(instance)} < minLength {schema['minLength']}")
        return errs
    if t == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            return [f"{path}: 应为 number，实际 {_typename(instance)}"]
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: {instance} > maximum {schema['maximum']}")
        return errs
    if t == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            return [f"{path}: 应为 integer，实际 {_typename(instance)}"]
        return errs
    if t == "boolean":
        if not isinstance(instance, bool):
            return [f"{path}: 应为 boolean，实际 {_typename(instance)}"]
        return errs
    if t == "null":
        if instance is not None:
            return [f"{path}: 应为 null，实际 {_typename(instance)}"]
        return errs
    return errs


# --------------------------------------------------------------------------- #
# 通用检查辅助：统一 {ok, msg, dim, sev} 结构（对齐 r01/r02 样板）。
# --------------------------------------------------------------------------- #
def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **ev) -> Dict[str, Any]:
    d: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    d.update(ev)
    return d


def result(checks: List[Dict[str, Any]], **fields) -> Dict[str, Any]:
    """所有检查通过才 ok；CRITICAL/HIGH 失败给 FAIL 语义。"""
    ok = all(x.get("ok", False) for x in checks)
    out: Dict[str, Any] = {"ok": ok, "checks": checks}
    out.update(fields)
    return out


# --------------------------------------------------------------------------- #
# 全局阈值（T9）：优先 experience/thresholds.json > 内置默认。
# --------------------------------------------------------------------------- #
_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "financial": {
        "recon_amount_tolerance": 0.01,
        "recon_qty_tolerance": 0,
        "min_matched_pct": 0.95,
        "materiality_pct": 0.05,
        "variance_floor": 1000,
        "variance_fields": ["account", "driver", "variance", "direction",
                            "action"],
        "close_tasks_required": ["accruals", "roll_forward",
                                 "reconciliation", "variance_review",
                                 "sign_off"],
    },
    "cfo": {
        "runway_triggers": {"start_fundraising": 9, "cost_reduction": 6,
                            "execute_cuts": 4, "emergency": 3},
        "burn_multiple_max": 2.0,
        "ltv_cac_min": 3.0,
        "payback_max_months": 12,
        "churn_default": 0.02,
        "churn_clamp": [0.001, 0.30],
        "benefits_pct_default": 0.22,
        "identities": [
            "assets = liabilities + equity",
            "cash_end = cash_begin + operating + investing + financing",
            "gross_profit = revenue - cogs",
        ],
    },
    "contract": {
        "critical_reissue_limit": 0,
        "policy_required_fields": ["purpose", "scope", "owner",
                                   "review_cycle_days", "enforcement"],
        "policy_review_cycle_days": 365,
        "min_redline_per_critical": 1,
        "min_severity": "MEDIUM",
    },
    "privacy": {
        "dsr_deadline_days": 30,
        "breach_notification_hours": 72,
        "lawful_bases": ["consent", "contract", "legal_obligation",
                         "vital_interests", "public_task",
                         "legitimate_interest"],
        "cross_border_basis": ["adequacy", "scc", "bcr", "derogation"],
        "dsr_types": ["access", "rectification", "erasure", "portability",
                      "restriction", "objection"],
        "min_days_retention": 1,
    },
    "aigov": {
        "risk_levels": ["prohibited", "high", "limited", "minimal"],
        "prohibited_practices": ["social_scoring", "realtime_biometric_id",
                                 "emotion_inference_workplace",
                                 "untargeted_face_scraping"],
        "high_risk_flags": ["employment_screening", "credit_scoring",
                            "education_admission", "essential_services",
                            "law_enforcement", "migration_border",
                            "biometric_categorization"],
        "transparency_required_fields": ["ai_disclosure", "human_oversight",
                                         "content_labeling"],
        "disclosure_required_fields": ["disclose_interaction",
                                       "label_generated_content",
                                       "human_oversight_point",
                                       "complaint_channel"],
    },
    "audit": {
        "retention_tiers": {
            "six_years": ["blotters", "general_ledger", "subsidiary_ledger",
                          "customer_account_records", "financial_statements",
                          "securities_records", "partnership_agreements"],
            "three_years": ["communications", "order_memoranda",
                            "compliance_procedures", "employment_applications",
                            "written_agreements", "inspection_reports"],
            "lifetime": ["charter_documents", "minutes_book",
                         "stock_certificate_book"],
        },
        "accessible_first_years": 2,
        "worm_alternatives": ["worm", "audit_trail"],
        "severity_targets": {"observation_min_pct": 0.40,
                             "minor_pct": [0.20, 0.30],
                             "major_pct": [0.15, 0.25],
                             "critical_max_pct": 0.15},
        "evidence_required_fields": ["control", "artifact",
                                     "collected_at", "collector"],
        "min_evidence_per_control": 1,
        "followup_severity": "major",
    },
    "risk": {
        "ctr_threshold": 10000,
        "ctr_deadline_days": 15,
        "sar_threshold": 5000,
        "sar_deadline_days": 30,
        "structuring_lookback_days": 1,
        "kyc_retention_years": 5,
        "ubo_threshold_pct": 25,
        "risk_factor_max": {
            "jurisdiction": 2, "applicant_type": 2, "ownership_opacity": 2,
            "pep": 3, "sanctions": 3, "source_of_funds": 2,
        },
        "low_max_score": 2,
        "medium_max_score": 4,
        "dispositions": ["clear", "request-docs", "escalate-edd",
                         "decline-recommend"],
        "ad_periods_years": [1, 5, 10],
        "accredited_income": 200000,
        "accredited_joint_income": 300000,
        "accredited_net_worth": 1000000,
    },
    "tax": {
        "iso_grant_holding_years": 2,
        "iso_exercise_holding_years": 1,
        "iso_first_exercisable_limit": 100000,
        "iso_termination_window_months": 3,
        "amt_exemption": 137000,
        "amt_breakpoint": 220000,
        "amt_rate_low": 0.26,
        "amt_rate_high": 0.28,
        "rmd_age_years": 73,
        "rmd_age_2033": 75,
        "rmd_divisors": {"73": 26.5, "75": 24.6, "80": 20.2,
                         "85": 16.0, "90": 12.2},
        "rmd_excise_rate": 0.25,
        "rmd_excise_corrected_rate": 0.10,
        "safe_harbor_current_pct": 0.90,
        "safe_harbor_prior_pct": 1.00,
        "safe_harbor_prior_high_agi_pct": 1.10,
        "high_agi_threshold": 150000,
        "supplemental_rate": 0.22,
        "supplemental_rate_over_1m": 0.37,
        "supplemental_threshold": 1000000,
    },
    "review": {
        "vague_words": ["尽快", "持续关注", "有待进一步", "适当优化",
                        "后续跟进", "推进中", "原则上"],
        "advice_words": ["建议", "应当", "必须", "务必"],
        "licensed_words": ["正式法律意见", "正式审计意见", "法律意见书",
                           "审计报告", "保证合规", "保证合法", "保本",
                           "承诺收益", "税务鉴证"],
        "owner_fields": ["owner", "collector", "reviewer", "dri"],
    },
}

_AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def thresholds_path() -> str:
    return os.path.join(_AGENT_DIR, "experience", "thresholds.json")


def load_thresholds() -> Dict[str, Any]:
    p = thresholds_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return dict(_DEFAULT_THRESHOLDS)
    return dict(_DEFAULT_THRESHOLDS)


# --------------------------------------------------------------------------- #
# 通用字符串工具（供句式/模糊措辞校验复用）
# --------------------------------------------------------------------------- #
def has_any(text: str, tokens: List[str]) -> bool:
    return any(t in text for t in tokens if t)
