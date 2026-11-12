# -*- coding: utf-8 -*-
"""报告套件：主题 CSS + 表格/图表/卡片等可复用组件（零依赖，纯 SVG/HTML）。"""
from __future__ import annotations

import html
import math

ACCENT = "#B45309"      # 果价橙
PRIMARY = "#1F2937"
HEALTHY = "#15803D"
CRITICAL = "#B91C1C"

CSS = """
:root {
  --theme-primary: #1F2937; --theme-accent: #B45309;
  --ink: #0F172A; --muted: #475569; --line: #E2E8F0; --line-strong: #94A3B8;
  --canvas: #F8FAFC; --paper: #FFFFFF; --surface: #F1F5F9; --surface-strong: #E2E8F0;
  --critical: #B91C1C; --critical-soft: #FEF2F2; --healthy: #15803D; --healthy-soft: #F0FDF4;
  --watch: #B45309; --watch-soft: #FFFBEB;
}
* { box-sizing: border-box; }
html { background: var(--canvas); scroll-behavior: smooth; }
body { margin: 0; background: var(--canvas); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  font-size: 14.5px; line-height: 1.68; -webkit-font-smoothing: antialiased; font-variant-numeric: tabular-nums; }
.document { max-width: 1120px; margin: 32px auto 64px; padding: 48px 56px 60px;
  background: var(--paper); border: 1px solid var(--line); border-radius: 4px;
  box-shadow: 0 4px 20px -2px rgba(15,23,42,.06); }
.doc-header { padding-bottom: 24px; border-bottom: 2px solid var(--ink); margin-bottom: 28px; }
.doc-type-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; color: var(--muted);
  font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
.doc-glyph { width: 24px; height: 24px; display: inline-flex; align-items: flex-end; justify-content: center;
  gap: 2px; padding: 4px; border: 1px solid var(--line-strong); border-radius: 2px; }
.doc-glyph i { width: 2.5px; display: block; background: var(--theme-accent); }
.doc-glyph i:nth-child(1) { height: 5px; } .doc-glyph i:nth-child(2) { height: 11px; } .doc-glyph i:nth-child(3) { height: 8px; }
h1 { margin: 0 0 12px; font-size: 27px; font-weight: 700; line-height: 1.32; letter-spacing: -.02em; }
.standfirst { margin: 12px 0 0; color: var(--muted); font-size: 15px; line-height: 1.65; max-width: 960px; }
.doc-meta { display: flex; flex-wrap: wrap; gap: 6px 20px; margin-top: 18px; color: var(--muted); font-size: 12px; }
.doc-meta span { position: relative; white-space: nowrap; }
.doc-meta span + span::before { position: absolute; left: -11px; content: "·"; color: var(--line-strong); }
.metric-strip { margin: 28px 0; border-top: 1px solid var(--line-strong); border-bottom: 1px solid var(--line-strong);
  padding: 18px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; }
.metric-cell { border-left: 2px solid var(--line); padding-left: 14px; }
.metric-cell.accent { border-left-color: var(--theme-accent); }
.metric-cell.critical { border-left-color: var(--critical); }
.metric-cell.healthy { border-left-color: var(--healthy); }
.metric-label { font-size: 12px; color: var(--muted); font-weight: 600; margin-bottom: 6px;
  text-transform: uppercase; letter-spacing: .04em; }
.metric-value { font-size: 24px; font-weight: 700; line-height: 1.15; letter-spacing: -.02em; }
.metric-value.critical { color: var(--critical); } .metric-value.healthy { color: var(--healthy); }
.metric-note { font-size: 11.5px; color: var(--muted); margin-top: 6px; }
.report-section { margin-top: 40px; padding-top: 24px; border-top: 1px solid var(--line); }
.section-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
.section-num { font-size: 13px; font-weight: 700; color: var(--theme-accent); letter-spacing: .05em; }
h2 { margin: 0; font-size: 19px; font-weight: 700; letter-spacing: -.01em; }
h3 { margin: 20px 0 8px; font-size: 15px; font-weight: 700; }
p { margin: 0 0 12px; }
.executive-card { background: var(--surface); border-left: 4px solid var(--theme-primary); padding: 20px 24px;
  margin-bottom: 24px; border-radius: 2px; }
.directive-box { font-size: 16px; font-weight: 700; color: var(--theme-primary); margin-bottom: 10px; line-height: 1.5; }
.executive-body { font-size: 14.5px; line-height: 1.7; }
.embed-figure { margin: 20px 0; border: 1px solid var(--line); border-radius: 2px; background: var(--paper); }
.embed-figure-head { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px;
  background: var(--surface); border-bottom: 1px solid var(--line); font-size: 12.5px; font-weight: 700; }
.embed-figure-body { padding: 12px 16px; } .embed-figure-body svg { display: block; width: 100%; height: auto; }
.embed-figure-note { padding: 8px 16px 12px; font-size: 12px; color: var(--muted); border-top: 1px dashed var(--line); }
table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }
th, td { padding: 9px 11px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { background: var(--surface); color: var(--muted); font-weight: 700; font-size: 12px;
  text-transform: uppercase; letter-spacing: .03em; }
tr:hover td { background: rgba(241,245,249,.5); }
table.compact { font-size: 12px; } table.compact th, table.compact td { padding: 6px 8px; }
.tag-critical { color: var(--critical); font-weight: 700; }
.tag-healthy { color: var(--healthy); font-weight: 700; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px; font-weight: 700;
  background: var(--surface-strong); color: var(--muted); margin-left: 6px; }
.badge.A { background: var(--healthy-soft); color: var(--healthy); }
.badge.B { background: var(--watch-soft); color: var(--watch); }
.badge.C { background: var(--critical-soft); color: var(--critical); }
.callout { border: 1px solid var(--line); border-left: 3px solid var(--theme-accent); background: #FFFDF8;
  padding: 12px 16px; margin: 16px 0; font-size: 13.5px; }
.callout.critical { border-left-color: var(--critical); background: var(--critical-soft); }
.callout.healthy { border-left-color: var(--healthy); background: var(--healthy-soft); }
.callout b { font-weight: 700; }
.chain { display: flex; flex-wrap: wrap; align-items: stretch; gap: 8px; margin: 18px 0; }
.chain-node { flex: 1 1 120px; border: 1px solid var(--line); background: var(--surface); padding: 12px;
  border-radius: 3px; font-size: 12.5px; position: relative; }
.chain-node b { display: block; font-size: 13px; margin-bottom: 4px; }
.chain-node span { color: var(--muted); }
.chain-arrow { align-self: center; color: var(--line-strong); font-weight: 700; }
nav.toc { display:flex; flex-wrap:wrap; gap:6px 14px; margin:18px 0 4px; font-size:12.5px; }
nav.toc a { color: var(--muted); border-bottom: 1px dotted var(--line-strong); }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 16px 0; }
.kpi-card { border: 1px solid var(--line); padding: 14px 16px; border-radius: 3px; background: var(--paper); }
.kpi-card .k { font-size: 12px; color: var(--muted); font-weight: 600; }
.kpi-card .v { font-size: 20px; font-weight: 700; margin-top: 4px; }
.kpi-card .n { font-size: 12px; color: var(--muted); margin-top: 4px; }
.roadmap-list { margin: 16px 0; padding: 0 0 0 18px; list-style: none; border-left: 2px solid var(--line-strong); }
.roadmap-item { position: relative; margin-bottom: 18px; }
.roadmap-item::before { position: absolute; left: -24px; top: 5px; content: ""; width: 10px; height: 10px;
  border-radius: 50%; background: var(--theme-accent); border: 2px solid var(--paper); }
.roadmap-phase { font-size: 14px; font-weight: 700; }
.roadmap-scope { margin-left: 8px; font-weight: 600; color: var(--theme-accent); font-size: 13px; }
.roadmap-meta { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
details.audit-ledger { margin-top: 36px; border-top: 1px solid var(--line); padding-top: 16px; }
details.audit-ledger summary { font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase;
  letter-spacing: .05em; cursor: pointer; list-style: none; }
details.audit-ledger summary::-webkit-details-marker { display: none; }
details.audit-ledger summary::before { content: "▸ "; color: var(--theme-accent); }
details.audit-ledger[open] summary::before { content: "▾ "; }
.audit-body { margin-top: 14px; padding: 16px; background: var(--surface); border-radius: 2px; font-size: 12px; color: var(--muted); }
.doc-footer { margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--line);
  display: flex; justify-content: space-between; color: var(--muted); font-size: 11.5px; }
ul, ol { padding-left: 20px; margin: 8px 0; } li { margin-bottom: 5px; }
a { color: #1D4ED8; text-decoration: none; } a:hover { text-decoration: underline; }
.scroll { overflow-x: auto; }
@media print {
  body { background: #fff; font-size: 9.6pt; line-height: 1.58; }
  .document { border: none; box-shadow: none; padding: 0; margin: 0; max-width: none; }
  h1 { font-size: 19pt; } h2 { font-size: 13pt; } h3 { font-size: 10.8pt; }
  .standfirst { font-size: 10pt; } .doc-meta { font-size: 9pt; }
  .report-section { page-break-inside: auto; }
  h2, h3, .section-head, .doc-header { page-break-after: avoid; }
  .embed-figure, .metric-strip, .executive-card, .callout, .kpi-card, .chain, .roadmap-item { page-break-inside: avoid; }
  .metric-strip { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
  table { page-break-inside: auto; }
  tr, th, td { page-break-inside: avoid; }
  thead { display: table-header-group; }
  .scroll { overflow: visible; }
  details.audit-ledger { display: block; page-break-before: auto; }
  details.audit-ledger > summary { display: block; page-break-after: avoid; }
  .doc-footer { display: none; }
  a { color: inherit; text-decoration: none; }
  svg { max-height: 150mm; }
}
"""


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def fmt(x, nd=2, dash="—") -> str:
    if x is None:
        return dash
    if isinstance(x, str):
        return x
    return f"{x:,.{nd}f}"


def pct(x, nd=2) -> str:
    if x is None:
        return "—"
    return f"{x:+.{nd}f}%"


def table(headers: list[str], rows: list[list], cls: str = "", align_right: set[int] | None = None) -> str:
    ar = align_right or set()
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            style = ' style="text-align:right"' if i in ar else ""
            cells.append(f"<td{style}>{c}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="scroll"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def metric_strip(cells: list[tuple[str, str, str, str]]) -> str:
    out = []
    for label, value, note, tone in cells:
        cls = f" {tone}" if tone else ""
        out.append(f'<div class="metric-cell{cls}"><div class="metric-label">{label}</div>'
                   f'<div class="metric-value{cls}">{value}</div><div class="metric-note">{note}</div></div>')
    return f'<div class="metric-strip">{"".join(out)}</div>'


def section(num: str, title: str, body: str) -> str:
    return (f'<section class="report-section" id="s{num}"><div class="section-head">'
            f'<span class="section-num">{num}</span><h2>{title}</h2></div>{body}</section>')


def figure(title: str, svg: str, note: str = "") -> str:
    n = f'<div class="embed-figure-note">{note}</div>' if note else ""
    return (f'<div class="embed-figure"><div class="embed-figure-head"><span>{title}</span></div>'
            f'<div class="embed-figure-body">{svg}</div>{n}</div>')


def callout(text: str, kind: str = "") -> str:
    cls = f" {kind}" if kind else ""
    return f'<div class="callout{cls}">{text}</div>'


# ---------------------------------------------------------------- SVG
def _scale(vals, lo, hi, a, b):
    if hi == lo:
        return (a + b) / 2
    return a + (vals - lo) / (hi - lo) * (b - a)


def svg_line(points: list[tuple[str, float]], height: int = 280, color: str = ACCENT,
             y_label: str = "元/公斤", x_ticks: int = 6, annotate: list[tuple[str, str]] | None = None) -> str:
    W, H = 940, height
    L, R, T, B = 56, 18, 22, 42
    ys = [v for _, v in points]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.12 or 0.05
    lo, hi = lo - pad, hi + pad
    n = len(points)
    xs = [L + (R and (W - L - R) * i / max(1, n - 1)) for i in range(n)]
    y = lambda v: _scale(v, lo, hi, H - B, T)
    path = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{y(v):.1f}" for i, (_, v) in enumerate(points))
    area = path + f" L{xs[-1]:.1f},{H-B} L{xs[0]:.1f},{H-B} Z"
    grid = []
    for k in range(5):
        gy = T + (H - T - B) * k / 4
        val = hi - (hi - lo) * k / 4
        grid.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{W-R}" y2="{gy:.1f}" stroke="#E2E8F0" stroke-width="1"/>'
                    f'<text x="{L-8}" y="{gy+4:.1f}" text-anchor="end" font-size="10" fill="#64748B">{val:.2f}</text>')
    ticks = []
    step = max(1, n // x_ticks)
    for i in range(0, n, step):
        ticks.append(f'<text x="{xs[i]:.1f}" y="{H-14}" text-anchor="middle" font-size="10" fill="#64748B">'
                     f'{points[i][0][5:]}</text>')
    dots = ""
    if annotate:
        for label, idx in annotate:
            i = min(n - 1, max(0, int(idx)))
            anchor = "end" if i >= n - 2 else ("start" if i == 0 else "middle")
            dx = -6 if anchor == "end" else (6 if anchor == "start" else 0)
            dots += (f'<circle cx="{xs[i]:.1f}" cy="{y(points[i][1]):.1f}" r="4" fill="#fff" stroke="{color}" stroke-width="2"/>'
                     f'<text x="{xs[i]+dx:.1f}" y="{y(points[i][1])-10:.1f}" text-anchor="{anchor}" font-size="10.5" '
                     f'fill="{PRIMARY}" font-weight="700">{label}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img"><rect width="{W}" height="{H}" fill="#fff"/>{"".join(grid)}'
            f'<path d="{area}" fill="{color}" opacity="0.08"/>'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>'
            f'{dots}{"".join(ticks)}'
            f'<text x="{L}" y="{T-8}" font-size="11" fill="#64748B">{y_label}</text></svg>')


def svg_multi(series: dict[str, list[tuple[str, float]]], height: int = 320, x_labels: list[str] | None = None) -> str:
    W, H = 940, height
    L, R, T, B = 56, 150, 22, 42
    allv = [v for pts in series.values() for _, v in pts]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.1 or 0.1
    lo, hi = lo - pad, hi + pad
    n = max(len(p) for p in series.values())
    xs = [L + (W - L - R) * i / max(1, n - 1) for i in range(n)]
    y = lambda v: _scale(v, lo, hi, H - B, T)
    palette = ["#B45309", "#1D4ED8", "#15803D", "#7C3AED", "#0891B2", "#B91C1C"]
    paths, legend = [], []
    for i, (name, pts) in enumerate(series.items()):
        c = palette[i % len(palette)]
        d = " ".join(f"{'M' if k == 0 else 'L'}{xs[k]:.1f},{y(v):.1f}" for k, (_, v) in enumerate(pts))
        paths.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2"/>')
        ly = T + 6 + i * 17
        legend.append(f'<line x1="{W-R+8}" y1="{ly}" x2="{W-R+26}" y2="{ly}" stroke="{c}" stroke-width="2"/>'
                      f'<text x="{W-R+30}" y="{ly+4}" font-size="11" fill="#475569">{name}</text>')
    grid = []
    for k in range(5):
        gy = T + (H - T - B) * k / 4
        val = hi - (hi - lo) * k / 4
        grid.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{W-R}" y2="{gy:.1f}" stroke="#E2E8F0"/>'
                    f'<text x="{L-8}" y="{gy+4:.1f}" text-anchor="end" font-size="10" fill="#64748B">{val:.1f}</text>')
    ticks = "".join(f'<text x="{xs[i]:.1f}" y="{H-14}" text-anchor="middle" font-size="10" fill="#64748B">'
                    f'{(x_labels[i] if x_labels else list(series.values())[0][i][0])}</text>'
                    for i in range(0, n, max(1, n // 7)))
    return (f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>{"".join(grid)}'
            f'{"".join(paths)}{"".join(legend)}{ticks}</svg>')


def svg_bars(items: list[tuple[str, float, str]], height: int = 280, unit: str = "") -> str:
    """竖向柱状：items=(label, value, color)。用于年度均值、规格阶梯。"""
    W, H = 940, height
    L, R, T, B = 60, 24, 30, 52
    hi = max(v for _, v, _ in items) * 1.15 or 1
    n = len(items)
    bw = (W - L - R) / n
    out = []
    for i, (label, v, color) in enumerate(items):
        h = (H - T - B) * v / hi
        x = L + i * bw + bw * 0.18
        out.append(f'<rect x="{x:.1f}" y="{H-B-h:.1f}" width="{bw*0.64:.1f}" height="{h:.1f}" fill="{color}" opacity="0.78" rx="2"/>'
                   f'<text x="{x+bw*0.32:.1f}" y="{H-B-h-7:.1f}" text-anchor="middle" font-size="11.5" font-weight="700" fill="#1F2937">{v:.2f}{unit}</text>'
                   f'<text x="{x+bw*0.32:.1f}" y="{H-24}" text-anchor="middle" font-size="11" fill="#475569">{label}</text>')
    grid = "".join(f'<line x1="{L}" y1="{T + (H-T-B)*k/4:.1f}" x2="{W-R}" y2="{T + (H-T-B)*k/4:.1f}" stroke="#E2E8F0"/>'
                    for k in range(5))
    return f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>{grid}{"".join(out)}</svg>'


def svg_hbar(items: list[tuple[str, float]], height_per: int = 30, suffix: str = "%") -> str:
    W = 940
    H = max(120, len(items) * height_per + 30)
    L, R = 150, 90
    vals = [v for _, v in items]
    lo, hi = min(0, min(vals)), max(0, max(vals))
    span = hi - lo or 1
    zero = L + (W - L - R) * (0 - lo) / span
    rows = []
    for i, (label, v) in enumerate(items):
        y = 12 + i * height_per
        x2 = zero + (W - L - R) * v / span
        x1, x2 = min(zero, x2), max(zero, x2)
        c = HEALTHY if v > 0 else CRITICAL
        rows.append(f'<text x="{L-10}" y="{y+15}" text-anchor="end" font-size="12" fill="#334155">{label}</text>'
                    f'<rect x="{x1:.1f}" y="{y+4}" width="{max(1.5, x2-x1):.1f}" height="16" fill="{c}" opacity="0.75"/>'
                    f'<text x="{x2 + 6:.1f}" y="{y+16}" text-anchor="start" '
                    f'font-size="11" fill="#334155">{v:+.2f}{suffix}</text>')
    return (f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>'
            f'<line x1="{zero:.1f}" y1="8" x2="{zero:.1f}" y2="{H-8}" stroke="#94A3B8" stroke-width="1"/>'
            f'{"".join(rows)}</svg>')


def svg_hist(values: list[float], bins: int = 12, height: int = 250, mark: list[tuple[float, str, str]] | None = None) -> str:
    W, H = 940, height
    L, R, T, B = 56, 20, 22, 40
    lo, hi = min(values), max(values)
    if hi == lo:
        hi = lo + 1
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = min(bins - 1, int((v - lo) / width))
        counts[idx] += 1
    maxc = max(counts) or 1
    bw = (W - L - R) / bins
    bars = []
    for i, c in enumerate(counts):
        bh = (H - T - B) * c / maxc
        x = L + i * bw
        bars.append(f'<rect x="{x+2:.1f}" y="{H-B-bh:.1f}" width="{bw-4:.1f}" height="{bh:.1f}" fill="{ACCENT}" opacity="0.55"/>'
                    f'<text x="{x+bw/2:.1f}" y="{H-16}" text-anchor="middle" font-size="9.5" fill="#64748B">'
                    f'{lo + i*width:.1f}—{lo+(i+1)*width:.1f}</text>')
    marks = ""
    for v, label, color in (mark or []):
        if lo <= v <= hi:
            x = L + (v - lo) / (hi - lo) * (W - L - R)
            marks += (f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{H-B}" stroke="{color}" stroke-width="1.5" stroke-dasharray="4 3"/>'
                      f'<text x="{x:.1f}" y="{T+12}" text-anchor="middle" font-size="10.5" fill="{color}" font-weight="700">{label}</text>')
    grid = "".join(f'<line x1="{L}" y1="{T + (H-T-B)*k/3:.1f}" x2="{W-R}" y2="{T + (H-T-B)*k/3:.1f}" stroke="#E2E8F0"/>'
                   for k in range(4))
    return (f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>{grid}{"".join(bars)}{marks}'
            f'<text x="{L}" y="{T-6}" font-size="11" fill="#64748B">市场数</text></svg>')


def svg_compare(items: list[tuple[str, float, str]], height: int = 220) -> str:
    """两项对比条（从 0 起），右侧标注差值与百分比，用于现状 vs 目标。"""
    W, H = 940, height
    L, R, T = 120, 220, 30
    hi = max(v for _, v, _ in items) * 1.08 or 1
    row_h = 46
    out = []
    for i, (label, v, color) in enumerate(items):
        y = T + i * (row_h + 34)
        w = (W - L - R) * v / hi
        out.append(f'<text x="{L-12}" y="{y+row_h/2+5}" text-anchor="end" font-size="12.5" fill="#334155">{label}</text>'
                   f'<rect x="{L}" y="{y}" width="{w:.1f}" height="{row_h}" fill="{color}" opacity="0.75" rx="2"/>'
                   f'<text x="{L + w + 8:.1f}" y="{y+row_h/2+5}" font-size="13" font-weight="700" fill="#1F2937">{v:.2f}</text>')
    if len(items) == 2:
        a, b = items[0][1], items[1][1]
        d = b - a
        out.append(f'<text x="{L}" y="{T + 2*(row_h+34) + 6}" font-size="12" fill="{"#15803D" if d < 0 else "#B91C1C"}" '
                   f'font-weight="700">差 {d:+.2f} 元/公斤（{d/a*100:+.1f}%）</text>')
    axis = f'<line x1="{L}" y1="{T-10}" x2="{L}" y2="{H-30}" stroke="#CBD5E1"/>'
    return f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>{axis}{"".join(out)}</svg>'


def svg_stack(items: list[tuple[str, float, str]], width: int = 940, height: int = 190) -> str:
    """items: (label, value, color)；单条水平堆叠 + 图例，用于成本构成。"""
    W, H = width, height
    L, R, T = 20, 20, 30
    total = sum(v for _, v, _ in items) or 1
    bar_h = 54
    x = L
    segs, legend = [], []
    for i, (label, v, color) in enumerate(items):
        w = (W - L - R) * v / total
        segs.append(f'<rect x="{x:.1f}" y="{T}" width="{w:.1f}" height="{bar_h}" fill="{color}" opacity="0.8"/>')
        if w > 90:
            segs.append(f'<text x="{x + w/2:.1f}" y="{T + bar_h/2 + 5:.1f}" text-anchor="middle" '
                        f'font-size="11" fill="#fff" font-weight="700">{v:.2f}</text>')
        lx = L + (i % 3) * 300
        ly = T + bar_h + 28 + (i // 3) * 22
        legend.append(f'<rect x="{lx}" y="{ly-9}" width="9" height="9" fill="{color}" opacity="0.8"/>'
                      f'<text x="{lx+14}" y="{ly}" font-size="11.5" fill="#334155">{label} {v:.2f}'
                      f'（{v/total*100:.1f}%）</text>')
    # 总长标尺
    ticks = []
    for k in range(0, int(total) + 1, max(1, int(total // 5))):
        tx = L + (W - L - R) * k / total
        ticks.append(f'<line x1="{tx:.1f}" y1="{T}" x2="{tx:.1f}" y2="{T+bar_h}" stroke="#fff" stroke-width="1" opacity="0.4"/>')
    return (f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>'
            f'{"".join(ticks)}{"".join(segs)}{"".join(legend)}'
            f'<text x="{L}" y="{T-10}" font-size="11" fill="#64748B">合计 {total:.2f} 元/公斤</text></svg>')


def svg_waterfall(steps: list[tuple[str, float, float]], height: int = 300) -> str:
    """steps: (label, delta, cumulative_after)。"""
    W, H = 940, height
    L, R, T, B = 60, 20, 26, 52
    vals = [c for _, _, c in steps] + [0]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.15 or 1
    lo, hi = lo - pad, hi + pad
    bw = (W - L - R) / len(steps)
    y = lambda v: _scale(v, lo, hi, H - B, T)
    bars = []
    for i, (label, delta, cum) in enumerate(steps):
        prev = steps[i - 1][2] if i else 0
        x = L + i * bw + bw * 0.18
        y1, y2 = y(prev), y(cum)
        c = HEALTHY if delta >= 0 else CRITICAL
        bars.append(f'<rect x="{x:.1f}" y="{min(y1,y2):.1f}" width="{bw*0.64:.1f}" height="{abs(y2-y1)+1:.1f}" fill="{c}" opacity="0.6"/>'
                    f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x+bw*0.64:.1f}" y2="{y1:.1f}" stroke="#64748B" stroke-dasharray="3 3"/>'
                    f'<text x="{x+bw*0.32:.1f}" y="{H-30}" text-anchor="middle" font-size="10" fill="#334155">{label}</text>'
                    f'<text x="{x+bw*0.32:.1f}" y="{min(y1,y2)-6:.1f}" text-anchor="middle" font-size="10.5" fill="{PRIMARY}">{cum:.2f}</text>')
    grid = "".join(f'<line x1="{L}" y1="{T + (H-T-B)*k/4:.1f}" x2="{W-R}" y2="{T + (H-T-B)*k/4:.1f}" stroke="#E2E8F0"/>'
                   for k in range(5))
    return f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>{grid}{"".join(bars)}</svg>'


def svg_chain(nodes: list[tuple[str, str, str]], height: int = 150, breaks: list[int] | None = None) -> str:
    W, H = 940, height
    n = len(nodes)
    gap = 10
    bw = (W - gap * (n - 1)) / n
    out = []
    for i, (title, v1, v2) in enumerate(nodes):
        x = i * (bw + gap)
        out.append(f'<rect x="{x:.1f}" y="18" width="{bw:.1f}" height="{H-50}" rx="4" fill="#F8FAFC" stroke="#CBD5E1"/>'
                   f'<text x="{x+bw/2:.1f}" y="42" text-anchor="middle" font-size="12.5" font-weight="700" fill="#1F2937">{title}</text>'
                   f'<text x="{x+bw/2:.1f}" y="66" text-anchor="middle" font-size="11" fill="#B45309">{v1}</text>'
                   f'<text x="{x+bw/2:.1f}" y="86" text-anchor="middle" font-size="10.5" fill="#475569">{v2}</text>')
        if i < n - 1:
            cx = x + bw + gap / 2
            out.append(f'<path d="M{cx-5:.1f},{H/2-5:.1f} L{cx+4:.1f},{H/2:.1f} L{cx-5:.1f},{H/2+5:.1f}" '
                       f'fill="none" stroke="#94A3B8" stroke-width="2"/>')
    for b in (breaks or []):
        cx = b * (bw + gap) - gap / 2
        out.append(f'<line x1="{cx:.1f}" y1="18" x2="{cx:.1f}" y2="{H-32}" stroke="{CRITICAL}" stroke-width="2" stroke-dasharray="4 3"/>'
                   f'<text x="{cx:.1f}" y="{H-18}" text-anchor="middle" font-size="10" fill="{CRITICAL}" font-weight="700">断点</text>')
    return f'<svg viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>{"".join(out)}</svg>'


def page(title: str, kicker: str, standfirst: str, meta: list[str], body: str, footer_left: str) -> str:
    meta_html = "".join(f"<span>{m}</span>" for m in meta)
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><main class="document">
<header class="doc-header">
  <div class="doc-type-bar"><span class="doc-glyph"><i></i><i></i><i></i></span><span>{esc(kicker)}</span></div>
  <h1>{esc(title)}</h1>
  <p class="standfirst">{standfirst}</p>
  <div class="doc-meta">{meta_html}</div>
</header>
{body}
<footer class="doc-footer"><span>{footer_left}</span><span>报告日 2026-11-12 · 数据窗口 2026-09-15—2026-11-12</span></footer>
</main></body></html>"""
