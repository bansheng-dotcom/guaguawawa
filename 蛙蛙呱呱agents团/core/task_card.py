# -*- coding: utf-8 -*-
"""core/task_card —— 任务卡 → 主表 / 主指标（决定「该问什么」）。

数据画像回答「能问什么」；任务卡回答「该问什么」。本模块把两者接起来：
  卡里的目标/范围/验收 → 关键词 → 给每张表、每个度量打分 → 选出主表与主指标。

不是硬编码业务，而是把「任务卡的词」与「数据的列名」对齐；
选不出来时明确返回 None，由调用方回落（而不是瞎猜）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# 业务词 → 数据列名的常见写法（只做同义对齐，不绑定具体表）
SYNONYMS = {
    "规模": ["size", "tam", "sales", "gmv", "revenue", "sheling", "retail", "amount", "总额", "零售"],
    "增速": ["growth", "yoy", "g", "增速", "同比", "增长"],
    "成本": ["cost", "price", "tco", "unit_price", "单价", "成本"],
    "结构": ["share", "pct", "ratio", "占比", "结构"],
    "差异": ["diff", "gap", "差"],
    "库存": ["stock", "inventory", "turnover", "库存", "周转"],
    "人口": ["pop", "population", "household", "人口", "户"],
    "集中": ["hhi", "cr", "concentration", "集中"],
}

STOP = set("的了和与及在是对将把为以于从到中上下内外个这那有要能会可以并而但其之者")


def load_card(path: str | Path) -> Dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    goal = str(raw.get("goal") or raw.get("objective") or raw.get("title") or "")
    scope = raw.get("scope") or raw.get("deliverable") or ""
    accept = raw.get("acceptance") or raw.get("acceptance_criteria") or ""
    if isinstance(accept, list):
        accept = "；".join(map(str, accept))
    text = " ".join([goal, str(scope), str(accept)])
    words = set(re.findall(r"[A-Za-z_]{2,}|[\u4e00-\u9fff]{2,4}", text))
    words = {w for w in words if w not in STOP}
    return {"title": raw.get("title") or goal[:30], "goal": goal, "raw": raw,
            "text": text, "words": words}


def _hits(words: set, target: str) -> int:
    t = target.lower()
    n = 0
    for w in words:
        wl = w.lower()
        if wl and wl in t:
            n += 1
            continue
        for biz, syn in SYNONYMS.items():
            if biz in w and any(s in t for s in syn):
                n += 1
                break
    return n


def select_focus(profile: Dict[str, Any], card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """给每张表/每个度量打分，返回主表、主指标、主维度与理由。"""
    words = card["words"]
    wants_trend = any(w in card["text"] for w in ("增速", "增长", "趋势", "变化", "每年"))
    best: Optional[Dict[str, Any]] = None
    for t in profile["tables"]:
        stem = Path(t["file"]).stem
        table_score = _hits(words, stem) * 3 + t["rows"] / 100.0
        if wants_trend and t["time"]:
            table_score += 3  # 任务问增速时，带时间轴的表优先
        for m in t["measures"]:
            if re.search(r"share|pct|ratio|占比", m, re.I):
                continue
            s = table_score + _hits(words, m) * 4
            if wants_trend and m in ("growth", "yoy", "g"):
                s += 2
            # 度量本身是主指标候选：数值列越"有信息"分越高
            if s > (best["score"] if best else -1):
                best = {"table": t, "measure": m,
                        "dimension": (t["dimensions"][0] if t["dimensions"] else None),
                        "score": round(s, 2),
                        "reason": f"表 {stem} 命中 {_hits(words, stem)} 个任务词，度量 {m} 命中 {_hits(words, m)} 个"}
    return best


def focus_brief_text(focus: Dict[str, Any], card: Dict[str, Any]) -> str:
    if not focus:
        return "任务卡未能对齐任何表/度量，按数据画像通用推导。"
    t = Path(focus["table"]["file"]).name
    return (f"任务卡「{card['title']}」对齐到主表 {t}、主指标 {focus['measure']}"
            f"{'、主维度 ' + focus['dimension'] if focus['dimension'] else ''}（{focus['reason']}）。")


if __name__ == "__main__":
    import sys
    from core.data_profile import profile_dir
    card = load_card(sys.argv[1])
    print(json.dumps(select_focus(profile_dir(sys.argv[2]), card), ensure_ascii=False, indent=1)[:1200])
