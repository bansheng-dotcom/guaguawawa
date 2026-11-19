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
.flow-block .head{break-after:avoid}
.flow-cover{position:relative;height:auto;min-height:272mm;padding:0;border-bottom:1pt solid var(--ink);break-after:page;page-break-after:always}
.flow-cover .inner{position:static;inset:auto;padding:0}
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


def flowify(html: str, sources: List[Any] | None = None) -> str:
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
    body = "".join(blocks)
    # 尾页：取 back 的 logo，生成小页脚
    bm = re.search(r'<section class="page back"[^>]*>(.*?)</section>', html, re.S)
    footer = _footer(bm.group(1) if bm else "")
    # 保留被转页面自带的 <style>（kit/pages 主题），否则 flow 只有 FLOW_CSS，版式会塌
    sm = re.search(r"<style>(.*?)</style>", html, re.S)
    base_css = sm.group(1) if sm else ""
    out = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<style>{base_css}{FLOW_CSS}</style></head><body class="flow-all" data-theme="paper">'
           f'<main class="flow-paper">{cover}{body}{footer}</main></body></html>')
    return out


def render_flow(c: Dict[str, Any]) -> str:
    """contract -> flow HTML。"""
    from core.report_theme.pages import render_contract
    return flowify(render_contract(c), c.get("sources"))
