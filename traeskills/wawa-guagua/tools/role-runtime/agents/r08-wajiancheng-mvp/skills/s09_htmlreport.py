# -*- coding: utf-8 -*-
"""S09 单文件 HTML 报告（自有实现）。

  plan  结构门禁：章节 ≥3、每章有摘要、论点 ≥3、来源 ≥3
  html  渲染：单文件、内联样式、目录、引用上标、来源表、打印样式

不依赖任何外部图表库或模板；需要图表时由 R06 产出静态 SVG 再嵌入。
"""
from __future__ import annotations

import html
import os
from typing import Any, Dict, List

from . import _common as c

NAME = "htmlreport"
DESC = "单文件 HTML 报告：plan/html"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    pl = act.add_parser("plan", help="校验报告结构")
    pl.add_argument("--input", required=True)
    ht = act.add_parser("html", help="渲染单文件 HTML")
    ht.add_argument("--input", required=True)
    ht.add_argument("--out", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "plan":
        return _validate(data)
    return _render(data, args.out)


def _validate(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    checks.append(_ck(bool(str(data.get("title", "")).strip()), "报告标题非空", "report.title"))
    meta = data.get("meta") or {}
    checks.append(_ck(all(str(meta.get(k, "")).strip() for k in ("audience", "purpose")),
                      "meta 含 audience 与 purpose", "report.meta"))

    chapters = data.get("chapters") or []
    checks.append(_ck(len(chapters) >= 3, f"章节 ≥3（实际 {len(chapters)}）", "report.chapters"))
    for i, ch in enumerate(chapters):
        ok_ch = isinstance(ch, dict) and bool(str(ch.get("title", "")).strip()) \
            and bool(str(ch.get("summary", "")).strip())
        checks.append(_ck(ok_ch, f"第 {i + 1} 章有标题与摘要", "report.chapter"))

    thesis = data.get("thesis") or []
    checks.append(_ck(len(thesis) >= 3, f"核心论点 ≥3（实际 {len(thesis)}）", "report.thesis"))
    sources = data.get("sources") or []
    checks.append(_ck(len(sources) >= 3, f"来源 ≥3（实际 {len(sources)}）", "report.sources"))
    for i, s in enumerate(sources):
        ok_s = isinstance(s, dict) and bool(str(s.get("label", "")).strip())
        checks.append(_ck(ok_s, f"来源[{i}] 有 label", "report.source.label"))
    ok = all(c["ok"] for c in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    chapter_count=len(chapters), source_count=len(sources),
                    next="结构通过，可渲染 html" if ok else "按 checks 补齐")


def _render(data: Any, out_path: str) -> Dict[str, Any]:
    gate = _validate(data)
    if not gate.get("ok"):
        gate["next"] = "结构未过门禁，先修 plan"
        return gate
    title = html.escape(str(data["title"]))
    meta = data.get("meta") or {}
    chapters = data.get("chapters") or []
    sources = data.get("sources") or []

    toc = "".join(f'<li><a href="#ch{i}">{html.escape(str(ch["title"]))}</a></li>'
                  for i, ch in enumerate(chapters, 1))
    body = []
    for i, ch in enumerate(chapters, 1):
        paras = [p for p in (ch.get("paragraphs") or []) if str(p).strip()]
        cites = [f'<sup>[{n}]</sup>' for n in (ch.get("cites") or [])]
        body.append(f'<section id="ch{i}"><h2>{i}. {html.escape(str(ch["title"]))}</h2>'
                    f'<p class="summary">{html.escape(str(ch["summary"]))}</p>')
        for p, cite in zip(paras, cites + [""] * len(paras)):
            body.append(f"<p>{html.escape(str(p))}{cite}</p>")
        if ch.get("svg"):
            body.append(f'<figure>{ch["svg"]}</figure>')
        body.append("</section>")
    thesis = "".join(f"<li>{html.escape(str(t))}</li>" for t in data.get("thesis") or [])
    src_rows = "".join(
        f'<tr><td>[{i}]</td><td>{html.escape(str(s["label"]))}</td>'
        f'<td>{html.escape(str(s.get("url", "—")))}</td></tr>'
        for i, s in enumerate(sources, 1))

    doc = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --accent:#0f172a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: system-ui,-apple-system,"Segoe UI","PingFang SC",sans-serif;
       color:var(--ink); line-height:1.75; }}
header {{ padding:64px 8vw 32px; border-bottom:1px solid var(--line); }}
h1 {{ margin:0 0 12px; font-size:clamp(26px,4vw,44px); line-height:1.2; }}
.meta {{ color:var(--muted); font-size:14px; }}
main {{ display:grid; grid-template-columns:240px 1fr; gap:48px; padding:40px 8vw 80px; }}
nav {{ position:sticky; top:32px; align-self:start; font-size:14px; }}
nav ul {{ list-style:none; padding:0; margin:0; }}
nav li {{ margin:8px 0; }}
nav a {{ color:var(--muted); text-decoration:none; }}
section {{ margin-bottom:56px; scroll-margin-top:24px; }}
h2 {{ font-size:24px; margin:0 0 8px; }}
.summary {{ color:var(--muted); margin-top:0; }}
sup {{ color:var(--accent); font-size:11px; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
td, th {{ border-bottom:1px solid var(--line); padding:8px 6px; text-align:left; }}
figure {{ margin:16px 0; }}
@media (max-width:820px) {{ main {{ grid-template-columns:1fr; }} nav {{ display:none; }} }}
@media print {{ nav {{ display:none; }} main {{ grid-template-columns:1fr; padding:0 8vw; }}
  section {{ page-break-inside:avoid; }} }}
</style></head>
<body>
<header><h1>{title}</h1>
<p class="meta">受众：{html.escape(str(meta.get("audience", "—")))}　目的：{html.escape(str(meta.get("purpose", "—")))}</p>
{('<ul class="thesis">' + thesis + '</ul>') if thesis else ''}</header>
<main>
<nav><ul>{toc}</ul></nav>
<div>{''.join(body)}
<h2>来源</h2><table><tbody>{src_rows}</tbody></table></div>
</main></body></html>
"""
    d = os.path.dirname(os.path.abspath(out_path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    return c.result(list(gate["checks"]) + [
        _ck("<!doctype html>" in doc, "单文件 HTML", "report.html"),
        _ck("http://" not in doc and "https://" not in doc, "无外部资源引用", "report.offline"),
        _ck("@media print" in doc, "含打印样式", "report.print")],
        ok=True, verdict="PASS", out=out_path, size_bytes=os.path.getsize(out_path),
        chapter_count=len(chapters), source_count=len(sources),
        next="可直接交付或打印为 PDF")
