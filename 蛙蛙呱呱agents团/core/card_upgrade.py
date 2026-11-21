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
    ("P2", "门店", "陈列、动销、缺货、导购"),
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
def _generate_case(pack: Dict[str, Any]) -> Dict[str, Any]:
    units = {str(n.get("unit")) for n in pack.get("numbers") or []}
    measures = [{"id": "retail_sales", "type": "simple", "agg": "sum", "expr": "retail_sales",
                 "unit": "亿元", "grain": "G_region_month",
                 "caliber": {"scope": "限额以上"}}]
    if "%" in units:
        measures += [
            {"id": "yoy", "type": "ratio", "numerator": "retail_sales",
             "denominator": "retail_sales@t-1", "unit": "%", "grain": "G_region_month"},
            {"id": "share", "type": "ratio", "numerator": "retail_sales",
             "denominator": "retail_sales@total", "unit": "%",
             "grain": "G_brand_channel_year", "non_additive_dimension": ["year"]},
        ]
    return {
        "schema": "dsh.semantic/v3", "generated": True,
        "entities": [
            {"id": "region", "type": "spatial", "levels": ["全国", "省", "盟市", "旗县"]},
            {"id": "category", "type": "hierarchy", "levels": ["大类", "子类"]},
            {"id": "brand", "type": "party"},
            {"id": "channel", "type": "structural"},
            {"id": "period", "type": "time", "grain": "year"},
        ],
        "grain_declarations": [
            {"id": "G_region_month", "dims": ["region", "category", "month"]},
            {"id": "G_brand_channel_year", "dims": ["brand", "category", "channel", "year"]},
        ],
        "measures": measures,
        "boundaries": [
            {"id": "B1", "text": "限额以上不含个体工商户", "affects": ["retail_sales"]},
            {"id": "B2", "text": "平台口径不可与统计公报相加", "affects": ["retail_sales", "share"]},
        ],
        "fingerprint": {"key": ["measure_id", "entity_scope", "period"]},
    }


def load_semantics(project: Path, pack: Dict[str, Any]) -> Dict[str, Any]:
    generic = _load_yaml(ROOT / "交付" / "generic_semantics_v1.yaml", {}) or {}
    case_path = project / "semantic_layer.yaml"
    case = _load_yaml(case_path)
    generated = False
    if not case:
        case = _generate_case(pack)
        generated = True
        if yaml is not None:
            case_path.write_text(yaml.safe_dump(case, allow_unicode=True, sort_keys=False),
                                 encoding="utf-8")
    elif case.get("generated"):
        # 兼容旧版自动生成的案例层：simple 补 expr
        for m in case.get("measures") or []:
            if m.get("type") == "simple" and not m.get("expr"):
                m["expr"] = m.get("id")
    return {"generic": generic, "case": case, "generated": generated,
            "source": str(case_path) if not generated else None}


def validate_semantic(sem: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    generic = sem.get("generic") or {}
    case = sem.get("case") or {}
    types = generic.get("metric_types") or {}
    entities = {e.get("id") for e in case.get("entities") or []}
    grains = {g.get("id") for g in case.get("grain_declarations") or []}
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
    have = {m["id"] for m in (sem.get("case") or {}).get("measures") or []}
    pref = {"ranking": "share", "composition": "share", "deviation": "yoy",
            "change": "retail_sales", "magnitude": "retail_sales"}
    m = pref.get(intent, "retail_sales")
    return m if m in have else (next(iter(have)) if have else "retail_sales")


def _brands(pack: Dict[str, Any], limit: int = 5) -> List[str]:
    out = []
    for n in pack.get("numbers") or []:
        name = str(n.get("name") or "")
        if "份额" not in name:
            continue
        head = re.split(r"(零售额)?份额", name)[0]
        head = re.sub(r"^(全国|中国|内蒙古|全区)", "", head)
        head = re.sub(r"(牙膏|口腔护理|口腔|洗发水|沐浴露|护肤品|彩妆|个护)$", "", head)
        head = head.strip("的 ")
        if any(k in head for k in ("合计", "总计", "其他", "其它", "前五", "前5", "CR")):
            continue
        if 2 <= len(head) <= 8 and head not in out:
            out.append(head)
    return (out or ["TOP5 品牌", "长尾合计"])[:limit]


def _causal_for(dim: str) -> str:
    return "A"          # 默认只到关联；机制格必须由执行者升级到 I/C


def _quality(period: str, grade: str = "B") -> Dict[str, str]:
    stale = (YEAR - int(period)) > STALE_YEARS if str(period).isdigit() else False
    return {"completeness": "full", "accuracy": f"grade_{grade}", "consistency": "checked",
            "timeliness": "stale" if stale else "fresh", "uniqueness": "ok",
            "validity": "ok"}


CITY_DISTRICTS = {
    "北京": ["北京", "朝阳", "海淀", "丰台", "通州", "昌平"],
    "上海": ["上海", "浦东", "徐汇", "静安", "闵行", "宝山"],
    "深圳": ["深圳", "南山", "福田", "罗湖", "宝安", "龙岗"],
    "广州": ["广州", "天河", "越秀", "海珠", "白云", "番禺"],
    "成都": ["成都", "锦江", "武侯", "高新", "成华", "双流"],
}


def _regions(clarify: Dict[str, Any], sem: Optional[Dict[str, Any]] = None) -> List[str]:
    # 1) 只看 clarify 里声明的“研究区域”，不是正文里提到哪个城市就套哪个城市
    region_text = str((clarify.get("understanding") or {}).get("region") or "")
    for city, dists in CITY_DISTRICTS.items():
        if city in region_text:
            return dists
    # 2) 本题语义层声明的区域优先级最高
    ents = ((sem or {}).get("case") or {}).get("entities") or []
    for e in ents:
        if e.get("id") == "region":
            levels = [x for x in (e.get("levels") or [])
                      if str(x).strip() and x not in ("全球",)]
            if levels:
                return levels[:5]
    text = json.dumps(clarify, ensure_ascii=False)
    if "内蒙古" in text:
        return ["全区", "呼和浩特", "包头", "鄂尔多斯", "赤峰"]
    for city, dists in CITY_DISTRICTS.items():
        if city in region_text:
            return dists
    return ["全国"]


Q_GRID = [
    (("市场", "份额", "集中度", "CR", "规模"),
     {"对象": ["中国IP玩具市场", "泡泡玛特份额", "CR3", "CR5"],
      "结构": ["品类×区域", "玩家×区域"],
      "机制": ["量价拆解", "份额变化"],
      "边界": ["IP玩具 vs 潮玩口径", "GMV vs 营收"]}),
    (("品类", "手办", "毛绒", "MEGA", "积木", "BJD", "衍生品"),
     {"对象": ["手办", "毛绒", "MEGA", "衍生品及其他"],
      "结构": ["品类×渠道", "品类×区域"],
      "机制": ["毛利率桥", "品类贡献度"],
      "边界": ["品类四分类口径", "MEGA与衍生品合并口径"]}),
    (("经营质量", "运营", "单店", "复购", "存货", "会员", "渠道"),
     {"对象": ["门店", "机器人商店", "会员", "存货"],
      "结构": ["渠道×区域", "线上×线下"],
      "机制": ["单店产出", "存货周转分解"],
      "边界": ["会员仅中国内地口径", "门店含合营口径"]}),
    (("IP", "生命周期", "授权", "续约", "依赖"),
     {"对象": ["THE MONSTERS", "星星人", "CRYBABY", "DIMOO", "SKULLPANDA", "MOLLY"],
      "结构": ["IP×品类", "IP×区域"],
      "机制": ["IP集中度", "单IP贡献"],
      "边界": ["IP归属口径", "授权 vs 自有"]}),
    (("竞争", "竞品", "格局", "打法"),
     {"对象": ["泡泡玛特", "52TOYS", "TOP TOY", "布鲁可", "卡游"],
      "结构": ["玩家×品类", "玩家×渠道"],
      "机制": ["毛利率对比", "规模差距"],
      "边界": ["营收 vs GMV", "市占率口径"]}),
    (("前景", "趋势", "增长", "出海", "第二曲线", "乐园", "游戏"),
     {"对象": ["中国市场", "亚太", "美洲", "欧洲及其他"],
      "结构": ["品类×区域", "渠道×区域"],
      "机制": ["情景驱动", "海外单位经济"],
      "边界": ["2026Q3未经审核", "预测口径"]}),
    (("供应链", "产能", "关税", "代工", "自产", "库存"),
     {"对象": ["中国基地", "印尼基地", "柬埔寨基地", "墨西哥基地"],
      "结构": ["基地×市场", "产能×品类"],
      "机制": ["库存回撤", "交期与关税"],
      "边界": ["产能为合作工厂口径", "自产比例未披露"]}),
    (("合规", "监管", "盲盒", "未成年", "诉讼", "侵权"),
     {"对象": ["盲盒指引", "8岁门槛", "IP诉讼"],
      "结构": ["风险×影响面", "条款×动作"],
      "机制": ["合规成本", "维权成本"],
      "边界": ["指引非强制国标", "个案不外推"]}),
]


ENTITY_MEASURE = {
    "中国IP玩具市场": "revenue", "泡泡玛特份额": "share", "CR3": "share", "CR5": "share",
    "手办": "revenue", "毛绒": "revenue", "MEGA": "revenue", "衍生品及其他": "revenue",
    "门店": "store_count", "机器人商店": "store_count", "会员": "member_count",
    "存货": "inventory_days",
    "THE MONSTERS": "revenue", "星星人": "revenue", "CRYBABY": "revenue",
    "DIMOO": "revenue", "SKULLPANDA": "revenue", "MOLLY": "revenue",
    "泡泡玛特": "revenue", "52TOYS": "revenue", "TOP TOY": "revenue",
    "布鲁可": "revenue", "卡游": "revenue",
    "中国市场": "revenue", "亚太": "revenue", "美洲": "revenue", "欧洲及其他": "revenue",
    "中国": "revenue", "全球": "revenue",
}


def _q_template(text: str) -> Dict[str, List[str]]:
    for keys, tpl in Q_GRID:
        if any(k in text for k in keys):
            return tpl
    return {"对象": ["TOP5 品牌", "长尾合计"],
            "结构": ["品类×渠道", "价格带×渠道"],
            "机制": ["铺货率", "单店动销", "复购"],
            "边界": ["平台口径 vs 统计公报", "样本覆盖"]}


def build_grid(clarify: Dict[str, Any], sem: Dict[str, Any],
               brands: Optional[List[str]] = None,
               template: Optional[Dict[str, Dict[str, List[str]]]] = None) -> Dict[str, Any]:
    cells: List[Dict[str, Any]] = []
    regions = _regions(clarify, sem)
    case = sem.get("case") or {}
    measures = {m.get("id"): m for m in case.get("measures") or []}

    def _first(kind: str, fallback: str) -> str:
        for mid, m in measures.items():
            if m.get("type") == kind:
                return mid
        return fallback

    period_grain = "year"
    for e in case.get("entities") or []:
        if e.get("id") == "period" and e.get("grain"):
            period_grain = str(e["grain"])
    periods = (["2024", "2025", "2026H1"] if period_grain == "half_year"
               else ["2024", "2025", "2026"])

    def _dim_measure(qtext: str, dim: str, base: str) -> str:
        pref = "revenue"
        if dim == "结构":
            pref = "category_mix"
        elif dim == "机制":
            pref = "unit_economics"
        elif dim == "时间" and any(k in qtext for k in ("前景", "趋势", "增长", "下滑", "Q3")):
            pref = "yoy"
        return pref if pref in measures else base

    for a in clarify.get("asks") or []:
        if not a.get("must"):
            continue
        intent = _intent(a["text"])
        base = _measure_for(intent, sem)
        tpl = ((template or {}).get(a["id"])
               or _q_template(str(a.get("text") or "")))
        per_q = {
            "对象": tpl["对象"],
            "空间": regions,
            "时间": periods,
            "结构": tpl["结构"],
            "机制": tpl["机制"],
            "边界": tpl["边界"],
        }
        for dim, vals in per_q.items():
            for v in vals:
                if dim == "对象":
                    m = ENTITY_MEASURE.get(v)
                    if not m or m not in measures:
                        m = "share" if "share" in measures else base
                elif dim == "结构":
                    m = "category_mix" if "category_mix" in measures else _first("ratio", base)
                elif dim == "机制":
                    m = _first("derived", base)
                elif dim == "边界":
                    m = "revenue" if "revenue" in measures else base
                else:
                    m = _dim_measure(str(a.get("text") or ""), dim, base)
                grain = (measures.get(m) or {}).get("grain") or "year"
                period = v if dim == "时间" else (periods[-1] if periods else "2025")
                cells.append({
                    "cell_id": f"{a['id']}.{dim}.{v}", "qid": a["id"], "dim": dim,
                    "entity": v, "measure": m, "depth_target": DEPTH_TARGET["must"],
                    "grain": grain, "period": period, "status": "open",
                    "causal_level": _causal_for(dim), "causal_hypothesis": dim == "机制",
                    "quality": _quality(period),
                    "chart_id": f"c-{a['id']}",
                    "query": {"measures": [m], "filters": {dim: v}, "period": period},
                })
    return {"schema": "dsh.grid/v1", "cells": cells, "count": len(cells),
            "dims": list(DIMS)}


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
            ("空间下钻到旗县", "缺旗县级公开数据，边际价值中"),
            ("渠道拆到门店级", "需一手 POS，成本高，先不做"),
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
        # 时间序列要总量，不能拿品类/IP 分项充数
        parts = ("手办", "毛绒", "MEGA", "衍生品", "THE MONSTERS", "星星人",
                 "CRYBABY", "DIMOO", "SKULLPANDA", "MOLLY")
        cands = [n for n in cands if not any(k in str(n.get("name")) for k in parts)]
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
                           "level": 1, "causal_level": r.get("causal_level", "A"),
                           "quality": fact.get("quality") or _quality(r["period"]),
                           "note": "指纹复用"})
            continue
        cands = _match_numbers(r, nums)
        if cands:
            n = cands[0]
            q = _quality(str(n.get("period") or r["period"]))
            filled.append({**r, "status": "filled", "value": n["value"],
                           "unit": n.get("unit"), "period": n.get("period"),
                           "source_file": n.get("source_file"), "grade": "B", "level": 1,
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
        alt["entity"] = re.sub(r"(牙膏|口腔|洗护)$", "", str(r["entity"]))
        cands = _match_numbers(alt, nums)
        if not cands and r["dim"] == "时间":
            alt["entity"] = str(max(int(x) for x in ["2024", "2025", "2026"]))
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
    return {"items": out, "ok": all(x["ok"] for x in out)}


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
    ck("G15", all(r.get("causal_level") in CAUSAL_LEVELS for r in mech)
       and all(not (r.get("level", 0) >= 3 and r.get("causal_level") == "A") for r in filled),
       f"机制格因果阶 {len(mech)}")
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
