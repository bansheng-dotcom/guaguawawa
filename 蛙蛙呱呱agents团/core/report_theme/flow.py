# -*- coding: utf-8 -*-
"""core.report_theme.flow —— 一条内容流渲染（HTML）+ A4 导出时再分页。

设计：
- HTML 不预设 A4 页，所有 block 连续；
- 封面是 hero，不拆成普通 block；
- 页脚只保留一个小签名；
- PDF 分页交给浏览器/导出器，页码由导出器后处理。

这是“页面是输出容器，不是写作容器”的 core 实现。
"""
from __future__ import annotations

import html as _html
import re
from typing import Any, Dict, List

FLOW_CSS = r"""
@page{size:A4;margin:14mm 16mm}
body.flow-all{background:#E7E5E0}
.flow-paper{width:210mm;margin:8mm auto;background:#fff;padding:18mm 18mm 12mm;
  box-shadow:0 10px 30px rgba(20,31,42,.08)}
.flow-block{width:auto;height:auto;min-height:0;margin:0;padding:0 0 9mm;
  box-shadow:none;page-break-after:auto;break-after:auto;overflow:visible}
.flow-block .rh,.flow-block .rf{display:none}
.flow-block .notes{position:static;margin-top:4mm}
.flow-block .boundary{margin-top:3mm}
.flow-block p{orphans:3;widows:3}
.flow-block .ex{break-inside:avoid}
.flow-block .head{break-after:avoid;page-break-after:avoid}
.sec-lead{break-inside:avoid;page-break-inside:avoid}
.flow-cover{position:relative;height:auto;min-height:272mm;padding:0;border-bottom:1pt solid var(--ink);
  break-after:page;page-break-after:always;display:flex;flex-direction:column}
.flow-cover .inner{position:static;inset:auto;padding:0;flex:1 1 auto;display:flex;flex-direction:column}
.kpi .v{white-space:nowrap}
.flow-break{break-before:page;page-break-before:always;height:0;margin:0;padding:0}
.src-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 7mm;margin-top:3mm}
.src-row{display:flex;gap:2mm;font-size:6.1pt;line-height:1.35;padding:.62mm 0;border-bottom:.3pt solid var(--line)}
.src-row b{color:var(--accent);font-family:var(--serif);min-width:7mm}
.src-row span{flex:1;color:var(--ink2)}
.src-row i{font-style:normal;color:var(--faint);font-size:6.2pt}
.flow-block.appendix{break-before:page;page-break-before:always}
.flow-footer{display:flex;align-items:center;gap:5mm;padding:10mm 0 4mm;
  border-top:1pt solid var(--ink);margin-top:2mm}
.flow-footer img{width:14mm;height:14mm;object-fit:contain;border-radius:2mm;background:#fff}
.flow-footer b{display:block;font-size:10pt;color:var(--ink);letter-spacing:.05em}
.flow-footer span{display:block;font-size:7.4pt;color:var(--muted);margin-top:1mm}
/* 口径页的「问题覆盖」：给人看的一块，不是机器对账表 */
.qcov{margin:5mm 0 4mm;border:.6pt solid var(--line);background:#FBFAF7;padding:4.5mm 6mm 4mm}
.qcov-top{display:flex;align-items:flex-end;justify-content:space-between;gap:6mm}
.qcov-kicker{font-size:7pt;letter-spacing:.2em;color:var(--faint);text-transform:uppercase}
.qcov-num{font-family:var(--serif);color:var(--ink);line-height:1}
.qcov-num b{font-size:26pt;letter-spacing:-.02em}
.qcov-num span{font-size:9pt;color:var(--muted);margin-left:1.6mm}
.qcov-bar{height:1.8mm;background:#E9E6E0;margin:3.2mm 0 0}
.qcov-bar i{display:block;height:100%;background:var(--accent)}
.qcov-sub{font-size:7.6pt;letter-spacing:.08em;color:var(--faint);margin:3.4mm 0 0.6mm}
.qcov-list{list-style:none;margin:0.6mm 0 0;padding:0}
.qcov-list li{display:grid;grid-template-columns:11mm 1fr 46mm;gap:3mm;
  padding:1.7mm 0;border-top:.3pt solid var(--line);align-items:baseline}
.qcov-id{font-family:var(--serif);font-size:9pt;color:var(--accent)}
.qcov-q{font-size:8.8pt;color:var(--ink);line-height:1.5}
.qcov-why{font-size:7.6pt;color:var(--muted);line-height:1.45}
.qcov-ok{margin-top:3mm;font-size:8.6pt;color:var(--ink2)}
.qcov-foot{margin-top:2.6mm;font-size:7.6pt;color:var(--faint)}
@media print{.qcov{break-inside:avoid;page-break-inside:avoid}}
.metalist-list{list-style:none;margin:4mm 0 0;padding:0}
.metalist-list li{position:relative;padding:2.6mm 0 2.6mm 7mm;border-top:.3pt solid var(--line);font-size:10pt;line-height:1.65;color:var(--ink2)}
.metalist-list li:before{content:'';position:absolute;left:0;top:5.1mm;width:3.2mm;height:.9mm;background:var(--accent)}
/* flow 的页码由导出后盖，目录里的估算页码会与实际不符，隐掉 */
.toc-row .pg{display:none}
@media print{
  body.flow-all{background:#fff}
  .flow-paper{width:auto;margin:0;padding:14mm 16mm 10mm;box-shadow:none}
  .flow-block{break-before:auto;page-break-before:auto}
}
@media screen and (max-width:900px){
  body.flow-all{background:#fff}
  .flow-paper{width:100%;margin:0;padding:22px 18px 40px;box-shadow:none}
  .flow-cover{height:auto;min-height:0;padding:0 0 10mm;break-after:auto}
  .flow-cover .inner{position:static;inset:auto;padding:0;display:block}
  .flow-block{width:auto;padding:0 0 8mm}
  .cover .kpis{grid-template-columns:repeat(2,1fr);gap:4mm;margin-top:8mm}
  .sum-grid,.acts,.toc-cols{grid-template-columns:1fr!important}
  .flow-footer{padding:8mm 0 2mm}
}
"""

_SEC = re.compile(r'<section class="page ([^"]+)"(?: id="([^"]*)")?>(.*?)</section>', re.S)
_RH = re.compile(r'<div class="rh">.*?</div>', re.S)
_RF = re.compile(r'<div class="rf">.*?</div>', re.S)
_COVER = re.compile(r'<div class="page cover">(.*?)</div>\s*(?=<section class="page )', re.S)


def _footer(inner: str) -> str:
    from core.report_theme.blocks import footer_html
    img = re.search(r'<img[^>]+>', inner)
    return footer_html(img.group(0) if img else "")


def flowify(html: str, sources: List[Any] | None = None,
            title: str = "", compiled: bool = False) -> str:
    """把 pages.render_contract 的 A4 页 HTML 变成一条 flow。"""
    cover = ""
    # 封面里套了两层 div，正则非贪婪会在内层 </div> 处截断；用切片取到下一个 section 之前
    cs = html.find('<div class="page cover">')
    nxt = html.find('<section class="page ', cs + 1) if cs >= 0 else -1
    if cs >= 0 and nxt > cs:
        inner = html[cs + len('<div class="page cover">'):nxt].rstrip()
        if inner.endswith("</div>"):
            inner = inner[:-len("</div>")]
        cover = ('<div class="cover flow-cover" id="cover">' + inner + "</div>"
                 '<div class="flow-break"></div>')
    blocks = []
    for cls, sid, inner in _SEC.findall(html):
        inner = _RH.sub("", _RF.sub("", inner)).strip()
        if "back" in cls:
            continue
        if "cover" in cls:
            continue
        if sources and "appendix" in cls:
            continue
        blocks.append(f'<section class="flow-block {cls}" id="{sid}">{inner}</section>')
    if sources:
        from core.report_theme.blocks import compact_sources
        blocks.append(compact_sources(sources))
    # 末节必须是「口径与分数」：先排正文与动作，再排附录（记录层），最后放口径节，
    # 自检信息才不挡在结论前，也不会变成末节。
    # 目录里也会出现「口径与分数」链接，按 h2 精确匹配，避免把目录挪到末尾
    cal = next((i for i, b in enumerate(blocks)
                if re.search(r"<h2[^>]*>\s*口径与分数\s*</h2>", b)), -1)
    if cal >= 0:
        cal_block = blocks[cal]
        rest = blocks[:cal] + blocks[cal + 1:]
        apps = [b for b in rest if 'flow-block appendix' in b]
        rest = [b for b in rest if 'flow-block appendix' not in b]
        blocks = rest + apps + ['<div class="flow-break"></div>' + cal_block]
    body = "".join(blocks)
    # 尾页：取 back 的 logo，生成小页脚
    bm = re.search(r'<section class="page back"[^>]*>(.*?)</section>', html, re.S)
    footer = _footer(bm.group(1) if bm else "")
    # 保留被转页面自带的 <style>（kit/pages 主题），否则 flow 只有 FLOW_CSS，版式会塌
    sm = re.search(r"<style>(.*?)</style>", html, re.S)
    base_css = sm.group(1) if sm else ""
    # 来源标记：确定性编译产物带 data-compiled，HTML 门禁据此跳过 F12 结构同构
    compiled_attr = ' data-compiled="cells"' if compiled else ""
    out = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width, initial-scale=1">'
           '<meta name="report-serif-titles" content="allow">'
           f'<title>{_html.escape(title) if title else "报告"}</title>'
           f'<style>{base_css}{FLOW_CSS}</style></head>'
           f'<body class="flow-all" data-theme="paper"{compiled_attr}>'
           f'<main class="flow-paper">{cover}{body}{footer}</main></body></html>')
    return out


def render_flow(c: Dict[str, Any]) -> str:
    """contract -> flow HTML。"""
    from core.report_theme.pages import render_contract
    lines = c.get("title_lines") or []
    title = str(lines[0]) if lines else str(c.get("short_title") or "")
    # 附录已由 pages.render_contract 收成一页（支撑判断+来源+口径），
    # 这里不再传 sources，否则 flowify 会把附录页丢掉、再拼一个纯来源页。
    return flowify(render_contract(c), [], title=title,
                   compiled=bool(c.get("machine_compiled")))
