# -*- coding: utf-8 -*-
"""可复用 flow 区块：小页脚、摘要元信息、紧凑来源表。"""
from __future__ import annotations

import html
from typing import Any, Iterable, List

ORG = "蛙蛙呱呱专家团"
DATE = "内部研究 · 2026 年 11 月"


def footer_html(logo: str = "", org: str = ORG, date: str = DATE) -> str:
    return (f'<footer class="flow-footer" id="back">{logo}'
            f'<div><b>{html.escape(org)}</b><span>{html.escape(date)}</span></div></footer>')


def summary_meta(rows: Iterable[tuple[str, str]]) -> str:
    rows = list(rows)
    if not rows:
        return ""
    return '<div class="sum-meta">' + "".join(
        f'<div><b>{html.escape(k)}</b>{html.escape(v)}</div>' for k, v in rows) + "</div>"


def compact_sources(rows: List[Any], per_col: int | None = None) -> str:
    """rows: (id,title,date) 或 (id,title,date,url)，也接受 contract 里的 dict 来源。"""
    items = []
    for r in rows:
        if isinstance(r, dict):
            sid = str(r.get("file") or r.get("id") or "")
            title = str(r.get("title") or r.get("url") or "")
            date = str(r.get("date") or r.get("period") or "")
        else:
            sid, title, date = str(r[0]), str(r[1]), str(r[2])
        items.append(f'<div class="src-row"><b>{html.escape(sid)}</b>'
                     f'<span>{html.escape(title)}</span><i>{html.escape(date)}</i></div>')
    half = per_col or (len(items) + 1) // 2
    return ('<section class="flow-block appendix" id="appendix">'
            '<div class="kick">附录 / EVIDENCE</div><h2>来源与数据文件</h2>'
            f'<p class="src-note">共 {len(items)} 条来源；日期为发布/检索日。</p>'
            f'<div class="src-grid"><div>{"".join(items[:half])}</div>'
            f'<div>{"".join(items[half:])}</div></div></section>')
