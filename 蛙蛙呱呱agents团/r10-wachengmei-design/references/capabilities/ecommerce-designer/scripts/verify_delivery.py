#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电商视觉设计 · 交付校验器（L3 确定性门禁）

用法：
    python scripts/verify_delivery.py --file 交付物.md
    python scripts/verify_delivery.py --file 交付物.md --strict
    python scripts/verify_delivery.py --self-test

退出码：
    0  全部通过
    1  有 FAIL 项（--strict 下 WARN 也计为 FAIL）
    2  文件读不到

设计约束：
    - 零第三方依赖，纯标准库，Python 3.10+；
    - 不做语义判断，只做确定性匹配，避免"看起来跑了其实是猜的"；
    - 极限词表是**常用子集**，不代表完整法条清单；表外命中由模型按
      references/ad-law-compliance.md 的语义规则补充。
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# --------------------------------------------------------------------------- #
# 极限词表：分九类，每类给三档替换策略（A 删 / B 改量化 / C 改主观感受）
# --------------------------------------------------------------------------- #
RULES = [
    # (类别, 级别, 词, 建议档位)
    ("L1 绝对化", "FAIL", "国家级", "A"),
    ("L1 绝对化", "FAIL", "最高级", "A"),
    ("L1 绝对化", "FAIL", "最佳", "A"),
    ("L1 绝对化", "FAIL", "最好", "A"),
    ("L1 绝对化", "FAIL", "最强", "A"),
    ("L1 绝对化", "FAIL", "第一品牌", "B"),
    ("L1 绝对化", "FAIL", "行业第一", "B"),
    ("L1 绝对化", "FAIL", "销量第一", "B"),
    ("L1 绝对化", "FAIL", "顶级", "A"),
    ("L1 绝对化", "FAIL", "极致", "A"),
    ("L1 绝对化", "FAIL", "唯一", "B"),
    ("L1 绝对化", "FAIL", "首个", "B"),
    ("L1 绝对化", "FAIL", "全网最低", "B"),
    ("L1 绝对化", "FAIL", "史上最低", "B"),
    ("L1 绝对化", "FAIL", "最便宜", "B"),
    ("L2 虚假功效", "FAIL", "治疗", "A"),
    ("L2 虚假功效", "FAIL", "治愈", "A"),
    ("L2 虚假功效", "FAIL", "根治", "A"),
    ("L2 虚假功效", "FAIL", "抗癌", "A"),
    ("L2 虚假功效", "FAIL", "防癌", "A"),
    ("L2 虚假功效", "FAIL", "降血压", "A"),
    ("L2 虚假功效", "FAIL", "消炎", "A"),
    ("L2 虚假功效", "FAIL", "包治", "A"),
    ("L3 保健越界", "FAIL", "增强免疫力", "A"),
    ("L3 保健越界", "FAIL", "改善睡眠", "A"),
    ("L3 保健越界", "FAIL", "排毒", "A"),
    ("L3 保健越界", "FAIL", "丰胸", "A"),
    ("L3 保健越界", "FAIL", "壮阳", "A"),
    ("L4 虚假承诺", "FAIL", "100%有效", "B"),
    ("L4 虚假承诺", "FAIL", "百分百有效", "B"),
    ("L4 虚假承诺", "FAIL", "永久", "B"),
    ("L4 虚假承诺", "FAIL", "终身保修", "B"),
    ("L4 虚假承诺", "FAIL", "无效退款", "B"),
    ("L4 虚假承诺", "FAIL", "零风险", "B"),
    ("L5 模糊时限", "FAIL", "最后一波", "B"),
    ("L5 模糊时限", "FAIL", "限时秒杀", "B"),
    ("L5 模糊时限", "FAIL", "抢完为止", "B"),
    ("L5 模糊时限", "FAIL", "卖完为止", "B"),
    ("L5 模糊时限", "WARN", "限时", "B"),
    ("L5 模糊时限", "WARN", "今日特价", "B"),
    ("L6 未授权背书", "FAIL", "驰名商标", "A"),
    ("L6 未授权背书", "FAIL", "国家免检", "A"),
    ("L6 未授权背书", "FAIL", "国家认证", "B"),
    ("L6 未授权背书", "WARN", "权威认证", "B"),
    ("L7 贬低对手", "FAIL", "吊打", "A"),
    ("L7 贬低对手", "FAIL", "秒杀同行", "A"),
    ("L7 贬低对手", "WARN", "比同行好", "B"),
    ("L7 贬低对手", "WARN", "唯一不含", "B"),
    ("L8 站外导流", "FAIL", "加微信", "A"),
    ("L8 站外导流", "FAIL", "扫码加", "A"),
    ("L8 站外导流", "FAIL", "站外下单", "A"),
    ("L8 站外导流", "WARN", "私信领券", "A"),
]

REPLACE_HINT = {
    "A": "删除该表述，主张改由画面承担",
    "B": "改为可核验的具体数字/区间/条件，并标注来源与统计期",
    "C": "改为用户主观体验表述，并标注样本量与来源",
}

# --------------------------------------------------------------------------- #
# 结构门禁
# --------------------------------------------------------------------------- #
TEN_FIELDS = [
    "版位", "转化职责", "独特点击理由", "文案", "版式骨架",
    "视线动线", "素材需求", "尺寸规格", "禁用项", "不重叠",
]
MANDATORY_MODULES = ["M03", "M27", "M29", "M33"]
TOKEN_PARTS = ["网格", "色彩", "字体", "材质"]
PROMPT_PARTS = ["主体", "材质", "光影", "镜头", "背景", "风格", "约束"]
RESPONSE_LEVELS = ["微调", "结构", "重做"]


def _gates(text: str) -> list[tuple[str, str, str]]:
    """返回 [(门禁ID, 状态 PASS|WARN|FAIL, 说明)]"""
    out: list[tuple[str, str, str]] = []
    low = text.lower()

    # G01 关键假设清单：每条带"若此假设不成立"
    if "关键假设" not in text:
        out.append(("G01", "FAIL", "缺「关键假设清单」小节"))
    else:
        blocks = re.findall(r"假设\s*\d+[：:].{0,200}", text)
        bad = [b for b in blocks if ("不成立" not in b and "若" not in b)]
        if not blocks:
            out.append(("G01", "FAIL", "关键假设清单为空"))
        elif bad:
            out.append(("G01", "WARN", f"{len(bad)} 条假设缺「若此假设不成立→改哪一步」从句"))
        else:
            out.append(("G01", "PASS", f"{len(blocks)} 条假设可被驳回"))

    # G02 视觉主张表三关
    for key, label in (("3 秒", "3 秒测试"), ("证据", "证据测试"), ("撞车", "差异测试")):
        if key not in text:
            out.append(("G02", "WARN", f"视觉主张表缺「{label}」"))
            break
    else:
        out.append(("G02", "PASS", "主张表三关校验齐全"))

    # G03 主图矩阵十项
    if "主图" in text:
        missing = [f for f in TEN_FIELDS if f not in text]
        if missing:
            out.append(("G03", "WARN", "主图矩阵缺字段：" + "、".join(missing)))
        else:
            out.append(("G03", "PASS", "主图矩阵十项齐全"))
    else:
        out.append(("G03", "WARN", "未发现主图矩阵小节"))

    # G04 详情页四类必含模块
    if "详情页" in text or "分屏" in text:
        miss = [m for m in MANDATORY_MODULES if m not in text]
        if miss:
            out.append(("G04", "FAIL", "详情页缺必含模块：" + "、".join(miss)))
        else:
            out.append(("G04", "PASS", "四类必含模块齐全"))
    else:
        out.append(("G04", "WARN", "未发现详情页/分屏小节"))

    # G05 设计系统四件 + 对比度
    if "令牌" in text or "设计系统" in text:
        miss = [p for p in TOKEN_PARTS if p not in text]
        if miss:
            out.append(("G05", "WARN", "令牌表缺：" + "、".join(miss)))
        elif not re.search(r"4\.5\s*[:：]\s*1|对比度", text):
            out.append(("G05", "WARN", "令牌表未见对比度 ≥4.5:1 声明"))
        else:
            out.append(("G05", "PASS", "令牌表四件 + 对比度齐全"))
    else:
        out.append(("G05", "WARN", "未发现设计系统令牌表"))

    # G06 提示词七段
    if "提示词" in text:
        miss = [p for p in PROMPT_PARTS if p not in text]
        if miss:
            out.append(("G06", "WARN", "提示词缺段：" + "、".join(miss)))
        else:
            out.append(("G06", "PASS", "提示词七段齐全"))
    else:
        out.append(("G06", "WARN", "未发现提示词包"))

    # G07 修改响应三级
    if "修改响应" in text or "迭代响应" in text:
        miss = [l for l in RESPONSE_LEVELS if l not in text]
        if miss:
            out.append(("G07", "WARN", "修改响应表缺级别：" + "、".join(miss)))
        else:
            out.append(("G07", "PASS", "修改响应三级齐全"))
    else:
        out.append(("G07", "WARN", "未发现修改响应表"))

    # G08 AIGC 标识
    if "AIGC" in text or "AI 生成" in text or "AI生成" in text:
        out.append(("G08", "PASS", "已声明 AIGC 标识"))
    else:
        out.append(("G08", "WARN", "未见 AIGC 标识声明"))

    # G09 规格来源声明
    if re.search(r"当期口径|后台|采集日期|未联网校验|内置规格库", text):
        out.append(("G09", "PASS", "规格来源/时效已声明"))
    else:
        out.append(("G09", "WARN", "规格未声明来源与采集日期"))

    _ = low
    return out


def _scan_adlaw(text: str) -> list[dict]:
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for cat, level, word, tier in RULES:
            if word in line:
                hits.append({
                    "line": lineno, "category": cat, "level": level,
                    "word": word, "tier": tier,
                    "hint": REPLACE_HINT[tier],
                    "text": line.strip()[:80],
                })
    return hits


def verify(text: str, strict: bool = False) -> dict:
    gates = _gates(text)
    hits = _scan_adlaw(text)
    hard_adlaw = {"L2 虚假功效", "L3 保健越界"}
    fails = [g for g in gates if g[1] == "FAIL"]
    warns = [g for g in gates if g[1] == "WARN"]
    for h in hits:
        if h["category"] in hard_adlaw:
            h["level"] = "FAIL"
    adlaw_fail = [h for h in hits if h["level"] == "FAIL"]
    ok = not fails and not adlaw_fail and not (strict and warns)
    return {"ok": ok, "gates": gates, "hits": hits,
            "fails": len(fails), "warns": len(warns),
            "adlaw_fail": len(adlaw_fail), "strict": strict}


def render(res: dict) -> str:
    lines = ["电商视觉设计 · 交付校验", "=" * 60,
             f"模式：{'strict（WARN 计 FAIL）' if res['strict'] else 'normal'}",
             "", "【结构门禁】"]
    for gid, status, msg in res["gates"]:
        lines.append(f"  [{status:<4}] {gid}  {msg}")
    lines += ["", "【极限词扫描】"]
    if not res["hits"]:
        lines.append("  命中 0 条")
    else:
        for h in res["hits"]:
            lines.append(f"  [{h['level']:<4}] L{h['line']:<4} {h['category']}  «{h['word']}»")
            lines.append(f"         建议档位 {h['tier']}：{h['hint']}")
            lines.append(f"         原文：{h['text']}")
    lines += ["", "=" * 60,
              f"FAIL {res['fails']} ｜ WARN {res['warns']} ｜ 极限词 FAIL {res['adlaw_fail']}",
              ("结论：通过，可交付" if res["ok"] else "结论：不通过，按上方条目返回修改后重跑")]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 自检
# --------------------------------------------------------------------------- #
GOOD = """
# 需求简报
## 关键假设清单
- 假设 1：客单价 199 元｜若此假设不成立，需改 Step 3。
- 假设 2：主力渠道天猫｜若此假设不成立，需改 Step 6。

# 视觉主张表
3 秒测试 / 证据测试 / 差异测试
## 排他说明
竞品主诉求为价格，我们不撞车。

# 主图矩阵
版位 转化职责 独特点击理由 文案 版式骨架 视线动线 素材需求 尺寸规格 禁用项 不重叠

# 详情页分屏
M03 M27 M29 M33

# 设计系统令牌表
网格 色彩 字体 材质
正文与背景对比度 ≥ 4.5:1

# AI 提示词包
主体 材质 光影 镜头 背景 风格 约束（含负面词）
AIGC 标识：画面右下角标注「AI 生成」

# 校验报告
规格来源：商家后台当期提示，采集日期 2026-11-11
修改响应：微调 / 结构 / 重做
"""

BAD = GOOD + "\n本产品为全网最低价，可治疗失眠，限时秒杀最后一波。\n"


def self_test() -> int:
    ok = verify(GOOD, strict=True)
    bad = verify(BAD, strict=False)
    problems = []
    if not ok["ok"]:
        problems.append("GOOD 样例未通过：" + "; ".join(m for _, s, m in ok["gates"] if s != "PASS"))
    if bad["ok"]:
        problems.append("BAD 样例应失败却通过")
    if bad["adlaw_fail"] < 2:
        problems.append(f"BAD 样例极限词 FAIL 数异常：{bad['adlaw_fail']}")
    lazy = verify("随便写点东西", strict=False)
    if lazy["ok"]:
        problems.append("空文档应失败却通过")

    if problems:
        print("[self-test] FAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("[self-test] PASS  3/3")
    print(f"  GOOD: FAIL {ok['fails']} WARN {ok['warns']} 极限词 {ok['adlaw_fail']}")
    print(f"  BAD : FAIL {bad['fails']} 极限词 FAIL {bad['adlaw_fail']}")
    print(f"  空文档: FAIL {lazy['fails']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="电商视觉设计交付校验器")
    ap.add_argument("--file", help="待校验的交付物 Markdown 路径")
    ap.add_argument("--strict", action="store_true", help="WARN 计为 FAIL")
    ap.add_argument("--self-test", action="store_true", help="跑内置自检")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if args.self_test:
        return self_test()
    if not args.file:
        ap.error("需要 --file 或 --self-test")
    if not os.path.isfile(args.file):
        print(f"[verify] 文件不存在: {args.file}", file=sys.stderr)
        return 2
    with open(args.file, encoding="utf-8-sig") as fh:
        text = fh.read()

    res = verify(text, strict=args.strict)
    if args.json:
        import json
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(render(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
