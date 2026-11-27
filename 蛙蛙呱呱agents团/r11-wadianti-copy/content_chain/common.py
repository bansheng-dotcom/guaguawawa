# -*- coding: utf-8 -*-
"""R11 内容链（7 段）公共层：工件读写、统一门禁结构、文本度量与确定性工具。

设计约束（对齐升级方案 §5 / §8 / §17.2）：
  - 每段只做一件事，产出一个可独立审计的 JSON 工件；
  - 门禁统一返回 ``{ok, grade, stage, checks, errors, blockers, warnings}``，
    ``ok=false`` 时 CLI 退出码非 0；
  - 时间只用于留痕（generated_at），不参与任何判断，保证同输入复算一致；
  - 只用标准库，不联网、不调用模型。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

STAGE_ORDER = ("topic", "research", "outline", "draft", "review", "rewrite", "final")

FILES = {
    "topic": "topic_candidates.json",
    "research": "research_pack.json",
    "outline": "outline.json",
    "draft": "drafts.json",
    "review": "review.json",
    "rewrite": "rewrite.json",
    "final": "final_audit.json",
}

# 门禁阈值：与 THICKNESS.md / 方案 §17.2 的 r11 表逐项对齐。
THRESHOLDS: Dict[str, Any] = {
    "topic": {"candidates": 10, "top_n": 3},
    "research": {"min_sources": 8, "min_quote": 12, "min_claims": 3},
    "outline": {"min_sections": 3, "max_sections": 5},
    "draft": {"candidates": 3, "min_diversity": 0.6, "min_score": 85},
    "review": {"dims": ["ai_flavor", "voice", "logic", "structure", "simplification"]},
    "rewrite": {"unit_min": 200, "unit_max": 400,
                "min_candidates": 2, "max_candidates": 4},
    "final": {"min_sections": 3, "max_fluff_per_1000": 0.5},
}

INTENT_ENUM = ("informational", "commercial", "transactional", "navigational")
TIER_ENUM = ("primary", "secondary", "tertiary")

# 公共轨道表达：写前统一删除，避免三份候选只在格式上不同。
COMMON_TRACK_PHRASES = ("需要指出的是，", "需要指出的是", "在这个意义上，",
                        "客观上来说，", "总而言之，")

# 兜底 AI 味词表（与 experience/thresholds.json 的 review.ai_fluff_words 合并）。
_FALLBACK_FLUFF = ("综上所述", "值得注意的是", "不难发现", "众所周知",
                   "毫无疑问", "显而易见", "简单来说", "说白了",
                   "从这个角度看", "换个角度看", "可以这样理解", "先给结论",
                   "有待进一步分析", "值得我们深思", "不可否认", "毋庸置疑",
                   "在此背景下", "越来越多的人", "随着科技的不断发展",
                   "需要我们注意的是", "需要关注的是", "归根结底", "总之",
                   "换句话说", "在这个时代", "赋能", "闭环", "抓手")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: str, data: Any) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def write_text(path: str, text: str) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 门禁结构
# --------------------------------------------------------------------------- #
def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **evidence: Any) -> Dict[str, Any]:
    d: Dict[str, Any] = {"ok": bool(ok), "msg": str(msg), "dim": dim, "sev": sev}
    d.update(evidence)
    return d


def grade(checks: Sequence[Dict[str, Any]]) -> str:
    if not checks:
        return "EMPTY"
    if all(x["ok"] for x in checks):
        return "PASS"
    if any(x["sev"] == "CRITICAL" and not x["ok"] for x in checks):
        return "FAIL"
    return "WARN"


def gate(checks: List[Dict[str, Any]], stage: str = "") -> Dict[str, Any]:
    """把检查清单压成统一门禁：只有 CRITICAL 失败才阻断。"""
    failed = [x for x in checks if not x["ok"]]
    blockers = [x for x in failed if x.get("sev") == "CRITICAL"]
    return {
        "ok": not blockers,
        "grade": grade(checks),
        "stage": stage,
        "checks": checks,
        "errors": [f"{x['dim']}: {x['msg']}" for x in failed],
        "blockers": [f"{x['dim']}: {x['msg']}" for x in blockers],
        "warnings": [f"{x['dim']}: {x['msg']}" for x in failed
                     if x.get("sev") != "CRITICAL"],
    }


def fail(msg: str, stage: str = "") -> Dict[str, Any]:
    return {"ok": False, "grade": "FAIL", "stage": stage,
            "checks": [ck(False, msg, "existence", "CRITICAL")],
            "errors": [msg], "blockers": [msg], "warnings": []}


def is_http_url(url: Any) -> bool:
    return isinstance(url, str) and bool(re.match(r"^https?://\S+$", url.strip()))


def is_date(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s.strip()):
        return False
    try:
        datetime.strptime(s.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# 文本度量
# --------------------------------------------------------------------------- #
def clean_text(text: Any) -> str:
    """去掉 Markdown 标记，保留正文。"""
    t = str(text or "")
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"^[#>\s]*", "", t, flags=re.M)
    t = re.sub(r"[*_~|]", "", t)
    return t


def char_len(text: Any) -> int:
    """正文字符数：去 Markdown 与空白后的长度。"""
    return len(re.sub(r"\s+", "", clean_text(text)))


def sentences(text: Any) -> List[str]:
    parts = re.split(r"(?<=[。！？!?；;])", str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def paragraphs(text: Any) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", str(text or "")) if p.strip()]


def number_tokens(text: Any) -> List[str]:
    """抽取阿拉伯数字（含小数），保持出现顺序。"""
    return re.findall(r"\d+(?:\.\d+)?", str(text or ""))


def number_set(text: Any) -> Set[str]:
    return set(number_tokens(text))


def contains_any(text: Any, tokens: Iterable[str]) -> bool:
    return any(t and t in str(text or "") for t in tokens)


def _bigrams(text: Any) -> Set[str]:
    s = re.sub(r"[\s\W_]+", "", str(text or "")).lower()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a: Any, b: Any) -> float:
    """字符二元组 Jaccard 相似度（0–1）。"""
    A, B = _bigrams(a), _bigrams(b)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    return round(len(A & B) / len(A | B), 4)


def diversity(texts: Sequence[str]) -> float:
    """多样性 = 1 − 两两相似度均值；用来判断三份候选是否只是换壳。"""
    if len(texts) < 2:
        return 1.0
    vals = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            vals.append(jaccard(texts[i], texts[j]))
    return round(1.0 - sum(vals) / len(vals), 4)


def max_similarity(texts: Sequence[str]) -> float:
    best = 0.0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            best = max(best, jaccard(texts[i], texts[j]))
    return round(best, 4)


def _load_fluff() -> List[str]:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, "experience", "thresholds.json")
    words: List[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        words = list((data.get("review") or {}).get("ai_fluff_words") or [])
    except (OSError, ValueError):
        words = []
    for w in _FALLBACK_FLUFF:
        if w not in words:
            words.append(w)
    return words


FLUFF_WORDS = _load_fluff()


def fluff_hits(text: Any) -> List[str]:
    t = str(text or "")
    return [w for w in FLUFF_WORDS if w in t]


def fluff_count(text: Any) -> int:
    t = str(text or "")
    return sum(t.count(w) for w in FLUFF_WORDS)


def fluff_density(text: Any) -> float:
    """每 1000 正文字符的套话命中数；无正文返回 0。"""
    n = char_len(text)
    if n <= 0:
        return 0.0
    return round(fluff_count(text) * 1000.0 / n, 3)


def strip_phrases(text: Any, phrases: Iterable[str]) -> str:
    t = str(text or "")
    for p in sorted([x for x in phrases if x], key=len, reverse=True):
        # 连同短语后面的逗号一起删，避免留下「，这一节」这类断头句。
        t = re.sub(re.escape(p) + r"[，,]?", "", t)
    t = re.sub(r"[，,]{2,}", "，", t)
    t = re.sub(r"[。；;]\s*[，,]", lambda m: m.group(0)[0], t)
    t = re.sub(r"^[，,。.\s]+", "", t)
    return t


def strip_common_tracks(text: Any) -> str:
    return strip_phrases(text, COMMON_TRACK_PHRASES)


def entities_in(text: Any, entities: Iterable[str]) -> List[str]:
    t = str(text or "")
    return sorted({e for e in entities if e and e in t})


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def ratio(num: float, den: float) -> float:
    return round(num / den, 4) if den else 0.0


def to_int(v: Any, default: int = 0) -> int:
    if isinstance(v, bool):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def source_index(research: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(s.get("id")): s for s in research.get("sources", [])}


def claim_index(research: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(c.get("claim_id")): c for c in research.get("claims", [])}


def claim_numbers(research: Dict[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for c in research.get("claims", []):
        for n in c.get("numbers", []) or []:
            out.update(number_tokens(n))
        out.update(number_tokens(c.get("statement", "")))
    return out


def section_ids(artifact: Dict[str, Any]) -> List[str]:
    secs = artifact.get("sections") or []
    return [str(s.get("id") or s.get("section_id") or "") for s in secs]
