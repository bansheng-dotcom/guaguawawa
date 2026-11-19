# -*- coding: utf-8 -*-
"""core.report_theme.pages —— consulting 主题的 A4 页式渲染（A/B 两种页型）。

不是替代 core/report_renderer.py 的文档流，而是它的一个可选出口：
contract["theme"] == "consulting" 或 contract["layout"] in ("pages","hybrid")
时走这里，输出固定 A4 页（封面/摘要/目录/节页/动作/附录/封底）。

两种节页：
- A 三块：事实 / 解释 / 所以，通栏；
- B 研报：主文 + 右侧 43mm 关键数字栏，正文绕排。
选 B 的条件是 section 里带 rail（3–4 个关键数字 + 一句话）。
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.charts import consulting as ccharts
from core.data_shape import fits

ROOT = Path(__file__).resolve().parents[2]
CSS = (Path(__file__).resolve().parent / "consulting.css").read_text(encoding="utf-8")
ORG = "蛙蛙呱呱专家团"

_SENT = re.compile(r"(?<=。)")


def esc(v: Any) -> str:
    return ("" if v is None else str(v)).replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace('"', "&quot;")


def _logo() -> str:
    p = ROOT / "avatars" / "team.png"
    if not p.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")


LOGO = _logo()


def _footer(pn: int, total: int) -> str:
    return (f'<div class="rf"><span>{ORG} · 内部研究</span>'
            f'<span class="pn">{pn:02d} <i>/ {total:02d}</i></span></div>')


def _header(left: str, right: str) -> str:
    return f'<div class="rh"><span><b>{esc(left)}</b></span><span>{esc(right)}</span></div>'


def _page(inner: str, cls: str, pn: int, total: int,
          head: Optional[tuple[str, str]] = None, sid: str = "") -> str:
    h = _header(*head) if head else ""
    return f'<section class="page {cls}" id="{sid}">{h}{inner}{_footer(pn, total)}</section>'


def _split3(text: str) -> List[str]:
    sents = [x for x in _SENT.split(text) if x.strip()]
    total = sum(len(x) for x in sents) or 1
    target = total / 3
    out: List[str] = []
    cur = ""
    acc = 0
    for s in sents:
        cur += s
        acc += len(s)
        if len(out) < 2 and acc >= target * (len(out) + 1):
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    while len(out) < 3:
        out.append("")
    return out


def _reading_blocks(s: Dict[str, Any], body: str) -> List[str]:
    """优先按 reading 的 strong 标签分组，避免把观察/落点混成一大段。"""
    fact, expl, act = [], [], []
    for r in (s.get("reading") or []):
        txt = str(r.get("text") or "").strip()
        if not txt or "边界" in str(r.get("strong") or ""):
            continue
        st = str(r.get("strong") or "")
        if "观察" in st or "事实" in st:
            fact.append(txt)
        elif "机理" in st or "判断" in st or "对照" in st or "解释" in st:
            expl.append(txt)
        elif "落点" in st or "所以" in st or txt.startswith("所以"):
            act.append(txt)
        else:
            fact.append(txt)
    if fact or expl or act:
        out = ["".join(fact), "".join(expl), "".join(act)]
        return out
    return _split3(body)


def _notes_html(notes: List[str]) -> str:
    if not notes:
        return ""
    rows = "".join(
        f'<div class="n"><b>{i}</b><span>{esc(n)}</span></div>'
        for i, n in enumerate(notes, 1)
    )
    return f'<div class="notes">{rows}</div>'


def _cover(c: Dict[str, Any]) -> str:
    lines = c.get("title_lines") or [""]
    title = lines[0]
    sub = lines[1] if len(lines) > 1 and lines[1] else ""
    kpis = "".join(
        f'<div class="kpi"><div class="v">{esc(m.get("value", ""))}</div>'
        f'<div class="l">{esc(m.get("label", ""))}</div>'
        f'<div class="s">{esc(m.get("note", ""))}</div></div>'
        for m in (c.get("metric_strip") or [])[:4]
    )
    brand = f'<img src="{LOGO}" alt="{ORG}">' if LOGO else ""
    return f"""
<div class="page cover"><div class="inner">
  <div class="top"><div class="brand">{brand}<div><div class="bw">{ORG}</div></div></div>
  <div class="chip">内部研究 · 2026.11</div></div>
  <div class="mid">
    <div class="ck">{esc(c.get("doc_type", "研究报告"))}</div>
    <h1 class="cover-t">{esc(title)}</h1>
    <div class="rule"></div>
    {f'<div class="sub">{esc(sub)}</div>' if sub else ''}
    <div class="stand">{esc(c.get("standfirst", ""))}</div>
  </div>
  <div class="kpis">{kpis}</div>
  <div class="foot"><span>{ORG} · 2026 年 11 月</span><span></span></div>
</div></div>
"""


def _summary(c: Dict[str, Any], actions: List[Dict[str, Any]], pn: int, total: int) -> str:
    items = []
    for i, p in enumerate((c.get("summary") or [])[:5], 1):
        label = str(p.get("label") or "").strip("：:")
        body = str(p.get("text") or "")
        if label:
            title, evidence = label, body
        else:
            head, _, tail = body.partition("。")
            title = (head + "。") if head else body
            evidence = tail.strip()
        items.append(
            f'<div class="sum-item"><div class="no">{i:02d}</div><div>'
            f'<div class="t">{esc(title)}</div>'
            f'<div class="e">{esc(evidence)}</div></div></div>'
        )
    acts = "".join(
        f'<div class="act"><div class="t">{esc(a.get("title", ""))}</div>'
        f'<div class="d">{esc(a.get("stop", ""))}</div></div>'
        for a in actions[:3]
    )
    one = c.get("one_thing") or (c.get("summary") or [{}])[0].get("text", "")
    inner = f"""
<div class="sum-head"><div class="kick">结论摘要 / EXECUTIVE SUMMARY</div>
  <h2>{esc(c.get("summary_title", "五条判断，一个动作"))}</h2></div>
<div class="sum-grid">
  <div class="sum-list">{''.join(items)}</div>
  <div><div class="one"><div class="k">如果只做一件事</div>
    <div class="x">{esc(c.get("one_x", "先做最小可行单元"))}</div>
    <div class="y">{esc(one)}</div></div>
    <div class="scope"><b>读法</b>：每节先给判断，再给数字、机理与边界；数字在页脚可回溯。</div></div>
</div>
<div class="acts">{acts}</div>
<div class="sum-foot"><b>边界</b>{esc(c.get("boundary", ""))}</div>
"""
    return _page(inner, "summary", pn, total, ("结论摘要", c.get("short_title", "")), "summary")


def _toc(sections: List[Dict[str, Any]], page_of: Dict[str, int],
         actions: bool, appendix: bool, pn: int, total: int, c: Dict[str, Any]) -> str:
    rows = []
    for s in sections:
        rows.append((str(s.get("index", "")).zfill(2), f"s-{s['index']}",
                     s.get("kicker") or "章节", s.get("title", "")[:24],
                     page_of[f"s-{s['index']}"]))
    if actions:
        rows.append(("A", "actions", "动作", "谁 / 何时 / 停止线", page_of["actions"]))
    if appendix:
        rows.append(("B", "appendix", "附录", "来源与口径", page_of["appendix"]))
    cells = "".join(
        f'<a class="toc-row" href="#{sid}"><span class="no">{no}</span>'
        f'<span class="ti">{esc(lab)}</span><span class="de">{esc(desc)}</span>'
        f'<span class="dots"></span><span class="pg">{pg}</span></a>'
        for no, sid, lab, desc, pg in rows
    )
    half = (len(rows) + 1) // 2
    parts = [x + "</a>" for x in cells.split("</a>") if x]
    left, right = "".join(parts[:half]), "".join(parts[half:])
    inner = f"""
<div class="toc-head"><div class="kick">目录 / CONTENTS</div>
  <h2>{esc(c.get("toc_title", "从判断到动作"))}</h2></div>
<div class="toc-cols"><div>{left}</div><div>{right}</div></div>
<div class="toc-note"><div class="note-box"><h4>阅读说明</h4>
<p>单位与口径见图下；来源等级 A 政府/官方、B 行业报告、C 平台/媒体。上标对应页脚编号；图和表的来源、样本、口径都写在图下。</p>
</div><div class="note-box"><h4>两种页型</h4>
<p>数据页：主文 + 右侧关键数字栏；地图/表格/长文页：事实 / 解释 / 所以三块。固定 A4，页脚有页码。</p>
</div></div>
"""
    return _page(inner, "toc", pn, total, ("目录", c.get("short_title", "")), "toc")


def _reading(s: Dict[str, Any]) -> tuple[str, str]:
    """把 contract 的 reading 拆成正文与边界。"""
    body: List[str] = []
    boundary = str(s.get("boundary") or "").strip()
    for r in (s.get("reading") or []):
        t = str(r.get("text") or "").strip()
        if not t:
            continue
        if "边界" in str(r.get("strong") or "") or t.startswith("本节边界"):
            boundary = t.replace("本节边界　", "").replace("本节边界", "").strip()
        else:
            body.append(t)
    return "".join(body), boundary


def _chart_html(s: Dict[str, Any], fig_no: str) -> str:
    ch = s.get("chart")
    if ch:
        svg = ccharts.render(ch, theme="consulting")
        src = "；".join(x for x in (ch.get("source"), ch.get("unit_meta")) if x)
        return f"""
<figure class="ex"><div class="ex-head"><span class="ex-no">{fig_no}</span>
  <span class="ex-title">{esc(ch.get("title", ""))}</span>
  <span class="ex-unit">{esc(ch.get("unit_meta", ""))}</span></div>
  {svg}<div class="ex-src">来源：{esc(src)}</div></figure>"""
    tb = s.get("table")
    if tb:
        cols = [c.get("text", "") if isinstance(c, dict) else str(c) for c in tb.get("columns", [])]
        th = "".join(f'<th>{esc(x)}</th>' for x in cols)
        trs = []
        for row in tb.get("rows", []):
            tds = "".join(
                f'<td>{esc(x.get("text", "") if isinstance(x, dict) else x)}</td>' for x in row
            )
            trs.append(f"<tr>{tds}</tr>")
        return f"""
<div class="ex"><div class="ex-head"><span class="ex-no">{fig_no}</span>
  <span class="ex-title">{esc(tb.get("caption", ""))}</span></div>
  <table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>"""
    return ""


def _first_sentence(text: str) -> str:
    head, sep, _ = text.partition("。")
    return (head + "。") if sep else text


def _section(s: Dict[str, Any], pn: int, total: int, fig_no: str,
             layout: str) -> str:
    body, boundary = _reading(s)
    # B 页需要右侧栏；正文过长时自动退回 A，避免压到页脚
    if layout == "rail" and len(body) > 520:
        layout = "blocks"
    blocks = _reading_blocks(s, body)
    labels = ("事实", "机理", "所以")
    kick = s.get("kicker") or "判断"
    verdict = s.get("verdict") or _first_sentence(body)
    head = f"""
<div class="head"><span class="num">{str(s.get("index", "")).zfill(2)}</span>
  <span class="kick">{esc(kick)}</span>
  <h2 class="action">{esc(s.get("title", ""))}</h2>
  <div class="q">{esc(s.get("question", ""))}</div>
  <div class="verdict"><b>结论</b><span>{esc(verdict)}</span></div>
</div>"""
    if str(s.get("kicker") or "") == "口径" or str(s.get("title") or "") == "口径与分数":
        rows = "".join(f'<p>{esc(str(r.get("text") or ""))}</p>'
                       for r in (s.get("reading") or [])
                       if "边界" not in str(r.get("strong") or ""))
        inner = head + f'<div class="metalist">{rows}</div>'
        return _page(inner, "sec", pn, total,
                     (f'{str(s.get("index","")).zfill(2)} / 口径', s.get("short_title", "")),
                     f's-{s["index"]}')
    fig = _chart_html(s, fig_no)
    if fig.strip() and "<svg" not in fig and "<table" not in fig:
        # 图型画不出来（返回空 svg）时退回本节表格：深度门禁按节验「至少一张图或表」，
        # 有表却因为 chart 渲染空而丢掉，会被判成空节（2026-11-19 修复）。
        fig = _chart_html({**s, "chart": None}, fig_no)
    rail = s.get("rail")
    fals = str(s.get("falsifier") or "").strip()
    fals_html = (f'<div class="boundary sec-falsifier"><b>什么会推翻它</b>'
                 f'{esc(fals)}</div>') if fals else ""
    if layout == "rail" and rail:
        items = "".join(
            f'<div class="rail-k"><b>{esc(x[0])}</b><span>{esc(x[1])}</span><i>{esc(x[2])}</i></div>'
            for x in rail.get("items", [])
        )
        rail_html = (f'<aside class="rail-float"><div class="rail-h">关键数字 / KEY NUMBERS</div>'
                     f'{items}<div class="rail-one"><em>一句话</em>{esc(rail.get("line", ""))}</div></aside>')
        main = "".join(
            f'<div class="rp"><span class="rl">{lab}</span><p>{tx}</p></div>'
            for lab, tx in zip(labels, blocks)
        )
        refs = s.get("refs") or []
        notes = [str(x) for x in (s.get("notes") or [])]
        if not notes and refs:
            notes = [f"证据：{len(refs)} 条可寻址数字，附录 / 原报告可回溯。"]
        inner = (head + fig + f'<div class="rail-main">{rail_html}{main}</div>'
                 f'<div class="rail-clear"></div>'
                 + (f'<div class="boundary"><b>边界</b>{esc(boundary)}</div>' if boundary else '')
                 + fals_html
                 + _notes_html(notes))
        return _page(inner, "sec rail-layout", pn, total,
                     (f'{str(s.get("index","")).zfill(2)} / {kick}',
                      s.get("short_title", "")), f's-{s["index"]}')
    pb = "".join(
        f'<div class="pblock"><span class="plabel">{lab}</span><p>{tx}</p></div>'
        for lab, tx in zip(labels, blocks) if tx.strip()
    )
    refs = s.get("refs") or []
    notes = [str(x) for x in (s.get("notes") or [])]
    if not notes and refs:
        notes = [f"证据：{len(refs)} 条可寻址数字，附录 / 原报告可回溯。"]
    inner = (head + fig + f'<div class="pblocks">{pb}</div>'
             + (f'<div class="boundary"><b>边界</b>{esc(boundary)}</div>' if boundary else '')
             + fals_html
             + _notes_html(notes))
    return _page(inner, "sec", pn, total,
                 (f'{str(s.get("index","")).zfill(2)} / {kick}',
                  s.get("short_title", "")), f's-{s["index"]}')


def _actions(c: Dict[str, Any], pn: int, total: int) -> str:
    acts = list(c.get("actions") or [])
    real = any(str(a.get("who") or "") not in ("", "—", "待定")
               for a in acts)
    if real:
        heads = ("#", "动作", "谁", "何时", "预算", "停止线", "验收")
        keys = ("id", "title", "who", "when", "budget", "stop", "accept")
    else:
        heads = ("#", "动作", "停止线", "验收")
        keys = ("id", "title", "stop", "accept")
    rows = ["<tr>" + "".join(f"<td>{esc(a.get(k, ''))}</td>" for k in keys) + "</tr>"
            for a in acts]
    th = "".join(f"<th>{x}</th>" for x in heads)
    inner = f"""
<div class="act-head"><div class="kick">动作 / ACTION REGISTER</div>
  <h2>{esc(c.get("actions_title", "谁、何时、花多少、什么条件停"))}</h2>
  <div class="q">没有停止线的动作，不是动作，是愿望。</div></div>
<div class="act-wrap"><table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>
<div class="stop"><b>统一停止线</b>　{esc(c.get("stop_rule", "单件毛利低于 15% 不加仓。"))}</div></div>
"""
    return _page(inner, "actions", pn, total, ("动作清单", c.get("short_title", "")), "actions")


def _appendix(c: Dict[str, Any], pn: int, total: int) -> str:
    sources = c.get("sources") or []
    rows = "".join(
        f"<tr><td>{esc(s.get('id',''))}</td><td>{esc(s.get('title',''))}</td>"
        f"<td>{esc(s.get('date',''))}</td></tr>"
        for s in sources
    )
    inner = f"""
<div class="ap-head"><div class="kick">附录 / EVIDENCE</div>
  <h2>{esc(c.get("appendix_title", "来源与口径"))}</h2>
  <div class="q">每条上标都能回到这里；重排不改数字。</div></div>
<div class="files" style="margin-top:5mm">
<table><thead><tr><th>来源</th><th>说明</th><th>日期</th></tr></thead><tbody>{rows}</tbody></table>
</div>
"""
    return _page(inner, "appendix", pn, total, ("附录 · 证据", c.get("short_title", "")), "appendix")


def _back(c: Dict[str, Any]) -> str:
    logo = f'<div class="logo-card"><img src="{LOGO}" alt="{ORG}"></div>' if LOGO else ""
    return f"""
<section class="page back" id="back"><div class="inner">
  {logo}<h2>{ORG}</h2><p class="back-sub">内部研究 · 2026 年 11 月</p>
  <div class="foot">{esc(c.get("disclaimer", "本报告为内部研究样板，不构成投资、采购或定价建议。"))}</div>
</div></section>
"""


def _validate_shapes(c: Dict[str, Any]) -> None:
    """严格模式：有图必须有 shape，且图型 ∈ chart_lib.recommend(shape,intent)。"""
    if not c.get("require_shape"):
        return
    bad = []
    for s in c.get("sections") or []:
        if not s.get("chart"):
            continue
        shape = s.get("shape")
        ch = s.get("chart")
        if isinstance(ch, dict):
            ch = ch.get("type")
        if not shape:
            bad.append(f"{s.get('index', '?')}: 有图未声明 shape")
        elif not fits(ch, shape):
            bad.append(f"{s.get('index', '?')}: 图型 {ch} 不适配 shape={shape}")
    if bad:
        raise ValueError("shape 校验失败: " + "; ".join(bad))


def render_contract(c: Dict[str, Any]) -> str:
    """contract → 固定 A4 页 HTML。"""
    _validate_shapes(c)
    all_sections = list(c.get("sections") or [])
    sections = [s for s in all_sections if not s.get("appendix")]
    appendices = [s for s in all_sections if s.get("appendix")]
    short = c.get("short_title") or ((c.get("title_lines") or [""])[0][:18])
    for i, s in enumerate(sections, 1):
        s["index"] = i
        s.setdefault("short_title", short)
    actions = bool(c.get("actions"))
    appendix = bool(c.get("sources") or appendices or c.get("notes"))
    total = 3 + len(sections) + (1 if actions else 0) + (1 if appendix else 0) + 1
    page_of: Dict[str, int] = {}
    p = 4
    for s in sections:
        page_of[f's-{s["index"]}'] = p
        p += 1
    if actions:
        page_of["actions"] = p
        p += 1
    if appendix:
        page_of["appendix"] = p
        p += 1
    page_of["back"] = p

    parts = [_cover(c), _summary(c, c.get("actions") or [], 2, total),
             _toc(sections, page_of, actions, appendix, 3, total, c)]
    fig = 0
    table = 0
    for s in sections:
        if s.get("chart"):
            fig += 1
            no = f"图 {fig}"
        elif s.get("table"):
            table += 1
            no = f"表 {table}"
        else:
            no = "图"
        layout = str(s.get("layout") or ("rail" if s.get("rail") else "blocks"))
        parts.append(_section(s, page_of[f's-{s["index"]}'], total, no, layout))
    if actions:
        parts.append(_actions(c, page_of["actions"], total))
    if appendix:
        merged = dict(c)
        if not merged.get("sources") and appendices:
            merged["sources"] = [
                {"id": f"A{i}", "title": s.get("title", ""), "date": ""}
                for i, s in enumerate(appendices, 1)
            ]
        parts.append(_appendix(merged, page_of["appendix"], total))
    parts.append(_back(c))

    tip_js = """
<script>
const tip=document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el=>{
 el.addEventListener('mousemove',e=>{tip.textContent=el.getAttribute('data-tip');
 tip.style.opacity=1;tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+14)+'px';});
 el.addEventListener('mouseleave',()=>{tip.style.opacity=0;});
});
</script>"""
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc((c.get("title_lines") or [""])[0])}</title>'
            f'<style>{CSS}</style></head><body>{"".join(parts)}<div id="tip"></div>{tip_js}</body></html>')

