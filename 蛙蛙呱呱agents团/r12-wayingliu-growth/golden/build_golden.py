#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用增长链真实跑 fixtures，生成 3 份黄金看板（确定性、离线）。

用法：python golden/build_golden.py
产物：selfmedia-dashboard-90d.html / attribution-budget.html / cohort-ltv-cac.html
"""
from __future__ import annotations

import html
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE = os.path.dirname(HERE)
if ROLE not in sys.path:
    sys.path.insert(0, ROLE)

from growth_chain import runner  # noqa: E402

CSS = """
:root{--ink:#1f2a37;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--bg:#f8fafc}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:32px 24px 56px}
h1{font-size:24px;margin:0 0 6px}.sub{color:var(--muted);font-size:13px}
.panel{background:#fff;border:1px solid var(--line);border-radius:12px;
padding:18px;margin-top:16px}h2{font-size:16px;margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:right}
th:first-child,td:first-child{text-align:left}th{color:var(--muted)}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;
background:#dbeafe;color:#1e40af}.note{color:var(--muted);font-size:12px;line-height:1.7}
"""


def _j(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _page(title, body):
    return (f"<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>"
            f"<div class=\"wrap\">{body}</div></body></html>\n")


def attribution_page(art):
    rows = []
    channels = sorted(art["models"]["last_touch"]["channels"])
    for ch in channels:
        cells = []
        for model in ("first_touch", "last_touch", "linear", "position_based"):
            slot = art["models"][model]["channels"].get(ch, {})
            cells.append(f"<td>{slot.get('revenue', 0):,.0f}</td>")
        rows.append(f"<tr><td>{html.escape(ch)}</td>{''.join(cells)}</tr>")
    budget = art["budget_recommendation"]["by_channel"]
    brows = "".join(f"<tr><td>{html.escape(ch)}</td><td>{amt:,.0f}</td>"
                    f"<td>{amt / art['budget_recommendation']['total'] * 100:.1f}%</td></tr>"
                    for ch, amt in sorted(budget.items()))
    inc = art["incrementality"]
    body = f"""
<h1>多渠道归因 + 预算建议</h1>
<div class="sub">分母：转化用户 {art['denominator']['value']} · 触点
{art['journeys']['touches']} · 增量：{html.escape(str(inc['method']))}</div>
<div class="panel"><h2>四模型收入分配（同一分母）</h2>
<table><thead><tr><th>渠道</th><th>首触</th><th>末触</th><th>线性</th><th>位置</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="note">相关不等于因果：本次增量结论为
{html.escape(str(inc['established']))}，预算建议仅按末触收入份额做起点，
上线前需 A/B 或地理实验验证。</p></div>
<div class="panel"><h2>预算建议（总额 {art['budget_recommendation']['total']:,.0f}）</h2>
<table><thead><tr><th>渠道</th><th>建议预算</th><th>占比</th></tr></thead>
<tbody>{brows}</tbody></table></div>"""
    return _page("R12 多渠道归因与预算建议", body)


def retention_page(ret, paid, diag):
    months = sorted(ret["cohorts"])
    max_cols = max(len(ret["cohorts"][m]["curve"]) for m in months)
    header = "".join(f"<th>M{c}</th>" for c in range(max_cols))
    trs = []
    for m in months:
        cells = {r["period"]: r["retention_rate"] for r in ret["cohorts"][m]["curve"]}
        tds = "".join(
            f"<td>{'—' if c not in cells else f'{cells[c] * 100:.1f}%'}</td>"
            for c in range(max_cols))
        trs.append(f"<tr><td>{html.escape(m)}</td>"
                   f"<td>{ret['cohorts'][m]['cohort_size']:,.0f}</td>{tds}</tr>")
    curve = " · ".join(f"M{r['period']} {r['retention_rate'] * 100:.1f}%"
                       for r in ret["overall_curve"])
    prows = "".join(
        f"<tr><td>{html.escape(ch)}</td><td>{v['cac']:,.0f}</td>"
        f"<td>{v['ltv']:,.0f}</td><td>{v['ltv_cac']:.2f}</td>"
        f"<td>{v['payback_months']:.2f}</td><td>{v['contribution_margin']:,.0f}</td></tr>"
        for ch, v in sorted(paid["channels"].items()))
    body = f"""
<h1>队列留存 + LTV/CAC</h1>
<div class="sub">队列规模合计 {ret['total_cohort_size']:,.0f}（= 诊断 signups
{diag['totals']['signups']:,.0f}）· 留存曲线：{html.escape(curve)}</div>
<div class="panel"><h2>队列留存矩阵（分母固定）</h2>
<table><thead><tr><th>队列</th><th>规模</th>{header}</tr></thead>
<tbody>{''.join(trs)}</tbody></table></div>
<div class="panel"><h2>付费回收（阈值 {paid['totals']['payback_threshold']} 个月）</h2>
<table><thead><tr><th>渠道</th><th>CAC</th><th>LTV</th><th>LTV/CAC</th>
<th>回收月</th><th>贡献毛利</th></tr></thead><tbody>{prows}</tbody></table>
<p class="note">口径：贡献毛利=ARPA×毛利率；LTV=贡献毛利/月流失率；
回收月=CAC/贡献毛利。留存分母为期初队列规模，流失逐期可解释。</p></div>"""
    return _page("R12 队列留存与 LTV/CAC", body)


def main():
    spec = os.path.join(ROLE, "fixtures", "chain_spec.json")
    tmp = tempfile.mkdtemp(prefix="r12_golden_")
    manifest = runner.run(spec, tmp)
    if not manifest["ok"]:
        raise SystemExit(f"增长链未通过，无法生成黄金：{manifest['gate']['failed']}")

    media = _j(os.path.join(tmp, "selfmedia.json"))
    with open(os.path.join(HERE, "selfmedia-dashboard-90d.html"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(media["dashboard_html"])

    attr = _j(os.path.join(tmp, "attribution.json"))
    with open(os.path.join(HERE, "attribution-budget.html"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(attribution_page(attr))

    ret = _j(os.path.join(tmp, "retention.json"))
    paid = _j(os.path.join(tmp, "paid.json"))
    diag = _j(os.path.join(tmp, "diagnose.json"))
    with open(os.path.join(HERE, "cohort-ltv-cac.html"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(retention_page(ret, paid, diag))
    print("golden 生成完成：3 份 HTML")


if __name__ == "__main__":
    main()
