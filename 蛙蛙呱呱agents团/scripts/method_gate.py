# -*- coding: utf-8 -*-
"""R04 方法门禁（v0）：检查报告里的 headline 是否做了对照/基线/匹配。

规则（可执行、可解释）：
1. 价差/溢价/差异/倍数 + 数字 → 附近必须有「匹配|同规格|同品种|对照|可比」；
2. 涨/跌/上升/下降/震荡/正常 + 数字 → 附近必须有「同比|环比|同期|基线|对照」；
3. 建议/推荐/应该 → 附近必须有「负责人|owner|阈值|KPI|回滚|责任」。

用法：
  python scripts/method_gate.py --input <report.html|md>
退出码：0 通过；1 有 FAIL；2 输入不可读。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text_of(p: Path) -> str:
    raw = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() in (".html", ".htm"):
        raw = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
        raw = re.sub(r"<style[\s\S]*?</style>", " ", raw, flags=re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
        raw = raw.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"[ \t]+", " ", raw)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。；！？\n])", text)
    return [p.strip() for p in parts if len(p.strip()) >= 8]


def near(text: str, idx: int, radius: int = 180) -> str:
    return text[max(0, idx - radius): idx + radius]


def check(p: Path) -> list[dict]:
    text = text_of(p)
    issues: list[dict] = []
    seen = set()
    for s in split_sentences(text):
        if s in seen:
            continue
        seen.add(s)
        idx = text.find(s)
        ctx = near(text, idx)
        # 1) 价差类
        numeric = re.search(r"\d+(?:\.\d+)?\s*%|\d+\.\d+|倍", s)
        if re.search(r"价差|溢价|差价|倍|高于|低于", s) and numeric:
            if not re.search(r"匹配|同规格|同品种|分规格|规格|对照|可比|控制变量|等级|品牌|口径", ctx):
                issues.append({"type": "价差未匹配", "sentence": s[:120],
                               "hint": "补同规格/同品种/同日对照，或标注不可比"})
        # 2) 趋势类
        if len(re.findall(r"\d+(?:\.\d+)?", s)) >= 4:
            continue  # 表格行/多数字串不做趋势判断
        if re.search(r"涨|跌|上升|下降|震荡|正常|异常", s) and numeric:
            if not re.search(r"同比|环比|同期|基线|对照|三年|去年", ctx):
                issues.append({"type": "趋势无基线", "sentence": s[:120],
                               "hint": "补同期基线/同比环比，或降级为描述"})
        # 3) 建议类
        if re.search(r"建议|推荐|应该|优先", s) and not re.search(r"负责人|owner|阈值|KPI|回滚|责任|R\d\d", ctx):
            issues.append({"type": "建议缺行动要素", "sentence": s[:120],
                           "hint": "补负责人/阈值/时间/回滚"})
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--limit", type=int, default=12)
    ns = ap.parse_args()
    p = Path(ns.input)
    if not p.exists():
        print(f"输入不存在：{p}")
        return 2
    issues = check(p)
    print(f"方法门禁：{p.name}")
    if not issues:
        print("PASS：未发现未匹配的价差/无基线的趋势/缺行动要素的建议")
        return 0
    by_type: dict[str, int] = {}
    for i in issues:
        by_type[i["type"]] = by_type.get(i["type"], 0) + 1
    print("FAIL：", "；".join(f"{k} {v} 处" for k, v in by_type.items()))
    for i in issues[: ns.limit]:
        print(f"- [{i['type']}] {i['sentence']}")
        print(f"    → {i['hint']}")
    print(f"\n合计 {len(issues)} 处；完整清单可加 --json（待实现）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
