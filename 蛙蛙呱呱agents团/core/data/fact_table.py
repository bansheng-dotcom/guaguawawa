# -*- coding: utf-8 -*-
"""core/fact_table —— 把项目目录里的「带来源观测」归一成一张可查的事实表。

为什么需要这一层（v7 的起点）：

`analysis_desk` 把数字压成 Obs（entity/time/value），够做价格序列，但**丢了三样
做深度分析必须具备的东西**：

1. **来源与等级**：没有 url / quote / grade，就无法回答「这个数凭什么信」；
2. **指标语义**：`indicator` 被压成了列名或文件名，无法回答「这是社零还是 CPI」；
3. **口径期**：`2026Q1-3`、`2025-11`、`2020` 混在一起，跨期比较会拿错基数。

本模块只做「读 + 归一 + 查」，不做分析：

    load(dir)   → FactTable
    find(...)   → 按指标关键词/地区/期取事实（AND 匹配，可排除）
    series(...) → 同一指标的多期序列（按年/季/月排序）
    one(...)    → 取一条，取不到就 None（调用方必须处理「没有」）

支持的项目数据形态（按优先级，全部可共存）：

    data/obs_*.json         [{id, indicator, value, unit, period, region,
                              source_org, source_title, url, quote, grade}]
    data/facts.json         [{metric, name, value, unit, period, source_id, level}]
                            或扁平 dict {key: value}（老项目）
    data/derived_metrics.json  {metrics: [{id, name, value, unit, formula, inputs}]}
    data/计算指标.json / 经营指标.json / 深度指标.json（嵌套数字，按路径命名）

一条事实的 `pct` 判定：单位是 % 且绝对值 ≤ 1.5 → 存的是比例（0.043 表示 4.3%）；
否则按百分数存（4.3 表示 4.3%）。两类都统一到 `as_ratio()`。
"""
from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
# 事实
# --------------------------------------------------------------------------- #
PERIOD_RE = re.compile(r"^(\d{4})(?:[QH](\d)(?:-(\d))?|[-年](\d{1,2})?)?$")


def period_key(p: str) -> Tuple[int, int, int, str]:
    """期排序键：年 > 季/半年 > 月；无法解析的排最后，保持稳定。"""
    s = str(p or "").strip()
    m = re.match(r"^(\d{4})Q(\d)(?:-(\d))?$", s)
    if m:
        # Q1-3 = 累计到三季度，按「期末季度」排序；H1 = 6 月
        end = int(m.group(3)) if m.group(3) else int(m.group(2))
        return (int(m.group(1)), end * 3, 0, s)
    m = re.match(r"^(\d{4})H(\d)$", s)
    if m:
        return (int(m.group(1)), int(m.group(2)) * 6, 0, s)
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), 1, s)
    m = re.match(r"^(\d{4})$", s)
    if m:
        return (int(m.group(1)), 12, 9, s)
    m = re.match(r"^(\d{4})", s)
    if m:
        return (int(m.group(1)), 0, 0, s)
    return (0, 0, 0, s)


@dataclass
class Fact:
    id: str
    indicator: str
    value: float
    unit: str = ""
    period: str = ""
    region: str = ""
    grade: str = ""
    source_org: str = ""
    source_title: str = ""
    url: str = ""
    quote: str = ""
    group: str = ""            # 来自哪个文件（obs_core / facts / derived）
    derived: bool = False
    formula: str = ""
    note: str = ""

    @property
    def pct(self) -> bool:
        return self.unit.strip() in ("%", "％", "个百分点", "pp")

    def as_ratio(self) -> float:
        """百分数/比例统一成「比例」：0.043 与 4.3 都返回 0.043。"""
        if not self.pct:
            return float(self.value)
        v = float(self.value)
        return v / 100.0 if abs(v) > 1.5 else v

    def as_pct(self) -> float:
        """统一成「百分点数值」：0.043 与 4.3 都返回 4.3。"""
        return self.as_ratio() * 100.0

    def __str__(self) -> str:
        return f"{self.indicator}={self.value:g}{self.unit}（{self.period}·{self.region}）"


# --------------------------------------------------------------------------- #
# 读
# --------------------------------------------------------------------------- #
def _f(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("，", "").rstrip("%").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm_pct_unit(unit: str) -> str:
    u = (unit or "").strip()
    return "%" if u in ("％", "百分比") else u


def _fact_from_obs(o: Dict[str, Any], group: str) -> Optional[Fact]:
    v = _f(o.get("value"))
    if v is None:
        return None
    return Fact(
        id=str(o.get("id") or ""), indicator=str(o.get("indicator") or o.get("name") or ""),
        value=v, unit=_norm_pct_unit(str(o.get("unit") or "")),
        period=str(o.get("period") or ""), region=str(o.get("region") or ""),
        grade=str(o.get("grade") or o.get("level") or ""),
        source_org=str(o.get("source_org") or o.get("org") or ""),
        source_title=str(o.get("source_title") or ""), url=str(o.get("url") or ""),
        quote=str(o.get("quote") or ""), group=group, note=str(o.get("note") or ""),
    )


def _walk_numbers(x: Any, prefix: str, depth: int = 0) -> Iterable[Tuple[str, float, str]]:
    """把嵌套 JSON 的数字按路径展开；跳过 quote/url 这类文本字段。"""
    if depth > 4:
        return
    if isinstance(x, dict):
        v = _f(x.get("value"))
        if v is not None and (x.get("name") or x.get("indicator")):
            yield (str(x.get("name") or x.get("indicator")), v, str(x.get("unit") or ""))
            return
        for k, val in x.items():
            if k in ("url", "quote", "source_title", "note", "source_date", "formula",
                     "inputs", "id", "grade", "level"):
                continue
            yield from _walk_numbers(val, f"{prefix}.{k}" if prefix else str(k), depth + 1)
    elif isinstance(x, list):
        for i, val in enumerate(x[:300]):
            yield from _walk_numbers(val, f"{prefix}[{i}]", depth + 1)
    else:
        v = _f(x)
        if v is not None and prefix:
            yield (prefix, v, "")


def _load_obs_file(path: str) -> List[Fact]:
    try:
        obj = json.loads(open(path, encoding="utf-8-sig").read())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    group = os.path.splitext(os.path.basename(path))[0]
    out: List[Fact] = []
    if isinstance(obj, list):
        for o in obj:
            if isinstance(o, dict):
                f = _fact_from_obs(o, group)
                if f and f.indicator:
                    out.append(f)
    elif isinstance(obj, dict):
        # {"sources": [...]} 之类的外壳，找第一个 list
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                for o in v:
                    f = _fact_from_obs(o, group)
                    if f and f.indicator:
                        out.append(f)
    return out


def _load_flat_facts(path: str) -> List[Fact]:
    """老项目 data/facts.json：扁平 {key: 数字} 或 [{metric,name,value,...}]。"""
    try:
        obj = json.loads(open(path, encoding="utf-8-sig").read())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    group = os.path.splitext(os.path.basename(path))[0]
    out: List[Fact] = []
    if isinstance(obj, list):
        for o in obj:
            if not isinstance(o, dict):
                continue
            v = _f(o.get("value"))
            if v is None:
                continue
            ind = str(o.get("name") or o.get("indicator") or o.get("metric") or "")
            if not ind:
                continue
            out.append(Fact(
                id=str(o.get("id") or ""), indicator=ind, value=v,
                unit=_norm_pct_unit(str(o.get("unit") or "")),
                period=str(o.get("period") or ""), region=str(o.get("region") or ""),
                grade=str(o.get("level") or o.get("grade") or ""),
                source_org=str(o.get("source_org") or ""),
                source_title=str(o.get("source_title") or ""),
                url=str(o.get("url") or ""), quote=str(o.get("quote") or ""),
                group=group))
    elif isinstance(obj, dict):
        for k, val in obj.items():
            if isinstance(val, (dict, list)):
                for name, v, unit in _walk_numbers(val, str(k)):
                    out.append(Fact(id="", indicator=name, value=v, unit=unit,
                                    group=group, derived=True))
            else:
                v = _f(val)
                if v is not None:
                    out.append(Fact(id="", indicator=str(k), value=v, group=group,
                                    derived=True))
    return out


def _load_derived(path: str) -> List[Fact]:
    try:
        obj = json.loads(open(path, encoding="utf-8-sig").read())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    group = os.path.splitext(os.path.basename(path))[0]
    out: List[Fact] = []
    metrics = obj.get("metrics") if isinstance(obj, dict) else obj
    if isinstance(metrics, list):
        for m in metrics:
            if not isinstance(m, dict):
                continue
            v = _f(m.get("value"))
            if v is None:
                continue
            out.append(Fact(
                id=str(m.get("id") or ""), indicator=str(m.get("name") or ""),
                value=v, unit=_norm_pct_unit(str(m.get("unit") or "")),
                period=str(m.get("period") or ""), region=str(m.get("region") or ""),
                grade=str(m.get("grade") or "derived"), group=group, derived=True,
                formula=str(m.get("formula") or ""), note=str(m.get("inputs") or "")))
    return out


def _dedupe(facts: Sequence[Fact]) -> List[Fact]:
    seen: set = set()
    out: List[Fact] = []
    for f in facts:
        key = (f.indicator, f.period, f.region, round(f.value, 6), f.unit)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def load(project_dir: str) -> "FactTable":
    root = os.path.abspath(project_dir)
    data = os.path.join(root, "data")
    base = data if os.path.isdir(data) else root
    files: List[str] = []
    for pat in ("obs*.json", "facts*.json", "derived*.json", "计算指标*.json",
                "经营指标*.json", "深度指标*.json", "单位经济*.json"):
        files += sorted(glob.glob(os.path.join(base, pat)))
    facts: List[Fact] = []
    for p in files:
        name = os.path.basename(p).lower()
        if name.startswith("obs"):
            facts += _load_obs_file(p)
        elif name.startswith("facts"):
            facts += _load_flat_facts(p)
        else:
            facts += _load_derived(p)
    return FactTable(facts=_dedupe(facts), root=root)


# --------------------------------------------------------------------------- #
# 查
# --------------------------------------------------------------------------- #
@dataclass
class FactTable:
    facts: List[Fact] = field(default_factory=list)
    root: str = ""

    # ---------------- 基本查找 ----------------
    def find(self, *needles: str, region: Optional[str] = None,
             exclude: Sequence[str] = (), exact: bool = False,
             pct: Optional[bool] = None) -> List[Fact]:
        """所有 needle 都要出现在 indicator 里（AND）；exclude 任一出现即排除。"""
        out: List[Fact] = []
        for f in self.facts:
            ind = f.indicator
            if exact:
                if ind not in needles:
                    continue
            elif not all(n in ind for n in needles):
                continue
            if exclude and any(x in ind for x in exclude):
                continue
            if region and region not in f.region:
                continue
            if pct is not None and f.pct != pct:
                continue
            out.append(f)
        return out

    def one(self, *needles: str, region: Optional[str] = None,
            exclude: Sequence[str] = (), exact: bool = False,
            prefer_period: Optional[str] = None) -> Optional[Fact]:
        cand = self.find(*needles, region=region, exclude=exclude, exact=exact)
        if not cand:
            return None
        if prefer_period:
            same = [f for f in cand if f.period == prefer_period]
            if same:
                cand = same
        # 同一指标多来源时：有 url 的优先 → A 级优先 → 期次最新
        with_url = [f for f in cand if f.url]
        if with_url:
            cand = with_url
        a = [f for f in cand if f.grade == "A"]
        if a:
            cand = a
        return max(cand, key=lambda f: period_key(f.period))

    def series(self, *needles: str, region: Optional[str] = None,
               exclude: Sequence[str] = (), pct: Optional[bool] = None) -> List[Fact]:
        cand = self.find(*needles, region=region, exclude=exclude, pct=pct)
        return sorted(cand, key=lambda f: period_key(f.period))

    def latest(self, *needles: str, region: Optional[str] = None,
               exclude: Sequence[str] = ()) -> Optional[Fact]:
        s = self.series(*needles, region=region, exclude=exclude)
        return s[-1] if s else None

    def value(self, *needles: str, region: Optional[str] = None,
              exclude: Sequence[str] = ()) -> Optional[float]:
        f = self.one(*needles, region=region, exclude=exclude)
        return f.value if f else None

    def pct(self, *needles: str, region: Optional[str] = None,
            exclude: Sequence[str] = ()) -> Optional[float]:
        f = self.one(*needles, region=region, exclude=exclude)
        return f.as_pct() if f else None

    # ---------------- 结构 ----------------
    def indicators(self) -> List[str]:
        seen, out = set(), []
        for f in self.facts:
            if f.indicator not in seen:
                seen.add(f.indicator)
                out.append(f.indicator)
        return out

    def regions(self) -> List[str]:
        seen, out = set(), []
        for f in self.facts:
            if f.region and f.region not in seen:
                seen.add(f.region)
                out.append(f.region)
        return out

    def by_prefix(self, prefix: str) -> List[Fact]:
        return [f for f in self.facts if f.indicator.startswith(prefix)]

    def has(self, *needles: str) -> bool:
        return bool(self.find(*needles))

    def counts(self) -> Dict[str, int]:
        return {"facts": len(self.facts),
                "indicators": len(self.indicators()),
                "regions": len(self.regions()),
                "with_url": sum(1 for f in self.facts if f.url),
                "grade_a": sum(1 for f in self.facts if f.grade == "A")}

    def assumptions(self) -> Dict[str, Dict[str, Any]]:
        """项目自带假设（data/assumptions.json）：{"key": {"value":..,"note":..}}。"""
        p = os.path.join(self.root, "data", "assumptions.json")
        if not os.path.exists(p):
            return {}
        try:
            obj = json.loads(open(p, encoding="utf-8-sig").read())
        except (json.JSONDecodeError, OSError):
            return {}
        return obj if isinstance(obj, dict) else {}
