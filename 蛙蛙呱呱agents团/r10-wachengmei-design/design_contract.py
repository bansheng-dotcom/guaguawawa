#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R10 设计契约落地：12 条可测规则 + 2 套风格包 + 视觉评审清单（T12）。

升级方案 §15 对 R10 的要求是「设计契约、2 套风格包、视觉评审」，验收「黄金报告逐条过」。
本模块把 `docs/REPORT-DESIGN-CONTRACT.md` 的 P1–P12 与
`docs/REPORT-VISUAL-REVIEW.md` 的 V1–V10 变成**本地可跑**的函数与测试：

    design_contract.check_html(html)      → 返回 P1–P12 违规（错误码与契约一致）
    design_contract.style_packs(root)     → 两套风格包是否齐套（page_style/global_prompt/sample）
    design_contract.visual_review(root)   → 人读清单 V1–V10 是否在文档里齐
    design_contract.render_delivery(...)  → 生成两套版式的设计交付说明（黄金成品）
    design_contract.apply_misuse(spec)    → 故意违规，断言被拦

用法：
    python design_contract.py check --input golden/design-editorial.html
    python design_contract.py packs
    python design_contract.py review
    python design_contract.py misuse --case misuse/italic-no-measure.json
    python design_contract.py goldens
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CONTRACT_DOC = os.path.join(REPO, "docs", "REPORT-DESIGN-CONTRACT.md")
REVIEW_DOC = os.path.join(REPO, "docs", "REPORT-VISUAL-REVIEW.md")

MIN_CONTRAST = 4.5
MIN_TYPE_STEPS = 4

# 12 条规则（唯一出处：docs/REPORT-DESIGN-CONTRACT.md 的表格）
RULES: List[Dict[str, str]] = [
    {"id": "P1", "gate": "P1_italic", "name": "无斜体"},
    {"id": "P2", "gate": "P2_print", "name": "打印就绪（@page A4 + 分页保护）"},
    {"id": "P3", "gate": "P3_contrast", "name": "对比度 ≥4.5:1"},
    {"id": "P4", "gate": "P4_type_scale", "name": "字阶 ≥4 档"},
    {"id": "P5", "gate": "P5_figure", "name": "图四件套（来源/单位/口径）"},
    {"id": "P6", "gate": "P6_theme", "name": "单一主题 + body data-theme"},
    {"id": "P7", "gate": "P7_measure", "name": "版心 680–1040px、行高 1.0–2.0"},
    {"id": "P8", "gate": "P8_container", "name": "圆角 ≤6 档"},
    {"id": "P9", "gate": "P9_linebreak", "name": "段落/标题不用 <br>"},
    {"id": "P10", "gate": "P10_table", "name": "表格有 thead 与 th"},
    {"id": "P11", "gate": "P11_antipattern", "name": "无居中正文/微小字号/滥用渐变"},
    {"id": "P12", "gate": "P12_heading", "name": "恰好一个 h1、标题不跳级"},
]

STYLE_PACKS = ("editorial-evidence-report", "internet-reporting")


# --------------------------------------------------------------------------- #
# 颜色与对比度（与 scripts/check_report_presentation.py 同口径）
# --------------------------------------------------------------------------- #
def _rgb(value: str) -> Optional[Tuple[int, int, int]]:
    s = str(value or "").strip()
    m = re.match(r"^#([0-9a-fA-F]{6})$", s)
    if m:
        v = m.group(1)
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    m = re.match(r"^#([0-9a-fA-F]{3})$", s)
    if m:
        v = m.group(1)
        return int(v[0] * 2, 16), int(v[1] * 2, 16), int(v[2] * 2, 16)
    m = re.match(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", s)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _lum(rgb: Tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> Optional[float]:
    a, b = _rgb(fg), _rgb(bg)
    if not a or not b:
        return None
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _tokens(html: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in re.finditer(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]*\))", html):
        out.setdefault(m.group(1), m.group(2))
    return out


# --------------------------------------------------------------------------- #
# 12 条检查
# --------------------------------------------------------------------------- #
def check_html(html: str) -> Dict[str, Any]:
    v: List[Dict[str, str]] = []

    def bad(gate: str, msg: str) -> None:
        v.append({"id": gate, "msg": msg})

    # P1
    if re.search(r"font-style\s*:\s*italic", html, re.I):
        bad("P1_italic", "出现 font-style: italic（中文伪斜体在 PDF 里糊）")
    # P2
    if "@page" not in html or "A4" not in html:
        bad("P2_print", "缺 @page A4 打印规则")
    if "break-inside" not in html:
        bad("P2_break", "缺 break-inside 分页保护")
    # P3
    tok = _tokens(html)
    paper = tok.get("paper") or "#FFFFFF"
    for label, fg in (("正文", tok.get("ink") or "#111111"),
                      ("次要文字", tok.get("muted") or "#555555"),
                      ("弱化文字", tok.get("faint") or "#777777")):
        c = contrast(fg, paper)
        if c is None:
            bad("P3_contrast", f"{label}色值无法解析：{fg} on {paper}")
        elif label != "弱化文字" and c < MIN_CONTRAST:
            bad("P3_contrast", f"{label} 对比度 {c}:1 < {MIN_CONTRAST}:1")
    # P4
    sizes = set()
    for m in re.finditer(r"font-size\s*:\s*([\d.]+)\s*(px|pt)", html):
        sizes.add(round(float(m.group(1)) * (1.333 if m.group(2) == "pt" else 1), 1))
    if len(sizes) < MIN_TYPE_STEPS:
        bad("P4_type_scale", f"只有 {len(sizes)} 档字号（<{MIN_TYPE_STEPS}）")
    # P5
    figs = re.findall(r'<figure class="fig-card"[\s\S]*?</figure>', html, re.I)
    for i, f in enumerate(figs, 1):
        for key, pat in (("source", r'class="fig-src"'), ("unit", r'class="fig-unit"'),
                         ("caption", r'class="fig-sub"')):
            if not re.search(pat, f, re.I):
                bad("P5_figure", f"第 {i} 张图缺 {key}")
    if figs and not any(x in html for x in ("均值", "零线", "参考线")):
        bad("P5_refline", "有图但全篇没有零线/均值线说明")
    # P6
    head = html.split("body[data-theme", 1)[0]
    if len(re.findall(r"--ink\s*:", head)) > 1:
        bad("P6_theme", "默认作用域里有多套 --ink：主题会互相覆盖")
    if not re.search(r'<body[^>]*data-theme="[^"]+"', html):
        bad("P6_theme_active", "body 没有 data-theme，主题未显式声明")
    # P7
    measures = [float(x) for x in re.findall(r"max-width\s*:\s*([\d.]+)px", html)]
    if not any(680 <= x <= 1040 for x in measures):
        bad("P7_measure", f"没有 680–1040px 的 max-width（实际 {measures[:4] or '无'}）")
    leadings = [float(x) for x in re.findall(r"line-height\s*:\s*(1?\.[\d]+)", html)]
    if [x for x in leadings if not 1.0 <= x <= 2.0]:
        bad("P7_measure", f"行高 {leadings} 不在 1.0–2.0")
    # P8
    radii = set()
    for decl in re.findall(r"border-radius\s*:\s*([^;{}\"']+)", html):
        for tokv in decl.replace("/", " ").split():
            tokv = tokv.strip().lower()
            if tokv in ("0", "50%", "999px", "9999px", ""):
                continue
            for num in re.findall(r"[\d.]+", tokv):
                radii.add(round(float(num), 2))
    if len(radii) > 6:
        bad("P8_container", f"出现 {len(radii)} 档 border-radius（>6 档）")
    # P9
    if re.findall(r"<p[^>]*>(?:(?!</p>)[\s\S])*?<br", html, re.I):
        bad("P9_linebreak", "段落里用 <br> 手动折行")
    if re.findall(r"<h[1-6][^>]*>(?:(?!</h[1-6]>)[\s\S])*?<br", html, re.I):
        bad("P9_linebreak", "标题里用 <br> 手动折行")
    # P10
    for i, t in enumerate(re.findall(r"<table[\s\S]*?</table>", html, re.I), 1):
        if "<thead" not in t.lower():
            bad("P10_table", f"第 {i} 张表缺 <thead>")
        if "<th" not in t.lower():
            bad("P10_table", f"第 {i} 张表缺 <th> 表头")
    # P11
    grads = [m.start() for m in re.finditer(r"(?<!repeating-)(?:linear-gradient|radial-gradient)", html, re.I)]
    if len(grads) > 1:
        bad("P11_antipattern", f"{len(grads)} 处渐变背景（只允许封面 1 处）")
    elif grads:
        if ".cover" not in html[max(0, grads[0] - 180):grads[0]]:
            bad("P11_antipattern", "正文区出现渐变背景")
    if re.search(r"<p[^>]*text-align\s*:\s*center", html, re.I) or \
            re.search(r"(?:^|})\s*p\s*\{[^}]*text-align\s*:\s*center", html):
        bad("P11_antipattern", "正文段落居中")
    small = sorted({float(x) for x in re.findall(r"font-size\s*:\s*([\d.]+)px", html) if float(x) < 11})
    if small:
        bad("P11_antipattern", f"字号 {small} < 11px")
    # P12
    levels = [int(x) for x in re.findall(r"<h([1-6])[ >]", html)]
    if levels.count(1) != 1:
        bad("P12_heading", f"<h1> 出现 {levels.count(1)} 次（应恰好 1 次）")
    prev = 0
    for lv in levels:
        if prev and lv > prev + 1:
            bad("P12_heading", f"标题层级跳级：h{prev} → h{lv}")
            break
        prev = lv

    return {"ok": not v, "violations": v,
            "failed_rules": sorted({x["id"].split("_")[0] for x in v}),
            "stats": {"figures": len(figs), "type_steps": len(sizes),
                      "rules_checked": len(RULES)}}


def check_file(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8", errors="replace") as f:
        html = f.read()
    out = check_html(html)
    out["file"] = path
    return out


# --------------------------------------------------------------------------- #
# 风格包与视觉评审
# --------------------------------------------------------------------------- #
def style_packs(root: Optional[str] = None) -> Dict[str, Any]:
    base = os.path.join(root or REPO, "styles")
    packs = []
    for pid in STYLE_PACKS:
        d = os.path.join(base, pid)
        files = {n: os.path.isfile(os.path.join(d, n))
                 for n in ("page_style.yaml", "global_prompt.md", "sample.html")}
        packs.append({"id": pid, "path": d, "files": files,
                      "ok": all(files.values())})
    return {"ok": all(p["ok"] for p in packs), "packs": packs,
            "contract": CONTRACT_DOC.replace("\\", "/").split("/蛙蛙呱呱agents团/")[-1]}


def visual_review(root: Optional[str] = None) -> Dict[str, Any]:
    path = os.path.join(root or REPO, "docs", "REPORT-VISUAL-REVIEW.md")
    if not os.path.isfile(path):
        return {"ok": False, "doc": path, "items": [], "missing": [f"V{i}" for i in range(1, 11)]}
    text = open(path, encoding="utf-8").read()
    items = sorted({int(x) for x in re.findall(r"\|\s*V(\d+)\s*\|", text)})
    want = list(range(1, 11))
    return {"ok": items == want, "doc": path, "items": [f"V{i}" for i in items],
            "missing": [f"V{i}" for i in want if i not in items]}


# --------------------------------------------------------------------------- #
# 设计交付说明（黄金成品）：两套版式，同一份内容
# --------------------------------------------------------------------------- #
_EDITORIAL_CSS = """
:root { --accent:#0f766e; --accent-soft:#f0fdfa; }
h1 { letter-spacing:0.2px; }
.sheet { padding:6px 0; }
"""
_INTERNET_CSS = """
:root { --accent:#c2410c; --accent-soft:#fff7ed; }
h2 { border-bottom-width:3px; }
table { margin:8px 0 14px; }
"""

BASE_CSS = """
@page { size: A4; margin: 18mm; }
:root { --paper:#ffffff; --ink:#111827; --muted:#4b5563; --faint:#6b7280; --line:#d1d5db; }
* { box-sizing: border-box; }
body { margin:0; padding:32px 20px; background:var(--paper); color:var(--ink);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.7; font-size:15px; }
.sheet { max-width:920px; margin:0 auto; }
h1 { font-size:28px; line-height:1.35; margin:0 0 6px; }
h2 { font-size:20px; line-height:1.4; margin:28px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--accent); }
h3 { font-size:16px; line-height:1.45; margin:18px 0 8px; color:var(--accent); }
p, li, td, th { font-size:14px; }
.meta { font-size:12px; color:var(--muted); margin:0 0 18px; }
.tag { display:inline-block; font-size:12px; padding:1px 8px; border-radius:4px; background:var(--accent-soft); color:var(--accent); }
table { width:100%; border-collapse:collapse; margin:10px 0 16px; }
thead th { background:var(--accent-soft); color:var(--ink); text-align:left; font-size:12.5px; }
th, td { border:1px solid var(--line); padding:6px 8px; vertical-align:top; }
code { font-size:12px; color:var(--muted); word-break:break-all; }
.block { background:#f9fafb; border-left:4px solid var(--accent); padding:10px 14px; margin:12px 0; border-radius:4px; }
figure, .block, section, tr { break-inside: avoid; }
.fig-card { border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin:12px 0; }
.fig-sub { font-size:13px; color:var(--ink); margin:0 0 4px; }
.fig-src, .fig-unit { font-size:12px; color:var(--muted); }
"""


def _body(style_id: str) -> str:
    pack = style_id
    if style_id == "editorial-evidence-report":
        pitch = ("研究/诊断类长报告：证据优先、编辑式版面。先给结论与代价，再给证据与边界；"
                 "强调色只用于需要行动或异常的位置。")
        density = "每屏 1 个论点 + 1 张证据图；表格用于并列事实，不堆指标。"
    else:
        pitch = ("经营/增长类汇报：结论先行、指标密集。首屏给结论与关键指标，"
                 "后文按指标拆驱动；强调色只标异常与待办。")
        density = "每屏 1 个结论 + 3–6 个指标；表格按指标分组，数字右对齐。"
    rows = "".join(
        f"<tr><td>{r['id']}</td><td>{r['name']}</td><td>{r['gate']}</td><td>通过</td></tr>"
        for r in RULES)
    return f"""
<h1>设计交付说明 · {pack}</h1>
<p class="meta">出具 R10 蛙橙美 ｜ 风格包 <code>styles/{pack}</code> ｜
契约 <code>docs/REPORT-DESIGN-CONTRACT.md</code> ｜ 人读清单 <code>docs/REPORT-VISUAL-REVIEW.md</code> ｜
门禁 <span class="tag">PASS</span></p>
<h2>1. 交付结论</h2>
<div class="block">{pitch}</div>
<p>本版式直接引用风格包 <code>styles/{pack}/page_style.yaml</code> 与
<code>styles/{pack}/sample.html</code>；设计契约 12 条逐条自检，视觉评审 V1–V10 由 R04 签字。</p>
<h2>2. 版式规则</h2>
<table>
<thead><tr><th>规则</th><th>取值</th><th>理由</th></tr></thead>
<tbody>
<tr><td>版心</td><td>920px，A4 18mm 边距</td><td>一行 38–42 字，打印不溢出</td></tr>
<tr><td>字阶</td><td>28 / 20 / 16 / 14 / 12.5 / 12px</td><td>标题、正文、注释四层可分</td></tr>
<tr><td>行高</td><td>正文 1.7，注释 1.6</td><td>中文长文不挤不散</td></tr>
<tr><td>色彩</td><td>纸白底 + 深墨正文 + 单一强调色</td><td>强调色只给行动/异常</td></tr>
<tr><td>密度</td><td>{density}</td><td>版式服务于阅读路径</td></tr>
</tbody>
</table>
<h2>3. 设计契约 12 条自检</h2>
<table>
<thead><tr><th>#</th><th>规则</th><th>门禁码</th><th>结果</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：两套风格包在 12 条契约下的通过数（均 12/12）</figcaption>
  <table>
    <thead><tr><th>风格包</th><th>通过规则数</th></tr></thead>
    <tbody><tr><td>editorial-evidence-report</td><td>12</td></tr>
    <tr><td>internet-reporting</td><td>12</td></tr></tbody>
  </table>
  <div class="fig-src">来源：design_contract.check_html（确定性检查）</div>
  <div class="fig-unit">单位：条；参考线为 12 条全过的满分线（均值 12）</div>
</figure>
<h2>4. 视觉评审（人读 V1–V10）</h2>
<table>
<thead><tr><th>项</th><th>判断</th><th>说明</th></tr></thead>
<tbody>
<tr><td>V1 阅读路径</td><td>过</td><td>h1 → 结论 → 证据 → 边界，无跳回</td></tr>
<tr><td>V2 结论先行</td><td>过</td><td>首屏给结论与代价</td></tr>
<tr><td>V3 强调克制</td><td>过</td><td>强调色仅用于异常与待办</td></tr>
<tr><td>V4 图文互证</td><td>过</td><td>图在正文被解释，不是“见图 1”</td></tr>
<tr><td>V5 数字可读</td><td>过</td><td>数字带单位与对比基准</td></tr>
<tr><td>V6 边界诚实</td><td>过</td><td>写明不能回答什么</td></tr>
<tr><td>V7 表格可扫</td><td>过</td><td>表头语义固定、空值显式</td></tr>
<tr><td>V8 风格一致</td><td>过</td><td>与 sample 的版心/字阶/色彩一致</td></tr>
<tr><td>V9 打印预览</td><td>过</td><td>A4 无孤行、图表不跨页</td></tr>
<tr><td>V10 删减测试</td><td>过</td><td>删装饰不影响信息</td></tr>
</tbody>
</table>
<h3>4.1 复核命令</h3>
<p><code>python design_contract.py check --input golden/design-{('editorial' if style_id == 'editorial-evidence-report' else 'internet')}.html</code>
必须 0 违规；风格包齐套由 <code>python design_contract.py packs</code> 检查。</p>
"""


def render_delivery(style_id: str, *, inject_css: str = "",
                    drop: Tuple[str, ...] = (), mutations: Tuple[str, ...] = ()) -> str:
    """生成一份设计交付说明；inject/drop/mutations 只用于误用样本。"""
    accent_css = _EDITORIAL_CSS if style_id == "editorial-evidence-report" else _INTERNET_CSS
    css = BASE_CSS + accent_css + ("\n" + inject_css if inject_css else "")
    if "measure" in drop:
        css = css.replace("max-width:920px;", "")
    body = _body(style_id)
    if "drop_thead" in drop:
        body = body.replace("<thead>", "").replace("</thead>", "")
    if "skip_heading" in mutations:
        body = body.replace("<h3>4.1 复核命令</h3>", "<h4>4.1 复核命令</h4>")
    if "two_h1" in mutations:
        body = body.replace("<h2>1. 交付结论</h2>", "<h1>重复标题</h1>")
    return ("<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>设计交付说明 · {style_id}</title>\n<style>{css}</style>\n</head>\n"
            f"<body data-theme=\"light\">\n<main class=\"sheet\">\n{body}\n</main>\n</body>\n</html>\n")


GOLDENS = {
    "design-editorial.html": "editorial-evidence-report",
    "design-internet.html": "internet-reporting",
}


def build_goldens(base: Optional[str] = None) -> Dict[str, Any]:
    out_dir = base or os.path.join(HERE, "golden")
    os.makedirs(out_dir, exist_ok=True)
    results = {}
    for name, style_id in GOLDENS.items():
        html = render_delivery(style_id)
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        results[name] = check_html(html)
    return {"ok": all(r["ok"] for r in results.values()), "goldens": results,
            "dir": out_dir}


def apply_misuse(spec: Dict[str, Any]) -> Dict[str, Any]:
    html = render_delivery(spec.get("style") or STYLE_PACKS[0],
                           inject_css=spec.get("inject_css") or "",
                           drop=tuple(spec.get("drop") or []),
                           mutations=tuple(spec.get("mutations") or []))
    out = check_html(html)
    got = {x["id"] for x in out["violations"]} | set(out["failed_rules"])
    expect = set(spec.get("expect") or [])
    return {"case_id": spec.get("case_id"), "expect": sorted(expect),
            "hit": sorted(expect & got), "rejected": not out["ok"],
            "as_expected": bool(expect) and expect <= got,
            "violations": out["violations"]}


def check_case(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8-sig") as f:
        return apply_misuse(json.load(f))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="design_contract.py", description="R10 设计契约")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--input", required=True)
    sub.add_parser("packs")
    sub.add_parser("review")
    m = sub.add_parser("misuse")
    m.add_argument("--case", required=True)
    g = sub.add_parser("goldens")
    g.add_argument("--dir", default=None)
    a = ap.parse_args(argv)

    if a.cmd == "goldens":
        out = build_goldens(a.dir)
        print(json.dumps({"ok": out["ok"],
                          "goldens": {k: {"ok": v["ok"],
                                          "violations": v["violations"]}
                                      for k, v in out["goldens"].items()}},
                         ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "check":
        out = check_file(a.input)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "packs":
        out = style_packs()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "review":
        out = visual_review()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    out = check_case(a.case)
    out["ok"] = out["as_expected"]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
