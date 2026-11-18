# -*- coding: utf-8 -*-
"""core/research_protocol —— 把「一句话」翻译成专业研究方案（v12）。

问题（这是用户最不满的一条）：
    用户说「做调味料内蒙市场」，他一不专业、二不该被迫定义研究问题。
    旧系统的做法是让他选 lens、交 CSV、补字段——把专业判断的活退给了用户。
    另一头的错法是给每个行业硬编码一套方法（seasoning.py / cheese.py），
    换行业就要写代码——那是模板，不是能力。

本模块的做法：
    把「一条业务线该怎么研究」写成**与行业无关的协议**：
        8 个研究模块（盘子/结构/玩家/渠道/价格/需求/政策/进入），
        每个模块规定「要回答什么、需要什么证据、最低来源等级、结论长什么样」。
    新业务线只换关键词，不换代码。

    plan("内蒙古调味料市场") →
        {
          "business_line": "调味料",
          "data_lane": "web|given",
          "modules": [{key, question, needs, min_grade, owner, search}],
          "experts": ["r05", "r06", "r15", "r03"],
          "protocol": "dsh.research_plan/v1"
        }

纪律：
1. 协议只规定「问什么、要什么证据」，不规定「答案是什么」——答案由专家去查。
2. 没有对应证据的模块不删，进 `gaps`，由报告显式写「未证实」。
3. `data_lane` 决定工作方式：given=清洗用户数据；web=联网找公开可核来源。

用法：
    python -m core.research_protocol --intent "内蒙古调味料市场调研" [--dir <项目>]
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any, Dict, List, Optional, Sequence

SCHEMA = "dsh.research_plan/v1"

# --------------------------------------------------------------------------- #
# 研究模块库：与行业无关的 8 个模块
# --------------------------------------------------------------------------- #
# needs: 需要哪类证据（不是字段名，是证据类型，专家自己找）
# min_grade: 结论能用的最低来源等级（A 政府/统计，B 研报/协会，C 媒体引第三方，D 摘要）
# owner: 默认由哪个角色负责
MODULES: List[Dict[str, Any]] = [
    {
        "key": "market_size", "name": "盘子多大", "always": True,
        "question": "这个盘子一年有多大、增速多少？至少两条独立口径互证。",
        "needs": ["总量口径（政府统计优先）", "增速口径", "至少一条可交叉验证的第二来源"],
        "min_grade": "B", "owner": "r05", "claim_kind": "size",
        "search": ["市场规模", "行业规模", "亿元", "同比", "统计公报"],
    },
    {
        "key": "structure", "name": "结构怎么分", "always": False,
        "question": "钱集中在哪几类/哪几个区域？结构在往哪边挪？",
        "needs": ["品类或区域拆分", "份额", "份额变化方向"],
        "min_grade": "B", "owner": "r05", "claim_kind": "mix",
        "search": ["品类结构", "市场份额", "占比", "区域", "细分"],
    },
    {
        "key": "players", "name": "谁在卖", "always": True,
        "question": "全国龙头是谁、本地玩家是谁、集中度多高？",
        "needs": ["集中度（CR/HHI 任一）", "头部企业名单与体量", "本地企业名单"],
        "min_grade": "B", "owner": "r15", "claim_kind": "concentration",
        "search": ["CR5", "集中度", "龙头企业", "本地企业", "营收"],
    },
    {
        "key": "channel", "name": "货怎么走", "always": True,
        "question": "货从哪条渠道到终端？各渠道占比与变化。",
        "needs": ["渠道结构", "B/C 端占比", "渠道变化方向"],
        "min_grade": "B", "owner": "r12", "claim_kind": "channel",
        "search": ["渠道结构", "经销", "餐饮直供", "商超", "电商", "B端", "C端"],
    },
    {
        "key": "price_band", "name": "价格带与加价", "always": True,
        "question": "零售价、批发价、出厂价各在什么区间？加价率多少？",
        "needs": ["零售价", "批发价或出厂价", "规格与单位"],
        "min_grade": "C", "owner": "r06", "claim_kind": "unit",
        "search": ["零售价", "批发价", "价格带", "元/", "加价率"],
    },
    {
        "key": "demand", "name": "谁在买", "always": False,
        "question": "买的人是谁、在什么场景用、需求在往哪边变？",
        "needs": ["客群或场景", "使用频次或渗透率", "变化方向"],
        "min_grade": "C", "owner": "r05", "claim_kind": "demand",
        "search": ["消费场景", "渗透率", "客群", "用户画像", "频次"],
    },
    {
        "key": "policy", "name": "政策与标准", "always": True,
        "question": "有哪些准入门槛、标准与监管要求？",
        "needs": ["规范性文件", "标准编号", "监管动作"],
        "min_grade": "A", "owner": "r03", "claim_kind": "policy",
        "search": ["国家标准", "地方标准", "管理办法", "通知", "许可", "抽检"],
    },
    {
        "key": "entry", "name": "怎么进、什么条件下停", "always": True,
        "question": "从哪进、先做哪一段、什么条件下退出？",
        "needs": ["进入方式（自建/代工/代理）", "前置条件", "停止条件"],
        "min_grade": "C", "owner": "r01", "claim_kind": "action",
        "search": ["代工", "OEM", "加盟", "准入", "投资", "产能"],
    },
]

# 行业/业务线关键词 → 额外要读的模块（只加不减）
_TRIGGERS: List[tuple] = [
    (("渠道", "经销", "铺货", "零售", "电商"), ("channel", "price_band")),
    (("竞争", "对手", "格局", "集中度", "龙头"), ("players",)),
    (("价格", "毛利", "成本", "定价", "加价"), ("price_band", "structure")),
    (("消费", "客群", "场景", "需求", "复购"), ("demand",)),
    (("政策", "合规", "标准", "监管", "许可"), ("policy",)),
    (("进入", "做不做", "能不能", "投资", "开厂", "代工"), ("entry",)),
    (("结构", "品类", "细分", "区域"), ("structure",)),
]

# 业务线识别（只用于命名与检索扩展，不改变协议）
_LINES: List[tuple] = [
    (("调味料", "调味品", "酱油", "食醋", "复合调味"), "调味料"),
    (("预制菜", "预加工", "中央厨房"), "预制菜"),
    (("宠物", "猫粮", "狗粮"), "宠物食品"),
    (("水果", "生鲜", "蔬菜"), "生鲜"),
    (("家居", "百货", "日用品"), "家居百货"),
    (("乳制品", "奶酪", "奶食"), "乳制品"),
    (("餐饮", "团餐", "食堂"), "餐饮"),
]


def business_line(intent: str) -> str:
    s = str(intent or "")
    for keys, name in _LINES:
        if any(k in s for k in keys):
            return name
    return ""


def _hit_any(text: str, words: Sequence[str]) -> bool:
    return any(w in text for w in words)


def plan(intent: str, project_dir: Optional[str] = None,
         has_files: bool = False) -> Dict[str, Any]:
    """一句话 → 研究方案。不调模型，纯规则，可复现。"""
    s = str(intent or "")
    picked = {m["key"]: m for m in MODULES if m.get("always")}
    for words, keys in _TRIGGERS:
        if _hit_any(s, words):
            for k in keys:
                for m in MODULES:
                    if m["key"] == k:
                        picked[k] = m
    # 顺序按模块库原序，保证同一意图每次生成的方案一致
    order = [m["key"] for m in MODULES]
    modules = [picked[k] for k in order if k in picked]

    experts: List[str] = []
    for m in modules:
        if m["owner"] not in experts:
            experts.append(m["owner"])
    if "r04" not in experts:
        experts.append("r04")          # 独立评审：交叉质询

    lane = "given" if (project_dir or has_files) else "web"
    return {
        "schema": SCHEMA,
        "intent": s,
        "business_line": business_line(s) or "未识别",
        "data_lane": lane,
        "lane_note": ("用户已给数据：先清洗（列名/单位/期次/重复值），再按模块取数"
                      if lane == "given" else
                      "用户未给数据：联网找公开可核来源（A/B/C 级），每条带原文引文"),
        "modules": [{"key": m["key"], "name": m["name"], "question": m["question"],
                     "needs": m["needs"], "min_grade": m["min_grade"],
                     "owner": m["owner"], "claim_kind": m["claim_kind"],
                     "search": m["search"]} for m in modules],
        "experts": experts,
        "gaps_policy": "每个模块查完仍缺，写入报告「未证实」，不当结论用",
        "report_shape": {
            "audiences": ["老板：拍板", "团队：执行", "客户：可引用", "自己：快速摸底"],
            "sections": ["一屏结论", "关键判断", "执行清单", "证据与出处", "边界与未查到"],
        },
    }


def to_markdown(p: Dict[str, Any]) -> str:
    """给人和 agent 看的调研简报（可直接当子智能体的任务书）。"""
    lines = [
        f"# 调研方案：{p['intent']}",
        "",
        f"- 业务线：{p['business_line']}",
        f"- 数据通道：{p['data_lane']}（{p['lane_note']}）",
        f"- 专家：{'、'.join(p['experts'])}",
        "",
        "## 要回答的问题",
        "",
    ]
    for i, m in enumerate(p["modules"], 1):
        lines.append(f"{i}. **{m['name']}**（{m['owner']}）：{m['question']}")
        lines.append(f"   - 需要证据：{'；'.join(m['needs'])}")
        lines.append(f"   - 最低来源等级：{m['min_grade']}")
        lines.append(f"   - 检索词：{'、'.join(m['search'])}")
    lines += ["", "## 交付要求", "",
              "- 每条结论带数字、带原文引文、带可点链接、带来源等级",
              "- 同一指标出现两个数，必须写明口径差异，不许二选一沉默",
              "- 查不到的写进「未查到」，不当结论用"]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="research_protocol",
                                 description="一句话 → 专业研究方案（不产报告）")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--dir", default=None, help="已给数据目录，决定 data_lane")
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    a = ap.parse_args(argv)
    p = plan(a.intent, project_dir=a.dir,
             has_files=bool(a.dir and __import__("os").path.isdir(a.dir)))
    if a.json:
        from pathlib import Path
        Path(a.json).write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.md:
        from pathlib import Path
        Path(a.md).write_text(to_markdown(p), encoding="utf-8")
    print(json.dumps({k: p[k] for k in ("business_line", "data_lane", "experts")}
                     | {"modules": [m["name"] for m in p["modules"]]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
