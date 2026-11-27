# -*- coding: utf-8 -*-
"""确定性 HTML 渲染：把工作流包渲染为可独立阅读的单文件页面。

只做版式，不改内容；用于黄金样本与人工对照。
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Tuple

from . import common as c

_CSS = """
:root{--ink:#1f2328;--muted:#656d76;--line:#d8dee4;--ok:#1a7f37;--bad:#cf222e;--bg:#f6f8fa}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);
font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
header{padding:40px 48px 24px;border-bottom:1px solid var(--line);background:var(--bg)}
h1{margin:0 0 6px;font-size:28px}h2{margin:0;font-size:20px}
.sub{color:var(--muted);font-size:14px}
main{padding:8px 48px 56px;max-width:1080px}
section{margin:32px 0;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.sec-head{display:flex;align-items:center;justify-content:space-between;gap:16px;
padding:16px 20px;background:var(--bg);border-bottom:1px solid var(--line)}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;
font-weight:600;color:#fff}.badge.ok{background:var(--ok)}.badge.bad{background:var(--bad)}
.badge.warn{background:#9a6700}.body{padding:18px 20px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}
pre{margin:14px 0 0;padding:14px;background:var(--bg);border:1px solid var(--line);
border-radius:8px;overflow:auto;font-size:12px;line-height:1.5}
details{margin-top:12px}summary{cursor:pointer;color:var(--muted);font-size:13px}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
footer{padding:24px 48px;color:var(--muted);font-size:12px;border-top:1px solid var(--line)}
"""


def _badge(gate: Dict[str, Any]) -> str:
    grade = str((gate or {}).get("grade") or "")
    cls = "ok" if grade == "PASS" else ("warn" if grade == "WARN" else "bad")
    return f'<span class="badge {cls}">{html.escape(grade or "UNKNOWN")}</span>'


def _checks_table(gate: Dict[str, Any]) -> str:
    checks = (gate or {}).get("checks") or []
    rows = []
    for item in checks:
        ok = bool(item.get("ok"))
        rows.append(
            "<tr><td>{}</td><td><code>{}</code></td><td>{}</td></tr>".format(
                "PASS" if ok else "FAIL",
                html.escape(str(item.get("dim") or "")),
                html.escape(str(item.get("msg") or ""))))
    return ("<table><thead><tr><th>结果</th><th>门禁维度</th><th>说明</th></tr>"
            "</thead><tbody>" + "".join(rows) + "</tbody></table>")


def render_packs_html(title: str, subtitle: str,
                      packs: List[Tuple[str, Dict[str, Any]]]) -> str:
    blocks: List[str] = []
    for name, pack in packs:
        gate = pack.get("gate") or {}
        body = json.dumps(pack, ensure_ascii=False, indent=2)
        blocks.append(
            f"""<section>
  <div class="sec-head"><div><h2>{html.escape(str(pack.get('artifact') or name))}</h2>
  <div class="sub">{html.escape(name)} · stage={html.escape(str(pack.get('stage') or ''))}</div></div>
  {_badge(gate)}</div>
  <div class="body">{_checks_table(gate)}
  <details><summary>展开工件 JSON</summary><pre>{html.escape(body)}</pre></details>
  </div>
</section>""")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{_CSS}</style></head>
<body><header><h1>{html.escape(title)}</h1><div class="sub">{html.escape(subtitle)}</div></header>
<main>{''.join(blocks)}</main>
<footer>R07 蛙得明 · 产品工作流黄金样本 · 由 pm_workflows 确定性渲染（无时间戳，可复算）</footer>
</body></html>
"""


def write_html(path: str, title: str, subtitle: str,
               packs: List[Tuple[str, Dict[str, Any]]]) -> str:
    return c.write_text(path, render_packs_html(title, subtitle, packs))
