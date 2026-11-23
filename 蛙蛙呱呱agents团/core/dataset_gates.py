# -*- coding: utf-8 -*-
"""core.dataset_gates —— 数据层门禁 G1'/G3'/G4'/G5'（DATA-LAYER-SOP v2.0 · S4）。

旧门禁（v1）判的是「填了几格 / 总共几格」，格子模型错了，覆盖率就没意义。
新门禁判的是「判断有没有数据集支撑、查询能不能在表上跑、图能不能画」：

    G1' 判断支撑率：每个判断引用的数据集是否到手，行数是否 ≥ min_rows
    G3' 数据集有契约：source/grain/columns/rows_expected 齐
    G4' grain 一致：query.group_by 必须落在数据集声明的 grain 内（照 GROUND）
    G5' 图形可行性：图需要的维度都在 group_by 里，且 min_rows 够画

用法：
    from core import dataset_gates
    res = dataset_gates.run(drill_doc, actual_rows={"DS-...": [row, ...]})
    # actual_rows 不给时，G1' 只判「有没有声明」，标 unverified
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import cell_claim
from core import dataset as _ds

MIN_POINTS = cell_claim.MIN_POINTS


def derivation_gates(demand_doc: Dict[str, Any],
                     match_doc: Dict[str, Any],
                     quality_res: Optional[Dict[str, Any]] = None
                     ) -> Dict[str, Any]:
    """G-ROLLUP / G-PREVIEW（DERIVATION-SOP v4.0，**软门禁**）。

    G-ROLLUP  每个需求都要有源能答（status != none）
    G-PREVIEW derive 出来的维度质量达标（空值率 <10%、取值数 ≥2）

    默认 hard=False：只报告，不拦。要拦由调用方决定。
    """
    checks: List[Dict[str, Any]] = []
    best = (match_doc or {}).get("best") or {}
    none_ms = sorted(m for m, b in best.items() if b.get("status") == "none")
    partial = sorted(m for m, b in best.items() if b.get("status") == "partial")
    checks.append({
        "id": "G-ROLLUP", "ok": not none_ms, "hard": False,
        "msg": "需求有源：%d/%d 可答（全无源 %d）"
               % (len(best) - len(none_ms), len(best), len(none_ms)),
        "detail": {"no_source": none_ms, "partial": partial},
    })
    if quality_res is None:
        checks.append({"id": "G-PREVIEW", "ok": True, "hard": False,
                       "msg": "未跑样本验证（skipped）"})
    else:
        probs = quality_res.get("problems") or []
        checks.append({
            "id": "G-PREVIEW", "ok": bool(quality_res.get("ok")), "hard": False,
            "msg": "derive 质量：%s" % ("达标" if not probs else
                                       "%d 个维度不达标" % len(probs)),
            "detail": {"problems": probs[:6],
                       "dims": quality_res.get("dims")},
        })
    passed = sum(1 for c in checks if c["ok"])
    return {"ok": passed == len(checks), "checks": checks,
            "passed": passed, "total": len(checks),
            "hard_fail": [c["id"] for c in checks
                          if not c["ok"] and c.get("hard")]}


def run(drill_doc: Dict[str, Any],
        actual_rows: Optional[Dict[str, List[Dict[str, Any]]]] = None
        ) -> Dict[str, Any]:
    drills = (drill_doc or {}).get("drills") or []
    dss: Dict[str, Dict[str, Any]] = {}
    claims: List[Dict[str, Any]] = []
    for dr in drills:
        for d in dr.get("datasets") or []:
            dss[str(d.get("id"))] = d
        claims.extend(dr.get("claims") or [])

    checks: List[Dict[str, Any]] = []

    def ck(cid, ok, msg, hard=True, detail=None):
        checks.append({"id": cid, "ok": bool(ok), "msg": msg,
                       "hard": bool(hard), "detail": detail})

    # ---- G3' 数据集契约 ----
    ds_errs: Dict[str, List[str]] = {}
    for did, d in dss.items():
        e = _ds.validate(d)
        if e:
            ds_errs[did] = e
    ck("G3_dataset_contract", not ds_errs,
       "数据集契约 %d/%d 合法" % (len(dss) - len(ds_errs), len(dss)),
       detail=ds_errs or None)

    # ---- G1' 判断支撑率 ----
    verified = unverified = unsupported = 0
    bad: List[Dict[str, Any]] = []
    for c in claims:
        did = str(c.get("dataset") or "")
        d = dss.get(did)
        if not d:
            unsupported += 1
            bad.append({"claim": c.get("claim_id"), "why": "数据集不在册: %s" % did})
            continue
        need = int(c.get("min_rows") or 0)
        if actual_rows is None or did not in actual_rows:
            unverified += 1
        elif len(actual_rows[did]) >= need:
            verified += 1
        else:
            unsupported += 1
            bad.append({"claim": c.get("claim_id"),
                        "why": "数据行 %d < min_rows %d"
                               % (len(actual_rows[did]), need)})
    total = max(len(claims), 1)
    if actual_rows is None:
        ck("G1_claim_support", not unsupported,
           "判断支撑：%d 条挂表、%d 条悬空（未提供实采数据，行数未验）"
           % (len(claims) - unsupported, unsupported),
           detail=bad or None)
    else:
        ck("G1_claim_support", unsupported == 0,
           "判断支撑：%d/%d 已验，%d 未达 min_rows"
           % (verified, total, unsupported), detail=bad or None)

    # ---- G4' grain 一致（照 GROUND：group_by 必须在声明 grain 内） ----
    grain_bad = []
    for c in claims:
        d = dss.get(str(c.get("dataset") or ""))
        if not d:
            continue
        parts = {p.strip() for p in str(d.get("grain") or "").split("×") if p.strip()}
        unknown = [g for g in (c.get("query") or {}).get("group_by") or []
                   if parts and g not in parts]
        if unknown:
            grain_bad.append({"claim": c.get("claim_id"),
                              "grain": d.get("grain"), "超出": unknown})
    ck("G4_grain", not grain_bad,
       "grain 一致" if not grain_bad else "group_by 超出 grain: %d 条" % len(grain_bad),
       detail=grain_bad or None)

    # ---- G5' 图形可行性 ----
    chart_bad = []
    for c in claims:
        spec = c.get("chart") or {}
        if not spec:
            continue
        gb = set((c.get("query") or {}).get("group_by") or [])
        for k in ("x", "series", "color"):
            v = spec.get(k)
            if v and v not in gb:
                chart_bad.append({"claim": c.get("claim_id"),
                                  "why": "chart.%s=%r 不在 group_by" % (k, v)})
        if int(c.get("min_rows") or 0) < MIN_POINTS:
            chart_bad.append({"claim": c.get("claim_id"),
                              "why": "min_rows < %d，画不出关系" % MIN_POINTS})
    ck("G5_chart_feasible", not chart_bad,
       "图可行" if not chart_bad else "图不可行: %d 条" % len(chart_bad),
       detail=chart_bad or None)

    passed = sum(1 for c in checks if c["ok"])
    hard_fail = [c["id"] for c in checks if not c["ok"] and c["hard"]]
    return {"ok": not hard_fail, "checks": checks, "passed": passed,
            "total": len(checks), "hard_fail": hard_fail,
            "counts": {"claims": len(claims), "datasets": len(dss),
                       "verified": verified, "unverified": unverified,
                       "unsupported": unsupported}}
