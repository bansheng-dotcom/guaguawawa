# -*- coding: utf-8 -*-
"""第 5 段 explain：贡献拆解 + 驱动树 + 替代解释 + 反事实。

方案 §13.4 / §17.2 的硬要求：
  - 点名驱动必须有拆解（量/价），不能只说“某渠道下降”；
  - 加总误差 ≤5%；
  - 至少 2 个替代解释，并写明是否被数据排除；
  - 默认不做因果声明（`causal_claim=false`），时间不是原因。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from skills import _common as c

from .common import ck, gate, now_iso


def _period(d: str, split: str) -> str:
    return "before" if str(d)[:10] <= split else "after"


def build(data_path: str, plan: Dict[str, Any], findings: Dict[str, Any],
          dim: Optional[str] = None, qty: Optional[str] = None,
          date: Optional[str] = None) -> Dict[str, Any]:
    pg = plan.get("gate") or {}
    fg = findings.get("gate") or {}
    if not pg.get("ok"):
        return {"artifact": "explanation", "gate": gate(
            [ck(False, "plan 门禁未通过", "upstream", "CRITICAL")], "explain")}
    if not fg.get("ok"):
        return {"artifact": "explanation", "gate": gate(
            [ck(False, "findings 门禁未通过", "upstream", "CRITICAL")], "explain")}
    rows = c.load_csv(data_path)
    fields = list(rows[0].keys()) if rows else []
    metric = plan.get("metric", "")
    dims = [d for d in (plan.get("dimensions") or []) if d in fields]
    split = plan.get("split", "")
    date_col = date or "date"
    if dim and dim in fields:
        dims = [dim]
    chosen = dims[0] if dims else ""
    if not chosen or metric not in fields or date_col not in fields:
        return {"artifact": "explanation", "gate": gate(
            [ck(False, "缺少维度/指标/日期列，无法拆解", "schema", "CRITICAL")], "explain")}

    agg: Dict[str, Dict[str, float]] = {}
    for r in rows:
        d = str(r.get(date_col, ""))[:10]
        if not d:
            continue
        per = _period(d, split)
        seg = str(r.get(chosen, ""))
        slot = agg.setdefault(seg, {"v_before": 0.0, "v_after": 0.0,
                                    "q_before": 0.0, "q_after": 0.0,
                                    "n_before": 0, "n_after": 0})
        try:
            v = float(r.get(metric, 0) or 0)
        except ValueError:
            continue
        slot[f"v_{per}"] += v
        slot[f"n_{per}"] += 1
        if qty and qty in fields:
            try:
                slot[f"q_{per}"] += float(r.get(qty, 0) or 0)
            except ValueError:
                pass

    root_before = sum(v["v_before"] for v in agg.values())
    root_after = sum(v["v_after"] for v in agg.values())
    root_delta = root_after - root_before
    drivers: List[Dict[str, Any]] = []
    for seg, v in agg.items():
        delta = v["v_after"] - v["v_before"]
        item: Dict[str, Any] = {
            "driver": f"{chosen}:{seg}",
            "segment": seg,
            "before": round(v["v_before"], 2),
            "after": round(v["v_after"], 2),
            "delta": round(delta, 2),
            "contribution_pct": round(delta / root_delta * 100, 2) if root_delta else 0.0,
            "effect_decomposition": None,
            "decomposition_unavailable_reason": None,
        }
        if qty and qty in fields and v["q_before"] and v["q_after"]:
            p_before = v["v_before"] / v["q_before"]
            p_after = v["v_after"] / v["q_after"]
            vol_effect = (v["q_after"] - v["q_before"]) * p_before
            price_effect = (p_after - p_before) * v["q_after"]
            item["effect_decomposition"] = {
                "quantity": round(vol_effect, 2),
                "price": round(price_effect, 2),
                "residual": round(delta - vol_effect - price_effect, 2),
                "qty_before": round(v["q_before"], 2),
                "qty_after": round(v["q_after"], 2),
                "price_before": round(p_before, 4),
                "price_after": round(p_after, 4),
            }
        else:
            item["decomposition_unavailable_reason"] = "缺少数量列或数量为 0，只能给贡献不能拆量价"
        drivers.append(item)

    drivers.sort(key=lambda x: -abs(x["delta"]))
    top = drivers[0] if drivers else None
    sum_delta = sum(d["delta"] for d in drivers)
    error_pct = abs(sum_delta - root_delta) / abs(root_delta) * 100 if root_delta else 0.0

    share_change = 0.0
    if root_before and root_after:
        for d in drivers:
            sb = d["before"] / root_before
            sa = d["after"] / root_after
            share_change = max(share_change, abs(sa - sb) * 100)

    n_before = sum(v["n_before"] for v in agg.values())
    n_after = sum(v["n_after"] for v in agg.values())
    volume_change_pct = abs(n_after - n_before) / n_before * 100 if n_before else 0.0

    alternatives = [
        {"id": "A1", "statement": "口径/数据采集变化制造了差异",
         "test": "比较前后期记录数与字段集合",
         "status": "possible" if volume_change_pct > 30 else "not_supported",
         "evidence": {"rows_before": n_before, "rows_after": n_after,
                      "row_change_pct": round(volume_change_pct, 2),
                      "fields": fields}},
        {"id": "A2", "statement": "其他维度结构变化（mix）解释了差异",
         "test": "比较其他计划维度的分段占比变化",
         "status": "partially_supported" if share_change > 5 else "not_supported",
         "evidence": {"other_dimensions": dims[1:],
                      "max_share_change_pp": round(share_change, 2)}},
        {"id": "A3", "statement": "外部季节性/竞争导致差异",
         "test": "需要 ≥2 个完整周期或外部基准",
         "status": "unverifiable",
         "evidence": {"reason": "单窗口数据不足以识别季节性，需补去年同期或对照市场"}},
    ]

    explanation = {
        "artifact": "explanation",
        "version": "1.0",
        "generated_at": now_iso(),
        "metric": metric,
        "dimension": chosen,
        "root": {"before": round(root_before, 2), "after": round(root_after, 2),
                 "delta": round(root_delta, 2),
                 "delta_pct": round(root_delta / root_before * 100, 2) if root_before else None},
        "driver_tree": {
            "root": metric,
            "level_1": [{"driver": d["driver"], "delta": d["delta"],
                         "contribution_pct": d["contribution_pct"]} for d in drivers],
            "additivity": {"sum_delta": round(sum_delta, 2), "root_delta": round(root_delta, 2),
                           "error_pct": round(error_pct, 4)},
        },
        "drivers": drivers,
        "top_driver": top["driver"] if top else "",
        "counterfactual": ({
            "assumption": f"若 {top['driver']} 维持前期水平",
            "root_after_counterfactual": round(root_after - top["delta"], 2),
            "delta_vs_actual": round(-top["delta"], 2),
        } if top else {}),
        "alternatives": alternatives,
        "claim_type": "descriptive_decomposition",
        "causal_claim": False,
        "experiment": False,
        "time_as_cause": False,
    }
    explanation["gate"] = check(explanation, findings, plan)
    return explanation


def check(explanation: Dict[str, Any], findings: Dict[str, Any],
          plan: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    drivers = explanation.get("drivers") or []
    checks.append(ck(bool(drivers), f"驱动数={len(drivers)}", "structure",
                     "CRITICAL" if not drivers else "OK"))
    top = next((d for d in drivers if d.get("driver") == explanation.get("top_driver")), None)
    if top:
        checks.append(ck(top.get("contribution_pct") is not None,
                         "头号驱动有贡献占比", "decomposition", "CRITICAL"))
        has_eff = bool(top.get("effect_decomposition"))
        reason = top.get("decomposition_unavailable_reason")
        checks.append(ck(has_eff or bool(reason),
                         f"头号驱动已拆解或写明不能拆的原因（{top.get('driver')}）",
                         "decomposition", "WARN" if reason else "CRITICAL"))
        checks.append(ck("\u65f6\u95f4" not in str(top.get("driver")) and
                         "time" not in str(top.get("driver")).lower() and
                         "date" not in str(top.get("driver")).lower(),
                         "头号驱动不是时间/日期", "causality",
                         "CRITICAL" if ("时间" in str(top.get("driver")) or
                                        "time" in str(top.get("driver")).lower() or
                                        "date" in str(top.get("driver")).lower()) else "OK"))
    add = (explanation.get("driver_tree") or {}).get("additivity") or {}
    err = add.get("error_pct")
    checks.append(ck(isinstance(err, (int, float)) and err <= 5.0,
                     f"驱动加总误差={err}%（≤5%）", "additivity",
                     "CRITICAL" if not (isinstance(err, (int, float)) and err <= 5.0) else "OK"))
    alts = explanation.get("alternatives") or []
    checks.append(ck(len(alts) >= 2, f"替代解释数={len(alts)}（≥2）", "alternatives",
                     "CRITICAL" if len(alts) < 2 else "OK"))
    for a in alts:
        checks.append(ck(bool(a.get("test")) and bool(a.get("status")),
                         f"替代解释 {a.get('id')} 有检验与结论", "alternatives",
                         "CRITICAL" if not (a.get("test") and a.get("status")) else "OK"))
    checks.append(ck(explanation.get("causal_claim") is False or
                     explanation.get("experiment") is True,
                     "没有实验就不做因果声明", "causality",
                     "CRITICAL" if (explanation.get("causal_claim") and
                                    not explanation.get("experiment")) else "OK"))
    # 与 findings 对齐：根变化必须一致
    overall = next((f for f in (findings.get("findings") or [])
                    if f.get("type") == "overall"), None)
    if overall:
        diff = abs(explanation["root"]["delta"] - overall.get("delta", 0))
        tol = max(0.5, abs(overall.get("delta", 0)) * 0.005)
        checks.append(ck(diff <= tol,
                         f"根变化与 findings 一致（差 {round(diff, 2)}）", "consistency",
                         "CRITICAL" if diff > tol else "OK"))
    checks.append(ck(bool(explanation.get("counterfactual")), "给出反事实参照",
                     "counterfactual", "HIGH" if not explanation.get("counterfactual") else "OK"))
    return gate(checks, "explain")
