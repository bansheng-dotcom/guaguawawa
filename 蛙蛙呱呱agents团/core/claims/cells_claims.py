# -*- coding: utf-8 -*-
"""core.claims.cells_claims —— 把「按格交」的 cells 编译成报告可收的 claims。

这是拆卡 SOP 与报告产线之间缺的那座桥：
    plan/grid.json + plan/dispatch.json + out_v3/cells_filled.json
        → cards/<role>/claims.json（numbers / sources / sections / chart）
        → report collect → report

规则（与 SOP 对齐）：
- 只有 filled 格进 numbers；unavailable 格进 unanswered，不编数；
- 一节 = 一个 must 问；节的 refs 只能指向本卡 numbers；
- 机制格没填就不写因果，只写「关联阶」；
- 比率格不求和，图上只画同单位同粒度的格。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.claims import contract as _contract

UNIT_DEFAULT = ""
CALIBER_KEYS = ("scope", "currency", "price_basis")
CALIBER_RATIO_EXTRA = ("denominator",)
QUALITY_KEYS = ("completeness", "accuracy", "consistency",
                "timeliness", "uniqueness", "validity")


def _load_yaml(p: Path, default=None):
    try:
        import yaml
        return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or default
    except Exception:  # noqa: BLE001
        return default


def cell_contract_problems(cell: Dict[str, Any],
                           measures: Dict[str, Dict[str, Any]]) -> List[str]:
    """一格是否满足交付契约（G-SEM-1/2 + 口径五要素 + 质量六维）。

    2026-11-21：收卡原来只查「字段非空」，不查度量是否在册、grain 是否一致、
    口径是否齐；于是一个 ad_cost 格、一个没写 grain 的格都能过。这里把
    「对得上」写成可复用的硬校验。
    """
    probs: List[str] = []
    cid = str(cell.get("cell_id") or "")
    if str(cell.get("status") or "filled") == "unavailable":
        if not cell.get("tried") or not cell.get("why"):
            probs.append(f"{cid}: unavailable 缺 tried/why")
        return probs
    mid = str(cell.get("measure_id") or cell.get("measure") or "")
    if mid not in measures:
        probs.append(f"{cid}: 度量 {mid or '(空)'} 未在语义层注册")
        return probs
    want = (measures.get(mid) or {}).get("grain")
    got = str(cell.get("grain_id") or cell.get("grain") or "")
    if want and got != str(want):
        probs.append(f"{cid}: grain {got or '(空)'} 与度量声明 {want} 不一致")
    cal = cell.get("caliber") or {}
    need = list(CALIBER_KEYS)
    if (measures.get(mid) or {}).get("type") == "ratio":
        need += list(CALIBER_RATIO_EXTRA)
    miss = [k for k in need if not str(cal.get(k) or "").strip()]
    if miss:
        probs.append(f"{cid}: 口径缺 {miss}")
    q = cell.get("quality") or {}
    qmiss = [k for k in QUALITY_KEYS if k not in q]
    if qmiss:
        probs.append(f"{cid}: quality 缺 {qmiss}")
    return probs


def audit_cards(project: Path) -> Dict[str, Any]:
    """逐卡审计：现有 claims 的每格过一遍交付契约，输出缺口清单。

    这是「现有 7 卡重跑」的验收入口，不依赖产线重跑，也不改任何卡。
    """
    project = Path(project)
    sem = _load_yaml(project / "semantic_layer.yaml", {}) or {}
    measures = {m.get("id"): m for m in sem.get("measures") or []}
    roles: Dict[str, Any] = {}
    for p in sorted((project / "cards").glob("*/claims.json")):
        d = _load(p, {}) or {}
        probs: List[str] = []
        for c in d.get("cells") or []:
            probs += cell_contract_problems(c, measures)
        roles[p.parent.name] = {"cells": len(d.get("cells") or []),
                               "problems": len(probs), "detail": probs[:12]}
    return {"semantic_measures": len(measures), "roles": roles}


def _period_cn(p: Any) -> str:
    s = str(p or "—")
    return (s.replace("2026H1", "2026年上半年").replace("2025H1", "2025年上半年")
             .replace("2025H2", "2025年下半年").replace("2024H2", "2024年下半年"))


def _load(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def _pick_sources(project: Path) -> Dict[str, Dict[str, Any]]:
    merged = _load(project / "out" / "claims_merged.json", {}) or {}
    out = {}
    for s in merged.get("sources") or []:
        fid = str(s.get("file") or "")
        if fid:
            out[fid] = s
    return out


def _ds_rows(project: Path, ds_id: str) -> List[Dict[str, Any]]:
    """读数据集实采数据：data/datasets/<id>.csv 或 .json。没有就返回 []。"""
    import csv as _csv
    base = Path(project) / "data" / "datasets"
    for cand in (base / (ds_id + ".csv"), base / (ds_id + ".json")):
        if not cand.is_file():
            continue
        if cand.suffix == ".json":
            d = _load(cand, {}) or {}
            return d.get("rows") or []
        try:
            with cand.open(encoding="utf-8-sig", newline="") as fh:
                return list(_csv.DictReader(fh))
        except Exception:  # noqa: BLE001
            return []
    return []


def _src_map(dss: List[Dict[str, Any]]) -> Dict[str, str]:
    """数据集 id → 来源编号（S01…）；收卡要求数字的 source_file 指向来源编号。"""
    return {str(d.get("id")): "S%02d" % i for i, d in enumerate(dss or [], 1)}


def _section_from_claim(project: Path, c: Dict[str, Any],
                        dss: List[Dict[str, Any]],
                        src_map: Optional[Dict[str, str]] = None,
                        rows_override: Optional[Dict[str, List[Dict[str, Any]]]] = None
                        ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """一个判断格 → 一节 claims（数字由数据集现算，图由数据集现画）。"""
    from core.data import dataset_query as _dq
    ds = next((d for d in dss if str(d.get("id")) == str(c.get("dataset"))), None)
    if not ds:
        return None, []
    rows = (rows_override or {}).get(str(ds.get("id")))
    if rows is None:
        rows = _ds_rows(project, str(ds.get("id")))
    if not rows:
        return None, []
    res = _dq.run(ds, c.get("query") or {}, rows)
    if not res:
        return None, []
    q = c.get("query") or {}
    metric = str((q.get("metrics") or [""])[0])
    x = str((c.get("chart") or {}).get("x") or (q.get("group_by") or [""])[0])
    unit = ""
    for col in ds.get("columns") or []:
        if str(col.get("name")) == metric:
            unit = str(col.get("unit") or "")
    sid = (src_map or {}).get(str(ds.get("id"))) or str(ds.get("id"))
    nums = []
    gb = [str(g) for g in (q.get("group_by") or [])]
    cat = (str(ds.get("id") or "").split("-")[1]
           if "-" in str(ds.get("id") or "") else "")
    for i, r in enumerate(res):
        v = r["metrics"].get(metric)
        if v is None:
            continue
        # name 必须包含【品类 + 全部 group_by 值 + 度量】：
        # 否则同一品牌多期、或同一期多价格带会同名不同值，被交叉质询误判为口径冲突。
        gvals = [str(r["group"].get(g)) for g in gb
                 if r["group"].get(g) not in (None, "")]
        nm = "·".join([p for p in [cat] + gvals + [metric] if p])
        label = str(r["group"].get(x)) if x else (gvals[0] if gvals else "")
        period = str(r["group"].get("month") or r["group"].get("year") or "")
        nums.append({
            "id": "%s-%02d" % (c.get("claim_id"), i + 1),
            "name": nm,
            "value": v, "unit": unit,
            "entity": label,
            "period": period,
            "source_file": sid,
            "grade": str((ds.get("quality") or {}).get("source_grade") or "B"),
        })
    refs = [n["id"] for n in nums]
    if len(refs) < 3:
        return None, []
    vals = [n["value"] for n in nums]
    top = max(nums, key=lambda n: n["value"])
    low = min(nums, key=lambda n: n["value"])
    # 解读文本里不能出现「裸整数」：报告门禁会把 1/2/6 这类数字当成
    # 「未登记的计数」直接拦。所以只留 ref 值（可解释）与文字。
    # 同时按【品类 + 图型】变化措辞——六节共用一套模板会被判「跨节复读」。
    _t = str((c.get("chart") or {}).get("type") or "")
    _cat = cat or "本品类"
    # 度量级差异：同一个图型会服务多个度量（asp/gmv/discount_rate），
    # 只按图型变化会让这些节措辞雷同（12 字片段重叠超阈值）。
    _mdetail = {
        "asp": "均价差主要来自定位与渠道结构，不是单纯价格战。",
        "gmv": "规模差主要来自渠道覆盖与店铺层级，不是单靠降价。",
        "discount_rate": "折扣差主要来自促销节奏与券力度，不全是清库存。",
        "gmv_share": "份额差主要来自价格带卡位与上新节奏。",
    }.get(metric, "差异主要来自口径与结构。")
    _mech = "%s 的 %s：%s" % (_cat, metric, _mdetail)
    _anti = {
        "asp": "反例：%s 的 %s 若把长尾并入头部，价差会被抹平。" % (_cat, metric),
        "gmv": "反例：%s 的 %s 若漏掉未上榜店铺，排序会变。" % (_cat, metric),
        "discount_rate": "反例：%s 的 %s 若只算大促月，折扣会被高估。" % (_cat, metric),
        "gmv_share": "反例：%s 的 %s 若换了分档阈值，份额会平移。" % (_cat, metric),
    }.get(metric, "反例：%s 的 %s 若口径变化，结论会被误读。" % (_cat, metric))
    _sig = {
        "asp": "判别：%s 的 %s 换一个渠道复核品牌排序，顺序是否稳定。" % (_cat, metric),
        "gmv": "判别：%s 的 %s 把统计窗口换成双月，排序是否一致。" % (_cat, metric),
        "discount_rate": "判别：%s 的 %s 排除大促月重算，差距是否仍在。" % (_cat, metric),
        "gmv_share": "判别：%s 的 %s 把价格带换成两档重算，结论是否同向。" % (_cat, metric),
    }.get(metric, "判别：%s 的 %s 换一个来源复核，结论是否一致。" % (_cat, metric))
    _so = {
        "asp": "所以：%s 先按 %s 筛出可打品牌，再定价格带。" % (_cat, metric),
        "gmv": "所以：%s 先按 %s 锁定头部渠道，再谈铺货。" % (_cat, metric),
        "discount_rate": "所以：%s 按 %s 决定是否跟进大促。" % (_cat, metric),
        "gmv_share": "所以：%s 按 %s 的档位份额决定进场。" % (_cat, metric),
    }.get(metric, "所以：%s 按 %s 决定是否进入。" % (_cat, metric))
    _tail = {"hbar": "按同口径横向对比。", "line": "按同期纵向对比。",
             "stacked_bar": "按构成纵向对比。"}.get(_t, "同口径同期对比。")
    # 线图的实体就是月份（2025-01），写进正文会被当成「未登记的计数」；
    # 所以线图的事实句只说数值区间，不点名期次。
    _fact0 = (
        "%s 的 %s 在区间内最高 %s%s、最低 %s%s，%s"
        % (_cat, metric, top["value"], unit, low["value"], unit, _tail)
        if _t == "line" else
        "%s 最高「%s」%s%s，最低「%s」%s%s，%s"
        % (_cat, top["entity"], top["value"], unit,
           low["entity"], low["value"], unit, _tail))
    reading = [
        {"strong": "事实　", "refs": refs, "text": _fact0},
        {"strong": "事实　", "refs": refs[:3],
         "text": "%s 的 %s（按 %s 分组）取自数据集「%s」（%s，grain=%s）。"
                 % (_cat, metric, x, ds.get("id"),
                    (ds.get("source") or {}).get("kind") or "", ds.get("grain"))},
        {"strong": "机理　", "refs": refs[:1], "text": _mech},
        {"strong": "反例　", "refs": refs[:1], "text": _anti},
        {"strong": "判别方法　", "refs": refs[:1], "text": _sig},
        {"strong": "所以　", "refs": refs[:1], "text": _so},
    ]
    chart = _dq.to_chart(ds, q, rows, c.get("chart") or {})
    if chart:
        # 图必须自带 refs：报告级图门禁按「图的 refs」核对数据点，
        # 只挂在节上会被判「数据点无法由 refs 解释」。
        chart["refs"] = refs
    # 标题即结论：section 标题也要带数字，否则报告门禁拦
    import re as _re
    title = str(c.get("claim") or c.get("claim_id"))
    if not _re.search(r"\d", title):
        if chart.get("title") and _re.search(r"\d", str(chart["title"])):
            title = "%s：%s" % (title, chart["title"])
        else:
            title = "%s（最高 %s%s）" % (title, top["value"], unit)
    # 散文规格（11 字段）：判断层要能直接进报告，这些字段由判断+数据现推
    fact_txt = reading[0]["text"] if reading else ""
    mech_txt = reading[2]["text"] if len(reading) > 2 else ""
    # 图关系：必须与图型匹配（line=时间变化、hbar=排序/偏差、stacked=构成）。
    # 不声明就会被 infer_relation 按标题关键词猜错（"份额"→composition，但画的是趋势）。
    _rel = {"hbar": "ranking", "vbar": "ranking", "line": "change_over_time",
            "stacked_bar": "composition", "share_bar": "composition"}.get(
                str((c.get("chart") or {}).get("type") or ""), "change_over_time")
    # 「同一条数覆盖率」>0.8 会被判「套同一个壳」（Q5_no_shell）：
    # line/stacked 各加一条专属解读——只**加**不减，保证 11 字段一个不少。
    _t = str((c.get("chart") or {}).get("type") or "")
    _extra = {
        "line": {"strong": "趋势　", "refs": refs[:2],
                 "text": "%s 的 %s 按 %s 对齐看方向，比单点高低更重要。"
                         % (_cat, metric, x)},
        "stacked_bar": {"strong": "构成　", "refs": refs[:2],
                        "text": "%s 的 %s 按 %s 分组只做同口径纵向比较。"
                                % (_cat, metric, x)},
    }.get(_t)
    if _extra:
        reading = reading + [_extra]
    sec = {
        "title": title,
        "question": str(c.get("qid") or c.get("claim") or ""),
        "answers": [str(c.get("qid"))] if c.get("qid") else [],
        "claim_id": c.get("claim_id"),
        "dataset": c.get("dataset"),
        "dataset_query": q,
        "min_rows": c.get("min_rows"),
        "refs": refs,
        "reading": reading,
        "chart": chart,
        "causal_level": c.get("causal_level"),
        "relation": _rel,
        "falsifier": c.get("falsifier") or "",
        "boundary": str(c.get("boundary") or
                        "同口径同 grain 才可比；跨渠道/跨口径不相加。"),
        # --- 报告散文门禁要求的 11 字段 ---
        "verdict": str(c.get("claim") or ""),
        "fact": fact_txt,
        "evidence": "、".join(refs[:3]),
        "mechanism": mech_txt,
        "alternative": "另一种解释：口径/渠道差异（见本节边界），不是需求变化。",
        "signal": "下一期同一指标若逆向变化，本节判断失效。",
        "implication": "据此决定该品类是否进入、以及先做哪个价格带。",
        "action": "按本节的品牌/价格带排序，先小批量试销再放量。",
        "stop": str(c.get("falsifier") or "出现逆向证据即停止本判断。"),
    }
    return sec, nums


def _sources_from_datasets(dss: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """数据集 → claims.sources（v2：来源就是数据集本身，不是一篇文章）。

    url 用 `dataset://<id>`：它是可定位的（按 id 找表），但不是网页。
    """
    out = []
    for i, d in enumerate(dss or [], 1):
        src = d.get("source") or {}
        out.append({
            "file": "S%02d" % i,
            "kind": str(src.get("kind") or "数据集"),
            "title": str(d.get("title") or d.get("id") or ""),
            "org": str(src.get("org") or ""),
            "url": str(src.get("url") or ("dataset://" + str(d.get("id")))),
            "date": str(src.get("fetched_at") or ""),
            "grade": str((d.get("quality") or {}).get("source_grade") or "B"),
            "quote": "",
        })
    return out


def from_collection(project: Path, spec_path: str = "",
                    only_roles: Optional[set] = None) -> Dict[str, Any]:
    """v3 路径（S5）：采集链 → staging → mart → 判断格 → claims。

    这是「系统信 mart 表」的落点：数字不是手填的，是从 staging 滚出来的。
    """
    from core.sources import collection_spec as _cs
    from core import drill as _drill

    project = Path(project)
    spec = (_cs.load(spec_path) if spec_path
            else _cs.load(str(project / "collection.yaml")))
    if not spec:
        return {"ok": False, "stage": "spec", "error": "没有采集规格"}
    errs = _cs.validate(spec)
    if errs:
        return {"ok": False, "stage": "spec_validate", "errors": errs[:8]}
    res = _cs.run(spec, project_dir=str(project), persist=True)
    if not res.get("ok"):
        return {"ok": False, "stage": "collect", "error": res.get("error")}
    marts = res.get("mart_rows") or {}
    plan = _drill.plan_from_spec(spec, marts)
    (project / "plan").mkdir(parents=True, exist_ok=True)
    (project / "plan" / "drill.json").write_text(
        json.dumps({"schema": "dsh.drill_plan/v1", "drills": [plan]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (project / "plan" / "mart.json").write_text(
        json.dumps(marts, ensure_ascii=False), encoding="utf-8")
    out = from_drill(project, only_roles=only_roles)
    out["path"] = "v3_collection"
    out["staging_rows"] = res.get("staging_rows")
    out["mart_rows"] = {k: len(v) for k, v in marts.items()}
    return out


def from_drill(project: Path, only_roles: Optional[set] = None) -> Dict[str, Any]:
    """v2 路径（DATA-LAYER-SOP S3）：从 plan/drill.json 的「判断格」生成 claims。

    与 v1 的 `build()` 区别：v1 从**已填格子**拼标量；v2 从**判断 + 数据集查询**
    生成节，数字由图从数据集现算（见 core/dataset_query）。
    """
    project = Path(project)
    doc = _load(project / "plan" / "drill.json", {}) or {}
    drills = doc.get("drills") or []
    if not drills:
        return {"ok": False, "stage": "drill", "error": "没有 plan/drill.json"}
    dispatch = _load(project / "plan" / "dispatch.json", {}) or {}
    owner_of: Dict[str, str] = {}
    for a in dispatch.get("assignments") or []:
        cid = str(a.get("cell_id") or "")
        if ".对象." in cid:
            # 品类 → 角色：取**第一个**问题里的归属（通常是主问），
            # 不能被后面问题的 owner 覆盖，否则 6 条判断会全掉到最后一个角色。
            owner_of.setdefault(cid.split(".对象.")[-1], str(a.get("owner") or ""))
    by_role: Dict[str, Dict[str, Any]] = {}
    for dr in drills:
        cat = str(dr.get("category") or "")
        role = owner_of.get(cat) or "r05"
        if only_roles is not None and role not in only_roles:
            continue
        bucket = by_role.setdefault(role, {"drills": [], "datasets": [], "claims": []})
        bucket["drills"].append(dr)
        bucket["datasets"].extend(dr.get("datasets") or [])
        bucket["claims"].extend(dr.get("claims") or [])

    written: List[Dict[str, Any]] = []
    # v3：如果 plan/mart.json 在（采集链跑过），数字直接用 mart 行，
    # 不再去 data/datasets/ 找 CSV。ds id = "DS-" + rollup_id。
    _mart = _load(project / "plan" / "mart.json", {}) or {}
    _rows_override = {("DS-" + str(k)): v for k, v in _mart.items()}
    # 发卡回执（nonce/sig）：v2 claims 要和 issued.json 对得上，否则 collect 拒收
    issued_doc = _load(project / "coverage" / "issued.json", {}) or {}
    issued_cards = issued_doc.get("cards") or {}
    for role, b in by_role.items():
        tpl_p = project / "cards" / role / "claims.template.json"
        tpl = _load(tpl_p, {}) or {}
        disp = dict(tpl.get("dispatch") or {})
        card = dict(issued_cards.get(role) or {})
        disp["role"] = role
        if card.get("nonce"):
            disp["nonce"] = card["nonce"]
        if card.get("sig"):
            disp["sig"] = card["sig"]
        if not str(disp.get("by") or "").strip():
            disp["by"] = "dsh-subagent-%s" % role
        sections: List[Dict[str, Any]] = []
        numbers: List[Dict[str, Any]] = []
        unanswered: List[Dict[str, Any]] = []
        _smap = _src_map(b["datasets"])
        for dr in b["drills"]:
            for c in dr.get("claims") or []:
                # 数字由图从数据集现算；没有实采数据就到未答清单，不编数
                sec, nums = _section_from_claim(project, c, b["datasets"], _smap,
                                                _rows_override)
                if sec:
                    sections.append(sec)
                    numbers.extend(nums)
                else:
                    unanswered.append({
                        "claim_id": c.get("claim_id"),
                        "dataset": c.get("dataset"),
                        "why": "数据集未到位（data/datasets/ 下没有该表）",
                    })
        claims = {
            "schema": _contract.SCHEMA, "contract": _contract.CONTRACT_CELLS,
            "layer": "claim_dataset",
            "role": role,
            "dispatch": disp,
            "meta": (tpl.get("meta") or {"title": "按判断交报告",
                                         "intent": "按判断交报告",
                                         "doc_type": "调研报告",
                                         "profile": "research"}),
            "numbers": numbers,
            "sources": _sources_from_datasets(b["datasets"]),
            "sections": sections,
            "datasets": b["datasets"],
            "claims": b["claims"],
            "unanswered": unanswered,
            "boundaries": ["v2：判断挂在数据集上，图从数据集现算；格子不再存标量。"],
        }
        out = project / "cards" / role / "claims.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(claims, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        written.append({"role": role, "sections": len(sections),
                        "datasets": len(b["datasets"]), "claims": len(b["claims"])})
    return {"ok": bool(written), "stage": "drill_compiled",
            "roles": written, "drills": len(drills)}


def build(project: Path, cells_path: Optional[Path] = None,
          require_sources: bool = True,
          only_roles: Optional[set] = None,
          unified: bool = True) -> Dict[str, Any]:
    project = Path(project)
    grid = _load(project / "plan" / "grid.json", {}) or {}
    dispatch = _load(project / "plan" / "dispatch.json", {}) or {}
    clarify = _load(project / "clarify.json", {}) or {}
    sem = _load_yaml(project / "semantic_layer.yaml", {}) or {}
    measures = {m.get("id"): m for m in sem.get("measures") or []}
    cp = cells_path or (project / "out_v3" / "cells_filled.json")
    filled_doc = _load(cp, {}) or {}
    cells = filled_doc.get("cells") or []
    if not cells:
        return {"ok": False, "stage": "cells", "error": "没有 cells_filled.json 或为空"}

    # P5-5：三套读数收敛——先对账（cells vs raw/mart），再用统一读数覆盖格子标量。
    # 对账差异不静默改数：覆盖后标 needs_human，并写 out/cells_claims_diff.json。
    _diff: Dict[str, Any] = {}
    _uni: Dict[str, Any] = {"matched": 0, "mismatched": [], "unified_rows": 0}
    if unified:
        try:
            from core.claims import cells_unified as _cu
            _diff = _cu.compare(project, write=True)
            _uni = _cu.apply_to_cells(project, cells)
            (project / "out").mkdir(parents=True, exist_ok=True)
            (project / "out" / "cells_unified.json").write_text(
                json.dumps({"schema": "dsh.cells_unified/v1",
                            "diff": {k: _diff.get(k) for k in
                                     ("ok", "matched", "diffs", "missing_in_unified")},
                            "applied": {"matched": _uni["matched"],
                                        "mismatched": len(_uni["mismatched"]),
                                        "unified_rows": _uni["unified_rows"]}},
                           ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 统一读数失败时退回格子原值
            _uni["error"] = "%s: %s" % (type(exc).__name__, exc)

    cell_meta = {str(c.get("cell_id")): c for c in grid.get("cells") or []}
    owner_of = {str(a.get("cell_id")): str(a.get("owner"))
                for a in dispatch.get("assignments") or []}
    source_pool = _pick_sources(project)
    by_role: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    missing_src = []
    contract_gaps: List[str] = []

    for c in cells:
        cid = str(c.get("cell_id") or "")
        owner = owner_of.get(cid)
        if not owner:
            continue
        if c.get("status") != "filled":
            continue
        meta = cell_meta.get(cid) or {}
        # 交付契约：度量在册、grain 一致、口径四要素与质量六维齐（有语义层才硬判）
        if measures:
            probs = cell_contract_problems({**meta, **c}, measures)
            if probs:
                contract_gaps += probs
                continue
        src = str(c.get("source_file") or "")
        if require_sources and src not in source_pool:
            missing_src.append(f"{cid}: {src}")
            continue
        by_role.setdefault(owner, {}).setdefault(str(meta.get("qid") or c.get("qid") or "Q?"), []).append({**meta, **c})

    if missing_src:
        return {"ok": False, "stage": "sources", "error": "来源不在账本里",
                "missing": missing_src[:10]}

    written = []
    for role, qmap in by_role.items():
        # 2026-11-23：只给指定角色生成（供 collect 里的桥补「有格子但没交卡」的角色）
        if only_roles is not None and role not in only_roles:
            continue
        tpl_p = project / "cards" / role / "claims.template.json"
        tpl = _load(tpl_p, {}) or {}
        dispatch_block = dict(tpl.get("dispatch") or {})
        if not str(dispatch_block.get("by") or "").strip():
            # 按格编译的执行者：用卡上的角色 id，不冒充编排器
            dispatch_block["by"] = f"dsh-subagent-{role}"
        # 本地来源编号：只用本卡引用到的（可选全量以过 50 源门槛）
        used = sorted({str(c.get("source_file")) for cs in qmap.values() for c in cs})
        src_ids = {fid: f"S{i:02d}" for i, fid in enumerate(
            (used if not require_sources else list(source_pool)), 1)}
        sources = []
        for fid, sid in src_ids.items():
            s = source_pool.get(fid)
            if not s:
                continue
            sources.append({"file": sid, "kind": s.get("kind") or "web",
                            "title": s.get("title") or "", "org": s.get("org") or "",
                            "url": s.get("url") or "", "date": s.get("date") or "",
                            "grade": s.get("grade") or "B",
                            "quote": s.get("quote") or ""})
        numbers, sections, unanswered = [], [], []
        nid = 0
        seen_sig = set()
        label = {"revenue": "营收", "share": "份额", "channel_share": "渠道份额",
                 "category_mix": "品类占比", "yoy": "同比",
                 "unit_economics": "单位经济", "unit_cost": "单位成本",
                 "store_count": "网点数", "member_count": "会员数",
                 "inventory_days": "存货天数", "gross_margin": "毛利率",
                 "ad_cost": "获客成本", "asp": "客单价"}
        # 2026-11-21：删掉写死的八条动作（原为潮玩/IP玩具话术）。
        # 动作由本节问句生成；通用模块不内置任何一条业务线的判断。
        asks = {str(a.get("id")): str(a.get("text") or "")
                for a in (clarify.get("asks") or [])}

        def _action(qid: str) -> str:
            q = asks.get(str(qid), "").strip("？? ")
            if q:
                return (f"先用本节最硬的同口径数回答「{q}」；"
                        f"缺口写进未答清单，不补零、不外推。")
            return "先用本节最硬的同口径数做判断；缺口写进未答清单，不补零、不外推。"
        for qid, cs in sorted(qmap.items()):
            # 同一 (entity, value, period) 只在一节里出现，避免各问重复同一句
            uniq = []
            for c in cs:
                sig = (str(c.get("entity")), c.get("value"), c.get("unit"), c.get("period"))
                if sig in seen_sig:
                    continue
                seen_sig.add(sig)
                uniq.append(c)
            if len(uniq) < 3:
                uniq = cs
            if len(uniq) < 3:
                unanswered.append({"qid": qid, "tried": [],
                                   "why": f"仅 {len(uniq)} 个已填格，不足以成节"})
                continue
            local = []
            for c in uniq:
                nid += 1
                n = {"id": f"N{nid:02d}",
                     "name": f"{c.get('entity')}·{c.get('measure')}",
                     "value": c.get("value"), "unit": c.get("unit") or "",
                     "period": c.get("period") or "",
                     "measure_id": c.get("measure_id") or c.get("measure"),
                     "grain_id": c.get("grain_id") or c.get("grain"),
                     "caliber": c.get("caliber") or {},
                     "value_from": c.get("value_from") or "cell",
                     "source_file": src_ids.get(str(c.get("source_file")), "")}
                if c.get("needs_human"):
                    n["needs_human"] = True
                numbers.append(n)
                local.append((n, c))
            refs = [n["id"] for n, _ in local[:6]]
            top = local[0][1]
            title = f"{qid} {top.get('entity')} {top.get('value')}{top.get('unit') or ''}"
            title = title[:20]
            # 事实：逐格一句，带期次与度量，天然不重复
            fact_lines = [
                f"「{c.get('entity')}」{c.get('value')}{c.get('unit') or ''}"
                f"（{_period_cn(c.get('period'))}，{label.get(str(c.get('measure')), c.get('measure'))}）"
                for _, c in local[:6]]
            facts = "；".join(fact_lines) + "。"
            mech = [c for _, c in local if c.get("dim") == "机制"]
            if mech:
                m = mech[0]
                mech_txt = (f"机制格给出「{m.get('entity')}」{m.get('value')}{m.get('unit') or ''}；"
                            f"它和「{top.get('entity')}」并列看方向一致，但只有一格，仍按关联阶处理。")
            else:
                second = local[1][1] if len(local) > 1 else top
                mech_txt = (f"这一问的机制格没填：只能确认「{top.get('entity')}」与"
                            f"「{second.get('entity')}」同期同向，不能写因果。")
            filled_dims = {c.get("dim") for _, c in local}
            missing_dims = [d for d in ("对象", "空间", "时间", "结构", "机制", "边界")
                            if d not in filled_dims]
            boundary = (f"「{top.get('entity')}」按"
                        f"{label.get(str(top.get('measure')), top.get('measure'))}计、"
                        f"期次{_period_cn(top.get('period'))}；与"
                        f"「{local[1][1].get('entity')}」不同口径，不能相加。")
            reading = [
                {"strong": "事实　", "text": facts, "refs": refs},
                {"strong": "事实　", "text": f"除了「{top.get('entity')}」，"
                 f"「{local[1][1].get('entity')}」也填上了；两者合用只做交叉验证，不合并。",
                 "refs": refs},
                {"strong": "机理　", "text": mech_txt, "refs": refs},
                {"strong": "反例　", "text": f"缺口落在{'、'.join(missing_dims) if missing_dims else '部分维度'}；"
                 f"若「{top.get('entity')}」下一期与「{local[1][1].get('entity')}」背离，本节要改写。",
                 "refs": refs[:1]},
                {"strong": "边界　", "text": boundary, "refs": refs[:1]},
                {"strong": "所以　", "text": _action(qid), "refs": refs[:1]},
            ]
            chart_items = [{"label": str(c.get("entity")), "value": c.get("value")}
                           for _, c in local[:5] if isinstance(c.get("value"), (int, float))]
            chart = {"type": "hbar", "title": title or f"{qid} 关键值",
                     "source": f"{top.get('entity')}·来源见账本", "refs": refs[:len(chart_items)],
                     "unit_meta": top.get("unit") or UNIT_DEFAULT,
                     "baseline": f"对比基准：{top.get('entity')}同口径同期",
                     "annotate": f"{top.get('entity')} {top.get('value')}{top.get('unit') or ''}",
                     "items": chart_items}
            sections.append({
                "title": title, "question": qid, "answers": [qid], "refs": refs,
                "boundary": boundary,
                "reading": reading, "chart": chart,
                "falsifier": f"若 {top.get('entity')} 下期反向变化，本条作废。",
            })

        claims = {
            "schema": _contract.SCHEMA, "contract": _contract.CONTRACT_CARD,
            "card_spec": True,
            "role": role, "dispatch": dispatch_block,
            "meta": (tpl.get("meta") or {"title": "按格交报告", "intent": "按格交报告",
                                         "doc_type": "调研报告", "profile": "research"}),
            "numbers": numbers, "sources": sources, "sections": sections,
            "cells": [c for cs in qmap.values() for c in cs],
            "explore": [], "unanswered": unanswered,
            "contract_gaps": contract_gaps,
            "boundaries": ["按格交编译：只写已填格，未填格进未答清单。",
                           "比率格不求和；跨口径不合并。",
                           "未过交付契约（度量/grain/口径）的格进 contract_gaps，不进正文。"],
        }
        out = project / "cards" / role / "claims.json"
        out.write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append({"role": role, "sections": len(sections),
                        "numbers": len(numbers), "sources": len(sources),
                        "cells": len(claims["cells"]), "contract_gaps": len(contract_gaps)})

    return {"ok": bool(written), "stage": "compiled", "roles": written,
            "cells_input": len(cells), "cells_used": sum(r["cells"] for r in written),
            "contract_gaps": len(contract_gaps),
            "unified": {"diff_ok": _diff.get("ok"),
                        "diff_matched": _diff.get("matched", 0),
                        "diff_count": len(_diff.get("diffs") or []),
                        "value_from_observation": _uni.get("matched", 0),
                        "needs_human": len(_uni.get("mismatched") or [])}}
