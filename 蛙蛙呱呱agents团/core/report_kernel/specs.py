# -*- coding: utf-8 -*-
"""report_kernel.specs —— 表/图规格推断器。

它解决的是「同一份 draft，细心的人写就 L4，不细心的人写就 L2」：
  - 表：首列左对齐、数字列右对齐、涨跌色、合计行、列宽、表头单位；
  - 图：口径副标题、来源/图注、连续量轴的均值参考线。

推断只做确定性动作，不发明业务含义；推不出来的（例如标题没有数字、
图没有来源）直接报错，交给作者补，而不是悄悄放过。
"""
from __future__ import annotations

import copy
import re
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

UNIT_TOKEN = r"(?:亿元|万元|元|%|pp|百分点|倍|天|周|月|年|个|条|分|点|人|户|斤|公斤|吨)"
UNIT_IN_TEXT = re.compile(r"[（(]([^()（）]*?" + UNIT_TOKEN + r"[^()（）]*?)[)）]")
NUMERIC_HEADER = re.compile(r"价|额|量|率|数|值|比|差|度|期|天|月|占比|贡献|覆盖|得分")
SIGNED_HEADER = re.compile(r"率|变化|同比|环比|差|毛利|净利|价差|改善|贡献|增速|降幅|涨幅")
TOTAL_WORDS = ("合计", "总计", "小计", "汇总")
REF_TYPES = {"hbar", "vbar", "dot", "lollipop", "line", "area"}


def _text(cell: Any) -> str:
    if isinstance(cell, dict):
        return str(cell.get("text", ""))
    return str(cell or "")


def _num(text: str) -> Optional[float]:
    s = str(text).strip().replace(",", "").replace("，", "").replace(" ", "")
    s = s.replace("−", "-").replace("—", "").replace("–", "-")
    s = s.rstrip("%")
    if not s or s in {"-", "+"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _caption_unit(caption: str) -> Optional[str]:
    units = []
    for m in UNIT_IN_TEXT.finditer(str(caption or "")):
        units.append(m.group(1).strip())
    # 只取单一单位；多元单位（元/件、%）不强行套到每一列
    uniq = list(dict.fromkeys(units))
    return uniq[0] if len(uniq) == 1 else None


def _header_has_unit(text: str) -> bool:
    return bool(UNIT_IN_TEXT.search(str(text or "")))


def _numeric_columns(table: Dict[str, Any]) -> List[int]:
    rows = table.get("rows") or []
    ncols = len(table.get("columns") or [])
    out: List[int] = []
    for j in range(ncols):
        vals = [_num(_text(r[j])) for r in rows if j < len(r)]
        vals = [v for v in vals if v is not None]
        total = len([r for r in rows if j < len(r)])
        if total and len(vals) / total >= 0.6:
            out.append(j)
    return out


def infer_table(table: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """返回（新表，统计）。不修改入参。"""
    t = copy.deepcopy(table)
    cols = t.get("columns") or []
    rows = t.get("rows") or []
    stats = {"with_unit": 0, "unit_headers": 0, "numeric": 0, "tone": 0, "total_row": 0}
    caption = str(t.get("caption") or "")
    cap_unit = _caption_unit(caption)
    numeric_cols = set(_numeric_columns(t))

    # 表头：首列 left，数字列 num；缺单位时用 caption 的单一单位补齐
    for j, c in enumerate(cols):
        if isinstance(c, str):
            c = {"text": c}
            cols[j] = c
        text = str(c.get("text") or "")
        if j == 0:
            c["left"] = True
        elif j in numeric_cols:
            c["num"] = True
            if cap_unit and not _header_has_unit(text) and NUMERIC_HEADER.search(text):
                c["text"] = f"{text}（{cap_unit}）"
        if _header_has_unit(str(c.get("text") or "")):
            stats["unit_headers"] += 1
    stats["with_unit"] = 1 if stats["unit_headers"] else 0
    t["columns"] = cols

    # 合计行：最后一行的首列是合计/总计/小计
    if rows:
        first = _text(rows[-1][0]) if rows[-1] else ""
        if any(w in first for w in TOTAL_WORDS):
            t["total_row"] = [{"text": _text(c), "num": j > 0}
                              for j, c in enumerate(rows[-1])]
            rows = rows[:-1]
            stats["total_row"] = 1

    # 单元格：数字列 num；涨跌列按正负加 tone
    for r in rows:
        for j, cell in enumerate(r):
            if isinstance(cell, str):
                cell = {"text": cell}
                r[j] = cell
            if j in numeric_cols:
                cell.setdefault("num", True)
                stats["numeric"] += 1
                header = _text(cols[j]) if j < len(cols) else ""
                txt = _text(cell)
                if SIGNED_HEADER.search(header) and "tone" not in cell:
                    if txt.startswith(("+", "＋")):
                        cell["tone"] = "up"
                        stats["tone"] += 1
                    elif txt.startswith(("-", "−", "–")):
                        cell["tone"] = "down"
                        stats["tone"] += 1
    t["rows"] = rows

    # 列宽：首列 22%，其余均分
    if cols and not t.get("col_widths"):
        rest = max(1, len(cols) - 1)
        t["col_widths"] = ["22%"] + [f"{78 / rest:.1f}%" for _ in range(rest)]
    return t, stats


def _chart_values(chart: Dict[str, Any]) -> List[float]:
    kind = str(chart.get("type") or "")
    vals: List[Any] = []
    if kind == "hbar":
        vals = [b.get("value") for b in (chart.get("bars") or [])]
    elif kind == "vbar":
        vals = [b.get("value") for b in (chart.get("vbars") or [])]
    elif kind in ("dot", "lollipop"):
        vals = [b.get("value") for b in (chart.get("items") or [])]
    elif kind in ("line", "area"):
        series = chart.get("series") or []
        vals = list((series[0] or {}).get("values") or []) if series else []
    elif kind in ("scatter", "bubble"):
        vals = [p.get("y") for p in (chart.get("points") or [])]
    out = []
    for v in vals:
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out


def complete_chart(chart: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int], List[str]]:
    ch = copy.deepcopy(chart)
    stats = {"ref_added": 0, "subtitle_added": 0}
    errors: List[str] = []
    kind = str(ch.get("type") or "")
    unit = str(ch.get("unit_meta") or "")
    title = str(ch.get("title") or "")

    if not re.search(r"\d", title):
        errors.append(f"图标题没有数字：{title or '(空)'}")
    if not str(ch.get("source") or "").strip():
        errors.append(f"图缺 source：{title or '(空)'}")

    if not str(ch.get("subtitle") or "").strip():
        ch["subtitle"] = f"单位：{unit}；口径见来源" if unit else "口径见来源"
        stats["subtitle_added"] += 1

    if kind in REF_TYPES and not ch.get("ref"):
        vals = _chart_values(ch)
        if len(vals) >= 2:
            m = round(mean(vals), 2)
            ch["ref"] = {"value": m, "label": f"均值 {m:g}"}
            stats["ref_added"] += 1

    if not str(ch.get("note") or "").strip():
        ch["note"] = "虚线为均值；口径见来源" if ch.get("ref") else "口径见来源"
    return ch, stats, errors


def apply_table_specs(contract: Dict[str, Any]) -> Dict[str, int]:
    stats = {"tables": 0, "with_unit": 0, "unit_headers": 0, "numeric": 0, "tone": 0, "total_row": 0}
    for sec in contract.get("sections") or []:
        tables = list(sec.get("tables") or [])
        if sec.get("table"):
            tables.insert(0, sec["table"])
        new_tables = []
        for tb in tables:
            nt, st = infer_table(tb)
            new_tables.append(nt)
            stats["tables"] += 1
            for k in ("with_unit", "unit_headers", "numeric", "tone", "total_row"):
                stats[k] += st[k]
        if new_tables:
            sec["table"] = new_tables[0]
            if len(new_tables) > 1:
                sec["tables"] = new_tables[1:]
            elif "tables" in sec:
                sec.pop("tables", None)
    return stats


def apply_chart_specs(contract: Dict[str, Any]) -> Dict[str, Any]:
    stats = {"charts": 0, "ref_added": 0, "subtitle_added": 0}
    errors: List[str] = []
    for sec in contract.get("sections") or []:
        charts = list(sec.get("charts") or [])
        if sec.get("chart"):
            charts.insert(0, sec["chart"])
        new_charts = []
        for ch in charts:
            nc, st, er = complete_chart(ch)
            new_charts.append(nc)
            stats["charts"] += 1
            stats["ref_added"] += st["ref_added"]
            stats["subtitle_added"] += st["subtitle_added"]
            errors.extend(er)
        if new_charts:
            sec["chart"] = new_charts[0]
            if len(new_charts) > 1:
                sec["charts"] = new_charts[1:]
            elif "charts" in sec:
                sec.pop("charts", None)
    return {"stats": stats, "errors": errors}


def apply_specs(contract: Dict[str, Any]) -> Dict[str, Any]:
    """原地补规格，返回统计与错误。"""
    tstats = apply_table_specs(contract)
    cstats = apply_chart_specs(contract)
    return {"tables": tstats, "charts": cstats["stats"],
            "errors": cstats["errors"],
            "ok": not cstats["errors"]}

