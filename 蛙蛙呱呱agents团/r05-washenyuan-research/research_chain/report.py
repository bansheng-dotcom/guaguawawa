# -*- coding: utf-8 -*-
"""第 8 段 report：结论先行 + 证据附录 + 边界。

报告是“可被审计的阅读层”，不是新结论：
- 每条结论必须能追到 ledger 里真实存在的 source id；
- 附录必须覆盖全部证据（条数与 evidence_id 双向核对）；
- 未验证项、矛盾、时效降级都必须写出来，不能只写好消息。
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from .common import ck, gate

CONF_CN = {"high": "高", "medium": "中", "low": "低"}


def _cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "／").replace("\n", " ")


def check_report(art: Dict[str, Any]) -> Dict[str, Any]:
    """报告门禁：结论可追、附录完整、边界与未验证披露。"""
    conclusions = art.get("conclusions") or []
    markdown = str(art.get("markdown") or "")
    ledger_sources = set(art.get("ledger_source_ids") or [])
    ledger_evidence = [str(x) for x in art.get("ledger_evidence_ids") or []]
    appendix_count = int(art.get("appendix_count") or 0)
    boundary = art.get("boundary") or []
    checks = [
        ck("report:conclusions", len(conclusions) > 0, "报告至少一条结论"),
        ck("report:traceability",
           all(sid in ledger_sources for c in conclusions
               for sid in (c.get("source_ids") or [])),
           "每条结论的来源必须存在于证据台账"),
        ck("report:appendix_count",
           appendix_count == len(ledger_evidence) and appendix_count > 0,
           "附录条数=%d，台账条数=%d" % (appendix_count, len(ledger_evidence))),
        ck("report:appendix_complete",
           all(eid in markdown for eid in ledger_evidence),
           "每条证据都必须出现在附录"),
        ck("report:boundary", len(boundary) > 0, "必须写研究边界"),
        ck("report:unverified_disclosed",
           "未验证" in markdown and "已声明" in markdown,
           "未验证项必须显式披露"),
        ck("report:structure",
           all(h in markdown for h in ("## 0 边界与口径", "## 1 结论先行",
                                       "## 4 证据附录", "## 5 矛盾记录",
                                       "## 6 验证与未验证项"))
           and markdown.index("## 1 结论先行") < markdown.index("## 4 证据附录"),
           "必须结论先行、证据在后"),
    ]
    return gate(checks)


def _render_size(sizing: Dict[str, Any]) -> List[str]:
    top = sizing.get("top_down") or {}
    bottom = sizing.get("bottom_up") or {}
    mc = sizing.get("monte_carlo") or {}
    lines = [
        "| 口径 | 结果（亿元） | 说明 |",
        "|---|---:|---|",
        "| top-down | %.2f | %s |" % (
            float(top.get("tam") or 0),
            " + ".join("%s %.2f" % (c.get("name"), float(c.get("value") or 0))
                       for c in top.get("components") or [])),
        "| bottom-up | %.2f | 客户数 %.0f × 可服务 %.0f%% × 年购 %.1f × 单价 %.0f 元 |" % (
            float(bottom.get("tam") or 0), float(bottom.get("customer_count") or 0),
            float(bottom.get("addressable_fraction") or 0) * 100,
            float(bottom.get("annual_quantity") or 0),
            float(bottom.get("price_per_unit") or 0)),
        "| 差异 | %.2f%% | 双口径差异门限 50%% |" % (float(sizing.get("variance") or 0) * 100),
        "",
        "敏感性（假设区间均匀抽样，n=%d，seed=%s）：**p10 %.2f / p50 %.2f / p90 %.2f**。"
        % (mc.get("n"), mc.get("seed"), float(mc.get("p10") or 0),
           float(mc.get("p50") or 0), float(mc.get("p90") or 0)),
        "",
        "| 假设 | 取值 | 区间 | 单位 | 证据 |",
        "|---|---:|---|---|---|",
    ]
    for a in sizing.get("assumptions") or []:
        lines.append("| %s | %.4g | [%.4g, %.4g] | %s | %s |" % (
            _cell(a.get("name")), float(a.get("value") or 0), float(a.get("low") or 0),
            float(a.get("high") or 0), _cell(a.get("unit")), _cell(a.get("evidence_id"))))
    return lines


def _render_competition(comp: Dict[str, Any]) -> List[str]:
    dims = comp.get("dimensions") or []
    lines = ["| 竞品 | " + " | ".join(dims) + " |",
             "|---|" + "---|" * len(dims)]
    for p in comp.get("competitors") or []:
        cells = p.get("cells") or {}
        row = ["%s" % p.get("name")]
        for d in dims:
            cell = cells.get(d) or {}
            row.append("%s（%s）" % (_cell(cell.get("value")), _cell(cell.get("source_id"))))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "**五力**", "",
              "| 力量 | 评分 | 理由 | 来源 |", "|---|---|---|---|"]
    for f in comp.get("five_forces") or []:
        lines.append("| %s | %s | %s | %s |" % (
            _cell(f.get("force")), _cell(f.get("rating")),
            _cell(f.get("rationale")), _cell(f.get("source_id"))))
    lines += ["", "**份额**：" + "；".join(
        "%s %.0f%%（%s）" % (_cell(s.get("player")), float(s.get("share") or 0),
                             _cell(s.get("source_id"))) for s in comp.get("shares") or []), ""]
    lines += ["**Battlecard 摘要**", ""]
    for p in comp.get("competitors") or []:
        card = p.get("battlecard") or {}
        lines.append("- **%s**：定位=%s；威胁=%s；打法=%s" % (
            p.get("name"), _cell(card.get("positioning")),
            _cell(card.get("threat")), _cell(card.get("attack"))))
    return lines


def build(plan: Dict[str, Any], ledger: Dict[str, Any], verification: Dict[str, Any],
          synthesis: Dict[str, Any], sizing: Dict[str, Any],
          competition: Dict[str, Any], limits: List[str]) -> Dict[str, Any]:
    """组装 Markdown 报告与 HTML，产出 report 工件。"""
    entries = ledger.get("entries") or []
    conclusions = synthesis.get("conclusions") or []
    contradictions = synthesis.get("contradictions") or []
    ledger_sources = sorted({str(e.get("source_id")) for e in entries})
    ledger_evidence = [str(e.get("evidence_id")) for e in entries]

    lines: List[str] = [
        "# 研究简报：%s" % plan.get("question"),
        "",
        "> 决策用途：%s" % plan.get("decision_use"),
        "> 市场口径：%s" % (plan.get("market_scope") or "未限定"),
        "> 生产口径：8 段研究链 scope→source→collect→verify→triangulate→size→compete→report",
        "",
        "## 0 边界与口径",
        "",
        "本研究只呈现证据与选项，不替决策人拍板。以下边界必须与结论一起阅读：",
        "",
    ]
    lines += ["- %s" % x for x in limits]
    lines += ["", "## 1 结论先行", ""]
    for idx, c in enumerate(conclusions, start=1):
        lines.append("%d. **[%s] %s**（证据 %s；来源 %s）" % (
            idx, CONF_CN.get(c.get("confidence"), c.get("confidence")),
            c.get("text"), "/".join(c.get("evidence_ids") or []),
            "/".join(c.get("source_ids") or [])))
    lines += ["", "## 2 市场测算（亿元）", ""]
    lines += _render_size(sizing)
    lines += ["", "## 3 竞争格局", ""]
    lines += _render_competition(competition)
    lines += ["", "## 4 证据附录（%d 条 / %d 源）" % (len(entries), len(ledger_sources)), "",
              "| # | 证据 | 数值 | 单位 | 口径期 | 日期 | 来源 | URL | 原文 |",
              "|---|---|---:|---|---|---|---|---|---|"]
    for e in entries:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            _cell(e.get("evidence_id")), _cell(e.get("claim")), _cell(e.get("value")),
            _cell(e.get("unit")), _cell(e.get("period")), _cell(e.get("date")),
            _cell(e.get("source_id")), _cell(e.get("url")), _cell(e.get("quote"))))
    lines += ["", "## 5 矛盾记录", ""]
    if contradictions:
        for c in contradictions:
            vals = "；".join("%s=%s%s（%s）" % (v.get("evidence_id"), v.get("value"),
                                              c.get("unit"), v.get("source_id"))
                             for v in c.get("values") or [])
            lines.append("- 子问题 %s：%s；极差 %.2f%%；状态=%s；处置=%s" % (
                c.get("subquestion_id"), vals, float(c.get("spread_pct") or 0),
                c.get("status"), c.get("resolution")))
    else:
        lines.append("- 无（证据口径一致）")
    summary = verification.get("summary") or {}
    lines += ["", "## 6 验证与未验证项", "",
              "- 已验证 %d / %d；未验证 %d（已声明清单：%s）" % (
                  summary.get("verified", 0), summary.get("total", 0),
                  summary.get("unverified", 0),
                  "、".join(verification.get("unverified_ids") or []) or "无"),
              "- 时效 stale %d 条；单层源偏置告警 %d 条。" % (
                  summary.get("stale", 0), summary.get("bias_flagged", 0)),
              "", "## 7 边界", ""]
    lines += ["- %s" % x for x in limits]
    markdown = "\n".join(lines) + "\n"

    art: Dict[str, Any] = {
        "artifact": "research_report",
        "question": plan.get("question"),
        "decision_use": plan.get("decision_use"),
        "markdown": markdown,
        "html": markdown_to_html(markdown),
        "conclusions": conclusions,
        "conclusions_trace": [
            {"conclusion_id": c.get("id"), "source_ids": c.get("source_ids") or []}
            for c in conclusions
        ],
        "ledger_source_ids": ledger_sources,
        "ledger_evidence_ids": ledger_evidence,
        "appendix_count": len(entries),
        "boundary": list(limits),
        "unverified_disclosed": True,
    }
    art["gate"] = check_report(art)
    return art


def markdown_to_html(markdown: str) -> str:
    """极简 Markdown → HTML（标题/表格/列表/加粗），用于离线阅读。"""
    out: List[str] = []
    in_table = False
    in_list = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            tag = "th" if not in_table else "td"
            if not in_table:
                out.append("<table>")
                in_table = True
            out.append("<tr>" + "".join("<%s>%s</%s>" % (tag, _inline(c), tag)
                                        for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>%s</li>" % _inline(line[2:]))
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            out.append("<h%d>%s</h%d>" % (level, _inline(line[level:].strip()), level))
        elif line.startswith(">"):
            out.append("<blockquote>%s</blockquote>" % _inline(line[1:].strip()))
        elif line.strip():
            out.append("<p>%s</p>" % _inline(line))
    if in_table:
        out.append("</table>")
    if in_list:
        out.append("</ul>")
    body = "\n".join(out)
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<title>研究简报</title>"
            "<style>body{max-width:1100px;margin:32px auto;padding:0 20px;"
            "font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;"
            "line-height:1.65;color:#1f2937}h1{border-bottom:3px solid #0f766e;"
            "padding-bottom:10px}h2{margin-top:30px;color:#0f766e}"
            "table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}"
            "th,td{border:1px solid #d1d5db;padding:6px 8px;text-align:left;"
            "vertical-align:top}th{background:#f0fdfa}"
            "blockquote{background:#f8fafc;border-left:4px solid #0f766e;"
            "margin:8px 0;padding:8px 12px;color:#475569}</style></head><body>"
            + body + "</body></html>")


def _inline(text: str) -> str:
    """转义 HTML 后处理 **加粗**。"""
    safe = html.escape(str(text))
    parts = safe.split("**")
    if len(parts) % 2 == 1:
        safe = "".join(p if i % 2 == 0 else "<strong>%s</strong>" % p
                       for i, p in enumerate(parts))
    return safe
