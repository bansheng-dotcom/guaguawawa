# -*- coding: utf-8 -*-
"""core.data.data_standard —— 唯一的数据标准：四份契约 + 校验 + 适配器。

为什么单独一个模块（而不是继续用 `data_model.Row`）：
    采集、清洗、作图三段各定义自己的形状，最后只能靠人肉对齐。
    本模块把「一行数据」在四个阶段的样子固定下来：

        Record        L1 原始记录：抓到了什么，原样留档（不可变）
        Observation   L2 清洗后指标：全链路唯一可比较单元
        Dataset       L3 observations + manifest + dq + profile
        ChartSpec     L4 图表声明：类型 + 数据引用 + 编码 + 选项

`data_model.Row` 不删除也不改名（历史产物仍要能读），
通过 `observation_from_row` / `row_from_observation` 双向适配。

约定：校验函数返回**人类可读错误清单**，空列表 = 合法；
不抛异常、不写盘、不调模型（确定性）。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence

SCHEMA = "dsh.data_standard/v1"

#: 四份契约的必填键（文档与门禁共用这一份，避免三处各写一套）
REQUIRED: Dict[str, Sequence[str]] = {
    "record": ("record_id", "source_id", "values"),
    "observation": ("metric_id", "entity", "period", "value", "unit"),
    "dataset": ("name", "grain", "observations"),
    "chart": ("chart_type", "data_ref", "encode"),
}

CHART_TYPES = (
    "hbar", "vbar", "line", "area", "stacked", "pie", "donut", "dot",
    "scatter", "heatmap", "table", "text",
)


# --------------------------------------------------------------------------- #
# 1. Record —— 原始记录（不可变）
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Record:
    """一次抓取的原始行。values 原样保留，不做单位/名称归一。"""

    record_id: str
    source_id: str
    values: Dict[str, Any]
    url: str = ""
    fetched_at: str = ""
    batch: str = ""
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Record":
        return cls(record_id=str(d.get("record_id") or ""),
                   source_id=str(d.get("source_id") or ""),
                   values=dict(d.get("values") or {}),
                   url=str(d.get("url") or ""),
                   fetched_at=str(d.get("fetched_at") or ""),
                   batch=str(d.get("batch") or ""),
                   raw_text=str(d.get("raw_text") or ""))


def validate_record(r: Record | Dict[str, Any]) -> List[str]:
    d = r.to_dict() if isinstance(r, Record) else dict(r or {})
    errs: List[str] = []
    for k in REQUIRED["record"]:
        if not d.get(k):
            errs.append(f"record 缺 {k}")
    if d.get("values") is not None and not isinstance(d.get("values"), dict):
        errs.append("record.values 必须是对象")
    elif isinstance(d.get("values"), dict) and not d["values"]:
        errs.append("record.values 为空（抓到了什么必须留档）")
    return errs


# --------------------------------------------------------------------------- #
# 2. Observation —— 清洗后指标（唯一可比较单元）
# --------------------------------------------------------------------------- #
@dataclass
class Observation:
    metric_id: str
    entity: str
    period: str
    value: float
    unit: str
    value_base: float = 0.0
    unit_base: str = ""
    scale: float = 1.0
    scope: str = ""
    segment: str = ""
    source_id: str = ""
    grade: str = ""
    record_id: str = ""
    role: str = ""
    question_id: str = ""
    metric_name: str = ""
    method: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def base_value(self) -> float:
        """统一取数：有归一值用归一值，否则用原值。

        万元与元混排时，图表必须读 `value_base`（D-4）。
        """
        return float(self.value_base) if self.unit_base else float(self.value)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Observation":
        def _f(v: Any, default: float) -> float:
            try:
                return float(v)
            except (TypeError, ValueError):
                return default
        return cls(
            metric_id=str(d.get("metric_id") or ""),
            entity=str(d.get("entity") or ""),
            period=str(d.get("period") or ""),
            value=_f(d.get("value"), 0.0),
            unit=str(d.get("unit") or ""),
            value_base=_f(d.get("value_base"), 0.0),
            unit_base=str(d.get("unit_base") or ""),
            scale=_f(d.get("scale"), 1.0),
            scope=str(d.get("scope") or ""),
            segment=str(d.get("segment") or ""),
            source_id=str(d.get("source_id") or ""),
            grade=str(d.get("grade") or ""),
            record_id=str(d.get("record_id") or ""),
            role=str(d.get("role") or ""),
            question_id=str(d.get("question_id") or ""),
            metric_name=str(d.get("metric_name") or ""),
            method=str(d.get("method") or ""),
        )


def validate_observation(o: Observation | Dict[str, Any]) -> List[str]:
    d = o.to_dict() if isinstance(o, Observation) else dict(o or {})
    errs: List[str] = []
    for k in REQUIRED["observation"]:
        if d.get(k) in (None, ""):
            errs.append(f"observation 缺 {k}")
    try:
        float(d.get("value"))
    except (TypeError, ValueError):
        errs.append("observation.value 不是数值")
    if d.get("unit") == "":
        errs.append("observation.unit 为空（未识别单位必须显式写 unknown）")
    return errs


# --------------------------------------------------------------------------- #
# 3. Dataset —— observations + manifest + dq + profile
# --------------------------------------------------------------------------- #
@dataclass
class Dataset:
    name: str
    grain: List[str]
    observations: List[Observation] = field(default_factory=list)
    manifest: Dict[str, Any] = field(default_factory=dict)
    dq: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": self.schema, "name": self.name, "grain": list(self.grain),
                "observations": [o.to_dict() for o in self.observations],
                "manifest": self.manifest, "dq": self.dq, "profile": self.profile}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Dataset":
        return cls(name=str(d.get("name") or ""),
                   grain=[str(x) for x in (d.get("grain") or [])],
                   observations=[Observation.from_dict(x)
                                 for x in (d.get("observations") or [])],
                   manifest=dict(d.get("manifest") or {}),
                   dq=dict(d.get("dq") or {}),
                   profile=dict(d.get("profile") or {}),
                   schema=str(d.get("schema") or SCHEMA))

    def rows(self) -> List[Dict[str, Any]]:
        """供旧代码消费：转成 data_model.Row 字段形状。"""
        return [row_from_observation(o) for o in self.observations]


def validate_dataset(ds: Dataset | Dict[str, Any]) -> List[str]:
    d = ds.to_dict() if isinstance(ds, Dataset) else dict(ds or {})
    errs: List[str] = []
    for k in REQUIRED["dataset"]:
        if not d.get(k):
            errs.append(f"dataset 缺 {k}")
    grain = d.get("grain") or []
    if grain and not isinstance(grain, list):
        errs.append("dataset.grain 必须是列表")
    obs = d.get("observations") or []
    if not obs:
        errs.append("dataset.observations 为空")
    keys = set()
    for i, o in enumerate(obs[:50]):
        for e in validate_observation(o):
            errs.append(f"[obs {i}] {e}")
        k = "|".join(str((o or {}).get(x) or "") for x in
                     ("metric_id", "entity", "period", "scope", "segment"))
        if k in keys:
            errs.append(f"[obs {i}] 主键重复（同指标同主体同期次同口径）")
        keys.add(k)
    return errs


def profile_observations(obs: Sequence[Observation],
                         max_values: int = 12) -> Dict[str, Any]:
    """列画像：空值率 / 不同值数 / top1 占比 / 数值统计。

    P4 的图型选型（chart_fit）读这份画像，不再从数据反推图型。
    """
    cols = ("entity", "period", "metric_id", "unit", "scope", "segment")
    n = len(obs) or 1
    out: Dict[str, Any] = {"rows": len(obs), "columns": {}}
    for c in cols:
        vals = [str(getattr(o, c) or "").strip() for o in obs]
        cnt: Dict[str, int] = {}
        for v in vals:
            cnt[v] = cnt.get(v, 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])
        out["columns"][c] = {
            "empty_rate": round(sum(1 for v in vals if not v) / n, 4),
            "distinct": len(cnt),
            "top1_share": round((top[0][1] / n) if top else 0.0, 4),
            "values": [k for k, _ in top[:max_values] if k],
        }
    nums = [o.value for o in obs if isinstance(o.value, (int, float))]
    if nums:
        s = sorted(nums)
        out["value"] = {"min": s[0], "max": s[-1],
                        "median": s[len(s) // 2],
                        "zero_rate": round(sum(1 for x in nums if x == 0) / len(nums), 4),
                        "neg_rate": round(sum(1 for x in nums if x < 0) / len(nums), 4)}
    out["time_like"] = bool(out["columns"]["period"]["distinct"] >= 2)
    out["categorical"] = [c for c in ("entity", "metric_id", "scope")
                          if out["columns"][c]["distinct"] >= 2]
    return out


# --------------------------------------------------------------------------- #
# 4. ChartSpec —— 图表声明（数据引用，不内嵌数字）
# --------------------------------------------------------------------------- #
@dataclass
class ChartSpec:
    chart_type: str
    data_ref: Dict[str, Any]
    encode: Dict[str, Any]
    option: Dict[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA

    def to_dict(self) -> Dict[str, Any]:
        return {"schema": self.schema, "chart_type": self.chart_type,
                "data_ref": self.data_ref, "encode": self.encode,
                "option": self.option}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ChartSpec":
        return cls(chart_type=str(d.get("chart_type") or ""),
                   data_ref=dict(d.get("data_ref") or {}),
                   encode=dict(d.get("encode") or {}),
                   option=dict(d.get("option") or {}),
                   schema=str(d.get("schema") or SCHEMA))


def validate_chart_spec(cs: ChartSpec | Dict[str, Any]) -> List[str]:
    d = cs.to_dict() if isinstance(cs, ChartSpec) else dict(cs or {})
    errs: List[str] = []
    for k in REQUIRED["chart"]:
        if not d.get(k):
            errs.append(f"chart 缺 {k}")
    t = str(d.get("chart_type") or "")
    if t and t not in CHART_TYPES:
        errs.append(f"未知图型 {t}（在 CHART_TYPES 里登记后才允许）")
    ref = d.get("data_ref") or {}
    if ref and not (ref.get("dataset") or ref.get("metric")):
        errs.append("chart.data_ref 至少要有 dataset 或 metric")
    enc = d.get("encode") or {}
    if enc and not any(k in enc for k in ("x", "value", "label", "series")):
        errs.append("chart.encode 至少要有 x/value/label/series 之一")
    return errs


# --------------------------------------------------------------------------- #
# 5. 双向适配器：Observation ↔ data_model.Row
# --------------------------------------------------------------------------- #
def observation_from_row(row: Any) -> Observation:
    """旧 Row（dataclass 或 dict）→ Observation。"""
    d = asdict(row) if hasattr(row, "__dataclass_fields__") else dict(row or {})
    return Observation.from_dict(d)


def row_from_observation(o: Observation, row_id: str = "",
                         number_id: str = "") -> Dict[str, Any]:
    """Observation → data_model.ROW_FIELDS 形状的 dict（可直接进 raw.csv）。"""
    d = o.to_dict()
    d["row_id"] = row_id
    d["number_id"] = number_id or o.record_id or o.metric_id
    d.setdefault("entity_type", "")
    return d


def dataset_from_raw(raw: Dict[str, Any], name: str = "",
                     grain: Optional[List[str]] = None) -> Dataset:
    """data_model.build_raw 的输出 → Dataset（observations 直接来自 rows）。"""
    rows = raw.get("rows") or []
    obs = [observation_from_row(r) for r in rows]
    dq = raw.get("coverage") or {}
    return Dataset(name=name or "raw", grain=list(grain or ["entity", "period"]),
                   observations=obs,
                   manifest={"sources": raw.get("sources") or [],
                             "conflicts": raw.get("conflicts") or [],
                             "unmapped": raw.get("unmapped") or []},
                   dq=dq,
                   profile=profile_observations(obs))


def dataset_from_records(records: Iterable[Record], name: str = "",
                         metric_id: str = "value", entity_key: str = "entity",
                         period_key: str = "period", unit: str = "unknown") -> Dataset:
    """Record → Dataset 的最小实现：不猜口径，字段名与单位由调用方给。"""
    obs: List[Observation] = []
    for r in records:
        vals = r.values or {}
        if not str(vals.get(entity_key) or "").strip():
            continue
        if not str(vals.get(period_key) or "").strip():
            continue
        try:
            v = float(vals.get(metric_id))
        except (TypeError, ValueError):
            continue
        obs.append(Observation(
            metric_id=str(metric_id), entity=str(vals.get(entity_key) or ""),
            period=str(vals.get(period_key) or ""), value=v, unit=unit,
            source_id=r.source_id, record_id=r.record_id))
    return Dataset(name=name or "records", grain=[entity_key, period_key],
                   observations=obs, manifest={"records": len(obs)},
                   dq={"rows_in": len(obs)}, profile=profile_observations(obs))
