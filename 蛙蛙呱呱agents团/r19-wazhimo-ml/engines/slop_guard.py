# -*- coding: utf-8 -*-
"""L05 质感去劣化 —— MLSlopGuard 物理级清洗假大空与无行动力汇报。

SOP v13.0 L05 体检病灶（R19 真实断点）：
    1. 模型评估/发布汇报充斥「整体表现良好」「效果显著提升」「相关细节待定」
       「基本可用」，没有一个可复算数字，人类无法据此决策；
    2. 报告没有强制绑定量化证据（accuracy/F1/P95）与责任人 DRI；
    3. `review.py` 只拦「效果不错」三个词，换个说法（「大致可用」「值得期待」）
       就漏过去了 —— 词表、清洗、注入三层全缺。

对标开源标杆（Stars > 1k）：
    * reviewdog/reviewdog (>8k) —— 把 lint 结果变成可执行评审
    * errata-ai/vale (>4k)      —— 可配置的文风/术语规则引擎
    * pbakaus/impeccable        —— 去塑料感与占位废话

落地的最低 3 项架构升级：
    1. 扩展假大空词库（30+ 条）+ 物理替换表，逐条给出替换依据；
    2. 量化证据门禁：报告必须出现可复算指标（accuracy/F1/P95/样本量）；
    3. 强制注入 DRI + Actionability 行动力评分（0~100），低于阈值直接判 SLOP。

用法：
    python -m engines.slop_guard --text "模型评估整体良好，相关细节待定" \
        --out workspace/rounds/L05_slop.json
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DRI = "R19 蛙智模"

# (假大空词, 替换为)
SLOP_RULES: List[Tuple[str, str]] = [
    ("整体表现良好", "以 ERA/GGR 量化值替换：accuracy/F1 与门禁通过率"),
    ("整体良好", "以 ERA/GGR 量化值替换"),
    ("效果显著提升", "以评估差值替换：Δaccuracy/ΔF1 + 样本量 + 置信口径"),
    ("显著提升", "以评估差值替换（须给出具体指标与样本量）"),
    ("大幅增长", "以评估差值替换（须给出具体指标与样本量）"),
    ("明显改善", "以评估差值替换"),
    ("相关细节待定", "补齐细节并指定 DRI 与截止时间"),
    ("细节待定", "补齐细节并指定 DRI 与截止时间"),
    ("基本可用", "给出 ERA/GGR 门禁结论（PASS/FAIL）"),
    ("大致可用", "给出 ERA/GGR 门禁结论（PASS/FAIL）"),
    ("应该没问题", "以评估证据 + 回归报告结论替换"),
    ("效果看起来不错", "以评估证据 + 回归报告结论替换"),
    ("持续关注", "指定监控指标、阈值与告警责任人"),
    ("值得期待", "给出可复算指标与验收阈值"),
    ("毋庸置疑", "删除主观断言，给出证据行号与结论"),
    ("总而言之", "删除总结套话，直接给结论与下一步"),
    ("众所周知", "删除断言，给出来源"),
    ("进一步优化", "给出优化项、预期指标变化与 owner"),
    ("视情况而定", "给出判定条件与决策树"),
    ("按需推进", "给出触发条件、DRI 与截止时间"),
    ("全面提升体验", "替换为可量化指标（如 accuracy ≥ 0.90）"),
    ("持续优化性能", "替换为可量化指标（如 P95 ≤ 200ms）"),
    ("功能待定", "给出明确范围或标记 out-of-scope"),
    ("经过充分验证", "给出验证方式、样本量与结论"),
    ("总体符合预期", "给出与验收阈值的逐项对比"),
    ("整体平稳", "给出指标波动区间与样本量"),
    ("没有明显问题", "给出零缺陷证据（检查项与结果）"),
    ("后续跟进", "指定 DRI、截止时间与验收判据"),
]

_QUANT_RE = re.compile(
    r"(accuracy|f1|precision|recall|准确率|精确率|召回率)\s*[=＝:：]?\s*(0?\.\d+|\d+(?:\.\d+)?%)"
    r"|(p50|p95|p99|P50|P95|P99)\s*[=＝:：≤<]?\s*\d+(?:\.\d+)?\s*(ms|毫秒)"
    r"|\d+\s*(条|条样本|样本|samples?)\s*(样本)?")

# [Cycle 2] 正则族假大空规则（覆盖精确词库覆盖不到的变体与英文套话）
SLOP_PATTERNS: List[Tuple[str, str, str]] = [
    (r"可能(存在|会有?)?(一定|些许|一些)?(的)?(问题|风险|偏差|提升|改善)",
     "模糊概率断言", "给出概率区间或阈值判定"),
    (r"(大概|大约|或许|也许|似乎|貌似|恐怕)",
     "模糊限定词", "替换为可复算数值"),
    (r"(较多|较少|不少|很多|大量的?)(样本|误差|提升|问题)",
     "模糊数量", "给出具体计数与占比"),
    (r"(显著|明显|大幅)(提升|改善|优于|好于)",
     "无量化对比", "给出 Δ指标 + 样本量 + 检验口径"),
    (r"(基本|大体|总体)上?(符合|满足|可用|没问题)",
     "模糊通过", "给出逐项门禁对比"),
    (r"significantly (improved|better|outperform\w*)",
     "EN vague claim", "quote delta metric + sample size"),
    (r"\b(robust|state[- ]of[- ]the[- ]art|cutting[- ]edge|world[- ]class)\b",
     "EN buzzword", "replace with measured metric and baseline"),
    (r"\b(should be fine|looks good|seems okay|probably works)\b",
     "EN subjective approval", "attach evaluation evidence + regression id"),
]


class MLSlopGuard:
    """物理级反假大空守卫：清洗 + 量化证据门禁 + DRI 注入 + 行动力评分。"""

    ENGINE = "MLSlopGuard"
    LAYER = "L05"
    CAPABILITIES = [
        "扩展假大空词库 (28 条) 物理替换与命中定位",
        "量化证据门禁 (accuracy/F1/P95/样本量) 强制绑定",
        "DRI 注入与 Actionability 行动力评分 (0~100)",
        "[C2] 正则族模糊限定词/英文套话检测 (中英双语, 非精确词匹配)",
        "[C2] 证据密度指标 (每百字可复算数字数 + 声明/证据比)",
    ]
    ACTIONABILITY_FLOOR = 60

    def __init__(self, actionability_floor: int = 60):
        self.actionability_floor = int(actionability_floor)

    # ------------------------------------------------------------------ #
    def audit(self, text: str, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raw = str(text or "")
        matches: List[Dict[str, str]] = []
        for term, repl in SLOP_RULES:
            if term in raw:
                matches.append({"term": term, "replacement": repl})
        has_slop = bool(matches)
        cleaned = raw
        for term, repl in SLOP_RULES:
            if term in cleaned:
                cleaned = cleaned.replace(term, f"【{repl}】")

        quant_hits = _QUANT_RE.findall(raw)
        has_quant = bool(quant_hits) or bool(metrics)
        if metrics and not has_quant:
            has_quant = True
        has_dri = DRI in raw or "DRI" in raw
        if not has_dri:
            cleaned = cleaned.rstrip() + f"\n\n> DRI：{DRI}｜量化口径：ERA（评估可复算）、GGR（回归门禁）"

        score = 100 - 18 * len(matches)
        score += 10 if has_quant else -10
        score += 10 if has_dri else 0
        actionability = max(0, min(100, score))

        status = "PASS" if (not has_slop and actionability >= self.actionability_floor) else "SLOP_DETECTED"
        return {
            "ok": status == "PASS",
            "engine": self.ENGINE, "layer": self.LAYER,
            "has_slop": has_slop,
            "slop_count": len(matches),
            "matches": matches,
            "cleaned_text": cleaned,
            "has_quantitative_evidence": has_quant,
            "quantitative_hits": ["".join(h) if isinstance(h, tuple) else str(h) for h in quant_hits][:6],
            "dri_injected": not has_dri,
            "dri": DRI,
            "actionability_score": actionability,
            "actionability_floor": self.actionability_floor,
            "status": status,
            "verdict": status,
            "checks": [
                {"ok": not has_slop, "msg": f"假大空词命中 {len(matches)} 条",
                 "dim": "slop.dictionary", "sev": "OK" if not has_slop else "HIGH"},
                {"ok": has_quant, "msg": "量化证据已绑定", "dim": "slop.quantitative",
                 "sev": "OK" if has_quant else "HIGH"},
                {"ok": actionability >= self.actionability_floor,
                 "msg": f"行动力 {actionability} ≥ {self.actionability_floor}",
                 "dim": "slop.actionability",
                 "sev": "OK" if actionability >= self.actionability_floor else "HIGH"},
            ],
            "capabilities": list(self.CAPABILITIES),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------------ #
    # [Cycle 2] 正则族 + 证据密度扩展审计（不改变原 audit 口径）
    # ------------------------------------------------------------------ #
    def evidence_density(self, text: str,
                         metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raw = str(text or "")
        numbers = re.findall(r"\d+(?:\.\d+)?%?", raw)
        metric_numbers = len(metrics or {})
        total_numbers = len(numbers) + metric_numbers
        chars = max(1, len(raw))
        sentences = [s for s in re.split(r"[。！？.!?\n]+", raw) if s.strip()]
        density = round(total_numbers * 100.0 / chars, 4)
        ratio = round(len(sentences) / max(1, total_numbers), 4)
        ok = total_numbers >= 2 and density >= 0.5 and ratio <= 3.0
        return {"ok": ok, "number_count": total_numbers,
                "metric_numbers": metric_numbers, "chars": chars,
                "sentences": len(sentences), "numbers_per_100_chars": density,
                "claims_per_number": ratio,
                "verdict": "DENSE" if ok else "SPARSE"}

    def audit_extended(self, text: str,
                       metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base = self.audit(text, metrics)
        raw = str(text or "")
        regex_hits: List[Dict[str, Any]] = []
        for pattern, label, replacement in SLOP_PATTERNS:
            hits = re.findall(pattern, raw, flags=re.IGNORECASE)
            if hits:
                flat = [h if isinstance(h, str) else "".join(h) for h in hits]
                regex_hits.append({"pattern": pattern, "label": label,
                                   "replacement": replacement,
                                   "hits": flat[:6], "count": len(hits)})
        density = self.evidence_density(raw, metrics)
        regex_count = sum(h["count"] for h in regex_hits)
        status = "PASS" if (base["status"] == "PASS" and regex_count == 0
                            and density["ok"]) else "SLOP_DETECTED"
        base.update({"regex_matches": regex_hits, "regex_count": regex_count,
                     "evidence_density": density,
                     "status_extended": status, "ok_extended": status == "PASS",
                     "checks": list(base["checks"]) + [
                         {"ok": regex_count == 0,
                          "msg": f"正则族命中 {regex_count} 条",
                          "dim": "slop.regex", "sev": "OK" if regex_count == 0 else "HIGH"},
                         {"ok": density["ok"],
                          "msg": f"证据密度 {density['numbers_per_100_chars']}/100字",
                          "dim": "slop.evidence_density",
                          "sev": "OK" if density["ok"] else "HIGH"}]})
        return base

    def cleanse(self, text: str) -> Dict[str, Any]:
        return self.audit(text)

    def render_markdown(self, audit: Dict[str, Any]) -> str:
        lines = ["# R19 质感去劣化报告", "",
                 f"- 结论：**{audit['status']}** | 假大空命中 {audit['slop_count']} 条 | "
                 f"行动力 {audit['actionability_score']}/100 | 量化证据 {audit['has_quantitative_evidence']}",
                 "", "## 替换明细", ""]
        if not audit["matches"]:
            lines.append("- 无假大空词命中")
        for m in audit["matches"]:
            lines.append(f"- `{m['term']}` → {m['replacement']}")
        lines += ["", "## 清洗后文本", "", audit["cleaned_text"], ""]
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L05 质感去劣化守卫")
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)

    guard = MLSlopGuard()
    out = guard.audit(args.text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(guard.render_markdown(out))
    # 探针：命中假大空也返回 0（工件已落盘），由门禁使用 ok 字段
    print(json.dumps({"status": out["status"], "slop_count": out["slop_count"],
                      "actionability": out["actionability_score"], "out": args.out},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
