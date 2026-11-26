# -*- coding: utf-8 -*-
"""core/research_protocol —— 调研的「交付契约」，不含任何行业清单（v12.1）。

为什么删掉了 8 个研究模块：
    上一版这里有一张固定的模块表（盘子/结构/玩家/渠道/价格/需求/政策/进入）。
    那仍然是「预先列举」——只不过列举的是问题而不是行业。
    用户的原话是：每次都要新建一套维度吗？不要。

所以这一版只保留**契约**，不保留**清单**：
    * 要查什么 → 由智能体（模型 + 工具）按任务自己判断，本模块不规定；
    * 必须交出什么 → 本模块规定：每条结论的形式、证据强度、来源等级、缺口写法；
    * 报告长什么样 → 四段（决策 / 判断 / 执行 / 证据）+ 边界。

一句话：**这里规定「怎么算合格」，不规定「该研究什么」。**
后者是能力，属于模型；前者是纪律，属于系统。

用法：
    python -m core.sources.research_protocol --intent "任意一句话" [--dir <已给数据>]
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional, Sequence

SCHEMA = "dsh.research_brief/v2"

# 来源等级：A 政府/统计；B 研报/协会（经转述降级）；C 媒体引第三方；D 仅摘要；S 规范性文件
GRADES: Dict[str, str] = {
    "S": "规范性文件原文（部委/标准文本）",
    "A": "政府统计、统计公报、主管部门发布",
    "B": "券商研报、行业协会报告（经媒体转述降 C）",
    "C": "媒体引用第三方数据",
    "D": "只能看到摘要、无法取原文——只作线索，不作结论",
}

# 每条结论必须长这样，缺一项即不合格
CLAIM_CONTRACT: Sequence[Dict[str, str]] = (
    {"field": "claim", "require": "一句话结论，含一个数字或一个明确方向"},
    {"field": "value", "require": "数字 + 单位 + 期次；没有数字的方向型结论要写明「定性」"},
    {"field": "quote", "require": "来源原文逐字引用，不能改写"},
    {"field": "url", "require": "可点开、可复核的链接"},
    {"field": "grade", "require": "S/A/B/C/D，按 GRADES 判定"},
    {"field": "falsifier", "require": "什么情况下这条结论作废（含可观测阈值）"},
    {"field": "boundary", "require": "这条结论在什么范围内成立、不能外推到哪"},
)

# 报告的固定四段 + 边界：读者决定结构，不随行业变化
REPORT_SHAPE: Sequence[Dict[str, str]] = (
    {"part": "决策页", "for": "拍板", "require": "结论 1—3 条 + 建议动作 + 停止条件"},
    {"part": "判断", "for": "复核", "require": "每节：观察 → 对照 → 机理 → 落点 → 证伪"},
    {"part": "执行清单", "for": "落地", "require": "动作 / 前置条件 / 验收口径 / 停止条件"},
    {"part": "证据", "for": "对外引用", "require": "来源分级表 + 关键引文 + 冲突说明"},
    {"part": "边界", "for": "诚实", "require": "没查到的、查不动的、不能外推的"},
)

# 交叉质询：报告出厂前的硬检查（core/claims/claim_consistency.py 会执行）
REVIEW_RULES: Sequence[Dict[str, str]] = (
    {"id": "C1", "rule": "同一指标同期两个值，必须写明口径差；沉默即拦"},
    {"id": "C2", "rule": "D 级来源只能作线索，不能支撑结论"},
    {"id": "C3", "rule": "头条结论的数字必须有 A/B/S 级来源支撑"},
    {"id": "C4", "rule": "必须写边界；没写边界等于没查缺口"},
)


def plan(intent: str, project_dir: Optional[str] = None,
         has_files: bool = False) -> Dict[str, Any]:
    """一句话 → 交付契约。不规定研究什么，只规定怎么算合格。"""
    lane = "given" if (project_dir or has_files) else "web"
    return {
        "schema": SCHEMA,
        "intent": str(intent or ""),
        "data_lane": lane,
        "lane_note": (
            "用户已给数据：先清洗（列名/单位/期次/重复值），再决定查什么"
            if lane == "given" else
            "用户未给数据：联网找公开可核来源，每条留原文引文与链接"),
        "what_to_research": "由执行者按任务判断——系统不预设问题清单",
        "claim_contract": list(CLAIM_CONTRACT),
        "report_shape": list(REPORT_SHAPE),
        "review_rules": list(REVIEW_RULES),
        "grades": GRADES,
        "gaps_policy": "查完仍缺的写进「边界」，标明影响哪条结论；不许用估值冒充实测",
    }


def to_markdown(p: Dict[str, Any]) -> str:
    """可直接交给执行者的任务书（不含任何行业预设）。"""
    lines = [
        f"# 调研任务契约：{p['intent']}",
        "",
        f"- 数据通道：**{p['data_lane']}** —— {p['lane_note']}",
        f"- 研究什么：{p['what_to_research']}",
        "",
        "## 一条结论必须长这样",
        "",
    ]
    for c in p["claim_contract"]:
        lines.append(f"- `{c['field']}`：{c['require']}")
    lines += ["", "## 报告结构（四段 + 边界）", ""]
    for s in p["report_shape"]:
        lines.append(f"- **{s['part']}**（给{s['for']}）：{s['require']}")
    lines += ["", "## 出厂前的交叉质询", ""]
    for r in p["review_rules"]:
        lines.append(f"- **{r['id']}** {r['rule']}")
    lines += ["", "## 来源等级", ""]
    for k, v in p["grades"].items():
        lines.append(f"- **{k}**：{v}")
    lines += ["", f"## 缺口\n\n{p['gaps_policy']}"]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="research_protocol",
                                 description="一句话 → 调研交付契约（不含行业预设）")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--dir", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    a = ap.parse_args(argv)
    p = plan(a.intent, project_dir=a.dir,
             has_files=bool(a.dir and os.path.isdir(a.dir)))
    if a.json:
        from pathlib import Path
        Path(a.json).write_text(json.dumps(p, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    if a.md:
        from pathlib import Path
        Path(a.md).write_text(to_markdown(p), encoding="utf-8")
    print(json.dumps({"data_lane": p["data_lane"],
                      "claim_fields": [c["field"] for c in p["claim_contract"]],
                      "report_parts": [s["part"] for s in p["report_shape"]]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
