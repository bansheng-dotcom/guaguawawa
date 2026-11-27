# -*- coding: utf-8 -*-
"""用真实链跑 fixtures，并导出 3 份黄金 HTML（研究简报 / 竞品矩阵 / 市场测算）。

用法：
    cd r05-washenyuan-research
    python -m research_chain.build_golden
"""
from __future__ import annotations

import html
import os
import tempfile
from typing import Any, Dict, List

from .common import read_json
from .runner import run_fixture

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(HERE, "fixtures", "pet_smart_hardware.json")
GOLDEN = os.path.join(HERE, "golden")

CSS = (
    "body{max-width:1120px;margin:32px auto;padding:0 20px;"
    "font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;"
    "line-height:1.65;color:#1f2937}h1{border-bottom:3px solid #0f766e;"
    "padding-bottom:10px}h2{margin-top:30px;color:#0f766e}"
    "table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}"
    "th,td{border:1px solid #d1d5db;padding:6px 8px;text-align:left;vertical-align:top}"
    "th{background:#f0fdfa}.meta{background:#f8fafc;border-left:4px solid #0f766e;"
    "padding:10px 14px;margin:10px 0;color:#475569}"
    ".tag{display:inline-block;background:#ccfbf1;color:#115e59;border-radius:4px;"
    "padding:1px 7px;margin-right:6px;font-size:12px}"
)


def _page(title: str, body: str) -> str:
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body>%s</body></html>"
            % (html.escape(title), CSS, body))


def _matrix_html(comp: Dict[str, Any]) -> str:
    dims = comp.get("dimensions") or []
    rows: List[str] = ["<table><thead><tr><th>竞品</th>%s</tr></thead><tbody>"
                       % "".join("<th>%s</th>" % html.escape(str(d)) for d in dims)]
    for p in comp.get("competitors") or []:
        cells = p.get("cells") or {}
        tds = []
        for d in dims:
            cell = cells.get(d) or {}
            tds.append("<td>%s<br><span class=\"tag\">%s</span></td>"
                       % (html.escape(str(cell.get("value"))),
                          html.escape(str(cell.get("source_id")))))
        rows.append("<tr><th>%s</th>%s</tr>" % (html.escape(str(p.get("name"))),
                                                "".join(tds)))
    rows.append("</tbody></table>")
    return "".join(rows)


def _competitor_page(comp: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    parts = [
        "<h1>黄金成品 · 竞品分析（5 家 × 8 维）</h1>",
        "<div class=\"meta\">研究链：%s；门禁：%s；份额合计 %.0f%%。</div>"
        % (" → ".join(manifest.get("stage_order") or []),
           "PASS" if manifest.get("ok") else "FAIL",
           float((comp.get("summary") or {}).get("share_sum") or 0)),
        "<h2>1. 5 × 8 竞品矩阵（每格附来源 id）</h2>",
        _matrix_html(comp),
        "<h2>2. Battlecard</h2>",
        "<table><thead><tr><th>竞品</th><th>定位</th><th>威胁</th><th>打法</th></tr></thead><tbody>",
    ]
    for p in comp.get("competitors") or []:
        card = p.get("battlecard") or {}
        parts.append("<tr><th>%s</th><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(str(p.get("name"))), html.escape(str(card.get("positioning"))),
            html.escape(str(card.get("threat"))), html.escape(str(card.get("attack")))))
    parts.append("</tbody></table>")
    parts.append("<h2>3. 五力</h2><table><thead><tr><th>力量</th><th>评分</th>"
                 "<th>理由</th><th>来源</th></tr></thead><tbody>")
    for f in comp.get("five_forces") or []:
        parts.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(str(f.get("force"))), html.escape(str(f.get("rating"))),
            html.escape(str(f.get("rationale"))), html.escape(str(f.get("source_id")))))
    parts.append("</tbody></table>")
    parts.append("<h2>4. 份额</h2><table><thead><tr><th>玩家</th><th>份额</th>"
                 "<th>来源</th></tr></thead><tbody>")
    for s in comp.get("shares") or []:
        parts.append("<tr><td>%s</td><td>%.0f%%</td><td>%s</td></tr>" % (
            html.escape(str(s.get("player"))), float(s.get("share") or 0),
            html.escape(str(s.get("source_id")))))
    parts.append("</tbody></table>")
    return _page("黄金成品 · 竞品分析", "".join(parts))


def _sizing_page(sizing: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    top = sizing.get("top_down") or {}
    bottom = sizing.get("bottom_up") or {}
    mc = sizing.get("monte_carlo") or {}
    parts = [
        "<h1>黄金成品 · 市场测算（top-down × bottom-up × p10/p50/p90）</h1>",
        "<div class=\"meta\">研究链门禁：%s；双口径差异 %.2f%%；蒙特卡洛 n=%s，seed=%s。</div>"
        % ("PASS" if manifest.get("ok") else "FAIL",
           float(sizing.get("variance") or 0) * 100, mc.get("n"), mc.get("seed")),
        "<h2>1. top-down（分品类加总）</h2>",
        "<table><thead><tr><th>品类</th><th>规模（亿元）</th></tr></thead><tbody>",
    ]
    for c in top.get("components") or []:
        parts.append("<tr><td>%s</td><td>%.2f</td></tr>" % (
            html.escape(str(c.get("name"))), float(c.get("value") or 0)))
    parts.append("<tr><th>合计</th><th>%.2f</th></tr></tbody></table>"
                 % float(top.get("tam") or 0))
    parts += [
        "<h2>2. bottom-up（客户数 × 可服务比例 × 年购买量 × 单价）</h2>",
        "<table><thead><tr><th>参数</th><th>取值</th></tr></thead><tbody>",
        "<tr><td>可服务客户数</td><td>%.0f 户</td></tr>" % float(bottom.get("customer_count") or 0),
        "<tr><td>可服务比例</td><td>%.0f%%</td></tr>" % (float(bottom.get("addressable_fraction") or 0) * 100),
        "<tr><td>户均年购买件数</td><td>%.1f 件</td></tr>" % float(bottom.get("annual_quantity") or 0),
        "<tr><td>件均到手价</td><td>%.0f 元</td></tr>" % float(bottom.get("price_per_unit") or 0),
        "<tr><th>bottom-up 合计</th><th>%.2f 亿元</th></tr>" % float(bottom.get("tam") or 0),
        "</tbody></table>",
        "<h2>3. 敏感性（确定性 LCG，假设区间均匀抽样）</h2>",
        "<table><thead><tr><th>分位</th><th>测算值（亿元）</th></tr></thead><tbody>",
        "<tr><td>p10</td><td>%.2f</td></tr>" % float(mc.get("p10") or 0),
        "<tr><td>p50</td><td>%.2f</td></tr>" % float(mc.get("p50") or 0),
        "<tr><td>p90</td><td>%.2f</td></tr>" % float(mc.get("p90") or 0),
        "</tbody></table>",
        "<h2>4. 假设清单（每条挂证据）</h2>",
        "<table><thead><tr><th>假设</th><th>取值</th><th>区间</th><th>单位</th>"
        "<th>证据</th><th>口径</th></tr></thead><tbody>",
    ]
    for a in sizing.get("assumptions") or []:
        parts.append("<tr><td>%s</td><td>%.4g</td><td>[%.4g, %.4g]</td><td>%s</td>"
                     "<td>%s</td><td>%s</td></tr>" % (
                         html.escape(str(a.get("name"))), float(a.get("value") or 0),
                         float(a.get("low") or 0), float(a.get("high") or 0),
                         html.escape(str(a.get("unit"))), html.escape(str(a.get("evidence_id"))),
                         html.escape(str(a.get("basis")))))
    parts.append("</tbody></table>")
    parts.append("<h2>5. 读法</h2><div class=\"meta\">top-down 回答“品类盘子有多大”，"
                 "bottom-up 回答“按客户行为能不能花到这么多”，p10–p90 给出假设同时波动时的区间。"
                 "三条必须同时成立，任一偏离都要回到证据台账改假设。</div>")
    return _page("黄金成品 · 市场测算", "".join(parts))


def main() -> int:
    os.makedirs(GOLDEN, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="r05-golden-") as tmp:
        manifest = run_fixture(FIXTURE, tmp)
        report_art = read_json(os.path.join(tmp, "report.json"))
        comp = read_json(os.path.join(tmp, "compete.json"))
        sizing = read_json(os.path.join(tmp, "size.json"))

        with open(os.path.join(GOLDEN, "industry-research.html"), "w", encoding="utf-8") as f:
            f.write(report_art["html"])
        with open(os.path.join(GOLDEN, "competitor-matrix.html"), "w", encoding="utf-8") as f:
            f.write(_competitor_page(comp, manifest))
        with open(os.path.join(GOLDEN, "market-sizing.html"), "w", encoding="utf-8") as f:
            f.write(_sizing_page(sizing, manifest))
    print("golden written: %s (ok=%s, sources=%d)"
          % (GOLDEN, manifest.get("ok"), len(report_art.get("ledger_source_ids") or [])))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
