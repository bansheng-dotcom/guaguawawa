# -*- coding: utf-8 -*-
"""S06 知识运营（能力域 6）。

来源：virgiliojr94__book-to-skill（书籍/文档 → 技能：支持类型白名单、
{author}-{concept} 命名、chNN 章节结构、SKILL.md <4000 token、
glossary/patterns/cheatsheet token 预算、sha256 指纹防重跑）
+ anthropics__knowledge-work-plugins/productivity/memory-management
（条目幂等检查：title+tags 指纹、尺寸 >150% 需拆分、过期刷新）
+ tobi__qmd（知识 store：collections + BM25 检索 + RRF 融合 k=60 + staleness 信任降权）。

确定性口径：token 预算、指纹、幂等、BM25/RRF 全部实算（纯标准库）。
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from skills import _common as c

NAME = "knowledge"
DESC = "知识运营：digest/entry/search"

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("digest", "文档→技能化门禁（类型白名单/命名/章节/token 预算/指纹）"),
                 ("entry", "知识条目登记（幂等指纹/尺寸拆分/过期检测）"),
                 ("search", "跨 collections 检索（BM25 + RRF 融合 + 过期降权）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"digest": _digest, "entry": _entry, "search": _search}[args.action]
    return fn(data)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(text: Any) -> int:
    """粗口径 token 估计：≈4 字符/token（对齐 graphify 的诚实规则）。"""
    return max(1, math.ceil(len(str(text)) / 4))


def _days_between(a: str, b: str) -> int:
    try:
        return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days
    except (ValueError, TypeError):
        return -1


# --------------------------------------------------------------------------- #
def _digest(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["knowledge"]
    src = data.get("source", {}) or {}
    stype = str(src.get("type", "")).lower().lstrip(".")
    checks: List[Dict[str, Any]] = []
    checks.append(c.ck(stype in th["supported_types"],
                       f"来源类型 {stype}（支持 {len(th['supported_types'])} 种）",
                       "type", "CRITICAL" if stype not in th["supported_types"]
                       else "OK"))
    slug = str(data.get("skill_slug", "")).strip()
    seg_ok = bool(_SLUG_RE.match(slug)) and len(slug.split("-")) >= th["slug_min_segments"]
    checks.append(c.ck(seg_ok, f"技能命名 {slug}（{th['slug_min_segments']}+ 段："
                       "{author}-{concept} 或主题 slug）", "slug",
                       "CRITICAL" if not seg_ok else "OK"))
    chapters = data.get("chapters", []) or []
    checks.append(c.ck(len(chapters) >= 1, "章节非空", "chapters",
                       "CRITICAL" if not chapters else "OK"))
    for i, ch in enumerate(chapters):
        secs = [s for s in ch.get("sections", []) or []
                if s in th["required_sections"]]
        if len(secs) < th["min_sections"]:
            checks.append(c.ck(False, f"章节「{ch.get('file', '')}」必含段落 "
                              f"{th['required_sections']} 中的 "
                              f"{th['min_sections']} 个，实际 {secs}",
                              "sections", "CRITICAL", item=i))
        tok = ch.get("tokens") or _tokens(ch.get("content", ""))
        if tok > th["chapter_token_max"]:
            checks.append(c.ck(False, f"章节「{ch.get('file', '')}」{tok} token 超"
                              f"预算 {th['chapter_token_max']}", "tokens",
                              "HIGH", item=i))
    # 编号连续：ch01-, ch02-, ...
    names = [str(ch.get("file", "")) for ch in chapters]
    nums = [int(m.group(1)) for n in names
            if (m := re.match(r"^ch(\d+)-", n))]
    if chapters and nums != list(range(1, len(chapters) + 1)):
        checks.append(c.ck(False, f"章节编号 {nums} 不连续（应 ch01..chNN）",
                           "numbering", "HIGH"))
    # token 预算四件套
    token_report: Dict[str, Any] = {}
    budgets = {"skill_md": th["skill_md_token_max"],
               "glossary.md": th["glossary_token_max"],
               "patterns.md": th["patterns_token_max"],
               "cheatsheet.md": th["cheatsheet_token_max"]}
    token_report["skill_md"] = data.get("skill_md_tokens",
                                        _tokens(data.get("skill_md", "")))
    for sf in data.get("supporting_files", []) or []:
        f = str(sf.get("file", ""))
        if f in budgets:
            tok = sf.get("tokens") or _tokens(sf.get("content", ""))
            token_report[f] = tok
    for f, tok in token_report.items():
        cap = budgets.get(f, budgets["skill_md"])
        checks.append(c.ck(tok <= cap, f"{f} {tok} token ≤ 预算 {cap}",
                           "tokens", "HIGH" if tok > cap else "OK", file=f))
    # 指纹（重跑防护）
    fp = _sha(f"{src.get('path', '')}|{stype}|{slug}")[:12]
    existing = data.get("existing_fingerprints", []) or []
    duplicate = fp in existing
    if duplicate:
        checks.append(c.ck(False, f"指纹 {fp} 已处理过（重跑需声明 foldin 合并模式）",
                           "fingerprint", "HIGH", fingerprint=fp))
    else:
        checks.append(c.ck(True, f"来源指纹 {fp}", "fingerprint", fingerprint=fp))
    return c.result(checks, chapters=len(chapters), token_report=token_report,
                    fingerprint=fp, duplicate=duplicate,
                    next="章节结构达标后生成 SKILL.md 入库")


# --------------------------------------------------------------------------- #
def _entry(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["knowledge"]
    title = str(data.get("title", "")).strip()
    tags = data.get("tags", []) or []
    content = str(data.get("content", ""))
    updated = str(data.get("updated", "")).strip()
    today = str(data.get("today", "")).strip()
    checks: List[Dict[str, Any]] = []
    checks.append(c.ck(bool(title), "条目标题", "title",
                       "CRITICAL" if not title else "OK"))
    checks.append(c.ck(len(tags) >= 1, f"标签 {len(tags)} 个（≥1，供检索过滤）",
                       "tags", "CRITICAL" if len(tags) < 1 else "OK"))
    sha = _sha(f"{title}|{'|'.join(sorted(str(t) for t in tags))}")
    existing = data.get("existing", []) or []
    existing_shas = {e.get("sha") for e in existing if e.get("sha")}
    duplicate = sha in existing_shas
    checks.append(c.ck(not duplicate,
                       f"幂等指纹 {sha[:12]}"
                       + ("（已存在，走更新合并而非重复登记）" if duplicate
                          else "（新条目）"), "idempotency",
                       "HIGH" if duplicate else "OK", duplicate=duplicate))
    # 尺寸检查：超过存量均值 150% → too_large，必须拆分
    existing_tokens = [_tokens(e.get("content", "")) for e in existing]
    too_large = False
    if existing_tokens:
        avg = sum(existing_tokens) / len(existing_tokens)
        cap = avg * th["too_large_growth_pct"] / 100
        too_large = _tokens(content) > cap
        checks.append(c.ck(not too_large,
                           f"尺寸 {_tokens(content)} token vs 存量均值 {round(avg, 1)}"
                           f"（上限 {round(cap, 1)}）", "size",
                           "HIGH" if too_large else "OK"))
    # 过期检查：>90 天未更新 → stale
    stale = bool(updated and today and _days_between(updated, today)
                 > th["staleness_days"])
    if updated and today:
        checks.append(c.ck(not stale,
                           f"更新于 {updated}（{th['staleness_days']} 天阈值）",
                           "staleness", "HIGH" if stale else "OK"))
    return c.result(checks, sha=sha, duplicate=duplicate, too_large=too_large,
                    stale=stale, tokens=_tokens(content),
                    next="新条目登记后可被 search 检索")


# --------------------------------------------------------------------------- #
def _tokenize(text: str) -> List[str]:
    """中英文混合分词：英文按词、中文按字符二元组（保证中文可命中）。"""
    words = re.findall(r"[a-z0-9]+", str(text).lower())
    cjk = re.findall(r"[\u4e00-\u9fff]", str(text))
    return words + cjk + [a + b for a, b in zip(cjk, cjk[1:])]


def _bm25_scores(query_tokens: List[str],
                 entries: List[Dict[str, Any]]) -> List[float]:
    th = c.load_thresholds()["knowledge"]
    k1, b = th["bm25_k1"], th["bm25_b"]
    docs = [_tokenize(" ".join([e.get("title", ""), " ".join(e.get("tags", [])),
                                e.get("content", "")])) for e in entries]
    n = len(docs) or 1
    avglen = sum(len(d) for d in docs) / n
    scores = []
    for doc in docs:
        s = 0.0
        for qt in set(query_tokens):
            tf = doc.count(qt)
            if not tf:
                continue
            df = sum(1 for d in docs if qt in d)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
            s += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * len(doc) / avglen))
        scores.append(round(s, 4))
    return scores


def _search(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["knowledge"]
    query = str(data.get("query", "")).strip()
    collections = data.get("collections", []) or []
    top_k = int(data.get("top_k") or th["default_top_k"])
    tag_filter = data.get("tag_filter")
    today = str(data.get("today", "")).strip()
    checks: List[Dict[str, Any]] = []
    checks.append(c.ck(bool(query), "检索词非空", "query",
                       "CRITICAL" if not query else "OK"))
    total_entries = sum(len(col.get("entries", []) or []) for col in collections)
    checks.append(c.ck(total_entries > 0, f"检索范围 {len(collections)} collections"
                       f" / {total_entries} 条", "corpus",
                       "CRITICAL" if total_entries == 0 else "OK"))
    q_tokens = _tokenize(query)
    # 每个(collection, entry)聚合：本地排名 → RRF 融合（k=60）→ 过期降权
    pool: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for col in collections:
        entries = col.get("entries", []) or []
        if tag_filter:
            entries = [e for e in entries if tag_filter in (e.get("tags") or [])]
        scores = _bm25_scores(q_tokens, entries)
        ranked = sorted(range(len(entries)), key=lambda i: -scores[i])
        for rank, idx in enumerate(ranked):
            e = entries[idx]
            key = (str(col.get("name", "")), str(e.get("title", "")))
            rrf = 1.0 / (th["rrf_k"] + rank + 1)
            stale = False
            if today and e.get("updated"):
                stale = _days_between(str(e["updated"]), today) > th["staleness_days"]
            weight = th["staleness_penalty"] if stale else 1.0
            if key in pool:
                pool[key]["rrf"] += rrf
                pool[key]["stale"] = pool[key]["stale"] or stale
            else:
                pool[key] = {"title": e.get("title", ""),
                             "collection": col.get("name", ""),
                             "tags": e.get("tags", []),
                             "local_score": scores[idx],
                             "rrf": rrf, "stale": stale,
                             "fused": round(rrf * weight, 6)}
    results = sorted(pool.values(), key=lambda r: -r["fused"])
    for r in results:
        r["fused"] = round(r["fused"], 6)
    results = results[:top_k]
    stale_count = sum(1 for r in results if r["stale"])
    checks.append(c.ck(len(results) > 0, f"命中 {len(results)} 条（top {top_k}）",
                       "hits", "HIGH" if not results else "OK"))
    checks.append(c.ck(True, f"RRF 融合 k={th['rrf_k']} · 过期降权 "
                       f"×{th['staleness_penalty']}（命中过期 {stale_count} 条）",
                       "ranking", stale_count=stale_count))
    return c.result(checks, results=results, top_k=top_k,
                    stale_count=stale_count,
                    next="命中条目随交接包分发给 DRI")
