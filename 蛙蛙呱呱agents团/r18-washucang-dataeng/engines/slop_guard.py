# -*- coding: utf-8 -*-
"""L05 质感去劣化 —— 数据管道报告的假大空物理清洗（DataEngSlopGuard）。

病灶（体检结论）：升级前 R18 的交付文本没有任何反套话闸门——模板一漂移写出
「整体良好」「按需采购」「视情况而定」「相关细节待定」「持续关注」，也没有
可复算的行动力分值可供验收，人类读完仍不知道「谁负责、何时闭环、缺哪些实测」。

对标标杆（Stars > 1k）：
- `reviewdog/reviewdog`（> 8k）：把 lint 结果变成可执行的 CI 阻断；
- `errata-ai/vale`（> 4k）：可配置文风规则 + 词表替换；
- `textlint/textlint`（> 2k）：规则驱动的内容质检。

本引擎落地（严格区分「指标目标」与「实测值」）：
1. `audit`：逐条定位套话（term + 行号 + 偏移），并给出 Actionability 分值；
2. `clean`：把套话物理替换为**可行动表述**（量化目标 / 待实测清单 / DRI / 截止期）。
   绝不凭空生成实测值——替换文本里出现的数字只允许是「目标值 / 策略参数 / 截止期」，
   实测数字只能由调用方通过 facts 传入；
3. `actionability_score`：无数字 −20、无 DRI −15、每个套话 −12，下限 0，上限 100。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# 套话词库：只做「可行动重述」，不伪造任何实测值。
SLOP_TERMS: List[Dict[str, str]] = [
    {"term": "相关细节待定", "dim": "placeholder",
     "replacement": "剩余项须清单化，由 DRI 蛙数仓（R18）在 T+1 10:00 前闭环并回填实测值"},
    {"term": "细节待定", "dim": "placeholder",
     "replacement": "剩余项须清单化，由 DRI 蛙数仓（R18）在 T+1 10:00 前闭环"},
    {"term": "值得重点关注", "dim": "vague_priority",
     "replacement": "须给出影响面（涉及表数 / 字段数 / SLA 影响），DRI 蛙数仓（R18）"},
    {"term": "视情况而定", "dim": "no_criteria",
     "replacement": "按 G4 质量门禁判定（目标：空值率≤0.10、重复率≤0.05、越界=0）"},
    {"term": "按需采购", "dim": "no_policy",
     "replacement": "按 ROP 再订货点 + 3 天安全库存策略执行，DRI 蛙数仓（R18）"},
    {"term": "持续关注", "dim": "no_action",
     "replacement": "按 DATAENG_SPEC 目标 MTTD≤15min 告警 + 每日 09:00 复核"},
    {"term": "整体良好", "dim": "empty_judgement",
     "replacement": "实测指标未采集：须回填 PSR / FSR / 空值率后按 G1~G8 重判"},
    {"term": "整体正常", "dim": "empty_judgement",
     "replacement": "实测指标未采集：须回填 PSR / DQR 后按 G1~G8 重判"},
    {"term": "基本正常", "dim": "empty_judgement",
     "replacement": "8 维发布门禁须以实测结果判定（G1~G8），不得以整体评价替代"},
    {"term": "基本可用", "dim": "empty_judgement",
     "replacement": "可用性须以 G4 门禁实测（空值率 / 重复率 / 越界）判定"},
    {"term": "大幅提升", "dim": "fake_growth",
     "replacement": "增幅未复算：禁止无源百分比，须提供两期实测值与样本量后重述"},
    {"term": "显著提升", "dim": "fake_growth",
     "replacement": "显著性未检验：须提供两期实测值与检验结果，且移交 R06 解读"},
    {"term": "全面提升", "dim": "fake_growth",
     "replacement": "须以 G1~G8 逐项实测结果替代整体性表述"},
    {"term": "加强合规", "dim": "no_metric",
     "replacement": "合规率须以 BCR 实测值回填（目标 100%），DRI 蛙数仓（R18）"},
    {"term": "高度重视", "dim": "no_action",
     "replacement": "已列入 T+1 排期，DRI 蛙数仓（R18），T+1 10:00 前给出实测闭环"},
    {"term": "暂无异常", "dim": "no_measure",
     "replacement": "异常数须以 G4 实测回填（目标 0），未采集前不得下结论"},
    {"term": "待定", "dim": "placeholder",
     "replacement": "由 DRI 蛙数仓（R18）在 T+1 10:00 前闭环并回填实测值"},
]

_DEFAULT_FACTS: Dict[str, Any] = {
    "dri": "蛙数仓（R18）",
    "deadline": "T+1 10:00",
}

_MIN_ACTIONABILITY = 70
_DRI_RE = re.compile(r"蛙数仓|DRI|R18")


class DataEngSlopGuard:
    """L05 反套话守卫：定位 → 可行动重述 → 行动力评分。"""

    def __init__(self, facts: Optional[Dict[str, Any]] = None):
        self.facts = dict(_DEFAULT_FACTS)
        self.facts.update(facts or {})

    # ------------------------------------------------------------------ #
    # 评分
    # ------------------------------------------------------------------ #
    def actionability_score(self, text: str, hits: Optional[List[Dict[str, Any]]] = None) -> int:
        raw = str(text or "")
        hits = self.audit(raw)["hits"] if hits is None else hits
        distinct = {h["term"] for h in hits}
        score = 100 - 12 * len(distinct)
        if not re.search(r"\d", raw):
            score -= 20
        if not _DRI_RE.search(raw):
            score -= 15
        return max(0, min(100, score))

    # ------------------------------------------------------------------ #
    # 审计
    # ------------------------------------------------------------------ #
    def audit(self, text: str) -> Dict[str, Any]:
        raw = str(text or "")
        hits: List[Dict[str, Any]] = []
        covered: List[tuple] = []
        # 长词优先：已被更长套话覆盖的区间不重复计数
        for item in sorted(SLOP_TERMS, key=lambda x: -len(x["term"])):
            term = item["term"]
            start = 0
            while True:
                idx = raw.find(term, start)
                if idx < 0:
                    break
                end = idx + len(term)
                if not any(s < end and idx < e for s, e in covered):
                    covered.append((idx, end))
                    line = raw.count("\n", 0, idx) + 1
                    hits.append({
                        "term": term, "dim": item["dim"], "index": idx,
                        "line": line,
                        "severity": "HIGH" if item["dim"] in
                        ("empty_judgement", "placeholder", "fake_growth") else "MEDIUM",
                    })
                start = idx + 1
        hits.sort(key=lambda h: h["index"])
        score = self.actionability_score(raw, hits)
        has_dri = bool(_DRI_RE.search(raw))
        ok = bool(raw) and not hits and score >= _MIN_ACTIONABILITY and has_dri
        return {
            "ok": ok,
            "has_slop": bool(hits),
            "hits": hits,
            "terms_found": sorted({h["term"] for h in hits}),
            "actionability_score": score,
            "has_dri": has_dri,
            "grade": "PASS" if ok else "FAIL",
            "checks": [
                {"ok": not hits, "dim": "slop.terms",
                 "msg": f"套话命中 {len(hits)} 处", "sev": "OK" if not hits else "HIGH"},
                {"ok": score >= _MIN_ACTIONABILITY, "dim": "slop.actionability",
                 "msg": f"行动力分值 {score} >= {_MIN_ACTIONABILITY}",
                 "sev": "OK" if score >= _MIN_ACTIONABILITY else "HIGH"},
                {"ok": has_dri, "dim": "slop.dri",
                 "msg": "责任主体 DRI 已声明" if has_dri else "缺 DRI（谁负责不明确）",
                 "sev": "OK" if has_dri else "MEDIUM"},
            ],
        }

    # ------------------------------------------------------------------ #
    # 清洗（只重述，不造数）
    # ------------------------------------------------------------------ #
    def _measured_clause(self, facts: Dict[str, Any]) -> str:
        """只把调用方显式传入的实测值写进正文；未传入的一律不出现。"""
        measured = facts.get("measured") or {}
        if not isinstance(measured, dict):
            return ""
        parts = [f"{k}={v}" for k, v in measured.items() if v not in (None, "", "未采集")]
        return ("实测值：" + "、".join(parts) + "；") if parts else ""

    def clean(self, text: str, facts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raw = str(text or "")
        before = self.audit(raw)
        merged = dict(self.facts)
        merged.update(facts or {})
        measured_clause = self._measured_clause(merged)

        cleaned = raw
        replaced: List[Dict[str, Any]] = []
        # 长词优先替换，避免「相关细节待定」被「细节待定」拆碎
        for item in sorted(SLOP_TERMS, key=lambda x: -len(x["term"])):
            term = item["term"]
            if term not in cleaned:
                continue
            replacement = item["replacement"].replace("蛙数仓（R18）", str(merged["dri"]))
            replacement = replacement.replace("T+1 10:00", str(merged["deadline"]))
            count = cleaned.count(term)
            cleaned = cleaned.replace(term, replacement)
            replaced.append({"term": term, "count": count, "replacement": replacement})

        if measured_clause and cleaned and not cleaned.startswith(measured_clause):
            cleaned = measured_clause + cleaned
        if cleaned and not _DRI_RE.search(cleaned):
            cleaned = cleaned.rstrip() + f"（DRI：{merged['dri']}）"

        after = self.audit(cleaned)
        return {
            "ok": bool(after["ok"]),
            "cleaned": cleaned,
            "replaced": replaced,
            "before": {"has_slop": before["has_slop"],
                       "actionability_score": before["actionability_score"],
                       "terms_found": before["terms_found"]},
            "after": {"has_slop": after["has_slop"],
                      "actionability_score": after["actionability_score"],
                      "terms_found": after["terms_found"],
                      "has_dri": after["has_dri"]},
            "grade": after["grade"],
        }


# --------------------------------------------------------------------------- #
# CLI：python -m engines.slop_guard --text "..." --out ...
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L05 反套话守卫")
    ap.add_argument("--text", default="", help="待审文本")
    ap.add_argument("--input", default="", help="待审文本文件（UTF-8）")
    ap.add_argument("--out", default="", help="结果 JSON 输出路径")
    ap.add_argument("--clean", action="store_true", help="执行物理清洗并输出 cleaning")
    args = ap.parse_args(argv)

    text = args.text
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    guard = DataEngSlopGuard()
    result: Dict[str, Any] = guard.audit(text)
    if args.clean:
        result["cleaning"] = guard.clean(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": result["ok"], "has_slop": result["has_slop"],
         "terms_found": result["terms_found"],
         "actionability_score": result["actionability_score"],
         "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
