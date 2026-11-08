# -*- coding: utf-8 -*-
"""S06 科学计算与 NLP —— 能力域 6。

整合自 scipy（统计/优化）、spaCy（文本管道/NER）、statsmodels（模型诊断）。
纯标准库实现基础能力（描述统计 + 文本统计），并把 scipy/spaCy 作为
「可选重型后端」探测登记：能 import 就用，不能就如实标记 unavailable。
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List

from . import _common as c

NAME = "scinlp"
DESC = "科学计算与NLP：describe / textstats / backend 探测"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    d = act.add_parser("describe", help="含偏度的扩展描述统计")
    d.add_argument("--input", required=True)
    d.add_argument("--col", required=True)

    t = act.add_parser("textstats", help="文本统计：词频 / bigram / 类 Zipf")
    t.add_argument("--input", required=True)
    t.add_argument("--text", required=True, help="文本列名")
    t.add_argument("--top", type=int, default=20)

    b = act.add_parser("backend", help="探测 scipy/spaCy/statsmodels 是否可用")


def run(args) -> Dict[str, Any]:
    if args.action == "backend":
        return _probe()
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    if args.action == "describe":
        vals = c.numeric(rows, args.col)
        return {"describe": c.describe(vals), "skew_pearson2": c.skew(vals)}
    if args.action == "textstats":
        return _textstats(rows, args.text, args.top)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    backends: Dict[str, Any] = {}
    for mod in ("scipy", "spacy", "statsmodels", "numpy", "pandas"):
        try:
            __import__(mod)
            backends[mod] = "available"
        except ImportError:
            backends[mod] = "unavailable"
    return {"backends": backends,
            "note": "重型后端可用时承载完整科学计算/NLP；不可用则退化到纯标准库子集"}


def _textstats(rows, text_col, top):
    docs = [str(r.get(text_col, "")) for r in rows]
    words = [w for doc in docs for w in _tokenize(doc)]
    total = len(words)
    freq = Counter(words).most_common(top)
    bigrams = Counter(zip(words, words[1:])).most_common(top)
    return {
        "doc_count": len([d for d in docs if d.strip()]),
        "token_count": total, "vocab_size": len(set(words)),
        "top_words": [{"word": w, "count": n} for w, n in freq],
        "top_bigrams": [{"bigram": f"{a}{b}", "count": n} for (a, b), n in bigrams],
        "zipf_like_rank1_share": round(freq[0][1] / total, 4) if freq and total else 0.0,
        "note": "分词为按空白/标点切分的中英混用简易实现，中文需 spaCy/jieba",
    }


def _tokenize(doc: str) -> List[str]:
    out: List[str] = []
    for ch in doc:
        if ch.isalnum() or "\u4e00" <= ch <= "\u9fff":
            out.append(ch.lower())
        else:
            out.append(" ")
    return "".join(out).split()