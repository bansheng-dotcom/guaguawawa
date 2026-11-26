# -*- coding: utf-8 -*-
"""core.data.data_model —— 专家团的「数据层」：行、度量、归一、冲突、覆盖。

为什么要有这个模块：
    现在角色的产物是 claims（论证），数字是自由文本
    （476 个数字、48 种单位、19 组重名），系统里**没有任何地方定义"一行数据"**。
    没有行，就没有 raw 表；没有 raw 表，图和表只能从段落里猜。

本模块只做四件事（确定性、不调模型）：
    1. 行契约 Row：metric_id / entity / period / value / unit / scope / source
    2. 度量注册 MetricRegistry：自由文本名 → 稳定 metric_id（去括号/城市/标点）
    3. 单位归一：亿元/万元/万只/元/只/年 → base_unit + scale
    4. 冲突与覆盖：同键不同值进 conflicts；缺 entity/period/source 进 coverage

产物：raw.json / raw.csv / raw.xlsx（六张表）+ metrics.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 1. 行契约
# --------------------------------------------------------------------------- #
ROW_FIELDS = ("row_id", "role", "question_id", "metric_id", "metric_name",
              "entity_type", "entity", "value", "unit", "period", "scope",
              "value_base", "unit_base", "scale", "source_id", "grade", "method")


@dataclass
class Row:
    row_id: str
    number_id: str
    role: str
    question_id: str
    metric_id: str
    metric_name: str
    entity_type: str
    entity: str
    value: float
    unit: str
    period: str
    scope: str = ""
    segment: str = ""
    value_base: float = 0.0
    unit_base: str = ""
    scale: float = 1.0
    source_id: str = ""
    grade: str = ""
    method: str = ""

    def ok(self) -> bool:
        return bool(self.metric_id and str(self.entity).strip()
                    and self.period and self.source_id)


# --------------------------------------------------------------------------- #
# 2. 单位归一
# --------------------------------------------------------------------------- #
UNIT_MAP: Dict[str, Tuple[str, float]] = {
    "亿元": ("元", 1e8), "万元": ("元", 1e4), "元": ("元", 1.0),
    "万元/月": ("元/月", 1e4), "元/月": ("元/月", 1.0),
    "万只": ("只", 1e4), "只": ("只", 1.0), "万件": ("件", 1e4), "件": ("件", 1.0),
    "万家": ("家", 1e4), "家": ("家", 1.0), "万人": ("人", 1e4), "人": ("人", 1.0),
    "元/只/年": ("元/只/年", 1.0), "元/只·年": ("元/只/年", 1.0),
    "天": ("天", 1.0), "周": ("周", 1.0), "个月": ("个月", 1.0), "岁": ("岁", 1.0),
    "㎡": ("㎡", 1.0), "公里": ("公里", 1.0), "%": ("%", 1.0), "": ("", 1.0),
}


def normalize_unit(unit: str) -> Tuple[str, float, bool]:
    """自由单位 → (base_unit, scale, verified)。

    `verified=False` 表示这个单位没有在 UNIT_MAP 里登记，scale 只能取 1.0；
    调用方必须把它显式记进 coverage（`unit_unverified`），
    不许当成「已经归一」继续往图上送（D-4 / P1-6）。
    """
    u = str(unit or "").strip().replace(" ", "")
    if u in UNIT_MAP:
        base, scale = UNIT_MAP[u]
        return (base, scale, True)
    # 亿元/年、元/㎡ 之类：拆分子单位
    for base, (b, s) in UNIT_MAP.items():
        if u.startswith(base + "/"):
            return (b + u[len(base):], s, True)
    return (u, 1.0, False)


# --------------------------------------------------------------------------- #
# 3. 度量注册
# --------------------------------------------------------------------------- #
def _load_geo_tokens() -> Tuple[str, ...]:
    """具体地名从 configs/geo_tokens.yaml 读，通用模块不内置任何城市名。

    2026-11-22 清理：原 CITY_TOKENS 写死了若干历史项目的区县与地市，
    是历史项目地名沉进通用模块的残留。现在只留中性值，
    具体地名交给项目 config 或 semantic_layer 声明。
    """
    p = Path(__file__).resolve().parent.parent.parent / "configs" / "geo_tokens.yaml"
    try:
        import yaml  # noqa: PLC0415
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        toks = [str(x) for x in (d.get("tokens") or []) if str(x).strip()]
        if toks:
            return tuple(toks)
    except Exception:  # noqa: BLE001
        pass
    return ("全国", "中国")


CITY_TOKENS = _load_geo_tokens()
ENTITY_TYPES = (("city", CITY_TOKENS),)


def parse_name(name: str) -> Dict[str, str]:
    """自由文本指标名 → metric_name + qualifier + city。"""
    raw = str(name or "").strip()
    qual = ""
    m = re.search(r"[（(]([^）)]*)[）)]", raw)
    if m:
        qual = m.group(1).strip()
        raw = raw[:m.start()] + raw[m.end():]
    city = ""
    for tok in CITY_TOKENS:
        if tok in raw:
            city = tok
            break
    label = raw
    if city:
        label = label.replace(city, "")
    label = re.sub(r"[\s，,。；;：:、\-—]+", "", label)
    label = re.sub(r"(同比|环比|增速|增长率)$", r"\1", label)
    return {"metric_name": label or raw or "未命名指标",
            "qualifier": qual, "city": city}


class MetricRegistry:
    """自由文本名 → 稳定 metric_id；同名不同义必须显式拆开（靠 qualifier）。"""

    def __init__(self) -> None:
        self._by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def key(self, metric_name: str, qualifier: str) -> Tuple[str, str]:
        return (metric_name, qualifier)

    def register(self, metric_name: str, qualifier: str = "",
                 unit: str = "", owner: str = "") -> Dict[str, Any]:
        k = self.key(metric_name, qualifier)
        if k not in self._by_key:
            h = hashlib.sha1(f"{metric_name}|{qualifier}".encode("utf-8")).hexdigest()[:8]
            base, scale, verified = normalize_unit(unit)
            self._by_key[k] = {
                "metric_id": f"m_{h}", "metric_name": metric_name,
                "qualifier": qualifier, "unit": unit, "unit_base": base,
                "unit_verified": verified,
                "additivity": ("ratio" if base == "%" else "flow"),
                "owner": owner, "rows": 0,
            }
        self._by_key[k]["rows"] += 1
        return self._by_key[k]

    def as_list(self) -> List[Dict[str, Any]]:
        return sorted(self._by_key.values(), key=lambda x: -x["rows"])


# --------------------------------------------------------------------------- #
# 4. 构建 raw
# --------------------------------------------------------------------------- #
GRADE_RANK = {"A": 4, "B": 3, "C": 2, "D": 1, "": 0}


def _arbitrate(prev: "Row", new: "Row") -> Tuple[str, "Row"]:
    """冲突裁决（P3-2）：按来源等级取值；同级保留第一条并标 needs_human。"""
    a, b = GRADE_RANK.get(str(prev.grade).upper(), 0), \
        GRADE_RANK.get(str(new.grade).upper(), 0)
    if b > a:
        return "kept_high_grade", new
    if a > b:
        return "kept_high_grade", prev
    return "needs_human", prev


def _period_ok(p: str) -> bool:
    t = str(p or "").strip()
    return bool(re.match(r"^(19|20)\d{2}(-\d{2})?$", t)) or "-" in t or t.endswith("年")


def build_raw(numbers: Iterable[Dict[str, Any]],
              sources: Optional[Iterable[Dict[str, Any]]] = None,
              role_of: Optional[Dict[str, str]] = None,
              question_of: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    reg = MetricRegistry()
    src_grade = {str(s.get("file") or ""): str(s.get("grade") or "")
                 for s in (sources or [])}
    rows: List[Row] = []
    unmapped: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    unit_unverified = 0
    seen: Dict[Tuple[str, str, str, str], Row] = {}
    for i, n in enumerate(numbers or [], 1):
        try:
            value = float(n.get("value"))
        except (TypeError, ValueError):
            unmapped.append({"id": n.get("id"), "why": "非数值", "name": n.get("name")})
            continue
        parsed = parse_name(str(n.get("name") or ""))
        unit = str(n.get("unit") or "")
        sid = str(n.get("id") or "")
        role = ((role_of or {}).get(sid)
                or (sid.split(":")[0] if ":" in sid else "")
                or str(n.get("role") or ""))
        metric = reg.register(parsed["metric_name"], parsed["qualifier"], unit, role)
        base, scale, verified = normalize_unit(unit)
        if not verified:
            unit_unverified += 1
        src = str(n.get("source_file") or "")
        period = str(n.get("period") or "").strip()
        row = Row(
            row_id=f"R{i:04d}", number_id=sid, role=role,
            question_id=(question_of or {}).get(str(n.get("id")), ""),
            metric_id=metric["metric_id"], metric_name=metric["metric_name"],
            entity_type="city" if (n.get("entity") or parsed["city"]) else "",
            entity=str(n.get("entity") or "") or parsed["city"] or parsed["qualifier"] or "全市场",
            value=value, unit=unit, period=period,
            scope=parsed["qualifier"], segment=str(n.get("segment") or parsed["qualifier"] or ""),
            value_base=value * scale, unit_base=base,
            scale=scale, source_id=src, grade=src_grade.get(src, ""),
        )
        key = (row.metric_id, row.entity, row.period, row.scope, row.segment)
        if key in seen:
            prev = seen[key]
            if abs(prev.value - row.value) > 1e-9:
                verdict, kept = _arbitrate(prev, row)
                conflicts.append({
                    "key": "|".join(key), "metric_id": row.metric_id,
                    "entity": row.entity, "period": row.period,
                    "values": [prev.value, row.value],
                    "sources": [prev.source_id, row.source_id],
                    "grades": [prev.grade, row.grade],
                    "verdict": verdict, "kept_value": kept.value,
                    "rule": "同键不同值：高等级优先；同级保留第一条并标人工裁决",
                })
                if kept is row:                 # 高等级替换低等级
                    rows[rows.index(prev)] = row
                    seen[key] = row
            continue
        seen[key] = row
        rows.append(row)

    coverage = {
        "rows": len(rows),
        "metrics": len(reg.as_list()),
        "with_entity": sum(1 for r in rows if r.entity and r.entity != "全市场"),
        "with_period": sum(1 for r in rows if _period_ok(r.period)),
        "with_source": sum(1 for r in rows if r.source_id),
        "conflicts": len(conflicts),
        "conflicts_needs_human": sum(1 for c in conflicts
                                     if c.get("verdict") == "needs_human"),
        "unit_unverified": unit_unverified,
        "unmapped": len(unmapped),
    }
    return {"rows": [asdict(r) for r in rows],
            "metrics": reg.as_list(), "conflicts": conflicts,
            "unmapped": unmapped, "coverage": coverage}


# --------------------------------------------------------------------------- #
# 5. 导出 raw.xlsx / raw.csv
# --------------------------------------------------------------------------- #
RAW_SHEETS = ("00 说明", "01 原始数据", "02 度量注册", "03 冲突", "04 覆盖", "05 来源")


def _rows_as_lists(rows: List[Dict[str, Any]]) -> Tuple[List[str], List[List[Any]]]:
    head = list(ROW_FIELDS)
    return head, [[r.get(k) for k in head] for r in rows]


def export(raw: Dict[str, Any], out_dir: Path,
           sources: Optional[Iterable[Dict[str, Any]]] = None,
           title: str = "") -> Dict[str, str]:
    from core.base import paths
    out_dir = paths.write_artifact(out_dir)      # 守卫：产物只能落项目，不落团内
    (out_dir / "raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "metrics.json").write_text(
        json.dumps(raw.get("metrics") or [], ensure_ascii=False, indent=1), encoding="utf-8")
    conflicts = raw.get("conflicts") or []
    csum = {"total": len(conflicts),
            "resolved": sum(1 for c in conflicts
                            if c.get("verdict") == "kept_high_grade"),
            "needs_human": sum(1 for c in conflicts
                               if c.get("verdict") == "needs_human"),
            "items": conflicts}
    (out_dir / "conflicts.json").write_text(
        json.dumps(csum, ensure_ascii=False, indent=1), encoding="utf-8")
    head, body = _rows_as_lists(raw.get("rows") or [])
    with (out_dir / "raw.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(body)
    paths = {"raw.json": str(out_dir / "raw.json"),
             "raw.csv": str(out_dir / "raw.csv"),
             "metrics.json": str(out_dir / "metrics.json"),
             "conflicts.json": str(out_dir / "conflicts.json")}
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws0 = wb.active
        ws0.title = "00 说明"
        ws0.append(["数据集", title or "专家团原始数据"])
        ws0.append(["生成方式", "core/data_model.build_raw（确定性归一，不调模型）"])
        cov = raw.get("coverage") or {}
        ws0.append(["行数", cov.get("rows")])
        ws0.append(["指标数", cov.get("metrics")])
        ws0.append(["冲突数", cov.get("conflicts")])
        ws0.append(["口径", "每行可回指 source_id；同键不同值进 03 冲突"])
        ws1 = wb.create_sheet("01 原始数据")
        ws1.append(head)
        for r in body:
            ws1.append(r)
        ws2 = wb.create_sheet("02 度量注册")
        mh = ["metric_id", "metric_name", "qualifier", "unit", "unit_base",
              "additivity", "owner", "rows"]
        ws2.append(mh)
        for m in raw.get("metrics") or []:
            ws2.append([m.get(k) for k in mh])
        ws3 = wb.create_sheet("03 冲突")
        ch = ["key", "metric_id", "entity", "period", "values", "sources", "grades", "rule"]
        ws3.append(ch)
        for c in raw.get("conflicts") or []:
            ws3.append([json.dumps(c.get(k), ensure_ascii=False) for k in ch])
        ws4 = wb.create_sheet("04 覆盖")
        ws4.append(["指标", "值"])
        for k, v in (raw.get("coverage") or {}).items():
            ws4.append([k, v])
        ws5 = wb.create_sheet("05 来源")
        sh = ["编号", "等级", "机构", "标题", "日期", "URL"]
        ws5.append(sh)
        for s in sources or []:
            ws5.append([s.get("file"), s.get("grade"), s.get("org"),
                        s.get("title"), s.get("date"), s.get("url")])
        xlsx = out_dir / "raw.xlsx"
        wb.save(xlsx)
        paths["raw.xlsx"] = str(xlsx)
    except Exception as exc:  # noqa: BLE001
        paths["raw.xlsx"] = f"skipped: {exc}"
    return paths
