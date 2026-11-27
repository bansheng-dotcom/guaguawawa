# -*- coding: utf-8 -*-
"""第 7 段 final：整合章节为 final.md + final_audit.json，并做终检。

终检四类：
  1. 结构完整：H1 + 与细纲一一对应的 H2 + 结尾边界节；
  2. 论证流：每节按“结论 → 证据 → 边界”组织，节内出现数字与边界句；
  3. AI 套话密度：每千字命中数不超过阈值；
  4. 事实核对与平台长度：正文数字必须可追到 claims，正文字符数落在平台区间。
"""
from __future__ import annotations

import html as _html
import re
from typing import Any, Dict, List

from .common import (THRESHOLDS, char_len, ck, claim_numbers, clean_text,
                     fluff_count, fluff_density, gate, now_iso, number_set,
                     sentences)

BOUNDARY_HEADING = "边界与后续"
BOUNDARY_MARK = "边界"


def _strip_digits(text: str) -> str:
    return re.sub(r"\d+(?:\.\d+)?", "", str(text or ""))


def compose(drafts: Dict[str, Any], rewrite: Dict[str, Any],
            research: Dict[str, Any], brief: Dict[str, Any]) -> str:
    brief = brief or {}
    title = str(brief.get("title") or research.get("topic_title") or "内容成品").strip()
    industry = str(brief.get("industry") or "这个主题").strip()
    audience = str(brief.get("audience") or "读者").strip()
    goal = str(brief.get("goal") or "把问题讲清楚").strip()

    intro = ("%s常把%s当成一句口号，真正难的是知道它在什么条件下成立。"
             "本文按证据台账逐节拆开：先给判断，再给来源，最后标出适用边界；"
             "目标只有一个——%s。" % (audience, industry, goal))

    parts: List[str] = ["# %s\n\n%s\n" % (title, intro)]
    for sec in rewrite.get("sections") or []:
        body = "\n\n".join(str(u.get("selected_text", "")) for u in sec.get("units") or [])
        parts.append("## %s\n\n%s\n" % (str(sec.get("title")), body))

    gaps = [str(g).strip() for g in (research.get("gaps") or []) if str(g).strip()]
    gap_line = "；".join(_strip_digits(g) for g in gaps[:4]) or "暂无"
    parts.append("## %s\n\n- 适用边界：本文只讨论%s，不覆盖未登记来源的场景。\n"
                 "- 未回答的问题：%s。\n- 事实口径：正文数字均可追到来源台账，改动数字需回写 claims。\n"
                 % (BOUNDARY_HEADING, industry, gap_line))
    return "\n".join(parts).strip() + "\n"


def audit(text: str, outline: Dict[str, Any], research: Dict[str, Any],
          brief: Dict[str, Any]) -> Dict[str, Any]:
    brief = brief or {}
    sections = [s for s in (outline.get("sections") or [])]
    expected = [str(s.get("title")) for s in sections]

    chunks = re.split(r"^## ", text, flags=re.M)
    head = chunks[0]
    got_titles: List[str] = []
    body: Dict[str, str] = {}
    for chunk in chunks[1:]:
        lines = chunk.split("\n", 1)
        got_titles.append(lines[0].strip())
        body[lines[0].strip()] = lines[1] if len(lines) > 1 else ""

    checks: List[Dict[str, Any]] = []
    checks.append(ck(bool(re.search(r"^# \S", head, flags=re.M)), "H1 标题存在",
                     "final.h1", "CRITICAL"))
    order_ok = got_titles[:len(expected)] == expected and BOUNDARY_HEADING in got_titles
    checks.append(ck(order_ok, "H2 顺序与细纲一致且含边界节", "final.structure",
                     "CRITICAL" if not order_ok else "OK",
                     expected=expected, got=got_titles))
    empty = [t for t in expected if len(clean_text(body.get(t, ""))) < 120]
    checks.append(ck(not empty, "每节正文非空且 ≥120 字", "final.sections",
                     "CRITICAL" if empty else "OK", offenders=empty))

    flow_bad: List[str] = []
    for t in expected:
        content = body.get(t, "")
        if not number_set(content):
            flow_bad.append(t + ":数字")
        if not all(mark in content for mark in ("结论", "证据", BOUNDARY_MARK)):
            flow_bad.append(t + ":三层")
        else:
            i1, i2, i3 = content.index("结论"), content.index("证据"), content.index(BOUNDARY_MARK)
            if not (i1 < i2 < i3):
                flow_bad.append(t + ":顺序")
        if len(sentences(content)) < 2:
            flow_bad.append(t + ":句数")
    checks.append(ck(not flow_bad, "论证流：每节按结论→证据→边界且含数字",
                     "final.argument_flow", "CRITICAL" if flow_bad else "OK",
                     offenders=flow_bad))

    density = fluff_density(text)
    limit = THRESHOLDS["final"]["max_fluff_per_1000"]
    hits = fluff_count(text)
    checks.append(ck(density <= limit,
                     "AI 套话密度 %.2f ≤ %.2f（命中 %d）" % (density, limit, hits),
                     "final.ai_fluff", "CRITICAL" if density > limit else "OK",
                     density=density, hits=hits))

    allowed = claim_numbers(research)
    # 专名里的数字（如 R11）不是事实数字，允许出现但不参与 claims 核对。
    name_text = " ".join([str(brief.get("title") or ""), str(brief.get("industry") or "")]
                         + [str(e) for e in (brief.get("entities") or [])])
    allowed |= number_set(name_text)
    extra = sorted(number_set(text) - allowed)
    checks.append(ck(not extra, "正文数字均可追到 claims", "final.fact_check",
                     "CRITICAL" if extra else "OK", offenders=extra,
                     allowed=sorted(allowed)))

    cons = brief.get("constraints") or {}
    lo = int(cons.get("min_chars") or 800)
    hi = int(cons.get("max_chars") or 6000)
    n = char_len(text)
    checks.append(ck(lo <= n <= hi, "平台长度 %d 在 %d–%d" % (n, lo, hi),
                     "final.platform_length",
                     "CRITICAL" if not (lo <= n <= hi) else "OK", char_len=n))

    return {
        "artifact": "final_audit",
        "version": "1.0",
        "generated_at": now_iso(),
        "topic_id": outline.get("topic_id", ""),
        "char_len": n,
        "section_titles": got_titles,
        "fluff": {"hits": hits, "density": density, "limit": limit},
        "numbers": {"final": sorted(number_set(text)), "claims": sorted(allowed)},
        "gate": gate(checks, "final"),
    }


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """复用 audit 已算好的门禁，供独立复核/误用样本复用。"""
    g = artifact.get("gate") or gate([ck(False, "缺少年度门禁", "final.gate", "CRITICAL")], "final")
    return g


def render_html(markdown: str, audit_artifact: Dict[str, Any]) -> str:
    """把 final.md 渲染成自包含 HTML（黄金成品与人工复核用）。"""
    body: List[str] = []
    para: List[str] = []

    def flush() -> None:
        if para:
            body.append("<p>%s</p>" % _html.escape(" ".join(para)))
            para.clear()

    for raw in str(markdown or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if line.startswith("# "):
            flush()
            body.append("<h1>%s</h1>" % _html.escape(line[2:].strip()))
        elif line.startswith("## "):
            flush()
            body.append("<h2>%s</h2>" % _html.escape(line[3:].strip()))
        elif line.lstrip().startswith("- "):
            flush()
            body.append("<li>%s</li>" % _html.escape(line.lstrip()[2:].strip()))
        else:
            para.append(line.strip())
    flush()

    out: List[str] = []
    in_list = False
    for frag in body:
        if frag.startswith("<li>"):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(frag)
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(frag)
    if in_list:
        out.append("</ul>")

    g = audit_artifact.get("gate") or {}
    badge = "门禁 %s · %d 字 · 套话密度 %.2f" % (
        g.get("grade", "?"), audit_artifact.get("char_len", 0),
        (audit_artifact.get("fluff") or {}).get("density", 0.0))
    first = next((ln for ln in str(markdown or "").splitlines() if ln.startswith("# ")), "")
    title = first[2:].strip() if first else "R11 内容成品"
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<style>
body{margin:0;background:#f6f5f1;color:#1f2328;font-family:"Noto Serif SC","Songti SC",Georgia,serif;line-height:1.9}
main{max-width:760px;margin:0 auto;padding:56px 28px 80px;background:#fff;box-shadow:0 1px 24px rgba(0,0,0,.06)}
h1{font-size:30px;line-height:1.4;margin:0 0 10px}
h2{font-size:21px;margin:38px 0 12px;padding-top:12px;border-top:1px solid #e6e2d8}
p{margin:0 0 14px;text-align:justify}
li{margin:6px 0}
.meta{font-size:12px;color:#7a7466;letter-spacing:.04em;margin-bottom:26px}
</style>
</head>
<body><main>
<h1>%s</h1>
<div class="meta">%s</div>
%s
</main></body></html>
""" % (_html.escape(title), _html.escape(title),
       _html.escape(badge), "\n".join(out))
