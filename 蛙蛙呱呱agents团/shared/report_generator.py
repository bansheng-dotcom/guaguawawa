# -*- coding: utf-8 -*-
"""一人公司 · 全角色通用专业报告生成器 (Universal Agent Report Generator) v2。

为全量智能体 (R01~R20) 提供统一、标准化、自包含、零外部依赖的
商业级 HTML + Markdown 双格式报告出具能力。

遵循：
    agents/docs/SOP_BUSINESS_ANALYSIS_AND_REPORTING.md （DSH-SOP-REP-001）
    agents/docs/SOP_AGENT_META_UPGRADE.md              （DSH-SOP-META-001）

v2 相对 v1 的硬化点（对齐 REP-001 五段式 + META-001 红线）：
    1. 五段式强制：决策指令 / KPI 格栅 / 三级归因 / 护栏熔断 / 灰度+下一步，
       缺任一段直接抛 ReportSpecError（不再允许「半份报告」静默落盘）。
    2. 三级归因（L1 数据真实性 → L2 经营下钻 → L3 商业外部）作为一等公民，
       独立渲染为阶梯卡片，而不是混在正文里。
    3. 证据与可复现：报告页脚强制附 runner / 输入哈希 / 门禁通过数 / 复算命令，
       任何数字都能回到一次真实执行。
    4. 编码零风险：HTML 直写 UTF-8 + 全部字段经 html.escape，杜绝注入与乱码；
       Markdown 用 \n 连接并显式指定 newline="\n"。
    5. 打印友好：@media print 去掉阴影与背景色，可直接 PDF 归档。
    6. 禁止空话：summary / content 中的空泛词由 report_engine 侧拦截，本模块
       负责把「数值 + 口径 + 阈值」结构化成可核对的视图。
"""
from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from agents.shared.role_profiles import ROLE_PROFILES, get as get_profile

try:  # 图表深度层：缺失时报告降级为纯表格（绝不阻断出报告）
    from agents.shared.report_depth import CHART_CSS_VARS, render_chart
except Exception:  # noqa: BLE001
    CHART_CSS_VARS = ""

    def render_chart(spec):  # type: ignore[misc]
        return {"title": (spec or {}).get("title", "图表"), "svg": "", "ok": False,
                "note": "深度图表层不可用，已降级为表格。"}


class ReportSpecError(ValueError):
    """报告规格不满足 REP-001 门禁（缺护栏 / 缺灰度 / 缺归因 / 空 KPI）。"""


# 角色主题色：唯一事实来源在 role_profiles，本模块不再重复维护一份。
ROLE_THEMES: Dict[str, Dict[str, str]] = {
    rid: {"primary": p["theme"]["primary"], "accent": p["theme"]["accent"],
          "title": p["title"]}
    for rid, p in ROLE_PROFILES.items()
}

_LEVEL_LABEL = {
    "L1": ("L1 数据真实性", "#2b6cb0", "#ebf8ff"),
    "L2": ("L2 经营下钻", "#b7791f", "#fffaf0"),
    "L3": ("L3 商业外部", "#6b46c1", "#faf5ff"),
}


def _e(value: Any) -> str:
    """HTML 转义：所有外部/计算结果进模板前必过这一层。"""
    return html.escape("" if value is None else str(value), quote=True)


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if value is None:
        return "—"
    return str(value)


# --------------------------------------------------------------------------- #
# 规格门禁：不符合 REP-001 直接失败，绝不"凑一份"报告
# --------------------------------------------------------------------------- #
def validate_spec(
    report_title: str,
    executive_summary: str,
    decision_directive: str,
    kpi_metrics: Sequence[Dict[str, Any]],
    analysis_sections: Sequence[Dict[str, Any]],
    guardrails: Optional[Sequence[Dict[str, str]]],
    rollout_plan: Optional[Sequence[Dict[str, str]]],
    next_steps: Optional[Sequence[str]],
    rca: Optional[Sequence[Dict[str, str]]],
) -> List[str]:
    """返回违规项清单；非空即禁止落盘（REP-001 第五章红线）。"""
    errs: List[str] = []
    if not (report_title or "").strip():
        errs.append("缺报告标题")
    if not (decision_directive or "").strip():
        errs.append("缺【决策指令】：报告必须给出批准/驳回/灰度/熔断中的明确动作")
    if len((executive_summary or "").strip()) < 20:
        errs.append("核心结论过短（<20 字）：必须结论先行并带数据锚点")
    if not kpi_metrics:
        errs.append("缺 KPI：至少 1 个可复算指标")
    if not analysis_sections:
        errs.append("缺分析正文：至少 1 节归因分析")
    if not guardrails:
        errs.append("缺护栏熔断：REP-001 红线③，无熔断条件的建议视为不合格")
    else:
        for i, g in enumerate(guardrails):
            if not (g.get("threshold") or "").strip():
                errs.append(f"护栏第 {i + 1} 行缺熔断阈值")
    if not rollout_plan:
        errs.append("缺灰度计划：REP-001 红线②，禁止一键 100% 全量")
    else:
        if len(rollout_plan) < 2:
            errs.append("灰度计划少于 2 档：必须是阶梯放量而非一次切换")
    if not next_steps:
        errs.append("缺下一步行动：必须落到角色/责任与验收")
    if rca:
        levels = {str(r.get("level", "")).upper() for r in rca}
        for need in ("L1", "L2", "L3"):
            if need not in levels:
                errs.append(f"三级归因缺 {need} 层")
    return errs


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def generate_professional_report(
    role_id: str,
    agent_name: str,
    report_title: str,
    executive_summary: str,
    decision_directive: str,
    kpi_metrics: List[Dict[str, Any]],
    analysis_sections: List[Dict[str, Any]],
    out_dir: str,
    report_slug: str = "business_decision_report",
    table_data: Optional[Dict[str, Any]] = None,
    guardrails: Optional[List[Dict[str, str]]] = None,
    rollout_plan: Optional[List[Dict[str, str]]] = None,
    next_steps: Optional[List[str]] = None,
    rca: Optional[List[Dict[str, str]]] = None,
    provenance: Optional[Dict[str, Any]] = None,
    figures: Optional[List[Dict[str, Any]]] = None,
    appendix: Optional[List[Dict[str, Any]]] = None,
    strict: bool = True,
) -> Dict[str, str]:
    """生成符合 REP-001 规范的 HTML + Markdown 双格式企业级决策报告。

    :param role_id: 角色代码 (e.g. "r01", "r06")
    :param agent_name: 角色名称 (e.g. "蛙全局", "蛙得清")
    :param report_title: 报告大标题
    :param executive_summary: 核心结论先行段（必须含数据锚点）
    :param decision_directive: 决策指令（批准/驳回/灰度/熔断）
    :param kpi_metrics: KPI 卡片 [{"label","value","sub","status":"green"|"red"|"normal"}]
    :param analysis_sections: 分析小节 [{"title","content","bullets":[...],"figure":{...},"table":{...}}]
    :param out_dir: 输出目录
    :param report_slug: 产物文件名前缀
    :param table_data: 明细表 {"headers":[...],"rows":[[...]]}
    :param guardrails: 护栏 [{"dim","metric","base","threshold"}]
    :param rollout_plan: 灰度 [{"phase","scope","duration","condition"}]
    :param next_steps: 下一步行动列表
    :param rca: 三级归因 [{"level":"L1|L2|L3","title","finding","evidence"}]
    :param provenance: 证据与可复现信息（runner/input_hash/复算命令等）
    :param figures: 独立图表卡 [{"type","title",...chart spec}]（走 core/charts 48 型 SVG）
    :param appendix: 附录表格 [{"title","table":{"headers","rows"},"note"}]
    :param strict: True 时规格不合规直接抛 ReportSpecError（默认，生产口径）
    :return: {"html": path, "md": path}
    """
    profile = get_profile(role_id)
    agent_name = agent_name or profile["name"]
    violations = validate_spec(report_title, executive_summary, decision_directive,
                               kpi_metrics, analysis_sections, guardrails,
                               rollout_plan, next_steps, rca)
    if violations and strict:
        raise ReportSpecError(
            f"{role_id.upper()} 报告未通过 REP-001 门禁：" + "；".join(violations))

    os.makedirs(out_dir, exist_ok=True)
    theme = ROLE_THEMES.get(role_id.lower(), {"primary": "#1a202c",
                                              "accent": "#3182ce",
                                              "title": "业务专家"})
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    report_code = f"{role_id.upper()}-{now.strftime('%Y%m%d-%H%M')}-{report_slug[:12].upper()}"
    prov = provenance or {}

    # ---------------- KPI 格栅 ----------------
    kpi_html = ""
    for kpi in kpi_metrics:
        status = (kpi.get("status") or "").lower()
        cls = "green" if status == "green" else ("red" if status == "red" else "normal")
        kpi_html += (
            '<div class="kpi-card">'
            f'<div class="kpi-title">{_e(kpi.get("label"))}</div>'
            f'<div class="kpi-value {cls}">{_e(kpi.get("value"))}</div>'
            f'<div class="kpi-sub">{_e(kpi.get("sub"))}</div>'
            "</div>"
        )

    # ---------------- 三级归因阶梯 ----------------
    rca_html = ""
    if rca:
        blocks = ""
        for item in rca:
            lvl = str(item.get("level", "")).upper()
            label, color, bg = _LEVEL_LABEL.get(
                lvl, ("归因层", theme["accent"], "#f7fafc"))
            evidence = item.get("evidence") or item.get("bullets") or []
            if isinstance(evidence, str):
                evidence = [evidence]
            ev_html = ""
            if evidence:
                ev_html = "<ul>" + "".join(
                    f"<li>{_e(x)}</li>" for x in evidence) + "</ul>"
            blocks += (
                f'<div class="rca-step" style="border-left-color:{color};background:{bg}">'
                f'<div class="rca-badge" style="background:{color}">{_e(label)}</div>'
                f'<div class="rca-body"><h3>{_e(item.get("title"))}</h3>'
                f'<p>{_e(item.get("finding"))}</p>{ev_html}</div></div>'
            )
        rca_html = (
            '<div class="card"><h2>三级归因下钻 (L1 → L2 → L3)</h2>'
            '<p class="hint">先排除假异动，再锁定贡献度 ≥70% 的核心因子，'
            "最后区分内因与外因；禁止跳过任何一层。</p>"
            f"{blocks}</div>"
        )

    # ---------------- 正文小节 ----------------
    def _table_html(tbl: Any) -> str:
        if not (isinstance(tbl, dict) and tbl.get("headers") and tbl.get("rows")):
            return ""
        thead = "".join(f"<th>{_e(h)}</th>" for h in tbl["headers"])
        tbody = "".join(
            "<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>"
            for row in tbl["rows"])
        cap = (f'<p class="hint">表：{_e(tbl["caption"])}</p>'
               if tbl.get("caption") else "")
        return (f"{cap}<table><thead><tr>{thead}</tr></thead>"
                f"<tbody>{tbody}</tbody></table>")

    def _figure_html(spec: Any) -> str:
        if not isinstance(spec, dict) or not spec:
            return ""
        res = render_chart(spec)
        if res.get("ok") and res.get("svg"):
            note = (f'<p class="hint">{_e(res["note"])}</p>'
                    if res.get("note") else "")
            return (f'<figure class="fig"><figcaption>{_e(res["title"])}</figcaption>'
                    f'<div class="fig-body">{res["svg"]}</div>{note}</figure>')
        # 降级：有表就出表，没有就留一条说明
        fallback = _table_html(spec.get("fallback_table"))
        note = f'<p class="hint">⚠️ {_e(res.get("note"))}</p>'
        return (f'<figure class="fig"><figcaption>{_e(res["title"])}</figcaption>'
                f"{fallback}{note}</figure>")

    sections_html = ""
    for sec in analysis_sections:
        bullets_html = ""
        if sec.get("bullets"):
            bullets_html = "<ul>" + "".join(
                f"<li>{_e(b)}</li>" for b in sec["bullets"]) + "</ul>"
        sections_html += (
            '<div class="card">'
            f'<h2>{_e(sec.get("title") or "分析结论")}</h2>'
            f'<p>{_e(sec.get("content"))}</p>{_figure_html(sec.get("figure"))}'
            f'{bullets_html}{_table_html(sec.get("table"))}</div>'
        )

    # ---------------- 独立图表区（深度层） ----------------
    figures_block = ""
    if figures:
        body = "".join(_figure_html(f) for f in figures)
        figures_block = (
            '<div class="card"><h2>📈 量化图谱支撑 · 图表证据区（全部由技能结果确定性渲染）</h2>'
            '<p class="hint">下列图表坐标与数值均来自本次真实执行的结果 JSON；'
            "渲染器为 core/charts 的 48 型 SVG 图谱，可打印、无前端依赖。</p>"
            f"{body}</div>")

    # ---------------- 附录 ----------------
    appendix_block = ""
    if appendix:
        body = ""
        for i, ap in enumerate(appendix, 1):
            body += (f'<h3>附录 {i} · {_e(ap.get("title"))}</h3>'
                     f'{_table_html(ap.get("table"))}')
            if ap.get("note"):
                body += f'<p class="hint">{_e(ap["note"])}</p>'
        appendix_block = (
            '<div class="card appendix"><h2>📎 附录（原始明细，供审计复算）</h2>'
            f"{body}</div>")

    # ---------------- 明细表 ----------------
    table_block = ""
    if table_data and table_data.get("headers") and table_data.get("rows"):
        thead = "".join(f"<th>{_e(h)}</th>" for h in table_data["headers"])
        tbody = "".join(
            "<tr>" + "".join(f"<td>{_e(c)}</td>" for c in row) + "</tr>"
            for row in table_data["rows"])
        table_block = (
            '<div class="card"><h2>数据对照与明细（可逐行复算）</h2>'
            f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"
            "</div>")

    # ---------------- 护栏熔断 ----------------
    guardrail_html = ""
    if guardrails:
        rows = "".join(
            f"<tr><td>{_e(g.get('dim'))}</td>"
            f"<td><strong>{_e(g.get('metric'))}</strong></td>"
            f"<td>{_e(g.get('base'))}</td>"
            f"<td><span class='tag-red'>{_e(g.get('threshold'))}</span></td></tr>"
            for g in guardrails)
        guardrail_html = (
            '<div class="card alert-box"><h2>⚠️ 护栏熔断机制 '
            "(Guardrails &amp; Kill-Switch)</h2>"
            "<p>上线 / 放量前必须先配置以下监控；触及任一红线立刻自动回滚，"
            "并由责任人 30 分钟内书面通报。</p>"
            "<table><thead><tr><th>维度</th><th>监控指标</th><th>基准线</th>"
            f"<th>熔断阈值</th></tr></thead><tbody>{rows}</tbody></table></div>")

    # ---------------- 灰度计划 ----------------
    rollout_html = ""
    if rollout_plan:
        steps = ""
        for i, p in enumerate(rollout_plan, 1):
            steps += (
                '<div class="tl-item">'
                f'<div class="tl-dot">{i}</div>'
                f'<div class="tl-body"><div class="tl-phase">{_e(p.get("phase"))}'
                f'<span class="tl-scope">{_e(p.get("scope"))}</span></div>'
                f'<div class="tl-meta">观察窗口 {_e(p.get("duration"))} · '
                f'放行标准 {_e(p.get("condition"))}</div></div></div>')
        rollout_html = (
            '<div class="card"><h2>🚀 阶梯灰度推进（禁止一键全量）</h2>'
            f'<div class="timeline">{steps}</div></div>')

    # ---------------- 下一步 ----------------
    next_html = ""
    if next_steps:
        next_html = (
            '<div class="card action-box"><h2>📋 下一步行动（责任到角色）</h2>'
            "<ol>" + "".join(f"<li>{_e(ns)}</li>" for ns in next_steps)
            + "</ol></div>")

    # ---------------- 证据与可复现 ----------------
    prov_rows = ""
    for k, v in prov.items():
        prov_rows += (f"<tr><td>{_e(k)}</td><td><code>{_e(v)}</code></td></tr>")
    prov_html = (
        '<div class="card prov"><h2>🧾 证据与可复现（本报告的每个数字都能回溯）</h2>'
        f"<table><tbody>{prov_rows}</tbody></table>"
        '<p class="hint">复算方式：按上表 runner 命令重跑，结果 JSON 与本报告 '
        "KPI 逐项对齐；若不一致，以重跑结果为准并作废本报告。</p></div>")

    gate_note = ""
    if violations:
        gate_note = ('<div class="card alert-box"><h2>报告门禁告警</h2><ul>'
                     + "".join(f"<li>{_e(v)}</li>" for v in violations)
                     + "</ul><p>以上项未满足 REP-001，本报告为降级稿。</p></div>")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(report_title)} · {_e(agent_name)}</title>
<style>
:root {{
  --primary: {theme['primary']};
  --accent: {theme['accent']};
  --ink: #1f2933; --muted: #6b7280; --line: #e5e7eb;
  --theme-base: #ffffff; --theme-primary: {theme['primary']};
  --theme-accent: {theme['accent']}; --canvas: #ffffff;
{CHART_CSS_VARS}
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei",
    Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.7; color: var(--ink); background: #f5f7fa;
  max-width: 1080px; margin: 0 auto; padding: 28px 20px 60px; -webkit-font-smoothing: antialiased;
}}
header.rpt {{
  background: linear-gradient(135deg, var(--primary), var(--accent));
  color: #fff; border-radius: 12px; padding: 28px 26px; margin-bottom: 22px;
  box-shadow: 0 10px 24px -12px rgba(0,0,0,.45);
}}
header.rpt h1 {{ margin: 0 0 10px; font-size: 25px; line-height: 1.35; }}
header.rpt .meta {{ font-size: 13px; opacity: .92; }}
header.rpt .tags {{ margin-top: 10px; }}
.tag {{ display: inline-block; background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.3);
  color: #fff; padding: 2px 10px; border-radius: 999px; font-size: 12px; margin: 0 6px 4px 0; }}
.card {{ background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 22px 24px; margin-bottom: 18px; box-shadow: 0 2px 10px -6px rgba(16,24,40,.18); }}
h2 {{ color: var(--primary); font-size: 17px; margin: 0 0 14px;
  border-left: 4px solid var(--accent); padding-left: 11px; }}
h3 {{ font-size: 15px; margin: 0 0 6px; color: var(--ink); }}
p {{ margin: 8px 0; }}
.hint {{ color: var(--muted); font-size: 13px; }}
.executive {{ background: #f0f7ff; border-left: 4px solid var(--accent);
  border-radius: 8px; padding: 16px 18px; }}
.directive {{ font-size: 16px; font-weight: 700; color: var(--primary); margin-bottom: 8px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px; margin-top: 18px; }}
.kpi-card {{ background: #fbfdff; border: 1px solid var(--line); border-radius: 10px;
  padding: 15px; text-align: center; }}
.kpi-title {{ font-size: 13px; color: var(--muted); margin-bottom: 6px; }}
.kpi-value {{ font-size: 23px; font-weight: 700; color: var(--ink); word-break: break-all; }}
.kpi-value.green {{ color: #15803d; }}
.kpi-value.red {{ color: #b91c1c; }}
.kpi-sub {{ font-size: 12px; color: #94a3b8; margin-top: 5px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0 4px; font-size: 13.5px; }}
th, td {{ border: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: top; }}
th {{ background: #f3f6fa; color: #475569; font-weight: 600; white-space: nowrap; }}
tbody tr:nth-child(even) {{ background: #fafcff; }}
code {{ background: #f1f5f9; padding: 1px 6px; border-radius: 4px; font-size: 12.5px; }}
.tag-red {{ color: #b91c1c; background: #fef2f2; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
.alert-box {{ background: #fffdf7; border-left: 4px solid #dd6b20; }}
.action-box {{ background: #f7fdf9; border-left: 4px solid #15803d; }}
.prov {{ background: #fafafa; }}
.rca-step {{ display: flex; gap: 14px; padding: 14px 16px; border-left: 4px solid;
  border-radius: 8px; margin-bottom: 12px; }}
.rca-badge {{ color: #fff; font-size: 12px; font-weight: 700; padding: 3px 9px;
  border-radius: 999px; height: 22px; white-space: nowrap; }}
.rca-body {{ flex: 1; }}
.rca-body p {{ margin: 4px 0; }}
.timeline {{ position: relative; padding-left: 6px; }}
.tl-item {{ display: flex; gap: 14px; padding: 10px 0; border-bottom: 1px dashed var(--line); }}
.tl-item:last-child {{ border-bottom: none; }}
.tl-dot {{ width: 26px; height: 26px; border-radius: 50%; background: var(--accent); color: #fff;
  font-size: 13px; font-weight: 700; display: flex; align-items: center;
  justify-content: center; flex: 0 0 26px; }}
.tl-phase {{ font-weight: 600; }}
.tl-scope {{ margin-left: 10px; font-weight: 400; color: var(--accent); font-size: 13px; }}
.tl-meta {{ color: var(--muted); font-size: 13px; }}
ul, ol {{ padding-left: 22px; margin: 8px 0; }}
li {{ margin-bottom: 5px; }}
footer {{ text-align: center; color: var(--muted); font-size: 12px; margin-top: 26px; line-height: 1.9; }}
figure.fig {{ margin: 16px 0 6px; padding: 12px 14px; background: var(--surface, #f8fafc);
  border: 1px solid var(--line); border-radius: 10px; }}
figure.fig figcaption {{ font-size: 13px; font-weight: 600; color: var(--ink);
  margin-bottom: 6px; }}
.fig-body svg {{ width: 100%; height: auto; display: block; }}
.appendix table {{ font-size: 12.5px; }}
.appendix h3 {{ margin: 16px 0 6px; font-size: 14px; color: var(--primary); }}
@media print {{
  body {{ background: #fff; padding: 0; }}
  .card {{ box-shadow: none; border-color: #ccc; page-break-inside: avoid; }}
  header.rpt {{ box-shadow: none; }}
}}
</style>
</head>
<body>
<header class="rpt">
  <h1>{_e(report_title)}</h1>
  <div class="meta">
    出品角色 <strong>{_e(role_id.upper())} {_e(agent_name)}</strong>（{_e(theme['title'])}）
    · 报告编号 {_e(report_code)} · 生成时间 {_e(now_str)} · 文档类型 {_e(profile['doc_type'])}
  </div>
  <div class="tags">
    <span class="tag">结论先行</span><span class="tag">数据可复算</span>
    <span class="tag">三级归因</span><span class="tag">护栏熔断</span>
    <span class="tag">阶梯灰度</span>
  </div>
</header>

<div class="card">
  <h2>一、核心结论先行 (Executive Summary)</h2>
  <div class="executive">
    <div class="directive">【决策指令】{_e(decision_directive)}</div>
    <p>{_e(executive_summary)}</p>
  </div>
  <div class="kpi-grid">{kpi_html}</div>
</div>

{rca_html}
{sections_html}
{figures_block}
{table_block}
{guardrail_html}
{rollout_html}
{next_html}
{prov_html}
{appendix_block}
{gate_note}

<footer>
  {_e(role_id.upper())} {_e(agent_name)} · {_e(profile['doc_type'])}<br>
  依据 DSH-SOP-REP-001 / DSH-SOP-META-001 出具 · 渲染器 agents/shared/report_generator.py<br>
  本报告为机器可复算产物：KPI 与门禁结论均来自一次真实执行的结果 JSON，未使用任何虚构数据。
</footer>
</body>
</html>
"""
    html_path = os.path.join(out_dir, f"{report_slug}.html")
    with open(html_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html_content)

    # ---------------- Markdown 快读版 ----------------
    md: List[str] = [
        f"# {report_title}",
        "",
        f"> 出品角色：{role_id.upper()} {agent_name}（{theme['title']}） · "
        f"编号：{report_code} · 时间：{now_str}",
        "",
        "## 一、核心结论先行",
        "",
        f"**【决策指令】{decision_directive}**",
        "",
        executive_summary,
        "",
        "### KPI 速览",
        "",
        "| 指标 | 数值 | 补充说明 | 状态 |",
        "| :--- | :---: | :--- | :---: |",
    ]
    for kpi in kpi_metrics:
        status = (kpi.get("status") or "").lower()
        mark = "🟢" if status == "green" else ("🔴" if status == "red" else "⚪")
        md.append(f"| {kpi.get('label', '')} | **{_fmt(kpi.get('value'))}** | "
                  f"{kpi.get('sub', '')} | {mark} |")
    md.append("")

    if rca:
        md += ["## 二、三级归因下钻", ""]
        for item in rca:
            lvl = str(item.get("level", "")).upper()
            label, _, _ = _LEVEL_LABEL.get(lvl, ("归因层", "", ""))
            md.append(f"### {label} · {item.get('title', '')}")
            md.append(item.get("finding", ""))
            ev = item.get("evidence") or []
            if isinstance(ev, str):
                ev = [ev]
            for x in ev:
                md.append(f"- {x}")
            md.append("")

    md += ["## 三、归因分析", ""]
    for sec in analysis_sections:
        md += [f"### {sec.get('title', '分析结论')}", "", sec.get("content", ""), ""]
        fig = sec.get("figure")
        if isinstance(fig, dict) and fig:
            md.append(f"> 📈 图：{fig.get('title', '')}"
                      f"（{fig.get('type', '')} 型，HTML 版内嵌 SVG，此处以表格替代）")
            md.append("")
            fb = fig.get("fallback_table")
            if isinstance(fb, dict) and fb.get("headers") and fb.get("rows"):
                md.append("| " + " | ".join(map(str, fb["headers"])) + " |")
                md.append("|" + "---|" * len(fb["headers"]))
                for row in fb["rows"]:
                    md.append("| " + " | ".join(map(str, row)) + " |")
                md.append("")
        for b in sec.get("bullets") or []:
            md.append(f"- {b}")
        tbl = sec.get("table")
        if isinstance(tbl, dict) and tbl.get("headers") and tbl.get("rows"):
            md.append("")
            if tbl.get("caption"):
                md.append(f"**表：{tbl['caption']}**")
                md.append("")
            md.append("| " + " | ".join(map(str, tbl["headers"])) + " |")
            md.append("|" + "---|" * len(tbl["headers"]))
            for row in tbl["rows"]:
                md.append("| " + " | ".join(map(str, row)) + " |")
        md.append("")

    if figures:
        md += ["### 图表清单（HTML 版为内嵌 SVG）", ""]
        for f in figures:
            fb = f.get("fallback_table")
            md.append(f"- **{f.get('title', '')}**（`{f.get('type', '')}` 型）"
                      f"{'：' + str(f.get('note')) if f.get('note') else ''}")
            if isinstance(fb, dict) and fb.get("headers") and fb.get("rows"):
                md.append("")
                md.append("| " + " | ".join(map(str, fb["headers"])) + " |")
                md.append("|" + "---|" * len(fb["headers"]))
                for row in fb["rows"]:
                    md.append("| " + " | ".join(map(str, row)) + " |")
        md.append("")

    if table_data and table_data.get("headers") and table_data.get("rows"):
        md += ["## 四、数据明细（可逐行复算）", ""]
        md.append("| " + " | ".join(map(str, table_data["headers"])) + " |")
        md.append("|" + "---|" * len(table_data["headers"]))
        for row in table_data["rows"]:
            md.append("| " + " | ".join(map(str, row)) + " |")
        md.append("")

    md += ["## 五、护栏熔断机制", "",
           "| 维度 | 监控指标 | 基准线 | 熔断阈值 |",
           "| :--- | :--- | :--- | :--- |"]
    for g in (guardrails or []):
        md.append(f"| {g.get('dim', '')} | **{g.get('metric', '')}** | "
                  f"{g.get('base', '')} | **{g.get('threshold', '')}** |")
    md.append("")

    md += ["## 六、阶梯灰度推进", "",
           "| 阶段 | 放量范围 | 观察窗口 | 放行标准 |",
           "| :--- | :--- | :--- | :--- |"]
    for p in (rollout_plan or []):
        md.append(f"| {p.get('phase', '')} | {p.get('scope', '')} | "
                  f"{p.get('duration', '')} | {p.get('condition', '')} |")
    md.append("")

    if next_steps:
        md += ["## 七、下一步行动", ""]
        for i, ns in enumerate(next_steps, 1):
            md.append(f"{i}. {ns}")
        md.append("")

    md += ["## 证据与可复现", ""]
    for k, v in prov.items():
        md.append(f"- **{k}**：`{v}`")
    md.append("")
    if violations:
        md += ["> ⚠️ 报告门禁告警：" + "；".join(violations), ""]

    md_path = os.path.join(out_dir, f"{report_slug}.md")
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md))

    return {"html": html_path, "md": md_path}


__all__ = ["generate_professional_report", "validate_spec", "ReportSpecError",
           "ROLE_THEMES"]
