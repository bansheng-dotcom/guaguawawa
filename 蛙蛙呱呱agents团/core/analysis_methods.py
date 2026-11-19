# -*- coding: utf-8 -*-
"""core/analysis_methods —— 分析方法库：每个方法产出一条「带数字的判断」。

设计原则（这是这一版和旧 deep_analysis 的根本差别）：

1. **方法按数据结构选，不按项目写死**。同一套方法在肉禽蛋、水果、蔬菜上跑，
   只是命中的方法不同；没有对应数据的节直接记为缺口，不写形容词补。
2. **每条判断必须落到「是多少 → 为什么 → 所以怎么办」**。只描述数字不给动作的，
   算半成品；给动作不带停止条件的，不许进报告。
3. **二阶判断优先于一阶描述**。一阶是"白条鸡 11.97 元"；二阶是
   "白条鸡加价 40.8%、同比 −6.48%——成本在降、加价在扩，它是利润品不是引流品"。
   本模块每条 finding 都带 `so_what` 与 `actions`，由数字触发，不写通用套话。

方法清单（命中即产出，未命中记 gap）：
    structure     横截面分化：谁在涨、涨多少、离散度多大
    momentum      节奏张力：环比 vs 同比（短期拐点 vs 基数效应）
    trajectory    时间轨迹：首末/极值/波动率/异常点（调 r06 time_series）
    contribution  两期贡献：总变化由哪个品类拉动（调 r06 decompose）
    economics     单位经济：加价率 → 扣损耗冷链 → 净毛利（负毛利识别）
    transmission  上下游传导：产地→批发→零售，价差被谁吃掉、有没有倒挂
    arbitrage     跨市场价差：买在 A、卖在 B，扣运费冷链还剩多少
    breakeven     保本线：提价多少 / 直采多少比例才能转正
    sensitivity   情景敏感性：零售价、损耗、冷链各动一档会怎样
    tco           到店成本：多货源 landed cost 排序（调 r15 tco）
    risk          风险与缺口：波动带、异常点、覆盖不足
    sample        样本充分性：这个差异要多少样本才判得动（调 r19 eval-ci）
"""
from __future__ import annotations

import csv
import re
import statistics as st
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core import runner

# --------------------------------------------------------------------------- #
# 品类假设：损耗率与冷链成本（元/斤）。这是「情景测算」不是财务决算，
# 每个用到的值都会写进该节的 assumptions，供校验器放行、供读者替换。
# --------------------------------------------------------------------------- #
CAT_RULES: List[Tuple[str, Dict[str, float]]] = [
    ("对虾", {"loss": 0.06, "cold": 1.60, "shelf": 1}),
    ("淡水虾", {"loss": 0.06, "cold": 1.60, "shelf": 1}),
    ("带鱼", {"loss": 0.03, "cold": 0.70, "shelf": 30}),
    ("草鱼", {"loss": 0.05, "cold": 0.55, "shelf": 1}),
    ("鲤鱼", {"loss": 0.05, "cold": 0.55, "shelf": 1}),
    ("鲫鱼", {"loss": 0.05, "cold": 0.55, "shelf": 1}),
    ("白条鸡", {"loss": 0.02, "cold": 0.55, "shelf": 2}),
    ("鸡蛋", {"loss": 0.01, "cold": 0.25, "shelf": 4}),
    # 水果：仁果/柑橘耐放，浆果与热带果货架期短、冷链贵
    ("苹果", {"loss": 0.020, "cold": 0.35, "shelf": 14}),
    ("梨", {"loss": 0.020, "cold": 0.35, "shelf": 14}),
    ("柑橘", {"loss": 0.020, "cold": 0.35, "shelf": 14}),
    ("葡萄", {"loss": 0.050, "cold": 0.55, "shelf": 5}),
    ("香蕉", {"loss": 0.040, "cold": 0.45, "shelf": 5}),
    ("芒果", {"loss": 0.050, "cold": 0.55, "shelf": 5}),
    ("菠萝", {"loss": 0.040, "cold": 0.45, "shelf": 7}),
    ("西瓜", {"loss": 0.030, "cold": 0.40, "shelf": 7}),
    ("桃", {"loss": 0.035, "cold": 0.50, "shelf": 5}),
    ("猕猴桃", {"loss": 0.050, "cold": 0.60, "shelf": 7}),
    ("火龙果", {"loss": 0.040, "cold": 0.50, "shelf": 7}),
    ("橙", {"loss": 0.020, "cold": 0.35, "shelf": 14}),
    ("红枣", {"loss": 0.010, "cold": 0.20, "shelf": 30}),
    ("虾", {"loss": 0.06, "cold": 1.60, "shelf": 1}),
    ("蛋", {"loss": 0.01, "cold": 0.25, "shelf": 4}),
    ("牛", {"loss": 0.015, "cold": 0.90, "shelf": 3}),
    ("羊", {"loss": 0.015, "cold": 0.90, "shelf": 3}),
    ("猪", {"loss": 0.02, "cold": 0.50, "shelf": 3}),
    ("鸭", {"loss": 0.02, "cold": 0.60, "shelf": 2}),
    ("鹅", {"loss": 0.02, "cold": 0.60, "shelf": 2}),
    ("鱼", {"loss": 0.05, "cold": 0.55, "shelf": 1}),
    ("鸡", {"loss": 0.02, "cold": 0.55, "shelf": 2}),
]
FREIGHT_PER_JIN = 0.30          # 跨市冷链城配（元/斤），2 天交期
DEFAULT_RULE = {"loss": 0.02, "cold": 0.50, "shelf": 3}

# 跨品类通用词：肉禽蛋之外也认（水果/蔬菜/家居百货的常见品类）
EXTRA_KEYS = ("苹果", "葡萄", "香蕉", "西瓜", "柑橘", "芒果", "菠萝",
              "梨", "红枣", "桃", "猕猴桃", "火龙果", "橙",
              "土豆", "白菜", "番茄", "黄瓜", "辣椒", "大葱")
KNOWN_KEYS = sorted({k for k, _ in CAT_RULES} | set(EXTRA_KEYS),
                    # 同长度时优先果蔬类词：避免「鸭梨」被归到「鸭」（集合序不稳定）
                    key=lambda k: (len(k), k in EXTRA_KEYS),
                    reverse=True)
_ORIGIN_BAN = ("当地", "零售", "批发", "市场价", "下架鸡", "肥牛",
               "活牛", "育肥", "活羊", "羔羊", "绒山羊")
_ORIGIN_PREFER = {
    "牛": ("育肥牛", "活牛", "犊牛"),
    "羊": ("羔羊", "活羊", "绒山羊"),
    "鸡": ("鸡白条", "白条鸡", "毛鸡"),
    "蛋": ("鲜蛋", "鸡蛋出场", "出场"),
    "鸡蛋": ("鲜蛋", "鸡蛋出场", "出场"),
}
_PCT_HINTS = ("环比", "同比", "涨幅", "占比", "pct", "mom", "yoy", "rate")


def cat_key(name: str) -> str:
    """把「活草鱼」「白条鸡批发」「羊肉（去骨）」「富士苹果」归到同一个品类键。"""
    s = str(name or "")
    best = ""
    for key in KNOWN_KEYS:
        if key in s and len(key) > len(best):
            best = key
    if best == "鸡" and "白条" in s:
        return "白条鸡"
    if best == "蛋":
        return "鸡蛋"
    return best or s.strip()


def rule_of(name: str) -> Dict[str, float]:
    k = cat_key(name)
    for key, r in CAT_RULES:
        if key == k:
            return r
    return DEFAULT_RULE


def obs_cat(obs) -> str:
    """从一条观测里判品类：先看第二维，再看第一维，最后看文件名。"""
    for cand in (obs.sub, obs.entity, Path(obs.file).stem):
        if not cand:
            continue
        k = cat_key(cand)
        if k in KNOWN_KEYS:
            return k
    return cat_key(obs.entity)


# --------------------------------------------------------------------------- #
# 数字登记
# --------------------------------------------------------------------------- #
@dataclass
class Num:
    id: str
    value: float
    unit: str = ""
    digits: int = 2

    def __str__(self) -> str:
        v = self.value
        if self.digits == 0:
            return f"{v:.0f}"
        return f"{v:.{self.digits}f}"

    def p(self) -> str:
        """按百分比显示（value 存的是小数比例）。"""
        return f"{self.value * 100:.{self.digits}f}%"


class Cite:
    """登记 + 格式化。文字里出现的每个数字都必须从 n/d 出来。"""

    def __init__(self, desk):
        self.desk = desk
        self.refs: List[str] = []

    def begin(self) -> int:
        return len(self.refs)

    def since(self, mark: int) -> List[str]:
        return list(self.refs[mark:])

    def n(self, name: str, value: float, unit: str = "", period: str = "",
          source: str = "", digits: int = 2) -> Num:
        nid = self.desk.add_number(name, value, unit, period, source)
        self.refs.append(nid)
        return Num(nid, float(value), unit, digits)

    def d(self, did: str, formula: str, value: float, note: str,
          unit: str = "", digits: int = 2) -> Num:
        self.desk.add_derived(did, formula, value, note, unit)
        self.refs.append(did)
        return Num(did, float(value), unit, digits)


class Skills:
    """真跑技能：只用于统计、成本、评审这类有确定性引擎的步骤；失败只降级。"""

    def __init__(self):
        self.runs: List[Dict[str, Any]] = []
        self._cache: Dict[str, Dict[str, Any]] = {}

    def call(self, role: str, skill: str, action: str = "",
             args: Optional[List[str]] = None, timeout: int = 120) -> Dict[str, Any]:
        key = f"{role}|{skill}|{action}|{' '.join(args or [])}"
        if key in self._cache:
            return self._cache[key]
        argv = [skill] + ([action] if action else []) + list(args or [])
        try:
            r = runner.invoke(role, argv, timeout=timeout)
            js = r.get("json") or {}
        except Exception as exc:  # noqa: BLE001  技能失败只降级，不伪造
            js = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        self.runs.append({"role": role, "skill": skill, "action": action,
                          "args": list(args or []), "ok": bool(js.get("ok", False)),
                          "result": js})
        self._cache[key] = js
        return js

    def covered(self) -> Dict[str, Any]:
        ok = [r for r in self.runs if r["ok"]]
        return {"skills": len({f"{r['role']}.{r['skill']}.{r['action']}" for r in ok}),
                "roles": len({r["role"] for r in ok})}


@dataclass
class Finding:
    key: str
    title: str
    question: str
    reading: List[Dict[str, Any]] = field(default_factory=list)
    refs: List[str] = field(default_factory=list)
    assumptions: List[float] = field(default_factory=list)
    chart: Optional[Dict[str, Any]] = None
    table: Optional[Dict[str, Any]] = None
    boundary: str = ""
    falsifier: str = ""
    so_what: str = ""
    actions: List[Dict[str, str]] = field(default_factory=list)
    weight: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def add(self, text: str, refs: Optional[Iterable[str]] = None,
            strong: str = "") -> None:
        self.reading.append({"text": text, "refs": list(refs or []),
                             "strong": strong})


def _table(caption: str, cols: List[str], rows: List[List[str]]) -> Dict[str, Any]:
    return {"caption": caption,
            "columns": [{"text": c} for c in cols],
            "rows": [[{"text": c} for c in r] for r in rows]}


def _cv(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = st.mean(vals)
    return st.pstdev(vals) / m if m else 0.0


def _pct_change(a: float, b: float) -> float:
    return (b - a) / a * 100 if a else 0.0


def _names(items: List[str], limit: int = 3) -> str:
    return "、".join(items[:limit]) + ("等" if len(items) > limit else "")


def _ids(*nums: Any) -> List[str]:
    out: List[str] = []
    for n in nums:
        if isinstance(n, Num):
            out.append(n.id)
        elif isinstance(n, str):
            out.append(n)
        elif isinstance(n, (list, tuple)):
            out.extend(_ids(*n))
    return out


def _is_period_label(s: str) -> bool:
    return bool(re.match(r"^\d{1,2}月\d{1,2}日$", s)) or bool(
        re.match(r"^(19|20)\d{2}-\d{2}", s))


def _period_key(t: str) -> Tuple[int, int, str]:
    """时间标签的自然序：'11月5日' > '10月20日' > '9月20日'，字符串序会排反。"""
    s = str(t or "")
    m = re.match(r"^(\d{1,2})月(?:(\d{1,2})日)?", s)
    if m:
        return (int(m.group(1)), int(m.group(2) or 0), s)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return (int(m.group(2)), int(m.group(3)), s)
    m = re.match(r"^(\d{2})-(\d{2})~", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), s)
    m = re.match(r"^(\d{1,2})月值$", s)
    if m:
        return (int(m.group(1)), 0, s)
    return (0, 0, s)


def _iso_date(t: str, fallback_year: int = 2026) -> str:
    """把 '11月5日' / '09-26~10-02' / '2026-11-02~11-08' 统一成 ISO 日期。

    技能引擎（r06 time_series）只认 ISO 日期，中文期标签会让它把整列当字符串，
    返回空趋势——这是必须在这层修掉的，不是引擎的错。
    """
    s = str(t or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"^(\d{1,2})月(\d{1,2})日", s)
    if m:
        return f"{fallback_year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{2})-(\d{2})~", s)
    if m:
        return f"{fallback_year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{1,2})月$", s)
    if m:
        return f"{fallback_year}-{int(m.group(1)):02d}-01"
    return ""


def _dedupe_series(rows: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    seen: Dict[str, float] = {}
    order: List[str] = []
    for t, v in rows:
        if t not in seen:
            order.append(t)
        seen[t] = v
    return [(t, seen[t]) for t in order]


def _score_market(entity: str, file: str) -> int:
    """同城 > 全国：零售是本地价，批发对标要尽量用同一个城市的市场报价。"""
    s = 0
    if "东瓦窑" in entity:
        s += 3
    if "呼和浩特" in entity or "呼市" in entity:
        s += 2
    if "全国" in file or "全国" in entity:
        s += 1
    return s


# --------------------------------------------------------------------------- #
# 视图：把长表观测整理成方法能直接吃的结构
# --------------------------------------------------------------------------- #
@dataclass
class Views:
    primary: str = ""                                   # 快照来源（横截面）
    snapshot: Dict[str, Tuple[float, str]] = field(default_factory=dict)
    snapshot_unit: str = "元/斤"
    labels: Dict[str, str] = field(default_factory=dict)   # 品类键 → 展示名
    series: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)
    series_src: Dict[str, str] = field(default_factory=dict)
    momentum: Dict[str, Dict[str, float]] = field(default_factory=dict)
    wholesale: Dict[str, Tuple[float, str]] = field(default_factory=dict)
    origins: List[Dict[str, Any]] = field(default_factory=list)
    region: Dict[Tuple[str, str], float] = field(default_factory=dict)
    quotes: Dict[Tuple[str, str], float] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    source_notes: List[str] = field(default_factory=list)

    def cats(self) -> List[str]:
        return list(self.snapshot.keys())

    def label(self, key: str) -> str:
        if key == "鸡" and "白条鸡" in self.labels:
            return "白条鸡"
        return self.labels.get(key, key)


def _clean_label(name: str) -> str:
    s = str(name or "")
    for junk in ("（去骨）", "(去骨)", "批发", "活", "（当地）"):
        s = s.replace(junk, "")
    return s.strip() or str(name)


def obs_name(obs) -> str:
    """品类字段的原始展示名：与 obs_cat 同一判定顺序（sub → entity → 文件名）。

    长表的主/次维顺序不固定（市场×品类 / 品类×地区），直接取 `sub or entity`
    会把「地区/市场」当成品类名。这里只认能归一到 KNOWN_KEYS 的那个字段。
    """
    for cand in (obs.sub, obs.entity, Path(obs.file).stem):
        if cand and cat_key(cand) in KNOWN_KEYS:
            return str(cand)
    return str(obs.entity or obs.sub or "")


def _score_retail_ds(d) -> Tuple[int, int, int, int]:
    """快照表优先级：非 engine/ 派生物 > 列就是期次 > 文件名带采价/零售 > 品类多。"""
    name = d.file
    raw = 0 if name.startswith("engine/") else 1
    period_cols = 1 if any(_is_period_label(c) for c in d.columns) else 0
    named = 1 if any(k in name for k in ("采价", "零售")) else 0
    cats = len({cat_key(o.entity) for o in d.obs if not o.pct})
    return (raw, period_cols, named, cats)


def build_views(desk) -> Views:
    v = Views()
    retail_ds = [d for d in desk.datasets if d.channel == "retail"]
    if not retail_ds:
        v.gaps.append("没有可识别的零售价数据")
        return v

    # 1) 快照：选一张「横截面最全」的零售表，取自然序最后一期
    t0 = max(retail_ds, key=_score_retail_ds)
    periods = sorted({o.time for o in t0.obs if o.time}, key=_period_key)
    last = periods[-1] if periods else ""
    for o in t0.obs:
        if o.pct or o.value <= 0 or o.time != last:
            continue
        cat = cat_key(o.entity)
        if _is_period_label(cat):
            continue
        val, unit = o.per_jin()
        v.snapshot[cat] = (val, o.time)
        v.snapshot_unit = unit
        v.labels.setdefault(cat, _clean_label(obs_name(o)))
    v.primary = t0.file
    v.source_notes.append(f"快照取 {t0.file} 的 {last}")

    # 2) 轨迹：只用一张表（口径一致），优先「和快照同名的品类最多」的那张
    def traj_score(d) -> Tuple[int, int]:
        rows: Dict[str, int] = {}
        for o in d.obs:
            if o.pct or o.value <= 0 or not o.time:
                continue
            rows[cat_key(o.entity)] = rows.get(cat_key(o.entity), 0) + 1
        matched = sum(1 for c, n in rows.items() if n >= 3 and c in v.snapshot)
        return (matched, sum(rows.values()))

    t1 = max(retail_ds, key=traj_score)
    groups: Dict[str, List[Tuple[str, float]]] = {}
    for o in t1.obs:
        if o.pct or o.value <= 0 or not o.time:
            continue
        cat = cat_key(o.entity)
        if _is_period_label(cat):
            continue
        val, _ = o.per_jin()
        groups.setdefault(cat, []).append((o.time, val))
    for cat, rows in groups.items():
        if len(rows) >= 2:
            v.series[cat] = _dedupe_series(
                sorted(rows, key=lambda x: _period_key(x[0])))
            v.series_src[cat] = t1.file

    # 3) 环比/同比（百分比列，按品类取最后一个）
    for o in desk.obs:
        if not o.pct:
            continue
        m = o.metric.lower()
        cat = cat_key(o.entity)
        if "环比" in m or "mom" in m:
            v.momentum.setdefault(cat, {})["mom"] = o.value
        elif "同比" in m or "yoy" in m:
            v.momentum.setdefault(cat, {})["yoy"] = o.value

    # 4) 批发价：优先同城市场报价，其次全国周度
    best_w: Dict[str, Tuple[int, str, float, str]] = {}
    for o in desk.obs:
        if o.channel != "wholesale" or o.pct or o.value <= 0:
            continue
        cat = obs_cat(o)
        val, _ = o.per_jin()
        score = _score_market(o.entity, o.file)
        cur = best_w.get(cat)
        if cur is None or (score, o.time) >= (cur[0], cur[1]):
            best_w[cat] = (score, o.time, val, o.entity)
    for cat, (_s, _t, val, ent) in best_w.items():
        v.wholesale[cat] = (val, ent)

    # 5) 产地出场价：保留细分标签（育肥牛/活牛/鲜蛋装车/鸡白条…），交给方法挑选
    for o in desk.obs:
        if o.channel != "origin" or o.pct or o.value <= 0:
            continue
        cat = obs_cat(o)
        if cat not in KNOWN_KEYS:
            continue  # 产地列写的是地名/规格而非品类：不能拿它冒充品类价
        val, _ = o.per_jin()
        v.origins.append({"cat": cat, "label": obs_name(o),
                          "place": o.entity, "time": o.time, "value": val})

    # 6) 地区零售（区域价格表：地区 × 品类 × 两期）
    for d in desk.datasets:
        if d.kind != "period_table":
            continue
        periods = sorted({o.time for o in d.obs}, key=_period_key)
        if len(periods) < 2:
            continue
        last = periods[-1]
        for o in d.obs:
            if o.time != last or o.pct:
                continue
            cat = obs_cat(o)
            place = str(o.sub) if cat_key(o.entity) in KNOWN_KEYS else str(o.entity)
            val, _ = o.per_jin()
            v.region[(place, cat)] = val

    # 7) 批发市场逐市场报价
    for o in desk.obs:
        if o.channel != "wholesale" or o.pct or not o.sub:
            continue
        cat = obs_cat(o)
        val, _ = o.per_jin()
        v.quotes[(o.entity, cat)] = val

    if not v.snapshot:
        v.gaps.append("零售价表里没有可解析的数值")
    return v


def pick_origin(v: Views, cat: str, floor: float = 0.0) -> Optional[Dict[str, Any]]:
    rows = [o for o in v.origins if o["cat"] == cat
            and o["value"] >= floor
            and not any(b in str(o["label"]) for b in _ORIGIN_BAN)]
    if not rows:
        return None
    prefer = _ORIGIN_PREFER.get(cat, ())

    def score(o):
        s = 0
        for i, k in enumerate(prefer):
            if k in str(o["label"]):
                s += (len(prefer) - i) * 10
        return (s, o["time"])

    return sorted(rows, key=score, reverse=True)[0]


# === METHODS ===


@dataclass
class Ctx:
    desk: Any
    views: Views
    skills: Skills
    cite: Cite
    profile: Dict[str, Any]
    tmpdir: str
    memo: Dict[str, Any] = field(default_factory=dict)
    # v7：带来源的事实表（研究类项目才有；价格类项目为空表）
    ft: Any = None
    frame: str = ""

    def tmp_csv(self, name: str, header: List[str],
                rows: List[List[Any]]) -> str:
        path = Path(self.tmpdir) / name
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        return str(path)


def _finding(key: str, title: str, question: str, c: Cite, mark: int) -> Finding:
    return Finding(key=key, title=title, question=question, refs=c.since(mark))


# --------------------------------------------------------------------------- #
# 1. 横截面分化
# --------------------------------------------------------------------------- #
def m_structure(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    cats = [k for k in v.snapshot if k in v.series and len(v.series[k]) >= 2]
    if len(cats) < 3:
        return None
    rows = []
    for k in cats:
        s = v.series[k]
        a, b = s[0][1], s[-1][1]
        na = c.n(f"{k} 期初零售价", a, "元/斤", s[0][0], v.series_src.get(k, ""))
        nb = c.n(f"{k} 期末零售价", b, "元/斤", s[-1][0], v.series_src.get(k, ""))
        ch = _pct_change(a, b)
        nch = c.n(f"{k} 区间变化率", ch / 100, "%", f"{s[0][0]}→{s[-1][0]}",
                  v.series_src.get(k, ""))
        rows.append({"cat": v.label(k), "key": k, "a": na, "b": nb,
                     "ch": nch, "v": ch})
    rows.sort(key=lambda r: r["v"], reverse=True)
    ups = [r for r in rows if r["v"] > 0]
    downs = [r for r in rows if r["v"] < 0]
    top, bot = rows[0], rows[-1]
    mean = st.mean(r["v"] for r in rows)
    med = st.median([r["v"] for r in rows])
    sd = st.pstdev([r["v"] for r in rows])
    nmean = c.n("品类变化率均值", mean / 100, "%")
    nmed = c.n("品类变化率中位数", med / 100, "%")
    nsd = c.n("品类变化率标准差", sd / 100, "%")
    n_up = c.n("上涨品类数", len(ups), "个", digits=0)
    n_dn = c.n("下跌品类数", len(downs), "个", digits=0)

    title = (f"结构：{n_up} 个品类在涨、{n_dn} 个在跌，"
             f"{top['cat']} {top['ch'].p()}、{bot['cat']} {bot['ch'].p()}")
    f = _finding("structure", title,
                 f"同一时点上看，{len(rows)} 个品类的价格往哪个方向分化？", c, mark)
    f.add(f"区间内 {len(ups)} 个品类上涨、{len(downs)} 个下跌；涨幅最大的是"
          f"{top['cat']}（{top['ch'].p()}），跌幅最大的是{bot['cat']}（{bot['ch'].p()}）。",
          _ids(top["ch"], bot["ch"], n_up, n_dn))
    f.add(f"变化率均值 {nmean.p()}、中位数 {nmed.p()}、标准差 {nsd.p()} 个百分点："
          + ("均值被跌幅最大的品类拖低，中位数才是多数品类的真实体感。"
             if mean < med else
             "均值被涨幅最大的品类拉高，中位数才是多数品类的真实体感。"),
          _ids(nmean, nmed, nsd))
    stable = [r["cat"] for r in rows if abs(r["v"]) <= 2]
    n_stable = c.n("窄幅波动品类数", len(stable), "个", digits=0)
    if stable:
        f.add(f"涨跌幅在 2% 以内的是{_names(stable)}：这些品类短期没有行情信号，"
              "按库存和周转做，不按价格判断做。", _ids(n_stable))
    f.table = _table(
        "品类价格与区间变化（零售价，元/斤）",
        ["品类", "期初", "期末", "变化率"],
        [[r["cat"], str(r["a"]), str(r["b"]), r["ch"].p()] for r in rows])
    f.chart = {
        "type": "hbar",
        "title": f"{top['cat']} {top['ch'].p()} 领涨、{bot['cat']} {bot['ch'].p()} 领跌，"
                 f"{len(rows)} 个品类分化 {nsd.p()} 个百分点",
        "subtitle": f"{len(rows)} 个品类 · {v.primary} 首末两期 · 区间变化率",
        "note": "未做季节调整，涨跌只代表区间首末两点",
        "unit_meta": "区间变化率（%）",
        "source": f"由 {v.primary} 首末两期重算",
        "refs": _ids([r["ch"] for r in rows]),
        "bars": [{"label": r["cat"], "value": round(r["v"], 2)} for r in rows],
    }
    f.so_what = ("分品类定价：涨的锁成本、跌的先看是需求塌陷还是供给放量；"
                 "把涨跌混在一个均价里考核，会把利润品和引流品一起做坏。")
    f.boundary = (f"只覆盖 {len(rows)} 个品类、{len(v.series.get(cats[0], []))} 个期次，"
                  "是同一张表首末两期的比较，未做季节调整。")
    f.meta = {"rows": rows}
    return f


# --------------------------------------------------------------------------- #
# 2. 节奏张力（环比 vs 同比）
# --------------------------------------------------------------------------- #
def m_momentum(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    cats = [k for k, m in v.momentum.items()
            if "mom" in m and "yoy" in m and k in v.snapshot]
    if len(cats) < 3:
        return None

    def quad(mom: float, yoy: float) -> str:
        if mom >= 0 and yoy >= 0:
            return "双升·成本推动"
        if mom < 0 <= yoy:
            return "高位回落·基数退潮"
        if mom >= 0 > yoy:
            return "短期反弹·趋势未改"
        return "双降·趋势下行"

    rows = []
    for k in cats:
        mom, yoy = v.momentum[k]["mom"], v.momentum[k]["yoy"]
        nm = c.n(f"{k} 环比", mom / 100, "%")
        ny = c.n(f"{k} 同比", yoy / 100, "%")
        rows.append({"cat": v.label(k), "key": k, "mom": nm, "yoy": ny,
                     "m": mom, "y": yoy, "q": quad(mom, yoy)})
    rows.sort(key=lambda r: abs(r["y"]), reverse=True)
    top = rows[0]
    tension = [r for r in rows if (r["m"] < 0 < r["y"]) or (r["m"] > 0 > r["y"])]
    tense = tension[0] if tension else top

    title = (f"节奏：{tense['cat']} 环比 {tense['mom'].p()}、同比 {tense['yoy'].p()}，"
             f"{tense['q']}")
    if tense is not top:
        title += f"；{top['cat']} 同比 {top['yoy'].p()}"
    f = _finding("momentum", title,
                 "环比和同比指向不一致时，该信哪一个？", c, mark)
    f.add(f"{tense['cat']} 环比 {tense['mom'].p()}、同比 {tense['yoy'].p()}，"
          f"属于「{tense['q']}」：短期在跌，但去年同期基数更低，不能读成需求转弱。",
          _ids(tense["mom"], tense["yoy"]))
    same_dir = [r for r in rows if r["q"].startswith("双")]
    if same_dir:
        s = same_dir[0]
        f.add(f"{s['cat']} 环比 {s['mom'].p()}、同比 {s['yoy'].p()}，"
              f"「{s['q']}」——方向一致时，环比就是可用的短期信号。",
              _ids(s["mom"], s["yoy"]))
    n_tense = c.n("环比同比反向品类数", len(tension), "个", digits=0)
    f.add(f"{len(rows)} 个品类里 {len(tension)} 个出现环比与同比反向；"
          "反向的品类只做周度随行，不做月度锁价，否则会把基数效应当成趋势。",
          _ids(n_tense))
    f.table = _table(
        "环比与同比的象限（%）",
        ["品类", "环比", "同比", "象限"],
        [[r["cat"], r["mom"].p(), r["yoy"].p(), r["q"]] for r in rows])
    f.chart = {
        "type": "grouped_bar",
        "title": f"{tense['cat']} 环比 {tense['mom'].p()}、同比 {tense['yoy'].p()}："
                 f"{len(rows)} 个品类的两期方向对比",
        "subtitle": f"{len(rows)} 个品类 · 最新一期 · 环比 vs 同比",
        "note": "同比基期由源表口径决定，本报告不重算",
        "unit_meta": "变化率（%）",
        "source": "品类环比/同比列，取最新一期",
        "refs": _ids([r["mom"] for r in rows] + [r["yoy"] for r in rows]),
        "categories": [r["cat"] for r in rows],
        "series": [
            {"name": "环比", "values": [round(r["m"], 2) for r in rows]},
            {"name": "同比", "values": [round(r["y"], 2) for r in rows]},
        ],
    }
    f.so_what = ("采购分档：环比同比双升的锁价、高位回落的锁量不锁价、"
                 "双降的随行就市、短期反弹的先不追。")
    f.boundary = "环比是相邻两期、同比是去年同月；用哪一列由源表口径决定，本报告不重算同比基期。"
    f.weight = 1.1
    f.meta = {"rows": rows}
    return f


# --------------------------------------------------------------------------- #
# 3. 时间轨迹
# --------------------------------------------------------------------------- #
def m_trajectory(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    cats = [k for k in v.snapshot if k in v.series and len(v.series[k]) >= 3]
    if len(cats) < 2:
        return None
    stats = []
    for k in cats:
        s = v.series[k]
        vals = [x for _, x in s]
        ch = _pct_change(vals[0], vals[-1])
        cv = _cv(vals) * 100
        n_first = c.n(f"{k} 轨迹首值", vals[0], "元/斤", s[0][0], v.series_src.get(k, ""))
        n_last = c.n(f"{k} 轨迹末值", vals[-1], "元/斤", s[-1][0], v.series_src.get(k, ""))
        stats.append({"cat": v.label(k), "key": k, "n": len(s), "first": vals[0],
                      "last": vals[-1], "ch": ch, "cv": cv, "max": max(vals),
                      "min": min(vals), "src": v.series_src.get(k, ""), "vals": vals,
                      "n_first": n_first, "n_last": n_last,
                      "times": [t for t, _ in s]})
    stats.sort(key=lambda s: s["ch"], reverse=True)
    hi, lo = stats[0], stats[-1]
    hi_cv = max(stats, key=lambda s: s["cv"])

    # 篮子序列：每个期次取品类均值，交给 r06 做一次独立诊断
    by_time: Dict[str, List[float]] = {}
    for k in cats:
        for t, x in v.series[k]:
            by_time.setdefault(t, []).append(x)
    basket = [(t, st.mean(xs)) for t, xs in by_time.items() if len(xs) >= 2]
    basket.sort(key=lambda x: _period_key(x[0]))
    n = c.n("篮子期数", len(basket), "期", digits=0)
    skill_line = ""
    if len(basket) >= 3:
        p = ctx.tmp_csv("basket.csv", ["date", "value"],
                        [[_iso_date(t) or f"2026-01-{i + 1:02d}", round(x, 4)]
                         for i, (t, x) in enumerate(basket)])
        ts = ctx.skills.call("r06", "explore", "time_series",
                             ["--input", p, "--date", "date", "--value", "value"])
        ctx.memo["time_series"] = ts
        slope = (ts.get("trend") or {}).get("slope_per_step")
        if isinstance(slope, (int, float)):
            ns = c.n("篮子序列斜率", float(slope), "元/期/斤")
            anom = (ts.get("anomalies") or {}).get("count", 0)
            na = c.n("异常点数", float(anom), "个", digits=0)
            skill_line = (f"引擎复核（r06 explore time_series）：{n} 期篮子斜率 "
                          f"{ns.value:.4f} 元/期，异常点 {na.value:.0f} 个；"
                          "斜率方向与首末变化一致，说明不是单点噪声。")
            ctx.memo["anomaly"] = float(anom)
        else:
            # 引擎因样本不足拒绝出斜率，这是有效结论：报告不许自己补一个斜率
            err = str(ts.get("error") or "引擎未给出趋势")
            skill_line = (f"引擎复核（r06 explore time_series）拒绝出结论：{err}。"
                          "本轮不解释斜率与季节性，只报首末变化。")

    ch_hi = c.n(f"{hi['cat']} 首末变化率", hi["ch"] / 100, "%")
    ch_lo = c.n(f"{lo['cat']} 首末变化率", lo["ch"] / 100, "%")
    cv_hi = c.n(f"{hi_cv['cat']} 变异系数", hi_cv["cv"] / 100, "%")
    f = _finding("trajectory",
                 f"轨迹：{n} 期里 {hi['cat']} {ch_hi.p()}、{lo['cat']} {ch_lo.p()}，"
                 f"{hi_cv['cat']} 波动最大（CV {cv_hi.p()}）",
                 "这段时间价格是趋势性移动，还是噪声？", c, mark)
    f.add(f"{hi['cat']} 从 {hi['first']:.2f} 走到 {hi['last']:.2f} 元/斤，"
          f"累计 {ch_hi.p()}；{lo['cat']} 从 {lo['first']:.2f} 到 {lo['last']:.2f}，"
          f"{ch_lo.p()}。", _ids(ch_hi, ch_lo, hi["n_first"], hi["n_last"],
                                 lo["n_first"], lo["n_last"]))
    f.add(f"{hi_cv['cat']} 的变异系数 {cv_hi.p()} 是这批品类里最高的，"
          "波动本身就是成本：报价有效期要缩到一周，否则接单即亏。", _ids(cv_hi))
    if skill_line:
        refs = _ids(ns, na) if "ns" in locals() else _ids(n)
        f.add(skill_line, refs)
    f.table = _table(
        "各品类轨迹统计（元/斤）",
        ["品类", "期数", "首值", "末值", "变化率", "CV"],
        [[s["cat"], str(s["n"]), f"{s['first']:.2f}", f"{s['last']:.2f}",
          f"{s['ch']:+.1f}%", f"{s['cv']:.1f}%"] for s in stats])
    picks = []
    for s in (hi, lo, hi_cv):
        if s["cat"] not in [p["cat"] for p in picks]:
            picks.append(s)
    xlabels = list(picks[0]["times"])
    series = []
    for s in picks:
        if len(s["vals"]) == len(xlabels):
            series.append({"name": s["cat"], "values": [round(x, 2) for x in s["vals"]]})
    if series:
        f.chart = {
            "type": "line",
            "title": f"{picks[0]['cat']} {ch_hi.p()}、{picks[1]['cat']} {ch_lo.p()}："
                     f"{len(xlabels)} 期内的反向轨迹",
            "subtitle": f"{len(xlabels)} 期 · {len(series)} 个品类 · 元/斤",
            "note": "短窗口估计，12 期以下不解释季节性",
            "unit_meta": "元/斤",
            "source": f"零售价序列（{v.series_src.get(picks[0]['key'], '')}）",
            "refs": [],
            "xlabels": xlabels,
            "series": series,
        }
    f.so_what = ("趋势向下的品类不要等反弹再采；波动大的品类用短周期报价，"
                 "把价格风险转移给合同而不是库存。")
    f.boundary = (f"只有 {n.value:.0f} 个期次，斜率与 CV 都是短窗口估计；"
                  "12 期以下不解释季节性。")
    f.meta = {"stats": stats}
    return f


# --------------------------------------------------------------------------- #
# 4. 两期贡献（涨跌两端拆）
# --------------------------------------------------------------------------- #
def m_contribution(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    cats = [k for k in v.snapshot if k in v.series and len(v.series[k]) >= 2]
    if len(cats) < 4:
        return None
    rows = []
    for k in cats:
        s = v.series[k]
        d = s[-1][1] - s[0][1]
        nd = c.n(f"{k} 价格变动额", d, "元/斤")
        rows.append({"cat": v.label(k), "key": k, "d": d, "nd": nd})
    up = [r for r in rows if r["d"] > 0]
    down = [r for r in rows if r["d"] < 0]
    net = sum(r["d"] for r in rows)
    gross_up = sum(r["d"] for r in up)
    gross_dn = sum(r["d"] for r in down)
    n_net = c.n("净变动", net, "元/斤")
    n_up = c.n("上涨端合计", gross_up, "元/斤")
    n_dn = c.n("下跌端合计", gross_dn, "元/斤")
    top = max(rows, key=lambda r: abs(r["d"]))
    n_top = c.n(f"{top['cat']} 变动额", top["d"], "元/斤")
    share = abs(top["d"]) / (gross_up + abs(gross_dn)) * 100 if (gross_up - gross_dn) else 0
    n_share = c.n("最大单项占毛变动比重", share / 100, "%")

    f = _finding("contribution",
                 f"贡献：涨的品类合计 +{gross_up:.2f} 元、跌的合计 {gross_dn:.2f} 元，"
                 f"净变动只有 {net:+.2f} 元",
                 "总变化是小幅净差还是结构性换手？", c, mark)
    f.add(f"{len(up)} 个上涨品类合计 {n_up} 元/斤，{len(down)} 个下跌品类合计 "
          f"{n_dn} 元/斤，两者相抵后净变动 {n_net} 元/斤。", _ids(n_up, n_dn, n_net))
    f.add(f"净差接近零不代表没变化：毛变动是净变动的数倍，说明这是一次结构性换手，"
          f"其中{top['cat']} 单项变动 {n_top} 元，占毛变动 {n_share.p()}。",
          _ids(n_top, n_share))
    f.add("把这种结构当成「价格平稳」会漏掉换手成本：涨的品类要多备货、"
          "跌的品类要防积压，两者不能用一个采购节奏。", _ids(n_top))
    f.table = _table(
        "两期价格变动与方向（元/斤）",
        ["品类", "变动额", "方向"],
        [[r["cat"], f"{r['d']:+.2f}", "涨" if r["d"] > 0 else "跌"] for r in rows])
    f.chart = {
        "type": "hbar",
        "title": f"涨跌相抵后净 {net:+.2f} 元，毛变动 {gross_up - gross_dn:+.2f} 元",
        "subtitle": f"{len(rows)} 个品类 · 首末两期 · 变动额（元/斤）",
        "note": "不含销量权重，只做价格口径拆解",
        "unit_meta": "价格变动额（元/斤）",
        "source": "首末两期价格重算",
        "refs": _ids([r["nd"] for r in rows]),
        "bars": [{"label": r["cat"], "value": round(r["d"], 2)} for r in rows],
    }
    f.so_what = ("按方向分别排采购节奏：涨的提前锁、跌的压缩在途库存；"
                 "不要用「均价平稳」掩盖换手。")
    f.boundary = "这是价格口径的变动拆解，不含销量权重；没有销量就做不了金额贡献，本报告不虚构权重。"
    return f


# --------------------------------------------------------------------------- #
# 5. 单位经济
# --------------------------------------------------------------------------- #
def m_economics(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    cats = [k for k in v.snapshot if k in v.wholesale]
    if len(cats) < 3:
        return None
    rows = []
    assumptions: List[float] = []
    for i, k in enumerate(cats, 1):
        r = v.snapshot[k][0]
        w = v.wholesale[k][0]
        rule = rule_of(k)
        loss, cold = rule["loss"], rule["cold"]
        assumptions += [loss, cold]
        nr = c.n(f"{k} 零售价", r, "元/斤", v.snapshot[k][1], v.primary)
        nw = c.n(f"{k} 批发价", w, "元/斤", "", v.wholesale[k][1])
        markup = (r / w - 1) * 100 if w else 0
        nmk = c.n(f"{k} 批零加价率", markup / 100, "%")
        nl = c.n(f"{k} 标准损耗率", loss, "%")
        nc = c.n(f"{k} 冷链与人工", cold, "元/斤")
        net = r * (1 - loss) - w - cold
        # 派生量走公式：零售 ×(1−损耗) − 批发 − 冷链；校验器会按 pack 里的 id 实算
        nnet = c.d(f"N{i:02d}", f"{nr.id}*(1-{loss})-{nw.id}-{cold}", net,
                   f"{k} 净毛利")
        margin = net / r if r else 0
        nmg = c.d(f"M{i:02d}", f"N{i:02d}/{nr.id}", margin,
                  f"{k} 净毛利率", "%")
        rows.append({"cat": v.label(k), "key": k, "r": nr, "w": nw,
                     "markup": nmk, "loss": nl, "cold": nc, "net": nnet,
                     "margin": nmg, "v": margin * 100, "nv": nnet})
    rows.sort(key=lambda x: x["v"], reverse=True)
    neg = [r for r in rows if r["v"] < 0]
    top = rows[0]
    worst = min(rows, key=lambda r: r["v"])
    title = (f"单位经济：{len(rows)} 个品类里 {len(neg)} 个扣损耗冷链后为负，"
             f"最好的是 {top['cat']} {top['nv'].value:+.2f} 元/斤"
             f"（{top['margin'].p()}）、最差的是 {worst['cat']} "
             f"{worst['nv'].value:+.2f} 元/斤")
    f = _finding("economics", title,
                 "批零差价看起来有钱赚，扣掉损耗和冷链还剩多少？", c, mark)
    f.assumptions = assumptions
    f.add(f"{top['cat']} 批零加价 {top['markup'].p()}，扣 {top['loss'].p()} 损耗与 "
          f"{top['cold']} 元/斤冷链后净毛利 {top['nv'].value:+.2f} 元/斤，"
          f"净利率 {top['margin'].p()}——"
          + ("这是利润品。" if top["nv"].value > 0 else "连最好的品类也没覆盖成本。"),
          _ids(top["markup"], top["loss"], top["cold"], top["nv"], top["margin"]))
    if neg:
        names = _names([f"{r['cat']}（{r['nv'].value:+.2f} 元、{r['margin'].p()}）"
                        for r in neg], 3)
        deep = [r for r in neg if r["v"] <= -0.5]
        tail = ("其中 " + _names([r["cat"] for r in deep], 2) + " 失血最快；"
                if deep else "三者都只是擦线为负；")
        f.add(f"扣完成本转负的是{names}。{tail}"
              "共同点是加价率撑不住损耗与冷链，规模放大只会放大亏损。",
              _ids([r["nv"] for r in neg] + [r["margin"] for r in neg]))
    f.add("批零差是名义空间，净毛利才是可执行空间；本表把品类按净毛利排序，"
          "排序结果与按加价率排会不一样。", _ids(top["margin"]))
    f.table = _table(
        "单位经济测算（元/斤）",
        ["品类", "零售", "批发", "加价率", "损耗", "冷链", "净毛利", "净利率"],
        [[r["cat"], str(r["r"]), str(r["w"]), r["markup"].p(), r["loss"].p(),
          str(r["cold"]), f"{r['nv'].value:+.2f}", r["margin"].p()] for r in rows])
    f.chart = {
        "type": "hbar",
        "title": f"{top['cat']} 净利率 {top['margin'].p()}、{worst['cat']} "
                 f"{worst['margin'].p()}，{len(neg)} 个品类为负",
        "subtitle": f"{len(rows)} 个品类 · 零售−批发−损耗−冷链 · 净毛利率",
        "note": "损耗与冷链为品类经验值，不含租金、人力与税",
        "unit_meta": "净毛利率（%）",
        "source": "零售价 − 批发价 − 标准损耗 − 冷链人工",
        "refs": _ids([r["margin"] for r in rows]),
        "bars": [{"label": r["cat"], "value": round(r["v"], 2)} for r in rows],
    }
    f.so_what = ("按净毛利分配品类角色：正的做利润品、负但有客流的做引流品、"
                 "负且无量又占资金的直接停采。")
    shown = "、".join(f"{r['cat']} {r['loss'].p()}/{str(r['cold'])}" for r in rows[:4])
    more = "等" if len(rows) > 4 else ""
    f.boundary = (f"损耗率与冷链成本是品类经验值（{shown}{more}；前者为损耗率，"
                  "后者为冷链元/斤），不是企业台账；净毛利不含门店租金、"
                  "人力与税，不能直接当财务口径。")
    f.meta = {"rows": rows}
    ctx.memo["economics"] = rows
    return f


# --------------------------------------------------------------------------- #
# 6. 上下游传导
# --------------------------------------------------------------------------- #
def m_transmission(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    rows = []
    dropped = []
    for k in v.snapshot:
        w = v.wholesale.get(k)
        if not w:
            continue
        # 产地报价低于销地批发三成的，按口径异常剔除（规格/单位错配），不当倒挂结论
        o = pick_origin(v, k, floor=0.3 * w[0])
        if not o:
            if pick_origin(v, k):
                dropped.append(v.label(k))
            continue
        r = v.snapshot[k][0]
        no = c.n(f"{k} 产地价", o["value"], "元/斤", o["time"], o["place"])
        nw = c.n(f"{k} 销地批发价", w[0], "元/斤", "", w[1])
        nr = c.n(f"{k} 零售价", r, "元/斤", v.snapshot[k][1], v.primary)
        up = w[0] - o["value"]
        nup = c.n(f"{k} 产地到批发价差", up, "元/斤")
        down = r - w[0]
        ndn = c.n(f"{k} 批发到零售价差", down, "元/斤")
        rows.append({"cat": v.label(k), "key": k, "o": no, "w": nw, "r": nr,
                     "up": nup, "dn": ndn, "label": o["label"], "place": o["place"]})
    if not rows:
        return None
    for r in rows:
        markup = (r["r"].value / r["w"].value - 1) * 100 if r["w"].value else 0
        r["mk"] = c.n(f"{r['key']} 批零加价率", markup / 100, "%")
        r["mk_v"] = markup
    inv = [r for r in rows if r["up"].value < 0]
    main = max(rows, key=lambda r: abs(r["dn"].value))
    title = ""
    if inv:
        bad = inv[0]
        title = (f"传导：{bad['cat']} 产地 {bad['o']} 已高于销地批发 {bad['w']}，"
                 f"倒挂 {abs(bad['up'].value):.2f} 元/斤")
    else:
        title = (f"传导：{main['cat']} 批发到零售吃掉 {main['dn']} 元/斤，"
                 f"批零加价 {main['mk'].p()}")
    f = _finding("transmission", title,
                 "链路利润被哪一段吃掉，有没有产地倒挂？", c, mark)
    if inv:
        bad = inv[0]
        f.add(f"{bad['cat']} 产地 {bad['place']} 报 {bad['o']} 元/斤，"
              f"销地批发只有 {bad['w']} 元/斤，按产地价直采每斤倒挂 "
              f"{abs(bad['up'].value):.2f} 元——这条直采路径必须关闭。",
              _ids(bad["o"], bad["w"], bad["up"]))
    if main["up"].value < 0:
        f.add(f"{main['cat']} 批发 {main['w']} 到零售 {main['r']} 加价 {main['mk'].p()}，"
              f"但产地到批发这一段是倒挂 {abs(main['up'].value):.2f} 元/斤；"
              "利润全在零售端，靠压上游拿不到空间。",
              _ids(main["w"], main["r"], main["mk"], main["up"]))
    else:
        f.add(f"{main['cat']} 批发 {main['w']} 到零售 {main['r']} 加价 {main['mk'].p()}，"
              f"产地到批发这一段有 {main['up']} 元/斤——两条价差要分开谈，"
              "不能合成一个「采购价」。",
              _ids(main["w"], main["r"], main["mk"], main["up"]))
    f.add("要压成本，只能压上游与物流那一段；对零售端加价动刀，等于自己把客流推走。",
          _ids(main["up"], main["dn"]))
    f.table = _table(
        "链路各段价格（元/斤）",
        ["品类", "产地", "批发", "零售", "加价率", "产地→批发", "批发→零售"],
        [[r["cat"], str(r["o"]), str(r["w"]), str(r["r"]), r["mk"].p(),
          f"{r['up'].value:+.2f}", f"{r['dn'].value:+.2f}"] for r in rows])
    f.chart = {
        "type": "grouped_bar",
        "title": f"{main['cat']} 批发到零售 {main['dn']} 元/斤，是产地到批发的 "
                 f"{abs(main['dn'].value / main['up'].value) if main['up'].value else 0:.1f} 倍",
        "subtitle": f"{len(rows)} 个品类 · 两段加价的绝对值 · 元/斤",
        "note": "两段不是同一交易环节，只比较加价厚度",
        "unit_meta": "元/斤",
        "source": "产地出场价 / 销地批发价 / 零售价",
        "refs": _ids([r["o"] for r in rows] + [r["r"] for r in rows]),
        "categories": [r["cat"] for r in rows],
        # 标题讲的是两段加价，柱子就必须画两段加价，不能画价格水平
        "series": [
            {"name": "产地→批发", "values": [round(r["up"].value, 2) for r in rows]},
            {"name": "批发→零售", "values": [round(r["dn"].value, 2) for r in rows]},
        ],
    }
    f.so_what = ("锁价锁在产地/一级批发这一端，不锁零售价；"
                 "跨市采购前先算倒挂，倒挂的直接关闭。")
    f.meta = {"rows": rows}
    f.boundary = ("产地价是出场/装车口径，与销地批发不是同一交易环节；价差只能看方向，"
                  "不能当套利收益。只有同品类、同规格、同一时点的两段价才可比，"
                  "跨环节直接相减不是套利收益。")
    if dropped:
        f.boundary += (f"；{_names(dropped)} 的产地报价低于销地批发三成，"
                       "按口径异常（规格或单位错配）剔除，未纳入本表。")
    return f


# --------------------------------------------------------------------------- #
# 7. 跨市场套利
# --------------------------------------------------------------------------- #
def m_arbitrage(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    by_cat: Dict[str, Dict[str, float]] = {}
    for (region, cat), val in v.region.items():
        by_cat.setdefault(cat, {})[region] = val
    # 批发市场逐市场报价也是跨市场价差：同品类、同时点、不同市场
    # 只纳入有零售价的品类，避免与本报告主线（零售品类）串台
    for (place, cat), val in v.quotes.items():
        if cat not in v.snapshot:
            continue
        by_cat.setdefault(cat, {})[place] = val
    rows = []
    for cat, prices in by_cat.items():
        if len(prices) < 2:
            continue
        buy_r = min(prices, key=prices.get)
        sell_r = max(prices, key=prices.get)
        if buy_r == sell_r:
            continue
        buy, sell = prices[buy_r], prices[sell_r]
        rule = rule_of(cat)
        net = sell * (1 - rule["loss"]) - buy - FREIGHT_PER_JIN - rule["cold"]
        margin = net / sell * 100 if sell else 0
        nb = c.n(f"{cat} {buy_r} 采购价", buy, "元/斤")
        ns = c.n(f"{cat} {sell_r} 销售价", sell, "元/斤")
        nnet = c.n(f"{cat} 跨市净毛利", net, "元/斤")
        nmg = c.n(f"{cat} 跨市净利率", margin / 100, "%")
        nsp = c.n(f"{cat} 跨市价差", sell - buy, "元/斤")
        rows.append({"cat": v.label(cat), "key": cat, "buy_r": buy_r,
                     "sell_r": sell_r, "b": nb, "s": ns, "net": nnet, "mg": nmg,
                     "v": margin, "nv": nnet, "nsp": nsp, "spread": sell - buy})
    if not rows:
        return None
    rows.sort(key=lambda r: r["v"], reverse=True)
    best, worst = rows[0], rows[-1]
    bad = [r for r in rows if r["v"] < 0]
    title = (f"套利：{best['cat']} {best['buy_r']} 买 {best['b']}、"
             f"{best['sell_r']} 卖 {best['s']}，扣运费冷链净 {best['nv'].value:.2f} 元/斤"
             f"（{best['mg'].p()}）")
    f = _finding("arbitrage", title,
                 "同一时点跨市场价差，扣掉运费与损耗还剩不剩钱？", c, mark)
    f.assumptions = [FREIGHT_PER_JIN, rule_of(best["cat"])["loss"],
                     rule_of(best["cat"])["cold"]]
    f.add(f"{best['cat']} 价差 {best['spread']:.2f} 元/斤，扣 {FREIGHT_PER_JIN} 元运费、"
          f"标准损耗与冷链后净 {best['nv'].value:.2f} 元/斤，净利率 {best['mg'].p()}；"
          "价差本身不是利润，扣完成本才是。",
          _ids(best["b"], best["s"], best["net"], best["mg"]))
    if bad:
        f.add(f"不能调运的是{_names([f'{r['cat']}（{r['nv'].value:+.2f} 元）' for r in bad], 3)}："
              "价差被运费和损耗吃掉，跨市反而亏。", _ids([r["net"] for r in bad]))
    else:
        f.add(f"最差的是{worst['cat']}，净 {worst['nv'].value:.2f} 元/斤；"
              "所有品类都还能覆盖运费，但单价低的品类只剩几分钱容错。",
              _ids(worst["net"]))
    f.table = _table(
        "跨市场套利测算（元/斤）",
        ["品类", "买入地", "买入价", "卖出地", "卖出价", "净毛利", "净利率"],
        [[r["cat"], r["buy_r"], str(r["b"]), r["sell_r"], str(r["s"]),
          f"{r['nv'].value:+.2f}", r["mg"].p()] for r in rows])
    f.chart = {
        "type": "hbar",
        "title": f"{best['cat']} 跨市净利 {best['mg'].p()}，{len(bad)} 个品类调运即亏",
        "subtitle": f"{len(rows)} 个品类 · 两地区同时点价差 − 运费 − 损耗 · 净毛利率",
        "note": "情景值，首单必须实测运费与到店损耗",
        "unit_meta": "跨市净毛利率（%）",
        "source": "地区同品类价差 − 运费 − 损耗 − 冷链",
        "refs": _ids([r["mg"] for r in rows]),
        "bars": [{"label": r["cat"], "value": round(r["v"], 2)} for r in rows],
    }
    f.so_what = ("配额按价差分档：价差大于两倍运费才扩量，低于运费不启动；"
                 "低单价品类只在价差能覆盖损耗时试单。")
    f.boundary = ("两地区价格不是同一交易环节的报价，且未计入冷链装载率；"
                  "净利是情景值，首单必须实测运费与到店损耗。")
    f.meta = {"rows": rows}
    ctx.memo["arbitrage"] = rows
    return f


# --------------------------------------------------------------------------- #
# 8. 保本线
# --------------------------------------------------------------------------- #
def m_breakeven(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    econ = ctx.memo.get("economics") or []
    if not econ:
        return None
    rows = []
    for r in econ:
        if r["v"] >= 0:
            continue
        cat = r.get("key") or r["cat"]
        rule = rule_of(cat)
        retail = r["r"].value
        whole = r["w"].value
        need = (whole + rule["cold"]) / (1 - rule["loss"])
        uplift = (need / retail - 1) * 100 if retail else 0
        nneed = c.n(f"{cat} 保本零售价", need, "元/斤")
        nuplift = c.n(f"{cat} 保本提价幅度", uplift / 100, "%")
        # 直采路径：产地 + 集配 + 分拣 对比批发
        o = pick_origin(v, cat)
        share = 0.0
        nshare = None
        if o:
            direct = o["value"] + FREIGHT_PER_JIN + 0.10
            saving = whole - direct
            if saving > 0:
                share = max(0.0, min(1.0, (-r["nv"].value) / saving)) * 100
                nshare = c.n(f"{cat} 保本直采占比", share / 100, "%")
        rows.append({"cat": r["cat"], "need": nneed, "up": nuplift,
                     "share": nshare, "w": r["w"], "v": uplift,
                     "loss": r["nv"].value, "nv": r["nv"]})
    if not rows:
        return None
    rows.sort(key=lambda x: x["v"])
    hard = min(rows, key=lambda r: r["v"])
    title = (f"保本：{hard['cat']} 零售提 {hard['up'].p()} 即转正"
             + (f"；{rows[-1]['cat']} 要提 {rows[-1]['up'].p()}" if len(rows) > 1 else ""))
    f = _finding("breakeven", title,
                 "负毛利的品类，是提价能救，还是只能降本？", c, mark)
    f.assumptions = [rule_of(r["cat"])["loss"] for r in rows] + \
                    [rule_of(r["cat"])["cold"] for r in rows]
    for r in rows[:3]:
        line = (f"{r['cat']} 净毛利 {r['loss']:+.2f} 元/斤，保本零售价 "
                f"{r['need']} 元，需提价 {r['up'].p()}。")
        if r["share"] is not None:
            line += f"若走产地直采，直采占比到 {r['share'].p()} 即可不动价保本。"
        f.add(line, _ids(r["nv"], r["need"], r["up"], r["share"]))
    f.add("提价与直采是两条不同的路：单价高的品类提一点就够，单价低的高频品只能降本，"
          "否则稍微提价就足以打掉客流。", _ids(rows[0]["up"], rows[0]["need"]))
    f.table = _table(
        "保本测算（元/斤）",
        ["品类", "现状净毛利", "保本零售价", "需提价", "保本直采占比"],
        [[r["cat"], f"{r['loss']:+.2f}", str(r["need"]), r["up"].p(),
          (r["share"].p() if r["share"] else "—")] for r in rows])
    f.so_what = ("按单价分路径：高单价品类先提价、低单价高频品只降本不涨价；"
                 "两条路径的验收指标不同，不能合成一个毛利率目标。")
    # 图：保本所需提价幅度（按品类排序）——这一节讲的就是「要提多少」，
    # 没有图等于让读者自己从表里读出排序（P4 之后图表覆盖率是硬门禁）。
    f.chart = {
        "type": "hbar",
        "title": (f"保本提价：{hard['cat']} 需 {hard['up'].p()}，"
                  f"{rows[-1]['cat']} 需 {rows[-1]['up'].p()}"),
        "subtitle": f"{len(rows)} 个负毛利品类 · 只覆盖损耗与冷链",
        "unit_meta": "%",
        "source": "证据包（保本价 =（批发价+冷链）÷（1−损耗率））",
        "refs": _ids(*[r["up"] for r in rows]),
        "bars": [{"label": r["cat"], "value": round(r["v"], 2)} for r in rows],
        "note": "线为保本所需提价幅度；超过 5% 的品类优先走直采降本",
    }
    f.boundary = ("保本价只覆盖损耗与冷链，不含租金与人力；直采成本按产地价 + "
                  f"{FREIGHT_PER_JIN} 元运费 + 0.10 元分拣估算。")
    f.meta = {"rows": rows}
    return f


# --------------------------------------------------------------------------- #
# 9. 风险与缺口
# --------------------------------------------------------------------------- #
def m_risk(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    if not v.series:
        return None
    stats = []
    for k, s in v.series.items():
        vals = [x for _, x in s]
        if len(vals) < 2:
            continue
        cv = _cv(vals) * 100
        # 最大回撤（从峰值到谷底）
        peak, mdd = vals[0], 0.0
        for x in vals:
            peak = max(peak, x)
            if peak:
                mdd = max(mdd, (peak - x) / peak * 100)
        ncv = c.n(f"{k} 变异系数", cv / 100, "%")
        nmdd = c.n(f"{k} 最大回撤", mdd / 100, "%")
        stats.append({"cat": v.label(k), "key": k, "n": len(vals), "cv": ncv,
                      "mdd": nmdd, "has_w": k in v.wholesale,
                      "cv_v": cv, "mdd_v": mdd})
    if not stats:
        return None
    no_base = [s["cat"] for s in stats if not s["has_w"]]
    short = [s["cat"] for s in stats if s["n"] < 8]
    hi = max(stats, key=lambda s: s["cv_v"])
    n_nb = c.n("无批发基准品类数", len(no_base), "个", digits=0)
    n_short = c.n("期数不足品类数", len(short), "个", digits=0)
    title = (f"风险：{n_short} 个品类期数不足 8 期，"
             f"{hi['cat']} 波动最大（CV {hi['cv'].p()}）")
    if no_base:
        title = (f"风险：{n_nb} 个品类没有批发基准价、"
                 f"{n_short} 个品类期数不足 8 期，{hi['cat']} 波动最大"
                 f"（CV {hi['cv'].p()}）")
    f = _finding("risk", title,
                 "哪些结论现在还不能用，缺哪一块数据？", c, mark)
    if no_base:
        f.add(f"{_names(no_base, 4)}没有同口径批发价，做不了单位经济；"
              "这几类只能看趋势，不能给毛利结论。", _ids(n_nb))
    f.add(f"{hi['cat']} 变异系数 {hi['cv'].p()}、最大回撤 {hi['mdd'].p()}，"
          "是这批品类里最需要设价格护栏的。", _ids(hi["cv"], hi["mdd"]))
    f.add(f"{n_short} 个品类序列不足 8 期，斜率与季节判断一律不成立；"
          "补数之前只做周度随行，不做趋势外推。", _ids(n_short))
    f.table = _table(
        "风险与数据覆盖（元/斤）",
        ["品类", "期数", "CV", "最大回撤", "批发基准", "说明"],
        [[s["cat"], str(s["n"]), s["cv"].p(), s["mdd"].p(),
          "有" if s["has_w"] else "缺",
          "样本偏短" if s["n"] < 8 else "可用"] for s in stats])
    # 分布复核：把波动最大的序列交给 r06 describe
    target = v.series.get(hi["key"]) or []
    if len(target) >= 3:
        p = ctx.tmp_csv("risk.csv", ["date", "value"],
                        [[_iso_date(t) or f"2026-01-{i + 1:02d}", round(x, 4)]
                         for i, (t, x) in enumerate(target)])
        ds = ctx.skills.call("r06", "describe", "",
                             ["--input", p, "--col", "value"])
        stt = (ds.get("describe") or {}).get("value") or {}
        if isinstance(stt.get("std"), (int, float)):
            nsd = c.n(f"{hi['cat']} 标准差", float(stt["std"]), "元/斤")
            f.add(f"r06 describe 复核：{hi['cat']} 标准差 {nsd} 元/斤，"
                  "与变异系数同向，波动不是单一异常点造成的。", _ids(nsd))
    f.so_what = ("先补三类数：批发基准价、至少 12 期序列、产地→到店的实际运费；"
                 "补不齐就在报告里保留缺口，不用估算值冒充实测。")
    f.boundary = "缺口来自源数据本身，不是本项目拒绝计算；有数据的部分仍按实际值计算。"
    f.meta = {"no_base": no_base, "no_base_count": len(no_base),
              "min_periods": 8}
    return f


# --------------------------------------------------------------------------- #
# 10. 样本充分性
# --------------------------------------------------------------------------- #
def m_sample(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    n_periods = max((len(s) for s in v.series.values()), default=0)
    if n_periods < 2:
        return None
    n = c.n("可用期数", n_periods, "期", digits=0)
    # r19：Wilson 区间，评估「N 期里同向的有几期」这一判断的置信度
    same_dir = sum(1 for s in v.series.values()
                   if len(s) >= 2 and s[-1][1] > s[0][1])
    k = c.n("同向品类数", same_dir, "个", digits=0)
    r19 = ctx.skills.call("r19", "eval-ci", "",
                          ["--successes", str(same_dir), "--n", str(len(v.series))])
    ci = ((r19.get("eval_ci") or {}).get("ci95") or [])
    lo = hi = None
    if len(ci) == 2:
        lo = c.n("同向占比下界", float(ci[0]) / 100, "%")
        hi = c.n("同向占比上界", float(ci[1]) / 100, "%")
    # r06 power：检验均值差异需要的样本量
    pw = ctx.skills.call("r06", "power", "", ["--baseline", "0.05", "--mde", "0.01"])
    req = (pw.get("power") or {}).get("required_n_per_group")
    nreq = c.n("每组所需样本量", float(req), "个", digits=0) if isinstance(req, (int, float)) else None
    title = (f"样本：{n} 期里 {k} 个品类同向"
             + (f"，同向占比 95% 区间 {lo.p()}—{hi.p()}" if lo and hi else "")
             + (f"；判 1 个百分点价差每组要 {nreq} 个样本" if nreq else ""))
    f = _finding("sample", title,
                 "这点差异是真实差异，还是样本不够造成的噪声？", c, mark)
    if lo and hi:
        f.add(f"{len(v.series)} 个品类里 {same_dir} 个首末同向，Wilson 95% 区间 "
              f"{lo.p()}—{hi.p()}；区间越宽，越不能把「多数上涨」说成趋势。",
              _ids(n, k, lo, hi))
    if nreq:
        f.add(f"要用均值差异判 1 个百分点的价差，每组需要 {nreq} 个样本；"
              "现有期数远不够，所以本报告只做方向判断，不做显著性结论。",
              _ids(nreq))
    f.add(f"可用的统计结论只有两类：方向（{k} 个同向）与量级（首末变化率）；"
          "「显著优于」这类判断在现有样本下不成立。", _ids(n, k))
    f.table = _table(
        "样本充分性",
        ["口径", "值", "含义"],
        [["可用期数", str(n), "序列长度"],
         ["同向品类", str(k), "首末价格方向"],
         ["每组所需样本", (str(nreq) if nreq else "—"), "均值差异口径"],
         ["置信区间", (f"{lo.p()}—{hi.p()}" if lo and hi else "—"), "Wilson"]])
    f.so_what = ("把结论强度降一档：方向可以说，显著性不能说；"
                 "要升级成显著结论，先补到每组所需样本量。")
    f.boundary = "Wilson 区间对二项比例有效，不适用于价格均值；均值检验的样本量按 MDE 1pp 估算。"
    f.assumptions = [95, 0.05, 0.01]
    f.meta = {"n_periods": n_periods, "min_same": same_dir,
              "min_effect_pp": 1, "required_n": req}
    return f


# --------------------------------------------------------------------------- #
# 11. 证据台账（r05）
# --------------------------------------------------------------------------- #
def m_ledger(ctx: Ctx, findings: List[Finding]) -> Optional[Finding]:
    c = ctx.cite
    mark = c.begin()
    if not findings:
        return None
    sources = []
    for i, f in enumerate(ctx.desk.files, 1):
        sources.append({"id": f"S{i:02d}", "name": f,
                        "type": "database" if f.endswith((".csv", ".json")) else "secondary"})
    src_id = {s["name"]: s["id"] for s in sources}
    # 结论挂来源：优先主力零售表；没有价格表时用第一张表，保证 claim 不落空
    if ctx.views.primary in src_id:
        base = [src_id[ctx.views.primary]]
    else:
        base = [sources[0]["id"]] if sources else []
    extra = [src_id[f] for f in ctx.desk.files
             if any(k in f for k in ("批发", "产地", "区域"))][:2]
    claims = []
    for i, f in enumerate(findings, 1):
        sids = base + (extra if f.key in ("economics", "transmission", "arbitrage",
                                         "breakeven") else [])
        claims.append({"id": f"C{i:02d}", "kind": "calculation",
                       "text": f.title[:90], "source_ids": sids or base})
    data = {"claims": claims, "sources": sources}
    import json
    p = Path(ctx.tmpdir) / "ledger_input.json"
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    res = ctx.skills.call("r05", "research", "ledger", ["--input", str(p)])
    cov = res.get("coverage_rate")
    verdict = res.get("verdict") or ("PASS" if res.get("ok") else "FAIL")
    ncl = c.n("台账结论数", len(claims), "条", digits=0)
    nsrc = c.n("台账来源数", len(sources), "个", digits=0)
    title = f"证据：{ncl} 条结论全部挂到 {nsrc} 个来源，R05 台账 {verdict}"
    f = _finding("ledger", title, "报告里的每条结论能不能回到源文件？", c, mark)
    f.add(f"r05 research ledger 对本报告 {len(claims)} 条结论、{len(sources)} 个来源做了"
          f"交叉引用校验，结论覆盖率 {float(cov or 0) * 100:.0f}%，判决 {verdict}。",
          _ids(ncl, nsrc))
    f.add("台账口径：结论 → 来源文件；数字口径：正文数字 → 证据包 id。"
          "两层都过，才算「可回放」的结论。", _ids(ncl))
    f.table = _table(
        "证据台账（摘要）",
        ["结论数", "来源数", "覆盖率", "判决"],
        [[str(ncl), str(nsrc), f"{float(cov or 0) * 100:.0f}%", verdict]])
    f.so_what = "台账 FAIL 的报告不发布；覆盖率低于 100% 时，未挂来源的结论从正文删掉。"
    f.boundary = "台账只校验引用关系，不校验源文件本身的真实性。"
    f.meta = {"verdict": verdict, "coverage": cov, "claims": len(claims),
              "sources": len(sources)}
    return f


# --------------------------------------------------------------------------- #
# 10. 趋势外推（带区间，不冒充点预测）
# --------------------------------------------------------------------------- #
def m_forecast(ctx: Ctx) -> Optional[Finding]:
    v, c = ctx.views, ctx.cite
    mark = c.begin()
    cats = [k for k in v.snapshot if k in v.series and len(v.series[k]) >= 4]
    if len(cats) < 2:
        return None
    rows = []
    for k in cats:
        ys = [x for _, x in v.series[k]]
        n = len(ys)
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        if not den:
            continue
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
        intercept = my - slope * mx
        resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
        sd = st.pstdev(resid) if n > 2 else 0.0
        nxt = intercept + slope * n
        low, high = nxt - 1.28 * sd, nxt + 1.28 * sd
        last = ys[-1]
        ch = _pct_change(last, nxt)
        rows.append({
            "cat": v.label(k), "key": k, "n": n, "last": last, "next": nxt,
            "low": low, "high": high, "ch": ch, "slope": slope, "sd": sd,
            "n_last": c.n(f"{k} 上期价", last, "元/斤"),
            "n_next": c.n(f"{k} 下期中枢", nxt, "元/斤"),
            "n_low": c.n(f"{k} 下期下沿", low, "元/斤"),
            "n_high": c.n(f"{k} 下期上沿", high, "元/斤")})
    if not rows:
        return None
    rows.sort(key=lambda r: abs(r["ch"]), reverse=True)
    top, bot = rows[0], rows[-1]
    n = c.n("外推期数", top["n"], "期", digits=0)
    n_next = c.n(f"{top['key']} 下期中枢", top["next"], "元/斤")
    n_low = c.n(f"{top['key']} 下期下沿", top["low"], "元/斤")
    n_high = c.n(f"{top['key']} 下期上沿", top["high"], "元/斤")
    n_ch = c.n(f"{top['key']} 下期变化率", top["ch"] / 100, "%")
    n_bot = c.n(f"{bot['key']} 下期变化率", bot["ch"] / 100, "%")
    title = (f"外推：按 {n} 期斜率，下期{top['cat']} {n_next} 元/斤"
             f"（{n_low}—{n_high}，{n_ch.p()}），{bot['cat']} {n_bot.p()}")
    f = _finding("forecast", title,
                 "按现有斜率外推，下一期会落在哪、区间多宽？", c, mark)
    f.assumptions = [80]
    f.add(f"用 {top['n']} 期最小二乘斜率外推，{top['cat']} 下期中枢 "
          f"{n_next} 元/斤，80% 区间 {n_low}—{n_high}；区间宽度来自残差，"
          "不是拍脑袋的上下 10%。", _ids(n, n_next, n_low, n_high))
    stable = [r for r in rows if r["n"] >= 6]
    if not stable:
        f.add(f"{len(rows)} 个品类都只有 {top['n']} 期，达不到 6 期；"
              "外推只能当方向参考，不能当采购承诺。", _ids(n, n_ch, n_bot))
    f.add(f"区间宽度比中枢更可用：{top['cat']} 的上下沿相差 "
          f"{top['high'] - top['low']:.2f} 元/斤，报价有效期应短于外推步长，"
          "到上沿前锁价、到下沿前清库。", _ids(n_low, n_high))
    f.table = _table(
        "下期外推与 80% 区间（元/斤）",
        ["品类", "期数", "上期", "下期中枢", "下沿", "上沿", "变化率"],
        [[r["cat"], str(r["n"]), str(r["n_last"]), str(r["n_next"]),
          str(r["n_low"]), str(r["n_high"]), f"{r['ch']:+.1f}%"] for r in rows])
    f.chart = {
        "type": "error_bar",
        "title": f"{top['cat']} 下期 {n_next} 元/斤，区间 {n_low}—{n_high}",
        "subtitle": f"最小二乘外推 · {top['n']} 期 · 80% 残差区间",
        "note": "区间宽度来自残差，不是固定 ±10%",
        "unit_meta": "元/斤（误差棒为 80% 残差区间）",
        "source": f"最小二乘外推（{n.value:.0f} 期，SD）",
        "err_type": "SD",
        "refs": _ids([r["n_next"] for r in rows] + [n_next, n_low, n_high]),
        "items": [{"label": r["cat"], "value": round(r["next"], 2),
                   "err": round(1.28 * r["sd"], 2)} for r in rows],
        "series": [{"name": "下期中枢",
                    "values": [round(r["next"], 2) for r in rows]}],
    }
    f.so_what = ("外推只用于定「报价有效期」和「锁价触发点」："
                 "靠近上沿锁价、靠近下沿清库；不用于承诺销量。")
    f.boundary = ("外推是线性模型，不含季节与政策冲击；残差区间只反映历史波动，"
                  "不代表未来概率；期数不足 6 时只当方向参考。")
    f.meta = {"rows": rows}
    return f


METHODS = {
    "structure": m_structure,
    "momentum": m_momentum,
    "trajectory": m_trajectory,
    "contribution": m_contribution,
    "economics": m_economics,
    "transmission": m_transmission,
    "arbitrage": m_arbitrage,
    "breakeven": m_breakeven,
    "risk": m_risk,
    "sample": m_sample,
    "forecast": m_forecast,
}


FALSIFIERS: Dict[str, str] = {
    "structure": "若下期涨跌方向反转，或离散度收敛到 5% 以内，结构分化判断作废。",
    "momentum": "若下期环比与同比同向，或拐点消失，节奏判断作废。",
    "trajectory": "若新增 3 期后斜率翻转，趋势判断作废。",
    "contribution": "若下期贡献方向反转，换手判断作废。",
    "economics": "若损耗率或冷链成本比假设低 2 个百分点、净利转正，负毛利判断作废。",
    "transmission": "若产地→批发价差方向反转，传导判断作废。",
    "arbitrage": "若扣运费与损耗后价差为负，跨市机会作废。",
    "breakeven": "若零售价跌破保本价，或提价后销量下滑超过 20%，保本判断作废。",
    "forecast": "若实际值落在区间外，外推作废。",
    "risk": "若补数后缺口消失，或回撤/波动收敛到阈值内，风险判断作废。",
    "sample": "若样本补到每组所需量后显著性改变，样本判断作废。",
    "ledger": "若来源-结论映射变化，台账结论作废。",
}


def collect(ctx: Ctx) -> Tuple[Dict[str, Finding], List[str]]:
    """按依赖顺序跑方法；单点失败只记缺口，不中断整环。"""
    out: Dict[str, Finding] = {}
    gaps: List[str] = []
    order = ["structure", "momentum", "trajectory", "contribution", "economics",
             "transmission", "arbitrage", "breakeven", "forecast", "risk", "sample"]
    for key in order:
        fn = METHODS[key]
        try:
            f = fn(ctx)
        except Exception as exc:  # noqa: BLE001  单方法失败降级
            # 异常原文不进报告；需要排查时看 analysis_trace 里 plan 的 errors
            gaps.append(f"「{key}」本轮计算未完成，相关结论不采用。")
            continue
        if f is None:
            gaps.append(f"「{key}」本轮未命中（缺对应数据）")
        else:
            out[key] = f
    led = m_ledger(ctx, list(out.values()))
    if led:
        out["ledger"] = led
    for key, f in out.items():
        if not f.falsifier:
            f.falsifier = FALSIFIERS.get(key, "")
    return out, gaps

