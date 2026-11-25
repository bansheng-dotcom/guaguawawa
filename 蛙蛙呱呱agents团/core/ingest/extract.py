# -*- coding: utf-8 -*-
"""Extractor 层：干净文本 → 记录。只认结构，不认业务。

三种抽取（降级链，与方案 §5 一致）：
    json   按点路径取数组（最稳，优先）
    table  HTML 表格 → 行（标准库 html.parser）
    regex  命名分组正则（兜底）

字段级异常不吞（C-5）：解析失败的行进 `dropped`，带 reason，
不许把半行数据当正常行交给下游。
"""
from __future__ import annotations

import json
import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple


def _json_path(node: Any, path: str) -> Any:
    cur = node
    for part in [p for p in str(path or "").split(".") if p]:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def _as_records(node: Any) -> List[Dict[str, Any]]:
    if isinstance(node, list):
        out = []
        for x in node:
            if isinstance(x, dict):
                out.append(x)
            elif isinstance(x, (str, int, float)):
                out.append({"value": x})
        return out
    if isinstance(node, dict):
        return [node]
    return []


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: List[List[str]] = []
        self.th_rows: set = set()
        self._row: List[str] = []
        self._cell: List[str] = []
        self._in_cell = False
        self._row_has_th = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
            self._row_has_th = False
        elif tag in ("td", "th"):
            self._cell = []
            self._in_cell = True
            if tag == "th":
                self._row_has_th = True

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._row.append("".join(self._cell).strip())
            self._in_cell = False
        elif tag == "tr":
            if any(x for x in self._row):
                if self._row_has_th:
                    self.th_rows.add(len(self.rows))
                self.rows.append(self._row)

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)


def extract_records(text: str, schema: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """→ (records, dropped)。dropped 每项带 reason。"""
    fmt = str((schema or {}).get("format") or "").lower()
    dropped: List[Dict[str, Any]] = []
    if not fmt:
        fmt = "json" if str(text).lstrip()[:1] in ("{", "[") else "table"

    if fmt == "json":
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            return [], [{"reason": "json_invalid", "detail": str(exc)}]
        node = _json_path(doc, str(schema.get("path") or ""))
        recs = _as_records(node)
        if not recs:
            dropped.append({"reason": "json_empty", "detail": str(schema.get("path") or "")})
        return recs, dropped

    if fmt == "table":
        p = _TableParser()
        try:
            p.feed(text)
        except Exception as exc:  # noqa: BLE001
            return [], [{"reason": "html_invalid", "detail": str(exc)}]
        rows = p.rows
        header = [str(x) for x in (schema.get("header") or [])]
        start = 0
        if header:
            # 调用方给了表头 → 表头行（含 <th>）不是数据
            rows = [r for i, r in enumerate(rows) if i not in p.th_rows]
        elif rows:
            header, start = rows[0], 1
        recs: List[Dict[str, Any]] = []
        for i, r in enumerate(rows[start:], start):
            if header and len(r) < len(header):
                dropped.append({"reason": "row_short", "row": i,
                                "detail": "%d < %d" % (len(r), len(header))})
                continue
            recs.append({(header[j] if j < len(header) else "c%d" % j): v
                         for j, v in enumerate(r)})
        if not recs:
            dropped.append({"reason": "table_empty"})
        return recs, dropped

    if fmt == "regex":
        pat = str(schema.get("pattern") or "")
        if not pat:
            return [], [{"reason": "regex_missing_pattern"}]
        out = []
        for m in re.finditer(pat, text, re.S):
            out.append(dict(m.groupdict()))
        if not out:
            dropped.append({"reason": "regex_no_match"})
        return out, dropped

    return [], [{"reason": "format_unknown", "detail": fmt}]


def iter_page_urls(query: Dict[str, Any], pagination: Dict[str, Any] | None,
                   max_pages: int = 20) -> List[str]:
    """把一个采集 spec 的 query 展开成 URL 列表（单页 / 列表 / 页码模板）。"""
    pg = pagination or {}
    start = int(pg.get("start") or 1)
    stop = int(pg.get("stop") or start)
    step = int(pg.get("step") or 1)
    cap = max(1, min(int(max_pages or 20), max(1, (stop - start) // max(step, 1) + 1)))
    urls: List[str] = []
    if query.get("urls"):
        urls = [str(x) for x in query["urls"]]
    elif pg.get("url_template"):
        tpl = str(pg["url_template"])
        for i, page in enumerate(range(start, stop + 1, step)):
            if i >= cap:
                break
            urls.append(tpl.replace("{page}", str(page)))
    elif query.get("url"):
        base = str(query["url"])
        if not pg.get("param"):
            return [base]
        for i, page in enumerate(range(start, stop + 1, step)):
            if i >= cap:
                break
            sep = "&" if urllib.parse.urlsplit(base).query else "?"
            urls.append("%s%s%s=%d" % (base, sep, pg["param"], page))
    return urls
