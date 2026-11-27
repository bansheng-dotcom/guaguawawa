# -*- coding: utf-8 -*-
"""core.prose.prose_contract —— 正文契约（11 字段）+ 文笔/深度门禁。

P5-7（2026-11-27）五合一：原 `prose_spec` 与 `prose_style` 合并到本模块。
产物语义不变：字段名、阈值、判据、JSON 键都不改，只是不再分两个文件。

契约（spec）：
    每节 11 字段固定写死，少一个字段就会退回三段套话。
    facts.SECTIONS 必填：verdict、question
    prose_specs     必填：fact、evidence、mechanism、alternative、signal、
                          implication、action、stop、boundary

门禁（style）：
    只量页内正文；阈值见 configs/report_prose.yaml，兜底只来自
    `report_contract.prose_defaults()`（P5-2 单一出处）。

CLI：
    python -m core.prose.prose_contract --html <report.html>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.report.report_contract import prose_defaults

# --------------------------------------------------------------------------- #
# 1. 11 字段契约
# --------------------------------------------------------------------------- #
FIELDS = ("fact", "evidence", "mechanism", "alternative", "signal",
          "implication", "action", "stop", "boundary")
SECTION_FIELDS = ("verdict", "question")
LABELS = {
    "verdict": "判断", "question": "这一节回答谁的问题",
    "fact": "事实", "evidence": "证据", "mechanism": "机理",
    "alternative": "替代解释", "signal": "判别信号", "implication": "含义",
    "action": "动作", "stop": "停止线", "boundary": "边界",
}
MIN_TEXT = 4


def validate(specs: Dict[str, Dict[str, Any]],
             sections: Iterable[Dict[str, Any]]) -> List[str]:
    """返回问题清单；空列表才算 11 字段齐。"""
    errs: List[str] = []
    secs = list(sections)
    ids = {str(s.get("id") or "") for s in secs}
    unknown = sorted(set(specs) - ids)
    if unknown:
        errs.append("spec 有 facts 里不存在的节：" + "、".join(unknown))
    for s in secs:
        sid = str(s.get("id") or "")
        for f in SECTION_FIELDS:
            if len(str(s.get(f) or "").strip()) < MIN_TEXT:
                errs.append(f"{sid}: facts 缺 {f}（{LABELS[f]}）")
        sp = specs.get(sid)
        if sp is None:
            errs.append(f"{sid}: 缺 spec")
            continue
        for f in FIELDS:
            if len(str(sp.get(f) or "").strip()) < MIN_TEXT:
                errs.append(f"{sid}: spec 缺 {f}（{LABELS[f]}）")
    return errs


# --------------------------------------------------------------------------- #
# 2. 文笔 / 深度门禁
# --------------------------------------------------------------------------- #
# 兜底值与 configs/report_prose.yaml 对齐（P5-2：阈值只在一个地方写死）。
DEFAULTS = prose_defaults()


def load_policy(path: str | Path | None = None) -> Dict[str, Any]:
    p = Path(path) if path else Path(__file__).resolve().parents[2] / "configs" / "report_prose.yaml"
    data = dict(DEFAULTS)
    if p.exists():
        try:
            import yaml
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            data.update(raw.get("prose") or {})
            data["banned_phrases"] = raw.get("banned_phrases") or []
            data["rubric"] = raw.get("rubric") or DEFAULTS["rubric"]
        except Exception:
            pass
    return data


def _sections(html: str) -> List[str]:
    return re.findall(r'<section class="[^"]*\bsec\b[^"]*"[^>]*>(.*?)</section>', html, re.S)


def _text(fragment: str) -> str:
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", t).strip()


def audit_section(text: str, policy: Dict[str, Any] | None = None,
                  table_only: bool = False) -> Dict[str, Any]:
    pol = policy or load_policy()
    n = len(re.sub(r"\s", "", text))
    nums = len(re.findall(r"\d+(?:\.\d+)?", text))
    per1000 = nums / max(n, 1) * 1000
    blocks = [b for b in pol["required_blocks"] if b in text]
    markers = sum(text.count(m) for m in pol["markers"])
    contrast = sum(text.count(m) for m in pol["contrast_markers"])
    banned = [b for b in pol.get("banned_phrases") or [] if b in text]
    suoyi = len(re.findall(r"(?:^|[。；\s])所以[：:，,]", text))
    issues = []
    if n < int(pol.get("chars_hard_min", 850)):
        issues.append(f"字数 {n} < 硬下限 {pol.get('chars_hard_min', 850)}")
    if len(blocks) < len(pol["required_blocks"]) - 1:
        issues.append(f"缺段块: {set(pol['required_blocks']) - set(blocks)}")
    if banned:
        issues.append("禁用词: " + ", ".join(banned))
    if n and per1000 < pol["numbers_per_1000_chars_min"]:
        issues.append(f"数字密度 {per1000:.0f}/千字 < {pol['numbers_per_1000_chars_min']}")
    if suoyi > 1:
        issues.append(f"「所以」段 {suoyi} > 1")
    # 分数：长度 40 + 段块 20 + 判别 10 + 对比 10 + 数字 20
    lo, hi = pol["chars_table_section"] if table_only else pol["chars_per_section"]
    length = 40 if n >= min(lo, 900) else 30 if n >= int(pol.get("chars_hard_min", 850)) else 0
    block = 20 if len(blocks) == len(pol["required_blocks"]) else 10 if len(blocks) >= 3 else 0
    score = length + block + (10 if markers else 0) + (10 if contrast else 0) + (20 if per1000 >= 35 else 10)
    score = max(0, min(100, score - 20 * len(banned)))
    return {"chars": n, "numbers": nums, "numbers_per_1000": round(per1000, 1),
            "markers": markers, "contrast": contrast, "blocks": blocks,
            "banned": banned, "suoyi": suoyi, "score": score, "issues": issues,
            "hard": n < int(pol.get("chars_hard_min", 850)) or bool(banned)}


def audit_html(html: str, policy: Dict[str, Any] | None = None,
               skip_titles: tuple = ()) -> Dict[str, Any]:
    pol = policy or load_policy()
    secs = _sections(html)
    rows = []
    for i, s in enumerate(secs, 1):
        # 延伸发现/附录这类清单节不是论证节：按「逐节字数下限」硬判会把
        # 一条一条的信号清单判成薄稿。跳过它们，但仍计入 sections 计数。
        head = _text(s)[:60]
        if any(str(t) and str(t)[:30] in head for t in skip_titles):
            continue
        table_only = 'class="ex"' in s and "<svg" not in s
        rows.append({"index": i, **audit_section(_text(s), pol, table_only)})
    avg = sum(r["chars"] for r in rows) / max(len(rows), 1)
    total_markers = sum(r["markers"] for r in rows)
    total_contrast = sum(r["contrast"] for r in rows)
    bonus = 0
    if rows and total_markers / len(rows) >= 0.5:
        bonus += 5
    if rows and total_contrast / len(rows) >= 0.5:
        bonus += 5
    score = min(100, sum(r["score"] for r in rows) / max(len(rows), 1) + bonus)
    hard = [r for r in rows if r["hard"]]
    return {"ok": not hard and score >= pol["rubric"]["pass"],
            "sections": len(rows), "avg_chars": round(avg, 1),
            "score": round(score, 1), "hard_fail": [r["index"] for r in hard],
            "markers_total": total_markers, "contrast_total": total_contrast,
            "bonus": bonus, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="prose_contract")
    ap.add_argument("--html", required=True)
    ap.add_argument("--config")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = audit_html(Path(a.html).read_text(encoding="utf-8", errors="replace"),
                     load_policy(a.config))
    out = Path(a.json) if a.json else Path(a.html).parent / "prose_gate.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("ok", "sections", "avg_chars", "score", "hard_fail")},
                     ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
