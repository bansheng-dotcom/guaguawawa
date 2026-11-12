# -*- coding: utf-8 -*-
"""咨询深度审计 v0：对报告/台账做五维启发式打分（0—5 分/维）。

为什么需要它：现有 100 分制技能审计只量「结构」（frontmatter、章节、触发语），
不量「方法」。这个脚本量的是方法：问题定义、证据、分析、洞察、行动。

注意：启发式打分只用于横向对比与回归，不作为质量结论；正式使用需人工标注校准。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text_of(path: Path) -> str:
    if path.suffix.lower() in (".html", ".htm"):
        h = path.read_text(encoding="utf-8", errors="replace")
        h = re.sub(r"<script[\s\S]*?</script>", " ", h, flags=re.I)
        h = re.sub(r"<style[\s\S]*?</style>", " ", h, flags=re.I)
        return re.sub(r"<[^>]+>", " ", h)
    return path.read_text(encoding="utf-8", errors="replace")


def has(text: str, *pats: str) -> bool:
    return any(re.search(p, text) for p in pats)


DIMS = [
    ("问题定义", [
        (r"决策问题|要回答|回答一个问题|核心问题", 1.0),
        (r"对照组|基线|同比|环比|同期", 1.0),
        (r"口径|假设|边界|不可比|口径提醒", 1.0),
        (r"竞争解释|替代解释|其他解释|反方|证伪", 1.0),
        (r"如果.*(成立|不成立)|什么情况下.*(错|不成立)|杀死标准", 1.0),
    ]),
    ("证据质量", [
        (r"来源|S\d+|证据", 1.0),
        (r"分级|A 级|B 级|C 级|证据级别", 1.0),
        (r"缺口|缺失|未取到|失败尝试|弃用", 1.0),
        (r"冲突|不可比|倒挂|矛盾", 1.0),
        (r"可回指|可追溯|复算|复现", 1.0),
    ]),
    ("分析深度", [
        (r"匹配|同规格|同品种|控制变量", 1.0),
        (r"基线|季节性|多年|2022|2023|2024|2025", 1.0),
        (r"分解|归因|贡献|拆解", 1.0),
        (r"区间|置信|不确定|敏感性|情景", 1.0),
        (r"回归|相关|显著|检验|p 值|p=", 1.0),
    ]),
    ("洞察力", [
        (r"不是.*而是|真正的|本质|结构性|反直觉|意外", 1.0),
        (r"机制|因为|传导|滞后|原因", 1.0),
        (r"分化|结构|分层|错配|倒挂", 1.0),
        (r"竞争解释|替代解释|排除", 1.0),
        (r"这意味着|含义|so what|所以", 1.0),
    ]),
    ("行动性", [
        (r"动作|建议|下一步|路线|实施", 1.0),
        (r"负责人|责任|R\d\d|owner", 1.0),
        (r"阈值|触发|止损|验收|KPI", 1.0),
        (r"成本|收益|回收|ROI|投入", 1.0),
        (r"回滚|风险|前提|依赖", 1.0),
    ]),
]


def score(text: str) -> dict:
    out = {}
    for name, checks in DIMS:
        hit = sum(w for pat, w in checks if has(text, pat))
        total = sum(w for _, w in checks)
        out[name] = round(hit / total * 5, 1)
    out["总分"] = round(sum(v for k, v in out.items() if k != "总分") / len(DIMS) * 5, 1)
    return out


def main() -> None:
    targets = sys.argv[1:] or [
        "内蒙古水果市场调研与数据分析报告.html",
        "内蒙古水果经营报告.html",
        "内蒙古水果链路优化报告.html",
        "深度样例_季节性与规格归因.html",
    ]
    base = Path(r"D:\蛙蛙呱呱\内蒙古水果调研_2026-11-12")
    print(f"{'文件':<34} " + " ".join(f"{n:<6}" for n, _ in DIMS) + " 总分")
    print("-" * 96)
    for t in targets:
        p = base / t
        if not p.exists():
            print(f"{t:<34} 缺失")
            continue
        s = score(text_of(p))
        print(f"{t[:32]:<34} " + " ".join(f"{s[n]:<6.1f}" for n, _ in DIMS) + f" {s['总分']:.1f}")


if __name__ == "__main__":
    main()
