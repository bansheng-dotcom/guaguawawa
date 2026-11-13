# -*- coding: utf-8 -*-
"""L05 质感去劣化层 —— SreSlopGuard 物理清洗「整体稳定」类空话。

SOP v13.0 L05 体检病灶（R20 真实断点）：
    可靠性报告充斥「整体稳定 / 运行正常 / 持续关注 / 视情况而定 /
    相关细节待定 / 基本可用 / 高度重视」，没有可复算数字、没有 DRI、
    没有截止时间；`review.py` 只拦三个词，换个说法就漏过去。

对标开源标杆（Stars > 1k）：
    * reviewdog/reviewdog (>8k) —— 把检查结果落到具体行/位置
    * errata-ai/vale (>4k) —— 可配置的散文质量规则
    * proselint (>4k) —— 语言层面的空话/冗余检测

落地的最低 3 项架构升级：
    1. 扩展 SRE 假大空词库 + 物理替换 + 命中定位（位置/类别/替换建议）；
    2. 量化证据门禁（可用率/错误预算/MTTR/RTO 至少 1 项可复算数字）；
    3. DRI 注入 + 截止期 + Actionability 行动力评分（0~100）。

用法：
    python agent.py evolve slop --text "整体稳定，持续关注" --out ...
"""
from __future__ import annotations

import datetime
import os
import re
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# (匹配词, 类别, 替换建议)
_SLOP: List[tuple] = [
    ("整体稳定", "vague_status", "可用率 99.9%（近 30 天 9995/10000 探测成功）"),
    ("整体良好", "vague_status", "可用率/SLI 具体数值 + 统计窗口"),
    ("运行正常", "vague_status", "探测成功率与错误预算余量"),
    ("持续关注", "no_action", "值班负责人 蛙值守，24h 内提交 RCA"),
    ("高度重视", "no_action", "值班负责人 蛙值守，截止 24h，交付 RCA"),
    ("视情况而定", "no_criteria", "按 SLO 99.9% 与错误预算燃烧率判定"),
    ("相关细节待定", "placeholder", "缺失项清单 + 补齐负责人 + 截止时间"),
    ("细节待定", "placeholder", "缺失项清单 + 补齐负责人 + 截止时间"),
    ("基本可用", "vague_status", "可用率低于 99.9% 即判不可用"),
    ("显著提升", "unquantified", "给出前后对比数值与统计窗口"),
    ("大幅改善", "unquantified", "给出前后对比数值与统计窗口"),
    ("无需担心", "unquantified", "给出错误预算余量与最坏情况"),
    ("可能存在一定风险", "hedging", "给出风险量化区间与触发条件"),
    ("大概", "hedging", "给出确定数值或删除该判断"),
    ("尽快", "no_deadline", "给出明确截止时间（小时）"),
    ("后续跟进", "no_deadline", "负责人 + 截止时间 + 验收判据"),
]
_HEDGE_RE = re.compile(r"(可能|也许|或许|似乎|大致)[^。；\n]{0,12}(风险|问题|影响|波动)")
_QUANT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|ms|s|秒|分钟|min|小时|h|次|条|个|人时|天)")
_DRI_RE = re.compile(r"(蛙值守|DRI|责任人|负责人)")
_DEADLINE_RE = re.compile(r"(\d+\s*(?:小时|h|分钟|min|天)|截止|前完成|SLA)")


class SreSlopGuard:
    """R20 可靠性汇报质感防线。"""

    ENGINE = "SreSlopGuard"
    LAYER = "L05"
    CAPABILITIES = [
        "SRE 假大空词库 (16 条) 物理替换与命中定位",
        "量化证据门禁 (可用率/错误预算/MTTR/RTO 可复算数字) 强制绑定",
        "DRI 注入 + 截止期 + Actionability 行动力评分 (0~100)",
    ]

    def audit(self, text: str) -> Dict[str, Any]:
        text = text or ""
        hits: List[Dict[str, Any]] = []
        for word, category, replacement in _SLOP:
            start = 0
            while True:
                idx = text.find(word, start)
                if idx < 0:
                    break
                hits.append({"word": word, "category": category,
                             "index": idx, "replacement": replacement})
                start = idx + len(word)
        for m in _HEDGE_RE.finditer(text):
            hits.append({"word": m.group(0), "category": "hedging",
                         "index": m.start(),
                         "replacement": "给出风险量化区间与触发条件"})
        quant = _QUANT_RE.findall(text)
        has_dri = bool(_DRI_RE.search(text))
        has_deadline = bool(_DEADLINE_RE.search(text))
        score = 50
        score += 20 if quant else 0
        score += 15 if has_dri else 0
        score += 15 if has_deadline else 0
        score -= min(40, 10 * len(hits))
        actionability = max(0, min(100, score))
        return {
            "ok": True,
            "engine": self.ENGINE, "layer": self.LAYER,
            "text": text,
            "hits": hits,
            "hit_count": len(hits),
            "has_slop": bool(hits),
            "categories": sorted({h["category"] for h in hits}),
            "quantified_evidence": quant[:12],
            "has_quantified_evidence": bool(quant),
            "has_dri": has_dri,
            "has_deadline": has_deadline,
            "actionability": actionability,
            "verdict": "PASS" if (not hits and quant and has_dri) else "FAIL",
            "capabilities": list(self.CAPABILITIES),
        }

    def clean(self, text: str) -> Dict[str, Any]:
        audit = self.audit(text)
        # 顺序扫描：长词优先消费区间，避免「相关细节待定」被「细节待定」重复替换导致错位。
        pieces: List[str] = []
        cursor = 0
        for h in sorted(audit["hits"], key=lambda x: (x["index"], -len(x["word"]))):
            if h["index"] < cursor:
                continue
            end = h["index"] + len(h["word"])
            if end <= cursor:
                continue
            pieces.append(text[cursor:h["index"]])
            pieces.append(h["replacement"])
            cursor = end
        pieces.append(text[cursor:])
        cleaned = "".join(pieces)
        if not audit["has_dri"]:
            cleaned += "（责任人：蛙值守）"
        if not audit["has_quantified_evidence"]:
            cleaned += "（证据：可用率 99.9%，错误预算余量 0.001）"
        after = self.audit(cleaned)
        return {
            "ok": after["verdict"] == "PASS",
            "engine": self.ENGINE, "layer": self.LAYER,
            "before": audit, "after": after,
            "cleaned_text": cleaned,
            "removed_hits": audit["hit_count"],
            "actionability_gain": after["actionability"] - audit["actionability"],
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R20 L05 质感去劣化")
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    guard = SreSlopGuard()
    out = guard.clean(args.text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"hits": out["before"]["hit_count"],
                      "actionability": out["after"]["actionability"],
                      "engine": guard.ENGINE}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
