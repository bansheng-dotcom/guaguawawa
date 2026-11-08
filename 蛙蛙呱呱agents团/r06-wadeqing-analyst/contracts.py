# -*- coding: utf-8 -*-
"""R06 技能契约（T6）：每技能机器可读的「输入 + 输出」JSON Schema。

把「技能能吃什么、吐什么」从 prose reference 升级为可校验的 JSON Schema。
`agent.py contract validate` 用它做确定性校验：技能实际输出不符契约即 FAIL。

这里的 schema 是 JSON Schema 的子集（对齐 skills._common.validate_schema）。

约定：
  - `input.args`：CLI 参数名 → 属性（required 表示调用必传）。
  - `output.<action>`：该动作产出对象的顶层契约（required 键 + 顶层类型）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

# --------------------------------------------------------------------------- #
# 通用片段
# --------------------------------------------------------------------------- #
_s = {"type": "string"}
_b = {"type": "boolean"}
_n = {"type": "number"}
_i = {"type": "integer"}
_arr = {"type": "array"}
_obj = {"type": "object"}


def _o(required: List[str], props: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "object", "required": required, "properties": props}


# --------------------------------------------------------------------------- #
CONTRACTS: Dict[str, Any] = {
"semantics": {
    "desc": "指标与语义建模：validate/tree/link/compute/reconcile",
    "input": {"args": {"input": _s, "data": _s, "strict": _b, "a": _n, "b": _n,
                      "domain": {"type": "string", "enum": ["ledger", "finance",
                       "marketing", "product", "ml"]}, "label": _s}},
    "output": {
        "validate": _o(["ok", "errors"], {"ok": _b, "errors": _arr,
                        "semantic_models": _i, "metrics": _i, "measures": _i}),
        "tree": _o(["metric_tree", "metric_count"],
                   {"metric_tree": _obj, "metric_count": _i}),
        "link": _o(["ok", "hallucinated_count", "links"],
                   {"ok": _b, "hallucinated_count": _i, "links": _arr,
                    "columns_in_data": _arr}),
        "compute": _o(["computed_measures", "measure_count"],
                      {"computed_measures": _obj, "measure_count": _i}),
        "reconcile": _o(["status", "within_tolerance"],
                        {"status": {"type": "string", "enum": ["pass", "fail"]},
                         "within_tolerance": _b, "pct_diff": _n, "domain": _s}),
    },
},
"quality": {
    "desc": "数据清洗与质量：audit/clean",
    "input": {"args": {"input": _s, "pk": _s, "date": _s, "output": _s}},
    "output": {
        "audit": _o(["overall_score", "grade", "dimension_score", "findings"],
                    {"rows": _i, "fields": _i, "overall_score": _n, "grade": _s,
                     "dimension_score": _obj, "findings": _arr,
                     "duplicate_rows": _i}),
        "clean": _o(["rows_before", "rows_after", "cleaned_path"],
                    {"rows_before": _i, "rows_after": _i,
                     "duplicate_rows_removed": _i, "cleaned_path": _s}),
    },
},
"explore": {
    "desc": "探索与产品分析：trend/groupby/funnel/cohort/rfm/saas/time_series/segment/metrics",
    "input": {"args": {"input": _s, "date": _s, "value": _s, "group": _s,
                      "stage": _s, "user": _s, "period": _s, "order": _s,
                      "mrr": _n, "active_users": _n, "churn_rate": _n,
                      "window": _i, "features": _s, "k": _i, "seed": _i,
                      "model": _s, "customer": _s, "month": _s, "cac_spend": _n}},
    "output": {
        "trend": _o(["series", "total"], {"type": _s, "series": _arr, "total": _n}),
        "groupby": _o(["groups"], {"type": _s, "groups": _arr}),
        "funnel": _o(["stages"], {"type": _s, "stages": _arr}),
        "cohort": _o(["periods", "matrix"], {"type": _s, "periods": _arr, "matrix": _arr}),
        "rfm": _o(["segments"], {"type": _s, "user_count": _i, "segments": _arr}),
        "saas": _o(["mrr", "arpu", "ltv"],
                   {"mrr": _n, "active_users": _n, "churn_rate": _n,
                    "arpu": _n, "ltv": _n}),
        "time_series": _o(["series", "trend", "seasonality_strength"],
                          {"type": _s, "n": _i, "window": _i, "series": _arr,
                           "trend": _obj, "seasonality_strength": _n,
                           "seasonality_strong": _b, "anomalies": _obj}),
        "segment": _o(["k", "silhouette", "clusters"],
                      {"type": _s, "k": _i, "n": _i, "features": _arr,
                       "inertia": _n, "silhouette": _n, "silhouette_ok": _b,
                       "clusters": _arr}),
        "metrics": _o(["model"], {"type": _s, "model": _s}),
    },
},
"rootcause": {
    "desc": "根因与贡献度：decompose/drilldown",
    "input": {"args": {"input": _s, "dim": _s, "value": _s, "period": _s,
                      "before": _s, "after": _s}},
    "output": {
        "decompose": _o(["total_change", "dimension", "segments"],
                        {"total_change": _n, "dimension": _s, "segments": _arr}),
        "drilldown": _o(["dimension", "total", "items"],
                        {"dimension": _s, "total": _n, "items": _arr,
                         "pareto_top_n_for_80pct": _i}),
    },
},
"describe": {
    "desc": "描述统计（能力域5拆细）：describe",
    "input": {"args": {"input": _s, "col": _s}},
    "output": {"describe": _o(["describe"], {"describe": _obj})},
},
"correlate": {
    "desc": "Pearson 相关（能力域5拆细）：correlate",
    "input": {"args": {"input": _s, "col_a": _s, "col_b": _s}},
    "output": {"correlate": _o(["correlation"], {"correlation": _obj})},
},
"ttest": {
    "desc": "两样本 Welch t 检验（能力域5拆细）：ttest",
    "input": {"args": {"input": _s, "value": _s, "group": _s,
                      "group_a": _s, "group_b": _s}},
    "output": {"ttest": _o(["welch_t"], {"welch_t": _obj})},
},
"chi2": {
    "desc": "卡方独立性检验（能力域5拆细）：chi2",
    "input": {"args": {"input": _s, "row": _s, "col": _s}},
    "output": {"chi2": _o(["chi2"], {"chi2": _obj})},
},
"anova": {
    "desc": "单因素 ANOVA（能力域5拆细）：anova",
    "input": {"args": {"input": _s, "value": _s, "group": _s}},
    "output": {"anova": _o(["anova"], {"anova": _obj})},
},
"regression": {
    "desc": "一元线性回归（能力域5拆细·新增）：regression",
    "input": {"args": {"input": _s, "x": _s, "y": _s}},
    "output": {"regression": _o(["regression"], {"regression": _obj, "x": _s, "y": _s})},
},
"abtest": {
    "desc": "A/B 实验（能力域5拆细）：abtest",
    "input": {"args": {"input": _s, "group": _s, "control": _s,
                      "treatment": _s, "metric": _s}},
    "output": {"abtest": _o(["abtest"], {"abtest": _obj})},
},
"power": {
    "desc": "A/B 设计功效（能力域5拆细）：power（样本量/MDE 反解）",
    "input": {"args": {"baseline": _n, "mde": _n, "n_per_group": _i,
                      "alpha": _n, "power": _n, "sigma": _n}},
    "output": {"power": _o(["power"], {"power": _obj})},
},
"causal": {
    "desc": "因果推断四步（能力域5拆细）：causal（model/identify/estimate/refute）",
    "input": {"args": {"input": _s, "outcome": _s, "treatment": _s,
                      "confounders": _s, "trials": _i, "seed": _i}},
    "output": {"causal": _o(["causal"], {"causal": _obj})},
},
"scinlp": {
    "desc": "科学计算与NLP：describe/textstats/backend",
    "input": {"args": {"input": _s, "col": _s, "text": _s, "top": _i}},
    "output": {
        "describe": _o(["describe"], {"describe": _obj, "skew_pearson2": _n}),
        "textstats": _o(["doc_count", "top_words"],
                        {"doc_count": _i, "token_count": _i, "vocab_size": _i,
                         "top_words": _arr, "top_bigrams": _arr}),
        "backend": _o(["backends"], {"backends": _obj}),
    },
},
"domain": {
    "desc": "专业领域分析(生信)：list/run",
    "input": {"args": {"filter": _s, "data": _s,
                      "pipeline": {"type": "string", "enum": ["preprocess",
                       "cluster", "deg", "full"]}}},
    "output": {
        "list": _o(["skill_count", "skills"],
                   {"domain": _s, "backend": _s, "skill_count": _i, "skills": _arr}),
        "run": _o(["status", "backends", "pipeline", "stages"],
                  {"status": {"type": "string", "enum": ["blocked", "scaffold"]},
                   "backends": _obj, "pipeline": _s, "stages": _arr}),
    },
},
"viz": {
    "desc": "可视化与报告：spec/report/guide",
    "input": {"args": {"input": _s, "metrics": _s, "title": _s, "output": _s,
                      "chart": _s}},
    "output": {
        "spec": _o(["ok", "errors"], {"ok": _b, "chart_type": _s, "errors": _arr}),
        "report": _o(["report_path", "sections"],
                     {"report_path": _s, "sections": _arr, "qa_checklist": _arr}),
        "guide": _o([], {"chart": _s, "guide": _s, "chart_guide": _obj,
                         "valid_chart_types": _arr}),
    },
},
"selfmedia": {
    "desc": "自媒体数据运营：normalize/dashboard/report",
    "input": {"args": {"input": _s, "output": _s, "today": _s}},
    "output": {
        "normalize": _o(["normalized_path", "records"],
                        {"normalized_path": _s, "platform_count": _i,
                         "fields": _arr, "records": _arr}),
        "dashboard": _o(["total_fans", "status", "by_platform"],
                        {"total_fans": _n, "total_new_fans": _n, "total_revenue": _n,
                         "total_posts": _i, "hhi": _n, "hhi_grade": _s,
                         "platform_count": _i, "stale_count": _i,
                         "status": {"type": "string", "enum": ["ready", "partial",
                          "failed"]}, "by_platform": _arr, "check_date": _s}),
        "report": _o(["report_path", "status"],
                     {"report_path": _s, "status": _s}),
    },
},
}


def skill_names() -> List[str]:
    return list(CONTRACTS)


def get(skill: str) -> Dict[str, Any]:
    return CONTRACTS.get(skill, {})


def actions(skill: str) -> List[str]:
    return list(get(skill).get("output", {}).keys())


def validate_output(skill: str, action: str, result: Any) -> Dict[str, Any]:
    """按契约校验技能输出。返回 {ok, action, errors[], schema_ref}。"""
    schema = get(skill).get("output", {}).get(action)
    if schema is None:
        return {"ok": False, "skill": skill, "action": action,
                "errors": [f"契约未定义动作 {action}（可用 {actions(skill)}）"]}
    errs = c.validate_schema(result, schema)
    return {"ok": not errs, "skill": skill, "action": action, "errors": errs,
            "schema": schema}