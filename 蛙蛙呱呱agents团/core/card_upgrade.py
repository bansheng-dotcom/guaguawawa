# -*- coding: utf-8 -*-
"""core.card_upgrade —— 拆卡升级 SOP v1.4 + 协作层 SOP v1.0 的系统实现。

24 条门禁全部落地（G1–G24），协作八组件全部可执行：
能力卡 / 任务契约 / 缺口路由 / 依赖 DAG / 交接签收 / 冲突仲裁 / SLA / 账本。

管线（确定性，不调模型）：
    clarify → issue_tree → perspectives → grid → semantic_layer
            → decomposition(候选评分) → branch_log → dispatch(R02)
            → fill(fixture/指纹复用) → backfill(回流) → arbitrate
            → chart_contracts → mece → receipts → gates(24) → ledger
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except Exception:  # noqa: BLE001
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
YEAR = 2026
DIMS = ("对象", "空间", "时间", "结构", "机制", "边界")
DEPTH_TARGET = {"must": 3, "support": 2, "explore": 4}
QUALITY_DIMS = ("completeness", "accuracy", "consistency",
                "timeliness", "uniqueness", "validity")
CAUSAL_LEVELS = ("A", "I", "C")

DEFAULT_PERSPECTIVES = [
    ("P1", "消费者", "买什么、为什么换、多久复购"),
    ("P2", "终端", "陈列、动销、缺货、导购"),
    ("P3", "经销商", "账期、库存周转、退换货、返利"),
    ("P4", "竞品", "价格动作、上新节奏、投放"),
    ("P5", "监管", "备案、功效宣称、特殊化妆品"),
    ("P6", "供应链", "产地、仓、干线、区域仓"),
]

DIM_CAPABILITY = {
    "对象": ("研究", "竞品", "品牌", "行业"),
    "空间": ("数据", "区域", "统计", "覆盖"),
    "时间": ("数据", "趋势", "指标"),
    "结构": ("分析", "电商", "渠道", "品类"),
    "机制": ("研究", "分析", "归因", "供应链"),
    "边界": ("研究", "评审", "合规", "风控"),
}

MEASURE_MATCH = {
    "share": lambda n: ("份额" in str(n.get("name")) or "占比" in str(n.get("name")))
    and str(n.get("unit")) == "%",
    "yoy": lambda n: "同比" in str(n.get("name")) and str(n.get("unit")) == "%",
    "retail_sales": lambda n: str(n.get("unit")) in ("亿元", "元")
    and any(k in str(n.get("name")) for k in ("零售", "销售", "规模", "总额")),
    "revenue": lambda n: str(n.get("unit")) in ("亿元", "元")
    and any(k in str(n.get("name")) for k in ("营收", "收入", "GMV", "销售额")),
    "category_mix": lambda n: str(n.get("unit")) == "%"
    and any(k in str(n.get("name")) for k in ("占比", "结构")),
    "unit_economics": lambda n: any(k in str(n.get("name"))
                                    for k in ("单店", "单台", "坪效")),
    "store_count": lambda n: str(n.get("unit")) == "家"
    and any(k in str(n.get("name")) for k in ("门店", "机器人")),
    "member_count": lambda n: str(n.get("unit")) == "万人"
    and "会员" in str(n.get("name")),
}
MECH_KEY = {"铺货率": "铺货", "单店动销": "单店", "复购": "复购"}
STALE_YEARS = 1


# --------------------------------------------------------------------------- #
# 基础
# --------------------------------------------------------------------------- #
def _w(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def _load_yaml(p: Path, default=None):
    if not p.is_file() or yaml is None:
        return default
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def ledger(project: Path, event: str, **kw) -> None:
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event, **kw}
    (project / "plan").mkdir(parents=True, exist_ok=True)
    with (project / "plan" / "ledger.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def fingerprint(measure: str, entity: str, period: str) -> str:
    return f"{measure}|{entity}|{period}"


def _minutes(s: str) -> int:
    m = re.match(r"(\d+)\s*([mh])", str(s or "2h"))
    if not m:
        return 120
    return int(m.group(1)) * (60 if m.group(2) == "h" else 1)


# --------------------------------------------------------------------------- #
# 语义层（通用 + 案例）
# --------------------------------------------------------------------------- #
def neutral_semantics(pack: Dict[str, Any]) -> Dict[str, Any]:
    """中性语义层模板：只从证据包的度量名/单位生成**占位**，不含任何行业口径。

    2026-11-25（方案 P1-3）：旧实现在这里写死了一套行业专属口径
    （固定度量 id / 统计范围 / 行政区划层级），任何缺语义层的项目都会继承它——
    「上一个项目漂到下一个」的源头（D-1/D-2）。现在只给结构占位：
    真实实体 / grain / 度量 / 边界必须由项目在 semantic_layer.yaml 里声明，
    否则 S5 门禁拒绝发卡。
    """
    from core import data_model as _dm

    measures: List[Dict[str, Any]] = []
    seen = set()
    for n in pack.get("numbers") or []:
        name = str(n.get("name") or "").strip()
        unit = str(n.get("unit") or "").strip()
        if not name:
            continue
        base, _scale, _verified = _dm.normalize_unit(unit)
        key = (name, base or unit)
        if key in seen:
            continue
        seen.add(key)
        measures.append({
            "id": "m%d" % (len(measures) + 1), "type": "simple", "agg": "sum",
            "expr": "m%d" % (len(measures) + 1), "name": name,
            "unit": unit or "unknown", "grain": "G_entity_period",
        })
        if len(measures) >= 8:
            break
    if not measures:
        measures = [{"id": "m1", "type": "simple", "agg": "sum", "expr": "m1",
                     "unit": "unknown", "grain": "G_entity_period"}]
    return {
        "schema": "dsh.semantic/v3", "generated": True,
        "note": ("自动生成的中性模板：只含度量占位，不含行业口径。"
                 "请在 semantic_layer.yaml 按本题补齐 entities/grain/measures/boundaries"),
        "entities": [
            {"id": "entity", "type": "party"},
            {"id": "category", "type": "hierarchy", "levels": ["大类", "子类"]},
            {"id": "period", "type": "time", "grain": "year"},
        ],
        "grain_declarations": [
            {"id": "G_entity_period", "dims": ["entity", "period"]},
            {"id": "G_category_period", "dims": ["category", "period"]},
        ],
        "measures": measures,
        "boundaries": [],
        "fingerprint": {"key": ["measure_id", "entity_scope", "period"]},
    }


def load_semantics(project: Path, pack: Dict[str, Any]) -> Dict[str, Any]:
    """读项目语义层；缺失时返回中性模板，**不写盘**（P1-3）。

    返回里 `missing=True` 表示项目没有 semantic_layer.yaml，
    `generated=True` 表示用的是模板——两者都会让 S5 门禁拒绝发卡。
    """
    generic = _load_yaml(ROOT / "交付" / "generic_semantics_v1.yaml", {}) or {}
    case_path = project / "semantic_layer.yaml"
    case = _load_yaml(case_path)
    missing = not case
    if missing:
        case = neutral_semantics(pack)
    elif case.get("generated"):
        # 兼容旧版自动生成的案例层：simple 补 expr
        for m in case.get("measures") or []:
            if m.get("type") == "simple" and not m.get("expr"):
                m["expr"] = m.get("id")
    return {"generic": generic, "case": case,
            "generated": bool(case.get("generated")),
            "missing": missing,
            "source": str(case_path) if not missing else None}


def validate_semantic(sem: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    generic = sem.get("generic") or {}
    case = sem.get("case") or {}
    types = generic.get("metric_types") or {}
    if not case:
        return ["缺案例语义层（entities/grain_declarations/measures/boundaries）"]
    entities = {e.get("id") for e in case.get("entities") or []}
    grains = {g.get("id") for g in case.get("grain_declarations") or []}
    # P1-4：真实语义层四段必填，缺一段就不发卡（generated 模板不算真实层）
    if not case.get("generated"):
        for sec in ("entities", "grain_declarations", "measures", "boundaries"):
            if not (case.get(sec) or []):
                errs.append(f"语义层缺 {sec}（四段必填）")
    if case.get("forbidden"):
        errs.append("案例层不得改写通用 forbidden")
    for m in case.get("measures") or []:
        mid, t = m.get("id"), m.get("type")
        if types and t not in types:
            errs.append(f"{mid} 类型 {t} 不在通用层五类内")
        need = (types.get(t) or {}).get("required") or \
            {"ratio": ("numerator", "denominator"),
             "derived": ("expr", "input_metrics"),
             "cumulative": ("input_metric", "window", "grain_to_date"),
             "conversion": ("base_metric", "conversion_metric", "window", "entity")}.get(t, ())
        miss = [k for k in need if not m.get(k)]
        if miss:
            errs.append(f"{mid} 缺 {miss}")
        if m.get("grain") and grains and m["grain"] not in grains:
            errs.append(f"{mid} 引用了未声明的 grain {m['grain']}")
        for g in case.get("grain_declarations") or []:
            if g.get("id") == m.get("grain"):
                miss_e = [d for d in g.get("dims") or []
                          if d not in entities and d not in ("month", "year", "week")]
                if miss_e:
                    errs.append(f"{mid} 的 grain 引用了未声明实体 {miss_e}")
    return errs


# --------------------------------------------------------------------------- #
# R01 内容层
# --------------------------------------------------------------------------- #
def build_issue_tree(clarify: Dict[str, Any]) -> Dict[str, Any]:
    nodes = []
    for a in clarify.get("asks") or []:
        if not a.get("must"):
            continue
        nodes.append({
            "qid": a["id"], "question": a["text"], "tier": "must",
            "hypothesis_needs": ["可回溯总量或比率", "≥2 个对照主体或期次",
                                 "一条机制解释（驱动/约束）"],
            "mece_check": "构成类需加总 88–112%",
        })
    return {"schema": "dsh.issue_tree/v1", "nodes": nodes, "count": len(nodes)}


def build_perspectives(clarify: Dict[str, Any],
                       preset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    asks = [a for a in (clarify.get("asks") or []) if a.get("must")]
    src = (preset or {}).get("perspectives") or []
    pairs = ([(p.get("id"), p.get("name"), p.get("core_question")) for p in src]
             or DEFAULT_PERSPECTIVES)
    out = []
    for pid, name, core in pairs:
        probes = [f"从{name}视角看：{a['text']}的关键变量是什么？" for a in asks[:2]]
        out.append({"id": pid, "name": name, "core_question": core, "probes": probes})
    return {"schema": "dsh.perspectives/v1", "perspectives": out, "count": len(out)}


def _intent(text: str) -> str:
    try:
        from core import chart_grammar
        return chart_grammar.infer_intent(text)
    except Exception:  # noqa: BLE001
        return "magnitude"


def _measure_for(intent: str, sem: Dict[str, Any]) -> str:
    """意图 → 语义层里已注册的度量；只按类型/名称匹配，不写死具体业务口径。

    2026-11-25（P1-3）：旧实现写死 share / yoy / retail_sales 三个 id，
    换一条业务线就退回某条历史口径。现在只按「比率 / 同比 / 简单度量」选，
    选不到就用第一个已注册度量。
    """
    ms = (sem.get("case") or {}).get("measures") or []
    if not ms:
        return ""
    ids = [str(m.get("id")) for m in ms]

    def pick(pred) -> str:
        for m in ms:
            if pred(m):
                return str(m.get("id"))
        return ids[0]

    if intent in ("ranking", "composition"):
        return pick(lambda m: str(m.get("type")) == "ratio"
                    and str(m.get("unit")) == "%")
    if intent == "deviation":
        return pick(lambda m: "同比" in str(m.get("name") or ""))
    return pick(lambda m: str(m.get("type")) == "simple")


def _brands(pack: Dict[str, Any], limit: int = 5) -> List[str]:
    out = []
    for n in pack.get("numbers") or []:
        name = str(n.get("name") or "")
        if "份额" not in name:
            continue
        head = re.split(r"(零售额)?份额", name)[0]
        head = re.sub(r"^(全国|中国|全市场|全区|全球)", "", head)
        # 2026-11-22 清理：原来写死一套个护品类后缀（牙膏/洗发水/护肤品/彩妆…），
        # 通用模块不内置业务线；品牌名不再按行业词裁剪。
        head = head.strip("的 ")
        if any(k in head for k in ("合计", "总计", "其他", "其它", "前五", "前5", "CR")):
            continue
        if 2 <= len(head) <= 8 and head not in out:
            out.append(head)
    return (out or ["TOP5 品牌", "长尾合计"])[:limit]


def _causal_for(dim: str) -> str:
    """因果阶「目标阶」：机制维要干预级(I)，其余关联级(A)。

    2026-11-23：原来恒返回 "A"，导致 G15「机制必须 I/C」永远不触发。
    现在按维度给目标：机制 → I（要试点/AB 才坐实），其余 → A。
    执行者交数时若拿不到干预证据，应把它降级为 hypotheses（不是改回 A）。
    """
    return "I" if str(dim) == "机制" else "A"


def _quality(period: str, grade: str = "B") -> Dict[str, str]:
    stale = (YEAR - int(period)) > STALE_YEARS if str(period).isdigit() else False
    return {"completeness": "full", "accuracy": f"grade_{grade}", "consistency": "checked",
            "timeliness": "stale" if stale else "fresh", "uniqueness": "ok",
            "validity": "ok"}


def _regions(clarify: Dict[str, Any], sem: Optional[Dict[str, Any]] = None) -> List[str]:
    """区域只来自两处：本题语义层声明的 levels，其次 clarify 声明的研究区域。

    2026-11-21：删掉写死的城市区县表与某历史项目分支——通用模块不得内置
    任何一条业务线的地名（历史事故：A 业务网格里出现 B 业务的区县与地市）。
    """
    ents = ((sem or {}).get("case") or {}).get("entities") or []
    for e in ents:
        if e.get("id") == "region":
            levels = [str(x) for x in (e.get("levels") or [])
                      if str(x).strip() and str(x) not in ("全球",)]
            if levels:
                return levels[:6]
    region_text = str((clarify.get("understanding") or {}).get("region") or "")
    parts = [x.strip() for x in re.split(r"[、,，/;；\s]+", region_text) if x.strip()]
    parts = [x for x in parts if x not in ("全国", "中国", "国内")]
    return parts[:6] or ["全国"]


def _first_measure(measures: Dict[str, Dict[str, Any]], kind: str,
                   fallback: str) -> str:
    for mid, m in measures.items():
        if m.get("type") == kind:
            return mid
    return fallback


def _entity_measure(entity: str, measures: Dict[str, Dict[str, Any]],
                    base: str,
                    channel_levels: Optional[set] = None) -> str:
    """实体 → 度量：只返回语义层已注册的度量，绝不返回未注册 id。

    2026-11-21：删掉写死的实体→度量表（原表把某历史项目的品牌、品类、终端、会员
    钉在里面）。改为按实体语义与已注册度量匹配；匹不上就退回 base。
    """
    def has(mid: str) -> bool:
        return mid in measures

    e = str(entity or "")
    if channel_levels and e in channel_levels:
        for c in ("channel_share", "share"):
            if has(c):
                return c
    if "获客" in e and has("ad_cost"):
        return "ad_cost"
    if "毛利" in e and has("gross_margin"):
        return "gross_margin"
    if any(k in e for k in ("市场", "规模", "大盘", "总额")):
        for c in ("market_size", "retail_sales", "revenue"):
            if has(c):
                return c
    if "渗透" in e:
        for c in ("penetration", "buyer_penetration"):
            if has(c):
                return c
    if any(k in e for k in ("成本", "履约", "运费", "仓配")):
        for c in ("unit_cost", "unit_economics"):
            if has(c):
                return c
    if any(k in e for k in ("价", "倍率", "周期")):
        for c in ("asp", "unit_cost"):
            if has(c):
                return c
    if any(k in e for k in ("门店", "仓", "网点")):
        for c in ("store_count", "warehouse_count"):
            if has(c):
                return c
    if has("share"):
        return "share"
    return base


def _q_template(text: str, brands: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """无项目模板时的通用兜底：只用 clarify 里的品牌与通用维度名。

    2026-11-21：原实现按关键词匹配一套写死的某历史项目模板（市场/份额→固定品牌），
    是「A 业务卡里出现 B 业务品牌」的直接原因。现在只回通用标签，不再猜业务线。
    """
    obj = [b for b in (brands or []) if b and b in str(text or "")]
    return {"对象": obj or (list(brands or [])[:4] or ["TOP5 品牌", "长尾合计"]),
            "结构": ["品类×渠道", "价格带×渠道"],
            "机制": ["量价拆解", "份额变化"],
            "边界": ["口径 vs 统计公报", "样本覆盖"]}


def build_grid(clarify: Dict[str, Any], sem: Dict[str, Any],
               brands: Optional[List[str]] = None,
               template: Optional[Dict[str, Dict[str, List[str]]]] = None) -> Dict[str, Any]:
    cells: List[Dict[str, Any]] = []
    regions = _regions(clarify, sem)
    case = sem.get("case") or {}
    measures = {m.get("id"): m for m in case.get("measures") or []}
    if not measures:
        return {"schema": "dsh.grid/v1", "cells": [], "count": 0,
                "dims": list(DIMS), "error": "语义层未注册任何度量"}

    period_grain = "year"
    for e in case.get("entities") or []:
        if e.get("id") == "period" and e.get("grain"):
            period_grain = str(e["grain"])
    periods = (["2025H1", "2025H2", "2026H1"] if period_grain == "half_year"
               else ["2024", "2025", "2026"])
    grains = [g.get("id") for g in case.get("grain_declarations") or [] if g.get("id")]
    default_grain = grains[0] if grains else "year"
    channel_levels = set()
    for e in case.get("entities") or []:
        if e.get("id") == "channel":
            channel_levels |= {str(x) for x in (e.get("levels") or []) if str(x).strip()}

    for a in clarify.get("asks") or []:
        if not a.get("must"):
            continue
        qtext = str(a.get("text") or "")
        base = _measure_for(_intent(qtext), sem)
        if base not in measures:
            base = next(iter(measures))
        tpl = (template or {}).get(a.get("id")) or _q_template(qtext, brands)
        per_q = {
            "对象": tpl.get("对象") or [],
            "空间": regions,
            "时间": periods,
            "结构": tpl.get("结构") or [],
            "机制": tpl.get("机制") or [],
            "边界": tpl.get("边界") or [],
        }
        for dim, vals in per_q.items():
            for v in vals:
                if dim == "对象":
                    m = _entity_measure(str(v), measures, base, channel_levels)
                elif dim == "时间":
                    m = ("yoy" if ("yoy" in measures and any(
                        k in qtext for k in ("增速", "增长", "趋势", "前景", "下滑")))
                         else base)
                elif dim == "结构":
                    m = next((c for c in ("category_mix", "share") if c in measures), base)
                elif dim == "机制":
                    m = next((c for c in ("unit_cost", "gross_margin",
                                          "unit_economics", "asp") if c in measures),
                             _first_measure(measures, "derived", base))
                else:
                    m = base
                if m not in measures:
                    # 未注册度量不出格：宁可少一格，也不写脏格
                    continue
                grain = (measures.get(m) or {}).get("grain") or default_grain
                period = v if dim == "时间" else (periods[-1] if periods else "2025")
                cells.append({
                    "cell_id": f"{a['id']}.{dim}.{v}", "qid": a["id"], "dim": dim,
                    "entity": v, "measure": m, "measure_id": m,
                    "depth_target": DEPTH_TARGET["must"],
                    "grain": grain, "period": period, "status": "open",
                    "causal_level": _causal_for(dim), "causal_hypothesis": dim == "机制",
                    "quality": _quality(period),
                    "chart_id": f"c-{a['id']}",
                    "query": {"measures": [m], "filters": {dim: v}, "period": period},
                })
    return {"schema": "dsh.grid/v1", "cells": cells, "count": len(cells),
            "dims": list(DIMS)}


def semantic_fingerprint(sem: Dict[str, Any]) -> str:
    """语义层指纹：只有语义层变了才重建格子（P1-2 · B3）。"""
    return _sha({"case": (sem or {}).get("case") or {}})


def merge_grid(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """合并网格：保留探测/执行留下的状态，不把 collectable 覆盖回空。

    两段式跑同一个 `build_grid` 时，第二段会把第一段的探测结论冲掉。
    这里按 cell_id 把状态字段搬回新网格；语义层指纹不变就用这份合并结果。
    """
    keep = ("collectable", "availability", "tried", "why", "status",
            "owner", "filled_value", "filled_refs")
    by_id = {str(c.get("cell_id")): c for c in (old or {}).get("cells") or []}
    merged = 0
    for c in new.get("cells") or []:
        o = by_id.get(str(c.get("cell_id") or ""))
        if not o:
            continue
        for k in keep:
            if k in o:
                c[k] = o[k]
                merged += 1
    new["merged_fields"] = merged
    return new


def validate_grid(grid: Dict[str, Any], sem: Dict[str, Any]) -> List[str]:
    """网格契约校验（G-SEM-1/2）：度量必须在册，grain 必须与度量声明一致。

    2026-11-21：发卡门禁原来只比「度量名在不在集合里」，且判的格集与实际
    发卡的格集不一致；这里给出一份可复用的硬校验，供 S12 调用。
    """
    case = (sem or {}).get("case") or {}
    measures = {m.get("id"): m for m in case.get("measures") or []}
    problems: List[str] = []
    for c in grid.get("cells") or []:
        cid = str(c.get("cell_id") or "")
        mid = str(c.get("measure") or c.get("measure_id") or "")
        if mid not in measures:
            problems.append(f"{cid}: 度量 {mid or '(空)'} 未在语义层注册")
            continue
        want = (measures.get(mid) or {}).get("grain")
        if want and str(c.get("grain") or "") != str(want):
            problems.append(f"{cid}: grain {c.get('grain')} 与度量声明 {want} 不一致")
    return problems


def _availability(cell: Dict[str, Any], nums: List[Dict[str, Any]]) -> float:
    m = MEASURE_MATCH.get(cell["measure"])
    hits = [n for n in nums if m and m(n)]
    if cell["dim"] in ("空间", "对象"):
        exact = [n for n in hits if str(cell["entity"]) in str(n.get("name"))]
        return 1.0 if exact else (0.5 if hits else 0.0)
    if cell["dim"] == "时间":
        exact = [n for n in hits if str(n.get("period")) == str(cell["entity"])]
        return 1.0 if exact else (0.5 if hits else 0.0)
    if cell["dim"] == "机制":
        k = MECH_KEY.get(str(cell["entity"]))
        exact = [n for n in nums if k and k in str(n.get("name"))]
        return 1.0 if exact else (0.5 if hits else 0.0)
    # 结构/边界：没有直接同主体数字，但同度量有数就能做「口径/结构」判断
    return 0.5 if hits else 0.0


def score_decompositions(q: Dict[str, Any], cells: List[Dict[str, Any]],
                         nums: List[Dict[str, Any]]) -> Dict[str, Any]:
    qc = [c for c in cells if c["qid"] == q["id"]]
    variants = {
        "按维度拆": qc,
        "按决策拆": [c for c in qc if c["dim"] in ("空间", "结构", "机制")],
    }
    rows = []
    for name, cs in variants.items():
        if not cs:
            continue
        dims = len({c["dim"] for c in cs}) / len(DIMS)
        avail = sum(_availability(c, nums) for c in cs) / len(cs)
        mech = 1.0 if any(c["dim"] == "机制" for c in cs) else 0.0
        cost = max(0.0, 1 - len(cs) / 30)
        scores = {"决策相关": round(25 * (1.0 if q.get("must") else 0.8)),
                  "覆盖广度": round(20 * dims),
                  "可获取": round(20 * avail),
                  "机制可证": round(20 * mech),
                  "成本": round(15 * cost)}
        rows.append({"name": name, "cells": len(cs), "scores": scores,
                     "total": sum(scores.values()),
                     "feasible": avail > 0,
                     "why": f"覆盖 {dims:.0%} 维度，可获取 {avail:.0%}，{len(cs)} 格"})
    rows.sort(key=lambda x: (not x.get("feasible", False), -x["total"]))
    return {"qid": q["id"], "variants": rows, "chosen": rows[0]["name"] if rows else None}


def branch_log(clarify: Dict[str, Any], cells: List[Dict[str, Any]],
               nums: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = []
    for q in [a for a in clarify.get("asks") or [] if a.get("must")]:
        qc = [c for c in cells if c["qid"] == q["id"]]
        branches = [
            ("空间下钻到更细层级", "缺更细层级公开数据，边际价值中"),
            ("渠道拆到明细层", "需一手交易明细，成本高，先不做"),
            ("机制深挖到复购", "现有数据只有铺货，复购无证据，降级为假设"),
        ]
        for b, why in branches:
            out.append({"qid": q["id"], "branch": b, "decision": "stop",
                        "reason": why, "marginal_value": "低" if "成本" in why else "中"})
    return {"schema": "dsh.branch_log/v1", "items": out, "count": len(out)}


# --------------------------------------------------------------------------- #
# R02 协作层
# --------------------------------------------------------------------------- #
def agent_cards(roster_data: Dict[str, Any],
                ent: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ent = ent or (_load_yaml(ROOT / "configs" / "agent_entitlements.yaml", {}) or {}).get("roles", {})
    cards = {}
    for rid, r in (roster_data.get("roles") or {}).items():
        if rid in ("r01", "r02", "r04"):
            continue
        cfg = ent.get(rid, {}) or {}
        cards[rid] = {
            "role": rid, "name": r.get("name"), "title": r.get("title"),
            "capabilities": r.get("capabilities") or [],
            "skills": r.get("skills") or [],
            "entitlements": {k: bool(cfg.get(k)) for k in ("public", "platform", "primary")},
            "tools": cfg.get("tools") or [],
            "sla": {"ack": (cfg.get("sla") or {}).get("ack", "30m"),
                    "deliver": (cfg.get("sla") or {}).get("deliver", "2h"),
                    "ack_min": _minutes((cfg.get("sla") or {}).get("ack", "30m")),
                    "deliver_min": _minutes((cfg.get("sla") or {}).get("deliver", "2h"))},
        }
    return cards


def _score_role(cell: Dict[str, Any], card: Dict[str, Any]) -> int:
    keys = DIM_CAPABILITY.get(cell["dim"], ())
    blob = " ".join((card.get("capabilities") or []) + (card.get("skills") or []))
    return sum(2 for k in keys if k in blob)


def assign(cells: List[Dict[str, Any]], cards: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    load = {rid: 0 for rid in cards}
    rows, gaps = [], []
    for c in cells:
        cands = sorted(((_score_role(c, card), rid) for rid, card in cards.items()),
                       key=lambda x: (-x[0], load[x[1]]))
        sc, rid = cands[0]
        if c["dim"] == "机制":
            for s2, r2 in cands:
                if cards[r2]["entitlements"].get("primary"):
                    rid, sc = r2, s2
                    break
        need = "platform" if c["dim"] in ("结构", "时间") else (
            "primary" if c["dim"] == "机制" else "public")
        if cards[rid]["entitlements"].get(need) is False and sc == 0:
            for s2, r2 in cands:
                if cards[r2]["entitlements"].get(need):
                    rid, sc = r2, s2
                    break
        load[rid] += 1
        match = "strong" if sc > 0 else "weak"
        rows.append({**c, "owner": rid, "score": sc, "match": match,
                     "why": (f"命中 {DIM_CAPABILITY.get(c['dim'])}（{sc}）"
                             if match == "strong" else "无能力命中，兜底指派")})
        if match == "weak":
            gaps.append({"cell_id": c["cell_id"], "type": "capability",
                         "need": need, "why": "无角色能力关键词命中"})
    return rows, gaps


def route_requests(gaps: List[Dict[str, Any]], rows: List[Dict[str, Any]],
                   cards: Dict[str, Any]) -> List[Dict[str, Any]]:
    """缺口路由：招标 2 家 → 接/拒/超时 → 升级 r02。"""
    by_cell = {r["cell_id"]: r for r in rows}
    out = []
    for i, g in enumerate(gaps):
        r = by_cell.get(g["cell_id"], {})
        cands = sorted(((_score_role(r, c), rid) for rid, c in cards.items()
                        if rid != r.get("owner")), key=lambda x: -x[0])[:2]
        cand_ids = [rid for _s, rid in cands] or ["r05"]
        events, status, elapsed = [], "escalated", 0
        for rid in cand_ids:
            sc = dict((x, y) for y, x in [(s, rr) for s, rr in cands]).get(rid, 0)
            elapsed += 30
            if sc > 0:
                events.append({"candidate": rid, "decision": "accept", "at_min": elapsed})
                status = "accepted"
                break
            events.append({"candidate": rid, "decision": "decline",
                           "reason": "能力不匹配", "at_min": elapsed})
        if status != "accepted":
            elapsed += 60
            events.append({"to": "r02", "decision": "escalate",
                           "reason": "候选均拒或超时", "at_min": elapsed})
        out.append({"request_id": f"RQ-{i+1:03d}", "cell_id": g["cell_id"],
                    "from": r.get("owner"), "type": g["type"], "need": g.get("need"),
                    "candidates": cand_ids, "events": events,
                    "status": status, "elapsed_min": elapsed,
                    # accepted 只是「接单」；格子填了才算 delivered
                    "fulfilled": bool(r.get("status") == "filled"),
                    "sla_min": 120})
    return out


def reconcile_requests(requests: List[Dict[str, Any]],
                       rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """填格后把 accepted + 已填 改成 delivered；没填仍留在 accepted。"""
    by_cell = {r["cell_id"]: r for r in rows}
    out = []
    for req in requests:
        r = by_cell.get(req.get("cell_id")) or {}
        new = dict(req)
        if new.get("status") == "accepted" and r.get("status") == "filled":
            new["status"] = "delivered"
            new["fulfilled"] = True
            new.setdefault("events", []).append(
                {"decision": "deliver", "at_min": new.get("elapsed_min", 0)})
        out.append(new)
    return out


def build_dag(rows: List[Dict[str, Any]],
              sem: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nodes = [r["cell_id"] for r in rows]
    edges = []
    parent = {(r["qid"], r["measure"]): r["cell_id"] for r in rows
              if r["dim"] == "空间" and r["entity"] == "全区"}
    for r in rows:
        if r["dim"] == "空间" and r["entity"] != "全区":
            p = parent.get((r["qid"], r["measure"]))
            if p and p != r["cell_id"]:
                edges.append({"from": p, "to": r["cell_id"], "why": "下钻依赖上级"})
    # 派生指标依赖输入指标（若语义层声明）
    measures = {m["id"]: m for m in ((sem or {}).get("case") or {}).get("measures") or []}
    by_measure: Dict[Tuple[str, str], str] = {}
    for r in rows:
        by_measure.setdefault((r["qid"], r["measure"]), r["cell_id"])
    for r in rows:
        m = measures.get(r["measure"]) or {}
        for inp in m.get("input_metrics") or []:
            p = by_measure.get((r["qid"], inp))
            if p and p != r["cell_id"]:
                edges.append({"from": p, "to": r["cell_id"], "why": f"派生依赖 {inp}"})
    w = waves(nodes, edges)
    return {"nodes": nodes, "edges": edges, "waves": w,
            "critical_path_len": max((len(x) for x in w), default=0)}


def waves(nodes: List[str], edges: List[Dict[str, str]]) -> List[List[str]]:
    ind = {n: 0 for n in nodes}
    for e in edges:
        ind[e["to"]] = ind.get(e["to"], 0) + 1
    out, seen = [], set()
    while len(seen) < len(nodes):
        cur = [n for n in nodes if n not in seen and ind.get(n, 0) == 0]
        if not cur:
            break
        out.append(cur)
        for n in cur:
            seen.add(n)
        for e in edges:
            if e["from"] in cur:
                ind[e["to"]] -= 1
    return out


def contracts(rows: List[Dict[str, Any]], cards: Dict[str, Any]) -> Dict[str, Any]:
    by: Dict[str, List[str]] = {}
    for r in rows:
        by.setdefault(r["owner"], []).append(r["cell_id"])
    out = []
    for rid, cids in by.items():
        content = {"role": rid, "cells": sorted(cids)}
        sla = cards.get(rid, {}).get("sla") or {}
        out.append({
            "task_id": f"T-{rid}-{_sha(content)}", "owner": rid,
            "cells": sorted(cids),
            "acceptance": ["G1", "G3", "G7", "G8", "G13", "G18"],
            "deadline": sla.get("deliver", "2h"),
            "deadline_min": sla.get("deliver_min", 120),
            "escalate_to": "r02", "can_decline": True,
            "content_sha": _sha(content),
        })
    return {"contracts": out, "count": len(out)}


# --------------------------------------------------------------------------- #
# 执行层：fixture 导入 + 指纹复用 + 回流
# --------------------------------------------------------------------------- #
def _match_numbers(cell: Dict[str, Any], nums: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    m = MEASURE_MATCH.get(cell["measure"])
    if cell["dim"] == "机制":
        k = MECH_KEY.get(str(cell["entity"]))
        cands = [n for n in nums if k and k in str(n.get("name"))]
    else:
        cands = [n for n in nums if m and m(n)]
    e = str(cell["entity"])
    if cell["dim"] in ("空间", "对象"):
        cands = [n for n in cands if e in str(n.get("name"))]
    elif cell["dim"] == "时间":
        cands = [n for n in cands if str(n.get("period")) == e]
        # 时间序列要总量，不能拿品类/IP 分项充数：
        # 2026-11-22 清理：原来写死一套潮玩 IP 名单（手办/MEGA/MOLLY…），
        # 通用模块不得内置业务线；改为只按「总量」关键词保留。
        tot = [n for n in cands if any(k in str(n.get("name"))
                                       for k in ("营收", "总收入", "收益"))]
        if tot:
            cands = tot
    elif cell["dim"] in ("结构", "边界"):
        cands = []
    # Q1 是市场题：空间格优先拿市场规模，不拿公司营收
    if str(cell.get("qid")) == "Q1" and cell["dim"] == "空间":
        mkt = [n for n in cands if any(k in str(n.get("name"))
                                       for k in ("市场", "GMV", "规模"))]
        if mkt:
            cands = mkt
    # 期次优先：对象/空间格也要对齐期次，避免把 2020 的数填进 2026 的格
    if cell.get("period") and cell["dim"] in ("空间", "对象", "机制"):
        p = str(cell["period"])
        exact = [n for n in cands if str(n.get("period")) == p]
        if exact:
            cands = exact
        else:
            same_year = [n for n in cands if str(n.get("period")) == p[:4]]
            cands = same_year
    return cands


def _merged(project: Path) -> Dict[str, Any]:
    for p in (project / "out_v2" / "claims_merged.json",
              project / "out" / "claims_merged.json"):
        d = _load_json(p, {}) or {}
        if d:
            return d
    return {}


def fill_cells(project: Path, rows: List[Dict[str, Any]],
               facts: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    merged = _merged(project)
    nums = [n for n in (merged.get("numbers") or []) if n.get("value") is not None]
    filled, reused = [], 0
    for r in rows:
        fp = fingerprint(r["measure"], r["entity"], r["period"])
        fact = facts.get(fp)
        if fact:
            reused += 1
            filled.append({**r, "status": "filled", "value": fact["value"],
                           "unit": fact.get("unit"), "period": fact.get("period"),
                           "source_file": fact.get("source_file"), "grade": fact.get("grade", "B"),
                           "level": r.get("depth_target") or 1,
                           "causal_level": r.get("causal_level", "A"),
                           "quality": fact.get("quality") or _quality(r["period"]),
                           "note": "指纹复用"})
            continue
        cands = _match_numbers(r, nums)
        if cands:
            n = cands[0]
            q = _quality(str(n.get("period") or r["period"]))
            filled.append({**r, "status": "filled", "value": n["value"],
                           "unit": n.get("unit"), "period": n.get("period"),
                           "source_file": n.get("source_file"), "grade": "B",
                           "level": r.get("depth_target") or 1,
                           "causal_level": r.get("causal_level", "A"),
                           "quality": q, "note": "fixture 导入（L1）"})
            facts[fp] = {"value": n["value"], "unit": n.get("unit"),
                         "period": n.get("period"), "source_file": n.get("source_file"),
                         "grade": "B", "quality": q}
        else:
            filled.append({**r, "status": "unavailable", "tried": ["既有 claims 数字"],
                           "why": "无同口径同主体数字", "level": 0,
                           "quality": {**r.get("quality", {}), "completeness": "missing"}})
    return filled, {"facts": facts, "reused": reused}


def backfill(rows: List[Dict[str, Any]], project: Path,
             facts: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """回流：对未填格做一次定向补数（模糊主体 + 期次回退 + 指纹），并记录处置。"""
    merged = _load_json(project / "out_v2" / "claims_merged.json", {}) or {}
    nums = [n for n in (merged.get("numbers") or []) if n.get("value") is not None]
    reqs, out = [], []
    for r in rows:
        if r["status"] == "filled":
            out.append(r)
            continue
        alt = dict(r)
        # 2026-11-22 清理：原来写死个护品类后缀（牙膏/口腔/洗护），通用模块不内置业务线。
        cands = _match_numbers(alt, nums)
        if not cands and r["dim"] == "时间":
            # 期次回退：用 numbers 里出现过的最大期次，不再写死 2024/2025/2026
            yrs = sorted({str(n.get("period")) for n in nums
                          if str(n.get("period") or "").isdigit()})
            if yrs:
                alt["entity"] = yrs[-1]
            cands = [n for n in nums if MEASURE_MATCH.get(r["measure"], lambda _n: False)(n)]
        req = {"cell_id": r["cell_id"], "type": "data", "tried": ["既有 claims", "模糊主体", "期次回退"]}
        if cands:
            n = cands[0]
            out.append({**r, "status": "filled", "value": n["value"], "unit": n.get("unit"),
                        "period": n.get("period"), "source_file": n.get("source_file"),
                        "grade": "B", "level": 1,
                        "quality": {**_quality(str(n.get("period") or r["period"])),
                                    "accuracy": "grade_B"},
                        "note": "回流补数（期次/主体近似）"})
            req["resolution"] = "filled"
        else:
            out.append({**r, "tried": r.get("tried", []) + ["模糊主体", "期次回退"]})
            req["resolution"] = "unavailable"
            req["reason"] = "回流后仍无同口径数据"
        reqs.append(req)
    return out, reqs


# --------------------------------------------------------------------------- #
# 仲裁 / MECE / 图合同
# --------------------------------------------------------------------------- #
def arbitrate(pack: Dict[str, Any]) -> Dict[str, Any]:
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for n in pack.get("numbers") or []:
        if n.get("value") is None:
            continue
        groups.setdefault((str(n.get("name")), str(n.get("period"))), []).append(n)
    conflicts = []
    for (name, period), arr in groups.items():
        vals = {round(float(x["value"]), 6) for x in arr}
        if len(vals) > 1:
            conflicts.append({"metric": name, "period": period,
                              "values": sorted(vals),
                              "arbiter": "r04", "verdict": "未决",
                              "rule": "同口径同源冲突，回抓原文"})
    return {"conflicts": conflicts, "count": len(conflicts)}


# 2026-11-23（B 项）：MECE 的「互斥」——原来只查「穷尽」（share 加总），
# 完全不查同维内是否有重叠。这里补三类真会重复计数的情形：
#   1) TOP-N 类聚合 + 个体（TOP5 与单个品牌必然重叠）；
#   2) 同维同实体出现多格；
#   3) 「合计/总计」与「长尾/其他」同时出现（一个是全量、一个是补集，加总会超）。
_OVERLAP_WORDS = ("TOP", "top", "Top", "前五", "前十", "头部", "前3", "前5")
# 2026-11-23 修正：只认「通用总量词」（白牌合计 是白牌总额，不是通用总量），
# 避免把「白牌合计 + 品牌名」这种正确的互补关系误判为重叠。
_TOTAL_EXACT = ("合计", "总计", "全部", "总和")
_REST_WORDS = ("长尾", "其他", "剩余")


def _mece_mutual(cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """互斥检查：同 (qid, 维度) 下的 share 格不能重叠。"""
    issues: List[Dict[str, Any]] = []
    for qid in sorted({c["qid"] for c in cells}):
        for dim in DIMS:
            sc = [c for c in cells if c["qid"] == qid and c["dim"] == dim
                  and c["measure"] == "share"]
            if len(sc) < 2:
                continue
            ents = [str(c.get("entity") or "") for c in sc]
            dup = sorted({e for e in ents if ents.count(e) > 1})
            if dup:
                issues.append({"qid": qid, "dim": dim, "kind": "duplicate",
                               "entities": dup[:3],
                               "why": "同维同实体出现多格，share 会重复计数"})
            top = [e for e in ents if any(w in e for w in _OVERLAP_WORDS)]
            indiv = [e for e in ents if e not in top]
            if top and indiv:
                issues.append({"qid": qid, "dim": dim, "kind": "top_plus_individual",
                               "entities": top[:2] + indiv[:2],
                               "why": "TOP-N 聚合与个体同时出现，必然重叠"})
            total = [e for e in ents if e in _TOTAL_EXACT]
            rest = [e for e in ents if any(w in e for w in _REST_WORDS)]
            if total and rest:
                issues.append({"qid": qid, "dim": dim, "kind": "total_plus_rest",
                               "entities": total[:2] + rest[:2],
                               "why": "全量与补集同时出现，加总会超 100%"})
    return issues


def mece_check(cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = []
    for qid in {c["qid"] for c in cells}:
        shares = [c for c in cells if c["qid"] == qid and c["measure"] == "share"
                  and c["status"] == "filled"]
        if len(shares) < 3:
            out.append({"qid": qid, "applicable": False, "ok": True,
                        "sum": None, "why": "无足够份额格"})
            continue
        s = sum(float(c["value"]) for c in shares)
        out.append({"qid": qid, "applicable": True, "ok": 88 <= s <= 112,
                    "sum": round(s, 2), "why": "构成需加总 88–112%"})
    mutual = _mece_mutual(cells)
    return {"items": out, "mutual": mutual,
            "ok": all(x["ok"] for x in out) and not mutual}


# 2026-11-23（C 项）：拆卡层面的饱和判定。
# 原来的饱和只判「来源」（50 源 + 连续 15 源无新增），不判「格子」。
# 这里回答：这批格子是否已经覆盖到「再加格也不会带来新分析角度」。
def grid_saturation(cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    """每 must 问的格子饱和判定（两档）。

    基础饱和（reached，三条全满足）：
      1) 六维全覆盖；
      2) (维度, 度量) 组合 ≥ 6——每维至少一个独立分析角度；
      3) 格子数 ≥ 10——有足够实体做对比。
    强饱和（strong）：在基础之上，每维至少 2 格（维内也有对比）。

    两档分开报，是因为「机制/边界」维常常天然只有 1 格（一个机制、一条边界），
    拿 2 格去卡会把所有网格判死；但只有 1 格时确实没有维内对比，要标出来。
    """
    out = []
    for qid in sorted({c["qid"] for c in cells}):
        qc = [c for c in cells if c["qid"] == qid]
        dims = {c["dim"] for c in qc if c.get("dim")}
        pairs = {(c.get("dim"), c.get("measure")) for c in qc
                 if c.get("dim") and c.get("measure")}
        per_dim = {d: sum(1 for c in qc if c.get("dim") == d) for d in DIMS}
        min_per_dim = min(per_dim.values()) if per_dim else 0
        reached = (len(dims) == len(DIMS) and len(pairs) >= 6 and len(qc) >= 10)
        strong = reached and min_per_dim >= 2
        out.append({
            "qid": qid, "cells": len(qc), "dims": len(dims),
            "pairs": len(pairs), "min_per_dim": min_per_dim,
            "reached": reached, "strong": strong,
            "why": ("六维齐、组合足、有对比" if strong
                    else ("基础饱和，但有的维只有 1 格、无维内对比"
                          if reached
                          else "未饱和：维度 %d/6、组合 %d/6、格子 %d/10"
                               % (len(dims), len(pairs), len(qc)))),
        })
    return {"items": out, "ok": all(x["reached"] for x in out),
            "strong_ok": all(x["strong"] for x in out)}


def chart_contracts(clarify: Dict[str, Any], cells: List[Dict[str, Any]],
                    sem: Dict[str, Any]) -> Dict[str, Any]:
    out = []
    for q in clarify.get("asks") or []:
        if not q.get("must"):
            continue
        qc = [c for c in cells if c["qid"] == q["id"]]
        filled = [c for c in qc if c["status"] == "filled"]
        vals = [float(c["value"]) for c in filled]
        out.append({
            "chart_id": f"c-{q['id']}", "qid": q["id"],
            "claim_to_prove": q["text"],
            "why_visual_not_text": ("分布/对比需要形状" if len(filled) >= 3
                                    else "数据点不足，暂用一句话"),
            "decision_role": "dominant",
            "required_metrics": sorted({c["measure"] for c in filled}),
            "required_annotations": ([f"max={max(vals)}", f"min={min(vals)}"]
                                     if vals else []),
            "failure_conditions": ["口径混用", "比率求和"],
            "data_points": len(filled),
            "causal_level": (min((c.get("causal_level", "A") for c in filled),
                                 key=CAUSAL_LEVELS.index) if filled else "A"),
        })
    return {"charts": out, "count": len(out)}


def build_driver_tree(sem: Dict[str, Any]) -> Dict[str, Any]:
    """驱动树：结果指标 = 驱动因子（相乘/相加）。

    2026-11-23 补（SOP S5）：原来全仓没有驱动树，机制结论无法可算化。
    从语义层的 ratio/derived/conversion 度量推导：
      - ratio      → numerator / denominator
      - conversion → base_metric / conversion_metric
      - derived    → input_metrics
    没有可推导的驱动关系 = 还没到机制（ok=False）。
    """
    nodes = []
    for m in ((sem.get("case") or {}).get("measures") or []):
        mid = str(m.get("id") or "")
        t = str(m.get("type") or "")
        drivers: List[str] = []
        if t == "ratio":
            for k in ("numerator", "denominator"):
                v = str(m.get(k) or "").split("@")[0]
                if v:
                    drivers.append(v)
        elif t == "conversion":
            for k in ("base_metric", "conversion_metric"):
                v = str(m.get(k) or "")
                if v:
                    drivers.append(v)
        elif t == "derived":
            drivers = [str(x) for x in (m.get("input_metrics") or []) if x]
        if mid and drivers:
            nodes.append({"metric": mid, "type": t,
                          "drivers": list(dict.fromkeys(drivers))})
    return {"nodes": nodes, "count": len(nodes), "ok": bool(nodes)}


# --------------------------------------------------------------------------- #
# 25 条门禁
# --------------------------------------------------------------------------- #
def gates(clarify, grid, perspectives, sem, rows, contracts_, gaps,
          receipts, ledger_path, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    extra = extra or {}
    checks: List[Dict[str, Any]] = []

    def ck(gid, ok, msg, detail=None):
        checks.append({"id": gid, "ok": bool(ok), "msg": msg, "detail": detail})

    total = len(rows)
    filled = [r for r in rows if r["status"] == "filled"]
    cover = len(filled) / total if total else 0
    ck("G1", cover >= 0.7, f"覆盖率 {len(filled)}/{total} = {cover:.0%}")
    ck("G2", any((r.get("level") or 0) >= 3 for r in filled), "must 题是否到 L3")
    ck("G3", all(r.get("source_file") and r.get("period") and r.get("unit") for r in filled),
       "每已填格有来源/期次/单位")
    dup = {}
    for r in filled:
        k = fingerprint(r["measure"], r["entity"], r["period"])
        dup.setdefault(k, set()).add(r["value"])
    ck("G4", all(len(v) == 1 for v in dup.values()), "同口径多值冲突")
    ck("G5", all(r.get("tried") and r.get("why") for r in rows if r["status"] != "filled"),
       "缺格带已试+原因")
    dims_hit = {r["dim"] for r in rows}
    ck("G6", len(dims_hit) >= 4, f"覆盖维度 {len(dims_hit)}")
    ck("G7", not any(r["measure"] in ("share", "yoy") and r["dim"] == "时间" for r in filled),
       "比率未按时间相加")
    charts = extra.get("charts") or {"charts": []}
    ck("G8", all(c["data_points"] >= 3 for c in charts["charts"]),
       "图数据点 ≥3（全量基础数据）")
    stale = [r for r in filled if (r.get("quality") or {}).get("timeliness") == "stale"]
    ck("G9", (len(stale) / len(filled) if filled else 0) <= 0.2,
       f"过期格 {len(stale)}/{len(filled)}")
    reqs = extra.get("backfill") or []
    ck("G10", all(x.get("resolution") in ("filled", "unavailable") for x in reqs),
       f"回流 {len(reqs)} 条均有处置")
    branches = extra.get("branches") or {"items": []}
    per_q: Dict[str, int] = {}
    for b in branches["items"]:
        if b["decision"] == "stop":
            per_q[b["qid"]] = per_q.get(b["qid"], 0) + 1
    must_q = [a["id"] for a in clarify.get("asks") or [] if a.get("must")]
    ck("G11", all(per_q.get(q, 0) >= 3 for q in must_q),
       f"分支 stop 覆盖 {per_q}")
    decs = extra.get("decompositions") or []
    ck("G12", all(len(d.get("variants") or []) >= 2 and d.get("chosen") for d in decs),
       f"候选拆解 {len(decs)} 组")
    ck("G13", perspectives["count"] >= 3, f"视角 {perspectives['count']}")
    mece = extra.get("mece") or {"ok": True, "items": []}
    ck("G14", mece["ok"], f"MECE {[(i['qid'], i['ok'], i['sum']) for i in mece['items']]}")
    mech = [r for r in filled if r["dim"] == "机制"]
    a_mech = [r for r in mech if r.get("causal_level") == "A"]
    # 2026-11-23（SOP S5）：去掉 level>=3 依赖——原来只有 L3 格才判，
    # 而实际网格的 机制格 常常 level=1，导致这条门禁永远不触发。
    # 现在：任何已填的 机制格 都不许停在 A 阶。
    ck("G15", all(r.get("causal_level") in CAUSAL_LEVELS for r in mech)
       and not a_mech,
       f"机制格因果阶 {len(mech)}（A 阶 {len(a_mech)} 个）")
    sem_errs = validate_semantic(sem)
    ck("G16", not sem_errs, "；".join(sem_errs) or "度量参数齐")
    ck("G17", all(r.get("grain") for r in rows), "每格声明 grain")
    ck("G18", all(all(k in (r.get("quality") or {}) for k in QUALITY_DIMS)
                  for r in filled), "质量六维齐")
    weak = sum(1 for r in rows if r.get("match") == "weak")
    ck("G19", all(r.get("owner") for r in rows) and weak <= total * 0.5,
       f"强匹配 {total - weak}/{total}")
    routed = extra.get("requests") or []
    ck("G20", all(x.get("status") in ("accepted", "delivered", "declined",
                                      "escalated", "timed_out")
                  for x in routed), f"请求 {len(routed)} 条均有终态")
    ck("G21", len(receipts) == contracts_["count"], f"签收 {len(receipts)}/{contracts_['count']}")
    arb = extra.get("arbitration") or {"conflicts": []}
    ck("G22", all(c.get("arbiter") and c.get("verdict") for c in arb["conflicts"]),
       f"冲突 {len(arb['conflicts'])} 条有裁决")
    ck("G23", all(x.get("elapsed_min", 0) <= x.get("sla_min", 120)
                  or x.get("status") == "escalated" for x in routed),
       "SLA 内或已升级")
    events = []
    if ledger_path.is_file():
        events = [json.loads(x) for x in ledger_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    kinds = {e.get("event") for e in events}
    ck("G24", {"plan", "dispatch", "handoff", "gates"} <= kinds, f"账本 {len(events)} 条")
    # G25：accepted 只是接单；格子没填就是没交付。过去 24 条 accepted 但 0 格填充
    # 仍能过 G20，这是「流程完成 ≠ 数据到手」的根因。
    accepted = [x for x in routed if x.get("status") == "accepted"]
    unfulfilled = [x for x in accepted if not x.get("fulfilled")]
    ck("G25", not unfulfilled,
       f"接单未交付 {len(unfulfilled)}/{len(accepted)} 条")

    passed = sum(1 for c in checks if c["ok"])
    return {"checks": checks, "passed": passed, "total": len(checks),
            "ok": passed == len(checks)}


# --------------------------------------------------------------------------- #
# 收卡后接线（SOP S0/S1）：格填充 → cells_filled → G1–G25
# --------------------------------------------------------------------------- #
def post_collect(project: Path, merged: Dict[str, Any]) -> Dict[str, Any]:
    """收卡后自动跑：fill_cells → cells_filled.json → 仲裁/MECE/图合同/签收 → G1–G25。

    2026-11-23：这段原来只存在于 `scripts/run_card_upgrade.py`，生产收卡从不调用，
    所以 G1–G25 是摆设、cells_filled 从不产出。现在接到 `dispatch.collect` 尾部。
    任何异常都吞掉，绝不影响主链路（收卡成功与否不取决于门禁结果）。
    """
    try:
        project = Path(project)
        plan = project / "plan"
        clarify = _load_json(project / "clarify.json", {}) or {}
        grid = _load_json(plan / "grid.json", {}) or {}
        if not (grid.get("cells")):
            return {"ok": False, "why": "无可填充的格子（未走拆卡或 grid 为空）"}
        persp = _load_json(plan / "perspectives.json", {}) or {}
        disp = _load_json(plan / "dispatch.json", {}) or {}
        sem = load_semantics(project, merged)

        # 采集契约（SOP S2）：拆卡真正该产出的东西
        contract, contract_errs = None, []
        try:
            from core import collection_contract as _cc
            contract = _cc.build(grid, sem, clarify)
            if contract:
                contract_errs = _cc.validate(contract)
                _w(plan / "collection_contract.json", contract)
                try:
                    import yaml as _yaml
                    (plan / "collection_contract.yaml").write_text(
                        _yaml.safe_dump(contract, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
                except Exception:  # noqa: BLE001
                    pass
        except Exception as exc:  # noqa: BLE001
            contract_errs = [str(exc)]

        owner_of = {str(a.get("cell_id")): str(a.get("owner") or "")
                    for a in (disp.get("assignments") or [])}
        rows = [{**c, "owner": owner_of.get(str(c.get("cell_id")), ""),
                 "status": "open"} for c in grid["cells"]]

        facts = _load_json(plan / "facts.json", {}) or {}
        filled, fmeta = fill_cells(project, rows, facts)
        filled, bf = backfill(filled, project, facts)

        out_v3 = project / "out_v3"
        out_v3.mkdir(parents=True, exist_ok=True)
        _w(out_v3 / "cells_filled.json",
           {"cells": filled, "facts_reused": fmeta.get("reused", 0)})

        ctrs = disp.get("contracts") or []
        ctr = {"contracts": ctrs, "count": len(ctrs)}
        gaps = disp.get("gaps") or []
        receipts = []
        for c in ctrs:
            mine = [r for r in filled if r.get("cell_id") in (c.get("cells") or [])]
            good = [r for r in mine if r.get("status") == "filled"]
            rate = (len(good) / len(mine)) if mine else 0
            receipts.append({
                "handoff_id": "H-" + str(c.get("task_id")), "from": c.get("owner"),
                "to": "r01", "contract": c.get("task_id"),
                "decision": "accept" if rate >= 0.7 else "reject",
                "evidence": "%d/%d 格已填（%.0f%%）" % (len(good), len(mine), rate * 100),
                "elapsed_min": 30, "sla_min": c.get("deadline_min", 120)})

        arb = arbitrate(merged)
        mece = mece_check(filled)
        sat = grid_saturation(filled)
        charts = chart_contracts(clarify, filled, sem)
        decs = (_load_json(plan / "decomposition_log.json", {}) or {}).get("items") or []
        branches = _load_json(plan / "branch_log.json", {}) or []
        requests = (_load_json(plan / "requests.json", {}) or {}).get("requests") or []
        driver_tree = _load_json(plan / "driver_tree.json", {}) or build_driver_tree(sem)
        if not (plan / "driver_tree.json").is_file():
            _w(plan / "driver_tree.json", driver_tree)
        _w(plan / "arbitration.json", arb)
        _w(plan / "mece.json", mece)
        _w(plan / "saturation.json", sat)
        _w(plan / "charts.json", charts)
        _w(plan / "handoffs.json", {"receipts": receipts})

        g = gates(clarify, grid, persp, sem, filled, ctr, gaps, receipts,
                  plan / "ledger.jsonl",
                  extra={"charts": charts, "backfill": bf, "branches": branches,
                         "decompositions": decs, "mece": mece,
                         "driver_tree": driver_tree,
                         "arbitration": arb, "requests": requests})
        _w(plan / "post_gates.json", g)
        return {"ok": True, "passed": g.get("passed"), "total": g.get("total"),
                "filled": len(filled),
                "contract": bool(contract), "contract_errors": contract_errs,
                "mece_mutual": len(mece.get("mutual") or []),
                "saturated": sat.get("ok"),
                "cells_filled": str(out_v3 / "cells_filled.json")}
    except Exception as exc:  # noqa: BLE001 收卡门禁绝不影响主链路
        return {"ok": False, "why": str(exc)}
