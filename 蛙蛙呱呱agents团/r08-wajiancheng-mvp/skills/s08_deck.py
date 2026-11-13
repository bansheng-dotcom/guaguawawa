# -*- coding: utf-8 -*-
"""S13 单文件 HTML 幻灯片（自有实现）。

把汇报大纲变成可放映的单文件 deck：
  plan  结构门禁：6–30 页、每页一个观点、标题 ≤20 字且不重复、封面/结论/行动页齐全
  html  渲染：内联样式、无外部 JS 库、自带打印样式，输出单个 .html 文件

设计原则：内容由用户/上游给，版式由确定性模板保证；不依赖任何第三方服务。
"""
from __future__ import annotations

import html
import os
from typing import Any, Dict, List

from . import _common as c

NAME = "deck"
DESC = "单文件 HTML 幻灯片：plan/html"

MIN_SLIDES, MAX_SLIDES = 6, 30
TITLE_MAX = 20


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    pl = act.add_parser("plan", help="校验 deck 大纲")
    pl.add_argument("--input", required=True)
    ht = act.add_parser("html", help="渲染单文件 HTML deck")
    ht.add_argument("--input", required=True)
    ht.add_argument("--out", required=True)
    ht.add_argument("--accent", default="#0F172A", help="主色（十六进制）")


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "plan":
        return _validate(data)
    if args.action == "html":
        return _render(data, args.out, args.accent)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _slides(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    slides = data.get("slides") if isinstance(data, dict) else None
    return [s for s in slides if isinstance(s, dict)] if isinstance(slides, list) else []


def _validate(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    slides = _slides(data)
    checks.append(_ck(MIN_SLIDES <= len(slides) <= MAX_SLIDES,
                      f"页数 {MIN_SLIDES}–{MAX_SLIDES}（实际 {len(slides)}）", "deck.count"))
    checks.append(_ck(bool(str(data.get("title", "")).strip()), "deck 标题非空", "deck.title"))

    titles = []
    for i, s in enumerate(slides):
        title = str(s.get("title", "")).strip()
        message = str(s.get("message", "")).strip()
        checks.append(_ck(bool(title), f"第 {i + 1} 页 title 非空", "deck.slide.title"))
        checks.append(_ck(len(title) <= TITLE_MAX,
                          f"第 {i + 1} 页标题 ≤{TITLE_MAX} 字（{len(title)}）", "deck.slide.title_len"))
        checks.append(_ck(bool(message), f"第 {i + 1} 页 message 非空（一页一个观点）",
                          "deck.slide.message"))
        if title:
            titles.append(title)
    dup = sorted({t for t in titles if titles.count(t) > 1})
    checks.append(_ck(not dup, f"页标题不重复（重复：{dup or '无'}）", "deck.slide.unique"))

    if slides:
        checks.append(_ck(bool(slides[0].get("is_cover")),
                          "首页是封面（is_cover=true）", "deck.cover"))
        checks.append(_ck(bool(slides[-1].get("is_closing")),
                          "末页是行动/结论页（is_closing=true）", "deck.closing"))
        bullets = sum(len(s.get("bullets") or []) for s in slides)
        checks.append(_ck(bullets <= 90, f"要点总数 ≤90（实际 {bullets}）", "deck.bullets"))
    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    slide_count=len(slides),
                    next="结构通过，可渲染 html" if ok else "按 checks 调整大纲")


def _render(data: Any, out_path: str, accent: str) -> Dict[str, Any]:
    gate = _validate(data)
    if not gate.get("ok"):
        gate["next"] = "大纲未过门禁，先修 plan 再渲染"
        return gate
    slides = _slides(data)
    title = html.escape(str(data.get("title", "")).strip())
    subtitle = html.escape(str(data.get("subtitle", "") or "").strip())

    blocks = []
    for i, s in enumerate(slides):
        st = html.escape(str(s.get("title", "")).strip())
        msg = html.escape(str(s.get("message", "")).strip())
        bullets = [html.escape(str(b)) for b in (s.get("bullets") or []) if str(b).strip()]
        cls = "slide cover" if s.get("is_cover") else "slide"
        parts = [f'<section class="{cls}">', f"<h2>{st}</h2>", f'<p class="lead">{msg}</p>']
        if bullets:
            parts.append("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>")
        parts.append(f'<span class="pn">{i + 1} / {len(slides)}</span>')
        parts.append("</section>")
        blocks.append("\n".join(parts))

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --accent: {html.escape(accent)}; --ink: #0f172a; --muted: #64748b; --bg: #f8fafc; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: system-ui, -apple-system, "Segoe UI", "PingFang SC", sans-serif;
        background: var(--bg); color: var(--ink); }}
.slide {{ min-height: 100vh; padding: 8vh 10vw; display: flex; flex-direction: column;
          justify-content: center; border-bottom: 1px solid #e2e8f0; position: relative; }}
.slide.cover {{ background: var(--accent); color: #f8fafc; }}
h1, h2 {{ margin: 0 0 .6em; line-height: 1.15; letter-spacing: -.01em; }}
h1 {{ font-size: clamp(28px, 5vw, 56px); }}
h2 {{ font-size: clamp(22px, 3.6vw, 40px); }}
.lead {{ font-size: clamp(16px, 2vw, 22px); color: var(--muted); margin: 0 0 1.2em; max-width: 46em; }}
.cover .lead {{ color: #cbd5e1; }}
ul {{ margin: 0; padding-left: 1.2em; font-size: clamp(15px, 1.6vw, 19px); line-height: 1.8; }}
.pn {{ position: absolute; right: 10vw; bottom: 4vh; font-size: 12px; color: var(--muted); }}
.cover .pn {{ color: #cbd5e1; }}
@media print {{ .slide {{ min-height: 100vh; page-break-after: always; }} }}
</style>
</head>
<body>
<h1 class="deck-title" style="padding:4vh 10vw 0;font-size:20px;color:var(--muted)">{title}</h1>
{subtitle}
{''.join(blocks)}
</body>
</html>
"""
    d = os.path.dirname(os.path.abspath(out_path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    checks = list(gate["checks"]) + [
        _ck("<!doctype html>" in doc, "单文件 HTML（含 doctype）", "deck.html.doctype"),
        _ck("http://" not in doc and "https://" not in doc, "无外部资源引用", "deck.html.offline"),
        _ck("page-break-after" in doc, "含打印分页样式", "deck.html.print"),
    ]
    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    out=out_path, size_bytes=os.path.getsize(out_path),
                    slide_count=len(slides),
                    next="浏览器直接打开即可放映；打印可导出 PDF")
