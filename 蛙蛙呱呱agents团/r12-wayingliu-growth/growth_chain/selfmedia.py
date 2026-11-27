# -*- coding: utf-8 -*-
"""第 6 段 · 自媒体：平台导出规范化 + 静态看板 + 三态日报。

三态：正常（字段齐全）/ 部分（有缺列缺值，缺失显式记录）/ 失败（无可用数据）。
铁律：缺数据不补零——缺失一律 None 并列入 missing，绝不写成 0。
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from . import common as c


PLATFORMS = ("公众号", "B站", "小红书", "抖音", "知乎", "微博")
METRICS = ("views", "likes", "comments", "shares", "followers_gain", "revenue")
STATUS_LABELS = {"normal": "正常", "partial": "部分", "failed": "失败"}

ALIASES = {
    "date": ("日期", "date"),
    "platform": ("平台", "platform"),
    "views": ("播放量", "播放", "浏览量", "views"),
    "likes": ("点赞", "点赞数", "likes"),
    "comments": ("评论", "评论数", "comments"),
    "shares": ("分享", "转发", "shares"),
    "followers_gain": ("涨粉", "新增粉丝", "followers_gain"),
    "revenue": ("收入", "revenue"),
}


def _pick(row: Dict[str, str], field: str) -> Optional[str]:
    """在原始导出中按别名取列；列不存在返回 None（与空值区分）。"""
    for alias in ALIASES[field]:
        if alias in row:
            return row[alias]
    return None


def _normalize(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    """把平台导出规范化为统一字段，缺失显式记 None。"""
    normalized: List[Dict[str, Any]] = []
    missing_fields: set = set()
    imputed = False
    for row in rows:
        item: Dict[str, Any] = {}
        for field in ("date", "platform"):
            raw = _pick(row, field)
            item[field] = (raw or "").strip() if raw is not None else None
            if item[field] in (None, ""):
                missing_fields.add(field)
        for field in METRICS:
            raw = _pick(row, field)
            value = c.num(raw)
            if value is None:
                missing_fields.add(field)
            item[field] = value
        normalized.append(item)
    return {"rows": normalized, "missing_fields": sorted(missing_fields),
            "imputed_zero": imputed}


def _status(rows: List[Dict[str, Any]], missing: List[str],
            platform: Optional[str]) -> str:
    if not rows or platform not in PLATFORMS:
        return "failed"
    if not any(r.get("views") is not None for r in rows):
        return "failed"
    if missing:
        return "partial"
    return "normal"


def _totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """只对观测到的值求和；不做 0 填充。"""
    totals = {}
    for field in METRICS:
        vals = [r[field] for r in rows if r.get(field) is not None]
        totals[field] = c.rnd(sum(vals), 2) if vals else None
        totals[field + "_observed_days"] = len(vals)
    totals["days"] = len(rows)
    totals["partial"] = any(totals[f + "_observed_days"] < len(rows) for f in METRICS)
    return totals


def _render_html(artifact: Dict[str, Any]) -> str:
    """生成单文件静态看板（离线、无外部依赖）。"""
    rows = artifact.get("rows", [])
    totals = artifact.get("totals", {})
    status = artifact.get("status_label", "失败")
    platform = artifact.get("platform") or "-"
    esc = html.escape

    by_week: Dict[int, float] = {}
    for idx, row in enumerate(rows):
        if row.get("views") is None:
            continue
        week = idx // 7 + 1
        by_week[week] = by_week.get(week, 0.0) + row["views"]
    peak = max(by_week.values()) if by_week else 1.0
    bars = []
    for week in sorted(by_week):
        width = max(2, int(round(by_week[week] / peak * 100)))
        bars.append(
            f'<div class="bar-row"><span class="bar-label">第{week}周</span>'
            f'<span class="bar" style="width:{width}%"></span>'
            f'<span class="bar-val">{by_week[week]:.0f}</span></div>')

    def fmt(key: str) -> str:
        val = totals.get(key)
        return "缺失" if val is None else f"{val:,.0f}"

    recent = rows[-14:]
    trs = "".join(
        "<tr>" + "".join(
            f"<td>{esc(str(r.get(k)) if r.get(k) is not None else '缺失')}</td>"
            for k in ("date", "views", "likes", "comments", "shares",
                      "followers_gain", "revenue"))
        + "</tr>" for r in recent)

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>R12 单平台 90 天看板 · {esc(platform)}</title>
<style>
:root{{--ink:#1f2a37;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--bg:#f8fafc}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:32px 24px 56px}}
h1{{font-size:24px;margin:0 0 6px}} .sub{{color:var(--muted);font-size:13px}}
.status{{display:inline-block;margin-left:8px;padding:2px 10px;border-radius:999px;
background:#dcfce7;color:#166534;font-size:12px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}}
.card{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px}}
.card b{{display:block;font-size:22px;margin-top:6px}} .card span{{color:var(--muted);font-size:12px}}
.panel{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px;margin-top:16px}}
.bar-row{{display:flex;align-items:center;gap:10px;margin:6px 0;font-size:12px}}
.bar-label{{width:54px;color:var(--muted)}} .bar{{height:12px;background:var(--accent);
border-radius:6px;display:inline-block}} .bar-val{{color:var(--muted)}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}}
th,td{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:right}}
th:first-child,td:first-child{{text-align:left}} th{{color:var(--muted);font-weight:600}}
.note{{margin-top:14px;color:var(--muted);font-size:12px;line-height:1.7}}
</style></head><body><div class="wrap">
<h1>单平台 90 天看板<span class="status">{esc(status)}</span></h1>
<div class="sub">平台：{esc(platform)} · 天数：{totals.get('days', 0)} · 缺失字段：
{esc(", ".join(artifact.get("missing_fields") or []) or "无")}</div>
<div class="cards">
<div class="card"><span>播放量</span><b>{fmt('views')}</b></div>
<div class="card"><span>点赞</span><b>{fmt('likes')}</b></div>
<div class="card"><span>涨粉</span><b>{fmt('followers_gain')}</b></div>
<div class="card"><span>收入</span><b>{fmt('revenue')}</b></div>
</div>
<div class="panel"><b>周播放趋势</b>{''.join(bars) or '<p class="note">无可用观测</p>'}</div>
<div class="panel"><b>最近 14 天日报</b>
<table><thead><tr><th>日期</th><th>播放</th><th>点赞</th><th>评论</th><th>分享</th><th>涨粉</th><th>收入</th></tr></thead>
<tbody>{trs}</tbody></table></div>
<p class="note">口径：缺失一律显示「缺失」，不补 0；部分态合计仅覆盖已观测天数。
本看板由 growth_chain.selfmedia 确定性生成。</p>
</div></body></html>"""


def analyze(rows: List[Dict[str, str]], platform: Optional[str] = None,
            zero_filled: bool = False, source: str = "") -> Dict[str, Any]:
    """规范 + 三态判定 + 看板；供 build 与门禁复核共用。"""
    norm = _normalize(rows)
    norm_rows = norm["rows"]
    if platform is None:
        platforms = [r["platform"] for r in norm_rows if r.get("platform")]
        platform = platforms[0] if platforms else None
    missing = [f for f in norm["missing_fields"]]
    status = _status(norm_rows, missing, platform)
    artifact = {
        "source": source,
        "platform": platform,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "rows": norm_rows,
        "missing_fields": missing,
        "zero_filled": bool(zero_filled or norm["imputed_zero"]),
        "totals": _totals(norm_rows),
        "coverage": c.rnd(
            sum(1 for r in norm_rows if all(r.get(f) is not None for f in METRICS))
            / len(norm_rows), 4) if norm_rows else 0.0,
    }
    artifact["dashboard_html"] = _render_html(artifact)
    return artifact


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """独立门禁复核（误用工件拦截）。"""
    status = artifact.get("status")
    rows = artifact.get("rows") or []
    missing = artifact.get("missing_fields") or []
    platform = artifact.get("platform")
    zero_filled = bool(artifact.get("zero_filled") or artifact.get("filled_zero"))
    imputed = any(bool(r.get("imputed")) for r in rows if isinstance(r, dict))

    checks = [
        c.check("缺数据不补零", not zero_filled and not imputed,
                "检测到缺失被写成 0 或 zero_filled=true"),
        c.check("三态日报合法", status in STATUS_LABELS, f"status={status}"),
        c.check("失败态不得出看板", status != "failed" or not artifact.get("dashboard_html"),
                "failed 态仍输出看板"),
        c.check("部分态须列缺失", status != "partial" or bool(missing),
                f"missing={missing}"),
        c.check("平台在白名单", platform in PLATFORMS, str(platform)),
        c.check("有观测值", any(r.get("views") is not None for r in rows
                              if isinstance(r, dict)), "全部缺失"),
    ]
    return c.gate(checks)


def build(export_path: str, platform: Optional[str] = None) -> Dict[str, Any]:
    """跑自媒体段并返回带门禁的工件。"""
    rows = c.read_csv_rows(export_path)
    artifact = analyze(rows, platform=platform, source=export_path)
    gate = check(artifact)
    art = {"stage": "selfmedia", "gate": gate}
    art.update(artifact)
    return art
