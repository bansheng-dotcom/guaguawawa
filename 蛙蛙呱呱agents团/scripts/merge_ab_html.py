# -*- coding: utf-8 -*-
"""把 A 层 HTML + B 层 appendix HTML 合并成单文件 HTML（不是只有 PDF）。

A 保留原样式；B 的 CSS 用 .bplus 作用域包住，避免污染 A。
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

W = Path(r"D:\蛙蛙呱呱\workspace")
D = W / "ab_plus"
MAN = json.loads((D / "ab_manifest.json").read_text(encoding="utf-8"))


def extract(doc, tag):
    return re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", doc, re.S | re.I)


def scope_css(css: str) -> str:
    out = []
    for line in css.splitlines():
        s = line.strip()
        if not s or s.startswith("@"):
            out.append(line)
            continue
        if "{" in s:
            sel, rest = s.split("{", 1)
            sels = []
            for x in sel.split(","):
                x = x.strip()
                if not x:
                    continue
                if x == "body":
                    sels.append(".bplus")
                elif x.startswith("."):
                    sels.append(".bplus " + x)
                elif x.startswith("h") or x.startswith("p") or x.startswith("table") or x.startswith("t") or x.startswith("u") or x.startswith("l") or x.startswith("*") or x.startswith("."):
                    sels.append(".bplus " + x)
                else:
                    sels.append(".bplus " + x)
            out.append(", ".join(sels) + "{" + rest)
        else:
            out.append(line)
    return "\n".join(out)


for x in MAN:
    a = (W / x["a_html"]).read_text(encoding="utf-8")
    b = (W / x["b_html"]).read_text(encoding="utf-8")
    a_css = "\n".join(extract(a, "style"))
    b_css = scope_css("\n".join(extract(b, "style")))
    a_body = extract(a, "body")[0]
    b_body = extract(b, "body")[0]
    m = re.search(r"<body([^>]*)>", a, re.I | re.S)
    body_attrs = m.group(1) if m else ""
    out = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{html.escape(x['role'])} · A+B Plus</title>
<style>{a_css}</style>
<style>{b_css}</style>
<style>.ab-nav{{position:sticky;top:0;z-index:99;background:#173f35;color:#fff;padding:10px 18px;font:13px/1.5 -apple-system,Segoe UI,Microsoft YaHei,sans-serif}}
.ab-nav a{{color:#fff;margin-right:16px;text-decoration:none;border-bottom:1px solid rgba(255,255,255,.4)}}
.ab-sep{{page-break-before:always;margin:0}}</style>
</head><body{body_attrs}>
<div class="ab-nav"><b>{html.escape(x['role'])} · A+B Plus</b>　<a href="#a">A 决策层</a><a href="#b">B 证据层</a><span>{html.escape(x['tier'])} · A {x['a_pages']} 页 + B {x['b_pages']} 页</span></div>
<div id="a">{a_body}</div>
<div class="ab-sep"></div>
<div id="b" class="bplus">{b_body}</div>
</body></html>'''
    (D / f"{x['role']}_AB.html").write_text(out, encoding="utf-8")
    print("saved", D / f"{x['role']}_AB.html")
