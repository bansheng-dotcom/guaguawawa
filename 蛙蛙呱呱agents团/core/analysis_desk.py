# -*- coding: utf-8 -*-
"""core/analysis_desk —— 报告产线的「数据台」：把项目目录归一成可算的观测。

为什么需要这一层（对比 v2/v3 的断点）：

- `evidence_pack` 只把 CSV 压成 last/max/min/mean 四条，**丢掉了行内结构**
  （哪个品类、哪一周、哪个市场），所以只能写"均值 7.45%"，写不出
  "白条鸡加价 40.8%、牛肉只有 3.6%"这种判断；
- 旧 `report_produce`（已删除）把「哪张表、哪一列」写死在 profile 里，换个项目就跑不动，
  这是"模板化"的根源；
- 旧 `deep_analysis` 会算趋势/贡献，但只看一列数值，不认价格、单位、市场。

本模块只做三件事，不做分析、不写报告：

1. `scan(dir)`  读目录里的 CSV / JSON，识别时间轴、实体轴、数值列、单位，
                 把每一行展开成一条**长表观测**（entity / sub / time / metric / value）；
2. `Desk`       维护证据索引：每个进入报告的数字都有 id、单位、期、来源文件；
                 派生量（净毛利、价差、保本线）用公式挂到原始 id 上，可复算；
3. `profile()`  给纲领层用的数据画像：有没有零售价、批发价、产地价、多市场。

单位统一走 `per_jin()`：元/公斤 ÷2、元/500克 原值、元/斤 原值。
价格类数据只有落到同一口径才能比，这一步不做，后面全是错的。
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core import evidence_pack

SKIP_DIRS = {"raw", "screens", "out", "node_modules", ".git", "_archive",
             "__pycache__", ".chrome", "gates"}
MAX_ROWS = 20000

TIME_HINTS = ("date", "日期", "周期", "week", "期间", "time", "月份")
ENTITY_HINTS = ("品类", "品种", "item", "地区", "区域", "产地", "市场", "market",
                "品类名称", "商品", "name")
UNIT_HINTS = ("单位", "unit")

# 价格来源（决定能不能做价差/传导）：零售 / 批发 / 产地出场
CHANNEL_HINTS = (
    ("retail", ("零售", "采价", "零售价", "门店价", "商超")),
    ("wholesale", ("批发", "市场报价", "东瓦窑", "友谊")),
    ("origin", ("产地", "出场", "装车", "育肥", "活牛", "羔羊", "绒山羊", "肥牛", "下架鸡")),
    ("futures", ("期货", "symbol", "close")),
)


def _to_float(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("，", "")
    if not s:
        return None
    s = s.rstrip("%").strip()
    try:
        return float(s)
    except ValueError:
        return None


_PERIOD_PATTERNS = (
    r"^\d{4}-\d{2}-\d{2}$", r"^\d{4}/\d{2}/\d{2}$", r"^\d{4}-\d{2}$",
    r"^\d{1,2}月\d{1,2}日$", r"^\d{1,2}月值$", r"^\d{1,2}月$",
    r"^\d{4}年$", r"^\d{8}$",
)
_TIME_CELL_PATTERNS = _PERIOD_PATTERNS + (
    r"^\d{8}-\d{8}$", r"^\d{2}-\d{2}~\d{2}-\d{2}$",
    r"^\d{4}-\d{2}-\d{2}~\d{2}-\d{2}$",
)
_PCT_HINTS = ("环比", "同比", "涨幅", "占比", "pct", "mom", "yoy", "rate")


def _is_period_name(x: str) -> bool:
    return any(re.match(p, str(x).strip()) for p in _PERIOD_PATTERNS)


def _is_time_cell(x: str) -> bool:
    return any(re.match(p, str(x).strip()) for p in _TIME_CELL_PATTERNS)


def _norm_time(x: str) -> str:
    s = str(x).strip()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}~{m.group(5)}-{m.group(6)}"
    return s


def _unit_scale(unit: str) -> Tuple[float, str]:
    u = (unit or "").strip()
    if "公斤" in u or "kg" in u.lower() or "千克" in u:
        return 0.5, "元/斤"
    if "500克" in u or "500g" in u.lower() or "斤" in u:
        return 1.0, "元/斤"
    return 1.0, u


def _channel(*texts: str) -> str:
    blob = " ".join(t for t in texts if t)
    for name, keys in CHANNEL_HINTS:
        if any(k in blob for k in keys):
            return name
    return ""


@dataclass
class Obs:
    entity: str          # 品类 / 地区 / 市场 / 产地（横向主体）
    sub: str             # 第二个主体维度（如 市场×品类 里的 品类）
    time: str
    metric: str          # 列名，或 "价格"
    value: float
    unit: str
    file: str
    row: int
    channel: str = ""    # retail / wholesale / origin / futures / ""
    pct: bool = False

    def per_jin(self) -> Tuple[float, str]:
        k, u = _unit_scale(self.unit)
        return self.value * k, u

    @property
    def label(self) -> str:
        return f"{self.sub or self.entity}"


@dataclass
class Dataset:
    file: str
    kind: str                      # wide_series / long_panel / period_table / metric_json
    rows: int
    columns: List[str]
    time_col: str = ""
    entity_col: str = ""
    sub_col: str = ""
    value_cols: List[str] = field(default_factory=list)
    unit: str = ""
    channel: str = ""
    obs: List[Obs] = field(default_factory=list)


@dataclass
class Table:
    """原始表：行级字典 + 列名。给「非价格类」方法用（订单/评价/工单/招聘…）。"""
    name: str
    file: str
    columns: List[str]
    rows: List[Dict[str, str]]
    n: int
    numeric: List[str] = field(default_factory=list)
    truncated: bool = False

    def col(self, *keys: str) -> Optional[str]:
        for k in keys:
            kk = k.lower()
            for c in self.columns:
                if kk in c.lower():
                    return c
        return None

    def num(self, col: str) -> List[float]:
        out = []
        for r in self.rows:
            try:
                out.append(float(str(r.get(col, "")).replace(",", "")))
            except (TypeError, ValueError):
                continue
        return out

    def vals(self, col: str) -> List[str]:
        return [str(r.get(col, "")).strip() for r in self.rows]


class Desk:
    """一个项目的全部可算素材 + 证据索引。"""

    def __init__(self, project_dir: str):
        self.root = Path(project_dir).resolve()
        self.project = self.root.name
        self.datasets: List[Dataset] = []
        self.obs: List[Obs] = []
        self.files: List[str] = []
        self.tables: Dict[str, Table] = {}
        self.facts: List[Dict[str, Any]] = []
        self.assumptions: List[Dict[str, Any]] = []
        self.pack: Dict[str, Any] = evidence_pack.build(str(self.root))
        self.derived: List[Dict[str, Any]] = []
        # v7：带来源的事实表（obs_*.json / facts.json / derived_metrics.json）
        try:
            from core import fact_table
            self.ft = fact_table.load(str(self.root))
        except Exception:  # noqa: BLE001  事实表加载失败不阻断价格线
            self.ft = None
        self._seq = 0
        self.notes: List[str] = []

    # ---------------- 表视图 ----------------
    def find_table(self, *keys: str) -> Optional[Table]:
        """找一张同时含这些列关键字的表；keys 越多越特异。"""
        for t in self.tables.values():
            if all(t.col(k) for k in keys):
                return t
        return None

    def tables_with(self, *keys: str) -> List[Table]:
        return [t for t in self.tables.values() if all(t.col(k) for k in keys)]

    # ---------------- 证据索引 ----------------
    def add_number(self, name: str, value: float, unit: str = "", period: str = "",
                   source: str = "", formula: str = "", inputs: str = "") -> str:
        self._seq += 1
        nid = f"E{self._seq:03d}"
        self.pack["numbers"].append({
            "id": nid, "name": name, "value": float(value), "unit": unit,
            "period": period, "region": "", "source_file": source,
            "org": "", "formula": formula, "inputs": inputs, "kind": "analysis",
        })
        return nid

    def add_derived(self, did: str, formula: str, value: float, note: str,
                    unit: str = "") -> str:
        """派生量：formula 只能引用包内 id 与四则运算，值必须与实算一致。"""
        self.derived.append({"id": did, "formula": formula,
                             "value": round(float(value), 6),
                             "note": note, "unit": unit})
        return did

    def counts(self) -> Dict[str, int]:
        return {"files": len(self.pack.get("sources") or []),
                "numbers": len(self.pack.get("numbers") or [])}

    # ---------------- 视图 ----------------
    def series(self, metric: str, entity: str = "", sub: str = "",
               channel: str = "") -> List[Obs]:
        rows = [o for o in self.obs
                if metric in o.metric and (not entity or entity in o.entity)
                and (not sub or sub in o.sub)
                and (not channel or channel == o.channel)]
        return sorted(rows, key=lambda o: o.time)

    def latest(self, metric: str, entity: str = "", sub: str = "",
               channel: str = "") -> Optional[Obs]:
        s = self.series(metric, entity, sub, channel)
        return s[-1] if s else None

    def price_obs(self, channel: str = "") -> List[Obs]:
        return [o for o in self.obs if o.channel and (not channel or o.channel == channel)]

    def entities(self, channel: str = "") -> List[str]:
        seen: List[str] = []
        for o in self.price_obs(channel):
            if o.entity and o.entity not in seen:
                seen.append(o.entity)
        return seen

    def subs(self, channel: str = "") -> List[str]:
        seen: List[str] = []
        for o in self.price_obs(channel):
            if o.sub and o.sub not in seen:
                seen.append(o.sub)
        return seen


def _classify(cols: List[str], rows: List[List[str]]) -> Dict[str, Any]:
    info = {"time": "", "entity": "", "sub": "", "values": [], "unit_col": ""}
    for j, c in enumerate(cols):
        cl = c.strip().lower()
        values = [r[j] if j < len(r) else "" for r in rows[:80]]
        vals = [v for v in values if str(v).strip()]
        nums = [v for v in vals if _to_float(v) is not None]
        times = [v for v in vals if _is_time_cell(v)]
        if any(k in cl for k in UNIT_HINTS):
            info["unit_col"] = c
            continue
        if not info["time"] and (any(k in cl for k in TIME_HINTS)
                                 or (times and len(times) >= len(vals) * 0.6)):
            info["time"] = c
            continue
        if len(nums) >= max(2, len(vals) * 0.6):
            info["values"].append(c)
            continue
        if any(k in cl for k in ENTITY_HINTS) or (vals and not nums):
            if not info["entity"]:
                info["entity"] = c
            elif not info["sub"]:
                info["sub"] = c
    return info


def _read_csv(path: Path) -> Tuple[List[str], List[List[str]]]:
    """读 CSV：UTF-8(BOM) 优先，失败回退 GBK；按行读到上限即停，不整表载入。"""
    rows: List[List[str]] = []
    last_err: Optional[Exception] = None
    for enc in ("utf-8-sig", "gbk"):
        try:
            rows = []
            with open(path, encoding=enc, newline="") as f:
                for i, r in enumerate(csv.reader(f)):
                    rows.append(r)
                    if i + 1 >= MAX_ROWS:
                        break
            last_err = None
            break
        except UnicodeDecodeError as exc:
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    if not rows:
        return [], []
    return ([c.strip() for c in rows[0]],
            [r for r in rows[1:] if any(str(x).strip() for x in r)])


def _load_csv(path: Path, rel: str) -> Optional[Dataset]:
    cols, rows = _read_csv(path)
    if not cols or not rows:
        return None
    ci = {c: j for j, c in enumerate(cols)}
    period_cols = [c for c in cols if _is_period_name(c)]
    rest = [c for c in cols if c not in period_cols]
    info = _classify(rest, [[r[ci[c]] if ci[c] < len(r) else "" for c in rest]
                            for r in rows])
    # 把 "_classify 只看得见 rest" 的列名还原成真实列
    unit = ""
    if info["unit_col"]:
        j = ci[info["unit_col"]]
        unit = next((str(r[j]).strip() for r in rows if j < len(r) and str(r[j]).strip()), "")
    ent_col, sub_col, time_col = info["entity"], info["sub"], info["time"]
    value_cols = info["values"]
    if not value_cols and not period_cols:
        return None
    channel = _channel(rel, *(cols or []))
    obs: List[Obs] = []

    def emit(r: List[str], i: int, col: str, t: str) -> None:
        j = ci[col]
        if j >= len(r):
            return
        raw = r[j]
        v = _to_float(raw)
        if v is None:
            return
        ent = str(r[ci[ent_col]]).strip() if ent_col and ci[ent_col] < len(r) else ""
        sub = str(r[ci[sub_col]]).strip() if sub_col and ci[sub_col] < len(r) else ""
        if not ent:
            # 只有一列「价格」时，商品名在文件名里（如 r06_周度_鸡蛋批发.csv）
            ent = Path(rel).stem if len(period_cols + value_cols) == 1 else col
        pct = ("%" in col) or any(h in col.lower() for h in _PCT_HINTS) \
            or str(raw).strip().endswith("%")
        obs.append(Obs(entity=ent, sub=sub, time=_norm_time(t) if t else "",
                       metric=col, value=v, unit=unit, file=rel, row=i,
                       channel=_channel(col, ent, sub, rel) or channel,
                       pct=pct))

    for i, r in enumerate(rows):
        t = str(r[ci[time_col]]).strip() if time_col and ci[time_col] < len(r) else ""
        for pc in period_cols:
            emit(r, i, pc, pc)
        for vc in value_cols:
            emit(r, i, vc, t)
    if not obs:
        return None
    kind = ("period_table" if period_cols and not value_cols else
            "long_panel" if time_col and (ent_col or sub_col) else "wide_series")
    return Dataset(file=rel, kind=kind, rows=len(rows), columns=cols,
                   time_col=time_col, entity_col=ent_col, sub_col=sub_col,
                   value_cols=period_cols + value_cols, unit=unit,
                   channel=channel, obs=obs)


def _load_json(path: Path, rel: str) -> Optional[Dataset]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    obs: List[Obs] = []

    def walk(x: Any, p: str, depth: int = 0) -> None:
        if depth > 3:
            return
        if isinstance(x, dict):
            v = _to_float(x.get("value"))
            if v is not None:
                name = str(x.get("name") or x.get("indicator") or x.get("metric") or p)
                obs.append(Obs(entity=name, sub="", time=str(x.get("period") or ""),
                               metric=name, value=v, unit=str(x.get("unit") or ""),
                               file=rel, row=len(obs)))
                return
            for k, val in x.items():
                if k in ("url", "quote", "source_title", "note", "source_date"):
                    continue
                walk(val, f"{p}.{k}" if p else str(k), depth + 1)
        elif isinstance(x, list):
            for i, val in enumerate(x[:200]):
                walk(val, f"{p}[{i}]", depth + 1)
        else:
            v = _to_float(x)
            if v is not None and p:
                obs.append(Obs(entity=p, sub="", time="", metric=p, value=v,
                               unit="", file=rel, row=len(obs)))

    walk(obj, "")
    if not obs:
        return None
    return Dataset(file=rel, kind="metric_json", rows=len(obs), columns=[], obs=obs)


def _load_table(path: Path, rel: str) -> Optional[Table]:
    """原始表：保留行与列，供非价格类方法使用（订单/评价/工单/招聘/故障）。"""
    cols, rows = _read_csv(path)
    if not cols or not rows:
        return None
    truncated = len(rows) >= MAX_ROWS
    header = [c.strip().strip('"') for c in cols]
    dicts = []
    for r in rows[:MAX_ROWS]:
        d = {}
        for i, c in enumerate(header):
            d[c] = str(r[i]).strip().strip('"') if i < len(r) else ""
        dicts.append(d)
    numeric = []
    for c in header:
        vals = [v for v in (d.get(c, "") for d in dicts[:200]) if v != ""]
        if vals and sum(1 for v in vals if _to_float(v) is not None) >= len(vals) * 0.6:
            numeric.append(c)
    return Table(name=path.stem, file=rel, columns=header, rows=dicts,
                 n=len(dicts), numeric=numeric, truncated=truncated)


def scan(project_dir: str) -> Desk:
    desk = Desk(project_dir)
    for p in sorted(desk.root.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(desk.root)).replace("\\", "/")
        if any(part in SKIP_DIRS or part.startswith(".") or part.startswith("out_")
               for part in Path(rel).parts):
            continue
        if p.suffix.lower() == ".csv":
            d = _load_csv(p, rel)
            t = _load_table(p, rel)
            if t:
                desk.tables[t.name] = t
        elif p.suffix.lower() == ".json" and "evidence_pack" not in p.name:
            d = _load_json(p, rel)
        else:
            continue
        if d:
            desk.datasets.append(d)
            desk.obs.extend(d.obs)
    desk.files = [d.file for d in desk.datasets]
    # 研究类项目：带来源的事实表（data/facts.json）
    # 两种合法外层：{"facts": [...], "assumptions": [...]} 或直接是列表（fact_table 两者都吃，
    # 这里曾经只认 dict，导致「列表形态的 facts.json」在扫描阶段就崩，报告出不来）。
    facts_path = desk.root / "data" / "facts.json"
    if facts_path.exists():
        try:
            obj = json.loads(facts_path.read_text(encoding="utf-8-sig"))
            if isinstance(obj, list):
                desk.facts = [x for x in obj if isinstance(x, dict)]
            elif isinstance(obj, dict):
                desk.facts = list(obj.get("facts") or [])
                desk.assumptions = list(obj.get("assumptions") or [])
        except (json.JSONDecodeError, OSError):
            pass
    return desk


def profile(desk: Desk) -> Dict[str, Any]:
    """数据画像：纲领层用它决定「能问什么问题」。"""
    kinds: Dict[str, int] = {}
    for d in desk.datasets:
        kinds[d.kind] = kinds.get(d.kind, 0) + 1
    chans = {c: len(desk.price_obs(c)) for c in ("retail", "wholesale", "origin", "futures")}
    ft = getattr(desk, "ft", None)
    return {
        "project": desk.project,
        "datasets": len(desk.datasets),
        "observations": len(desk.obs),
        "facts": len(ft.facts) if ft is not None else 0,
        "kinds": kinds,
        "channels": chans,
        "retail_entities": desk.entities("retail")[:20],
        "wholesale_entities": desk.entities("wholesale")[:20],
        "origin_entities": desk.entities("origin")[:20],
        "files": desk.files,
    }
