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
from core.report_marks import BOUNDARY_LABEL, FIGURE_SRC_CLASSES

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
    fact, expl, rebut, act = [], [], [], []
    for r in (s.get("reading") or []):
        txt = str(r.get("text") or "").strip()
        if not txt or "边界" in str(r.get("strong") or ""):
            continue
        st = str(r.get("strong") or "")
        if "观察" in st or "事实" in st:
            fact.append(txt)
        elif "机理" in st or "判断" in st or "对照" in st or "解释" in st:
            expl.append(txt)
        elif "反例" in st or "边界" in st:
            rebut.append(txt)
        elif "落点" in st or "所以" in st or txt.startswith("所以"):
            act.append(txt)
        else:
            fact.append(txt)
    if fact or expl or rebut or act:
        # 结论框已经放了首句，事实块不要重复同一句：从事实块剥掉结论句，
        # 读者先看一句判断，再看支撑细节，而不是同一句话读两遍。
        verdict = str(s.get("verdict") or "").strip()
        if fact and verdict:
            first = fact[0]
            if first[:12] == verdict[:12]:
                _, sep, rest = first.partition("。")
                fact[0] = rest.lstrip("。； ") if sep else ""
        # 组内不合并：一段 1500 字在纸上就是一堵墙，按块用空行隔开，渲染时拆成多个 <p>
        out = ["\n\n".join(x for x in fact if x),
               "\n\n".join(x for x in expl if x),
               "\n\n".join(x for x in rebut if x),
               "\n\n".join(x for x in act if x)]
        return out
    return _split3(body)


def _paras(tx: str) -> str:
    parts = [p.strip() for p in str(tx or "").split("\n\n") if p.strip()]
    if not parts:
        parts = [str(tx or "")]
    # 必须包一层：.pblock 是 grid，直接放多个 <p> 会被当成多个格子塞进 13mm 窄栏
    inner = "".join(f"<p>{p}</p>" for p in parts)
    return f'<div class="ptext">{inner}</div>'


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
    strip = (c.get("metric_strip") or [])[:4]
    # 列数跟着条数走：三条就三列，避免被压窄
    cols = max(1, min(len(strip), 4))
    kpis = "".join(
        f'<div class="kpi"><div class="v">{esc(m.get("value", ""))}</div>'
        f'<div class="l">{esc(m.get("label", ""))}</div>'
        f'<div class="s">{esc(m.get("note", ""))}</div></div>'
        for m in strip
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
  <div class="kpis" style="grid-template-columns:repeat({cols},1fr)">{kpis}</div>
  <div class="foot"><span>{ORG} · 2026 年 11 月</span><span></span></div>
</div></div>
"""


def _summary(c: Dict[str, Any], actions: List[Dict[str, Any]], pn: int, total: int) -> str:
    dec = c.get("decision") or {}
    if dec.get("items"):
        items = []
        for i, it in enumerate((dec.get("items") or [])[:5], 1):
            claim = str(it.get("claim") or "")
            number = str(it.get("number") or "")
            action = str(it.get("action") or "")
            stop = str(it.get("stop") or "")
            items.append(
                f'<div class="sum-item"><div class="no">{i:02d}</div><div>'
                f'<div class="t">{esc(claim)}</div>'
                f'<div class="e"><b>{esc(number)}</b>　{esc(action)}</div>'
                f'<div style="font-size:8.5pt;color:#6b7a80;margin-top:1mm">'
                f'停止：{esc(stop)}</div></div></div>')
        one = dec.get("one_thing") or (dec.get("items") or [{}])[0].get("action", "")
        inner = f"""
<div class="sum-head"><div class="kick">决策纸 / DECISION</div>
  <h2>决策纸：{esc(dec.get("title") or "先做哪一个，钱怎么分")}</h2></div>
<div class="sum-grid">
  <div class="sum-list">{''.join(items)}</div>
  <div><div class="one"><div class="k">如果只做一件事</div>
    <div class="x">{esc(dec.get("subtitle") or "先做最小可行单元")}</div>
    <div class="y">{esc(one)}</div></div>
    <div class="scope"><b>读法</b>：每条判断先给数字，再给动作与停止条件；证据、口径与缺口见附录。</div></div>
</div>
<div class="sum-foot"><b>边界</b>{esc(dec.get("boundary") or "")}</div>
"""
        return _page(inner, "summary", pn, total, ("决策纸", c.get("short_title", "")), "summary")
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
        rows.append(("B", "s-A1", "附录", "来源与口径", page_of.get("appendix", 0)))
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


_CHART_STATS = {"total": 0, "pro": 0, "legacy": 0, "error": 0, "echarts": 0}


def chart_stats() -> Dict[str, int]:
    return dict(_CHART_STATS)


def reset_chart_stats() -> None:
    for k in _CHART_STATS:
        _CHART_STATS[k] = 0


def _render_svg(ch: Dict[str, Any]) -> tuple[str, str]:
    """先走升级后的 charts_pro；映射不了再回退老引擎。

    2026-11-20：flow 线一直直接调 `core.charts.consulting`，
    charts_pro 只接在 report_renderer（paper）上，所以默认版式的图全是旧引擎画的。
    """
    _CHART_STATS["total"] += 1
    import os
    if str(os.environ.get("GUAGUA_CHART_ENGINE") or "").lower() == "legacy":
        svg = ccharts.render(ch, theme="consulting") or ""
        _CHART_STATS["legacy"] += 1
        return svg, "legacy"
    if str(os.environ.get("GUAGUA_CHART_BACKEND") or "svg").lower() == "echarts":
        try:
            from core.report_theme.charts_pro import interactive
            html = interactive.render_chart(ch)
        except Exception:  # noqa: BLE001 交互后端坏了必须回退，不阻断报告
            html = None
        if html:
            _CHART_STATS["echarts"] += 1
            return html, "echarts"
    try:
        from core.report_theme.charts_pro.compat import render_chart as pro_render
        svg = pro_render(ch) or ""
    except Exception:  # noqa: BLE001
        svg = ""
    if svg.strip():
        _CHART_STATS["pro"] += 1
        return svg, "pro"
    try:
        svg = ccharts.render(ch, theme="consulting") or ""
    except Exception:  # noqa: BLE001
        _CHART_STATS["error"] += 1
        return "", "error"
    if not svg.strip():
        try:
            from core import chart_capabilities
            key = str(ch.get("type") or "")
            if chart_capabilities.has_chart(key):
                svg = chart_capabilities.render_chart(key, ch) or ""
        except Exception:  # noqa: BLE001
            svg = ""
    _CHART_STATS["legacy"] += 1
    return svg, "legacy"


def _chart_html(s: Dict[str, Any], fig_no: str) -> str:
    ch = s.get("chart")
    if ch:
        svg, engine = _render_svg(ch)
        # 来源只写来源：单位已经在图头 ex-unit 里，别混进来源行。
        src = str(ch.get("source") or "").strip()
        notes = []
        base = ch.get("baseline")
        if base:
            if isinstance(base, dict):
                base = base.get("label") or base.get("text") or str(base)
            notes.append(f"基线：{base}")
        ann = ch.get("annotate")
        if ann:
            if isinstance(ann, (list, tuple)):
                ann = "；".join(
                    str(x.get("text") if isinstance(x, dict) else x) for x in ann)
            notes.append(f"标注：{ann}")
        note_html = (f'<div class="chart-note" style="font-size:8.5pt;color:#5b6b73;'
                     f'line-height:1.6;margin:1mm 0 2mm">'
                     f'{esc("；".join(notes))}</div>') if notes else ""
        return f"""
<figure class="ex" data-engine="{engine}"><div class="ex-head"><span class="ex-no">{fig_no}</span>
  <span class="ex-title">{esc(ch.get("title", ""))}</span>
  <span class="ex-unit">{esc(ch.get("unit_meta", ""))}</span></div>
  {svg}{note_html}<div class="{FIGURE_SRC_CLASSES}">来源：{esc(src)}</div></figure>"""
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
<div class="ex"><div class="ex-head"><span class="ex-no">{fig_no.replace('图', '表')}</span>
  <span class="ex-title">{esc(tb.get("caption") or ("对比：" + " / ".join(cols[:4])))}</span></div>
  <table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>"""
    return ""


def _first_sentence(text: str) -> str:
    import re as _re
    t = _re.sub(r"^【[^】]{1,6}】", "", str(text or "").strip())
    t = _re.sub(r"^[一二三四五六七八九十]+、", "", t)
    head, sep, _ = t.partition("。")
    out = (head + "。") if sep else t
    return out if len(out) <= 80 else out[:78].rstrip("，、；,;") + "…"


def _coverage_panel(cov: Dict[str, Any] | None) -> str:
    """口径页上的「问题覆盖」：给人看的一块，不是机器对账表。

    2026-11-20：把"必答 10 问 / 答了 7 问"做成正文第一屏，读者会觉得这是审计日志；
    放在口径页，用进度条 + 未答清单，才既清楚又不打扰正文。
    """
    if not cov or not cov.get("must"):
        return ""
    n = int(cov.get("claimed") or 0)
    m = int(cov.get("must") or 0)
    pct = int(round(n / m * 100)) if m else 0
    items = cov.get("items") or []
    if items:
        rows = "".join(
            f'<li><span class="qcov-id">{esc(i.get("id", ""))}</span>'
            f'<span class="qcov-q">{esc(i.get("text") or "（问句未记录）")}</span>'
            f'<span class="qcov-why">{esc(i.get("why") or "未给原因")}</span></li>'
            for i in items)
        body = (f'<div class="qcov-sub">未答 {len(items)} 问 · 未答原因</div>'
                f'<ul class="qcov-list">{rows}</ul>')
    else:
        body = ('<div class="qcov-ok">必答问题全部有正文认领——'
                '没有藏在附录里的缺口。</div>')
    explore = int(cov.get("explore") or 0)
    foot = (f'<div class="qcov-foot">另有 {explore} 条计划外发现，'
            f'见「延伸发现」。</div>') if explore else ""
    return f"""
<div class="qcov">
  <div class="qcov-top">
    <div class="qcov-kicker">问题覆盖 / QUESTION COVERAGE</div>
    <div class="qcov-num"><b>{n}</b><span>/ {m} 问</span></div>
  </div>
  <div class="qcov-bar"><i style="width:{pct}%"></i></div>
  {body}{foot}
</div>"""


def _section(s: Dict[str, Any], pn: int, total: int, fig_no: str,
             layout: str) -> str:
    body, boundary = _reading(s)
    # B 页需要右侧栏；正文过长时自动退回 A，避免压到页脚
    if layout == "rail" and len(body) > 520:
        layout = "blocks"
    blocks = _reading_blocks(s, body)
    labels = ("事实", "机理", "反例", "所以")
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
        cov = s.get("coverage")
        rows_src = [r for r in (s.get("reading") or [])
                    if "边界" not in str(r.get("strong") or "")]
        # 面板已经把"必答几问/答了几问"讲清楚了，正文不再重复一遍
        if cov:
            rows_src = [r for r in rows_src
                        if "对账" not in str(r.get("strong") or "")]
        rows = "".join(
            (f'<p><b>{esc(str(r.get("strong") or "").strip())}</b>　'
             f'{esc(str(r.get("text") or ""))}</p>'
             if str(r.get("strong") or "").strip() else
             f'<p>{esc(str(r.get("text") or ""))}</p>')
            for r in rows_src)
        # 口径页的"结论"不该是"生成方式"的复述：直接给覆盖结论
        if cov and cov.get("must"):
            v_txt = (f"必答 {int(cov['must'])} 问，正文认领 {int(cov['claimed'])} 问；"
                     f"没答上的写在下面，不藏在附录里。")
        else:
            v_txt = "这一页只交代口径与校验，不承载结论。"
        cal_head = f"""
<div class="head"><span class="num">{str(s.get("index", "")).zfill(2)}</span>
  <span class="kick">{esc(kick)}</span>
  <h2 class="action">{esc(s.get("title", ""))}</h2>
  <div class="q">{esc(s.get("question", ""))}</div>
  <div class="verdict"><b>口径</b><span>{esc(v_txt)}</span></div>
</div>"""
        inner = cal_head + _coverage_panel(cov) + f'<div class="metalist">{rows}</div>'
        return _page(inner, "sec", pn, total,
                     (f'{str(s.get("index","")).zfill(2)} / 口径', s.get("short_title", "")),
                     f's-{s["index"]}')
    # list 型章节（延伸发现这类）：一条一列，不能拼成一段塞进"事实/机理/所以"。
    # 只对显式声明 list_render 的节生效——其它 `reading_style: list` 的节
    #（例如动作清单）仍走原路径，避免把证伪/边界渲染丢掉。
    if s.get("list_render") and not s.get("chart"):
        items = "".join(
            f'<li>{esc(str(r.get("text") or ""))}</li>'
            for r in (s.get("reading") or []) if str(r.get("text") or "").strip())
        list_head = f"""
<div class="head"><span class="num">{str(s.get("index", "")).zfill(2)}</span>
  <span class="kick">{esc(kick)}</span>
  <h2 class="action">{esc(s.get("title", ""))}</h2>
  <div class="q">{esc(s.get("question", ""))}</div>
  <div class="verdict"><b>看点</b><span>{esc(s.get("verdict") or "这些不在原问题清单里；成立与否，下一轮验证。")}</span></div>
</div>"""
        inner = list_head + (f'<ul class="metalist metalist-list">{items}</ul>' if items else "")
        # 延伸发现这类节也要有「图表」：逐节深度门禁按节验「至少一张图或表」，
        # list 渲染的节若把 table 丢了，会被判成空节（2026-11-20）。
        if s.get("table"):
            inner += _chart_html({**s, "chart": None}, fig_no)
        return _page(inner, "sec", pn, total,
                     (f'{str(s.get("index","")).zfill(2)} / {kick}',
                      s.get("short_title", "")), f's-{s["index"]}')

    fig = _chart_html(s, fig_no)
    # 有图也有表：图给关系，表给正文提到的全部数；表放在正文之后，
    # 避免「图后立刻插表」把半页留白。
    tbl = ""
    if s.get("chart") and s.get("table"):
        tbl = _chart_html({**s, "chart": None}, fig_no)
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
                     f'{items}<div class="rail-one"><em class="hl">一句话</em>{esc(rail.get("line", ""))}</div></aside>')
        main = "".join(
            f'<div class="rp"><span class="rl">{lab}</span>{_paras(tx)}</div>'
            for lab, tx in zip(labels, blocks)
        )
        refs = s.get("refs") or []
        notes = [str(x) for x in (s.get("notes") or [])]
        inner = (head + fig + f'<div class="rail-main">{rail_html}{main}</div>'
                 f'<div class="rail-clear"></div>' + tbl
                 + (f'<div class="boundary" data-label="{BOUNDARY_LABEL}"><b>边界</b>{esc(boundary)}</div>' if boundary else '')
                 + fals_html
                 + _notes_html(notes))
        return _page(inner, "sec rail-layout", pn, total,
                     (f'{str(s.get("index","")).zfill(2)} / {kick}',
                      s.get("short_title", "")), f's-{s["index"]}')
    pb = "".join(
        f'<div class="pblock"><span class="plabel">{lab}</span>{_paras(tx)}</div>'
        for lab, tx in zip(labels, blocks) if tx.strip()
    )
    refs = s.get("refs") or []
    notes = [str(x) for x in (s.get("notes") or [])]
    inner = (head + fig + f'<div class="pblocks">{pb}</div>' + tbl
             + (f'<div class="boundary" data-label="{BOUNDARY_LABEL}"><b>边界</b>{esc(boundary)}</div>' if boundary else '')
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


def _sources_page(c: Dict[str, Any], pn: int, total: int) -> str:
    """附录 A：数据来源（记录层）单独一页，全部来源放一起。"""
    srcs = c.get("sources") or []
    n = len(srcs)
    step = (n + 3) // 4
    cols = [srcs[i * step:(i + 1) * step] for i in range(4)]

    def rows(items):
        return "".join(
            f"<tr><td>{esc(s.get('id', ''))}</td>"
            f"<td>{esc(str(s.get('title', ''))[:16])}</td></tr>"
            for s in items)

    inner = f"""
<div class="ap-head"><div class="kick">附录 A / SOURCES</div>
  <h2>附录 A · 数据来源（记录层）</h2>
  <div class="q">全部登记 {n} 条，编号与正文上标一致；只换位置，不改数字。</div></div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:2.4mm;margin-top:1mm;font-size:6.8pt;line-height:1.18">
  {''.join(f'<table style="width:100%;font-size:6.8pt;line-height:1.18"><thead><tr><th>编号</th><th>来源</th></tr></thead><tbody>{rows(x)}</tbody></table>' for x in cols)}
</div>
"""
    return _page(inner, "appendix", pn, total,
                 ("附录 · 来源", c.get("short_title", "")), "s-A1")


def _support_page(c: Dict[str, Any], pn: int, total: int,
                  support: List[Dict[str, Any]] | None = None) -> str:
    """附录 B：支撑判断单列，不与来源并排，也不套五块模板。"""
    support = support or []
    rows = []
    for s in support[:12]:
        title = str(s.get("short_title") or s.get("full_title") or s.get("title") or "")
        if len(title) > 64:
            title = title[:63] + "…"
        rows.append(f"<li>{esc(title)}</li>")
    gaps = [str(x)[:110] for x in (c.get("boundaries") or []) if str(x).strip()][:4]
    if not gaps:
        for s in (c.get("sections") or []):
            g = str(s.get("boundary") or s.get("falsifier") or "").strip()
            if g and g not in gaps:
                gaps.append(g[:110])
            if len(gaps) >= 4:
                break
    gap_html = "".join(f"<li>{esc(g)}</li>" for g in gaps) or "<li>未记录</li>"
    inner = f"""
<div class="ap-head"><div class="kick">附录 B / SUPPORT</div>
  <h2>附录 B · 支撑判断</h2>
  <div class="q">未进正文的判断 {len(support)} 条；不占主判断名额，也不和来源并排。</div></div>
<h3 style="font-size:10pt;margin:5mm 0 2mm">判断清单</h3>
<ul class="bullets">{''.join(rows) or '<li>无</li>'}</ul>
<h3 style="font-size:10pt;margin:5mm 0 2mm">缺口与假设</h3>
<ul class="bullets">{gap_html}</ul>
"""
    return _page(inner, "appendix", pn, total,
                 ("附录 · 支撑", c.get("short_title", "")), "s-B1")



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
    sections = [s for s in all_sections if not s.get("appendix")
                and str(s.get("title") or "") not in ("记录层", "口径与分数")]
    support = [s for s in all_sections if s.get("appendix")
               and str(s.get("title") or "") not in ("记录层", "口径与分数")]
    caliber = next((s for s in all_sections
                    if str(s.get("title") or "") == "口径与分数"), None)
    sources = c.get("sources") or []
    short = c.get("short_title") or ((c.get("title_lines") or [""])[0][:18])
    for i, s in enumerate(sections, 1):
        s["index"] = i
        s.setdefault("short_title", short)
    actions = bool(c.get("actions"))
    from core import report_structure
    has_sources = bool(sources) and report_structure.has(c, "sources")
    has_support = bool(support) and report_structure.has(c, "support")
    has_caliber = (caliber is not None) and report_structure.has(c, "caliber")
    appendix = has_sources or has_support or has_caliber
    total = (3 + len(sections) + (1 if actions else 0)
             + (1 if has_sources else 0) + (1 if has_support else 0)
             + (1 if has_caliber else 0) + 1)
    page_of: Dict[str, int] = {}
    p = 4
    for s in sections:
        page_of[f's-{s["index"]}'] = p
        p += 1
    if actions:
        page_of["actions"] = p
        p += 1
    if has_sources:
        page_of["sources"] = p
        page_of["appendix"] = p
        p += 1
    if has_support:
        page_of["support"] = p
        page_of["appendix"] = page_of.get("appendix", p)
        p += 1
    if has_caliber:
        page_of["caliber"] = p
        page_of["appendix"] = page_of.get("appendix", p)
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
    if has_sources:
        parts.append(_sources_page(c, page_of["sources"], total))
    if has_support:
        parts.append(_support_page(c, page_of["support"], total, support=support))
    if has_caliber:
        cal_page = dict(caliber)
        cal_page["kicker"] = "口径"
        parts.append(_section(cal_page, page_of["caliber"], total, "图", "blocks"))
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

