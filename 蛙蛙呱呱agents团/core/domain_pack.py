# -*- coding: utf-8 -*-
"""core/domain_pack —— 业务线 → 领域编队 + 专家作战计划。

解决的问题（针对「换个业务线就不会分析」）：
旧产线只能吃「已有数据的项目」，换一条业务线就没有可挂的方法。
本模块先不碰数据，只做三件事：

1. 把业务线意图匹配到一个**行业假设**（指标树、关键问题、情景轴、数据清单）；
2. 从 20 个角色领域包里选出一个**任务编队**（谁负责哪一段、用什么方法）；
3. 输出一份**领域作战计划**：先验证什么、用什么识别策略、三种情景、
   90 天计划、这个域最容易错的四件事、数据到位后跑哪条产线。

它不编项目数字：行业基准只给区间并标注「需按项目校准」；
真正的数字等数据到位后由 `report produce` 的方法库算。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import skill_bridge

ROOT = Path(__file__).resolve().parent.parent
ROLES = ROOT / "knowledge" / "roles"

# --------------------------------------------------------------------------- #
# 行业假设：业务线 → 指标树 / 关键问题 / 情景轴 / 数据清单
# --------------------------------------------------------------------------- #
INDUSTRIES: Dict[str, Dict[str, Any]] = {
    "retail": {
        "role_boost": {"r14": 2, "r15": 1, "r12": 1},
        "name": "连锁零售 / 商超 / 母婴 / 家居",
        "keywords": ["零售", "超市", "便利店", "母婴", "家居", "门店", "连锁", "SKU", "坪效"],
        "hypothesis": "同店增长 = 客流 × 转化 × 客单 × 复购；先验证客流是不是真在掉",
        "critical": "客流与复购，而不是客单价",
        "kpis": ["同店增速", "客流", "转化率", "客单价", "复购率", "坪效", "库存周转", "缺货率"],
        "questions": ["增量来自新店还是同店？", "客流、转化、客单、复购各贡献多少？",
                      "哪些 SKU 是引流、哪些是利润、哪些该汰换？", "补贴退坡后价格带怎么移？"],
        "scenarios": [("消费力（收入预期）", "渠道迁移（线上/社区店）")],
        "benchmarks": {"坪效": "因业态差异极大，需按同类门店校准",
                       "库存周转": "快消 30—60 天，家居 90—180 天（需校准）"},
        "data": [
            ("门店日销", "门店/日期/销售额/客流/客单", "同店与漏斗"),
            ("SKU 销售", "SKU/品类/销量/售价/成本/库存", "选品与毛利"),
            ("会员交易", "会员/订单/金额/品类/日期", "复购与 RFM"),
            ("促销记录", "活动/折扣/时间/门店", "增量实验"),
        ],
    },
    "energy_retail": {
        "role_boost": {"r14": 2, "r15": 1, "r12": 1},
        "name": "能源零售（加油站 / 非油）",
        "keywords": ["加油站", "油站", "非油", "油非", "能源", "便利店", "进站"],
        "hypothesis": "非油不是独立生意，是进站流量的二次变现；先验证进站率与转化率",
        "critical": "进站率 × 非油转化率，而不是非油 SKU 数量",
        "kpis": ["单站日销", "进站率", "非油转化率", "客单价", "油非比", "非油毛利率", "单站日均车流", "复购"],
        "questions": ["非油收入里，多少是加油顾客顺带、多少是专程？",
                      "进站率的天花板是位置、价格还是服务？",
                      "鲜食/饮料/车品三类，哪类该自营、哪类该联营？",
                      "新能源渗透后，非油是补位还是主战场？"],
        "scenarios": [("油价与新能源渗透", "便利店运营能力")],
        "benchmarks": {"油非比": "行业常见 10%—20%，站型差异大，需按站校准",
                       "非油毛利率": "包装饮料 20%—35%，鲜食 35%—50%（需校准）"},
        "data": [
            ("站点日销", "站点/日期/油品销量/进站车流/非油销售额", "进站率与油非比"),
            ("非油 SKU", "SKU/品类/销量/售价/成本/损耗", "品类结构与毛利"),
            ("会员/支付", "会员/订单/油品/非油/时间", "连带与复购"),
            ("周边竞品", "竞品/距离/油价/非油品类", "分流"),
        ],
    },
    "saas": {
        "role_boost": {"r13": 2, "r12": 1, "r07": 1},
        "name": "SaaS / 软件 / 订阅",
        "keywords": ["SaaS", "软件", "订阅", "续费", "NRR", "客户成功", "B端"],
        "hypothesis": "增长 = 获客 × 激活 × 留存 × 扩展；先验证留存与 NRR",
        "critical": "留存与 NRR，而不是新签合同额",
        "kpis": ["MRR/ARR", "CAC", "LTV", "NRR", "GRR", "流失率", "激活率", "回本周期"],
        "questions": ["留存差是产品价值、实施还是客户错配？",
                      "扩展收入来自加座、加模块还是涨价？",
                      "CAC 回本周期多长，现金流能撑几个周期？",
                      "哪些客户该放弃，哪些该加投服务？"],
        "scenarios": [("客户预算周期", "产品替代（AI/平台内置）")],
        "benchmarks": {"NRR": "优秀 >110%，健康 100%—110%（需按客群校准）",
                       "CAC 回本": "<12 个月为健康（需校准）"},
        "data": [
            ("订阅", "客户/套餐/起止/金额/席位", "MRR 与 NRR"),
            ("使用", "客户/功能/频次/日期", "激活与健康分"),
            ("工单", "客户/类型/时长/满意度", "服务与流失"),
            ("获客", "渠道/花费/线索/成交", "CAC 与归因"),
        ],
    },
    "food_service": {
        "role_boost": {"r14": 2, "r15": 1, "r02": 1},
        "name": "餐饮 / 烘焙 / 茶饮",
        "keywords": ["餐饮", "餐厅", "烘焙", "茶饮", "咖啡", "翻台", "门店"],
        "hypothesis": "单店模型 = 客流 × 客单 × 毛利率 − 租金人力；先验证翻台与复购",
        "critical": "客流与复购，而不是客单价",
        "kpis": ["翻台率", "客单价", "毛利率", "人效", "坪效", "复购率", "出餐时长", "损耗率"],
        "questions": ["增长来自新客还是复购？", "毛利被食材、人工还是租金吃掉？",
                      "出餐时长是否限制了高峰产能？", "外卖与堂食的客单与毛利差多少？"],
        "scenarios": [("商圈客流", "外卖平台规则")],
        "benchmarks": {"食材成本率": "30%—40%（需按品类校准）",
                       "人工成本率": "15%—25%（需校准）"},
        "data": [
            ("订单", "门店/日期/订单/金额/品类/渠道", "客单与结构"),
            ("客流", "门店/时段/进店/下单", "转化与翻台"),
            ("成本", "门店/月份/食材/人工/租金", "单店模型"),
            ("评价", "门店/评分/标签/日期", "体验与复购"),
        ],
    },
    "manufacturing": {
        "role_boost": {"r02": 2, "r15": 1, "r03": 1},
        "name": "制造 / 加工",
        "keywords": ["制造", "工厂", "加工", "产能", "良率", "OEE", "产线"],
        "hypothesis": "利润 = 产能利用率 × 良率 × 价格 − 料工费；先验证瓶颈",
        "critical": "瓶颈节拍与良率，而不是单台设备效率",
        "kpis": ["OEE", "良率", "产能利用率", "单位成本", "交付准时率", "在制品", "能耗"],
        "questions": ["瓶颈在哪道工序，节拍是多少？", "良率损失集中在哪一段？",
                      "换型时间是否吃掉了产能？", "自制还是外协更便宜（含质量）？"],
        "scenarios": [("订单结构", "原料价格")],
        "benchmarks": {"OEE": "世界级 85%，常见 60%—75%（需校准）",
                       "良率": "因行业差异大，需按品类校准"},
        "data": [
            ("工单", "工单/产品/数量/起止/良品数", "产能与良率"),
            ("设备", "设备/日期/运行/停机/速度", "OEE"),
            ("成本", "产品/月份/原料/人工/能耗", "单位成本"),
            ("质量", "批次/缺陷类型/数量", "良率损失"),
        ],
    },
    "agriculture": {
        "role_boost": {"r15": 2, "r14": 1, "r05": 1},
        "name": "种植 / 养殖 / 农产品",
        "keywords": ["农业", "种植", "养殖", "农产品", "亩产", "产地", "生鲜"],
        "hypothesis": "收益 = 亩产 × 价格 × 商品率 − 投入；先验证损耗与规格",
        "critical": "商品率与损耗，而不是亩产",
        "kpis": ["亩产", "商品率", "损耗率", "产地价", "到店成本", "周转天数", "毛利率"],
        "questions": ["收益波动来自价格还是商品率？", "损耗发生在田间、运输还是门店？",
                      "规格差是否被当成区域差？", "订单农业能否锁价？"],
        "scenarios": [("天气/产量", "价格周期")],
        "benchmarks": {"生鲜损耗": "5%—10%（需按品类校准）",
                       "批零倍率": "1.4—1.8 倍（需校准）"},
        "data": [
            ("产地", "品类/产地/日期/价格/规格", "产地价与规格"),
            ("批发", "市场/品类/日期/价格/到货量", "批零差"),
            ("零售", "门店/品类/日期/售价/销量", "零售与损耗"),
            ("成本", "批次/运费/损耗/人工", "到店成本"),
        ],
    },
    "education": {
        "role_boost": {"r13": 2, "r12": 1, "r07": 1},
        "name": "教育 / 培训",
        "keywords": ["教育", "培训", "课程", "完课", "续费", "学员"],
        "hypothesis": "续费 = 完课 × 满意度 × 效果；先验证完课率",
        "critical": "完课率与效果，而不是报名人数",
        "kpis": ["报名转化", "完课率", "续费率", "退费率", "获客成本", "课耗", "满班率"],
        "questions": ["完课率低是内容、服务还是时间冲突？", "续费来自效果还是销售推动？",
                      "退费集中在哪个环节？", "小班/大班/线上的单位经济差多少？"],
        "scenarios": [("政策合规", "就业/升学需求")],
        "benchmarks": {"完课率": "线上 20%—40%，线下 60%—80%（需校准）",
                       "续费率": "因品类差异大，需校准"},
        "data": [
            ("报名", "学员/课程/金额/渠道/日期", "转化与 CAC"),
            ("学习", "学员/课次/出勤/作业/完课", "完课与效果"),
            ("续费", "学员/课程/金额/日期", "续费与退费"),
            ("服务", "学员/工单/满意度", "体验"),
        ],
    },
}


def load_roles() -> Dict[str, Dict[str, Any]]:
    out = {}
    for p in sorted(ROLES.glob("r*.json")):
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        out[d["role"]] = d
    return out


def match_industry(intent: str) -> Dict[str, Any]:
    best, score = None, 0
    for key, ind in INDUSTRIES.items():
        s = sum(1 for w in ind["keywords"] if w in intent)
        if s > score:
            best, score = ind, s
    if best is None:
        best = dict(INDUSTRIES["retail"])
        best["_fallback"] = True
    return best


def score_roles(intent: str, roles: Dict[str, Dict[str, Any]],
                industry: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    boost = (industry or {}).get("role_boost") or {}
    scored = []
    for rid, r in roles.items():
        s = sum(1 for w in r.get("keywords", []) if w in intent) + boost.get(rid, 0)
        # 战略与分析是任何业务线的底座
        if rid in ("r01", "r06"):
            s += 1
        scored.append({"role": rid, "name": r["name"], "title": r["title"],
                       "domain": r["domain"], "score": s,
                       "hits": [w for w in r.get("keywords", []) if w in intent],
                       "industry_fit": rid in boost})
    scored.sort(key=lambda x: (-x["score"], x["role"]))
    picked = [x for x in scored if x["score"] > 0][:5]
    for must in ("r01", "r06"):
        if not any(x["role"] == must for x in picked):
            picked.append(next(x for x in scored if x["role"] == must))
    return picked[:5]


def _coverage_for(role_ids: List[str]) -> Dict[str, Any]:
    counts = {"exact": 0, "partial": 0, "new": 0}
    rows = []
    for rid in role_ids:
        for name, m in (skill_bridge.methods(rid) or {}).items():
            fit = m.get("fit", "new")
            counts[fit] = counts.get(fit, 0) + 1
            rows.append({"role": rid, "method": name, "fit": fit,
                         "skill": f"{m.get('skill_role', '')}.{m.get('skill', '')}".strip("."),
                         "action": m.get("action", ""),
                         "command": m.get("command", ""),
                         "note": m.get("note", "")})
    total = sum(counts.values())
    return {"total": total, **counts,
            "coverage_rate": round((counts["exact"] + counts["partial"]) / max(1, total), 4),
            "rows": rows}


def plan(intent: str) -> Dict[str, Any]:
    roles = load_roles()
    ind = match_industry(intent)
    picked = score_roles(intent, roles, ind)
    return {
        "schema": "dsh.domain_plan/v1",
        "intent": intent,
        "industry": {k: ind.get(k) for k in
                     ("name", "hypothesis", "critical", "kpis", "questions",
                      "scenarios", "benchmarks", "data")},
        "roles": [{**p, "books": roles[p["role"]]["books"],
                   "methods": [{**m, "skill": skill_bridge.info(p["role"], m["name"])}
                               for m in roles[p["role"]]["methods"]],
                   "failure_modes": roles[p["role"]]["failure_modes"],
                   "sections": roles[p["role"]]["report_sections"]}
                  for p in picked],
        "skill_coverage": _coverage_for([p["role"] for p in picked]),
        "analysis_design": [
            {"question": "变化从哪来（价/量/结构）", "method": "decompose_mix_rate",
             "needs": "两期权重与率", "level": "L1"},
            {"question": "改版/促销有没有用", "method": "ab_proportion / ab_mean",
             "needs": "随机分流 + 样本量", "level": "L3"},
            {"question": "政策/上线前后效果", "method": "did_twfe + event_study + placebo",
             "needs": "处理组/对照组 + ≥4 期", "level": "L3"},
            {"question": "定价与促销弹性", "method": "elasticity",
             "needs": "≥6 期价格与销量", "level": "L2"},
            {"question": "留存与复购", "method": "cohort_retention",
             "needs": "队列×期", "level": "L1"},
        ],
        "sprints": [
            {"window": "第 1—2 周", "goal": "补数据 + 定口径",
             "deliverable": "数据清单逐项到位；指标定义冻结"},
            {"window": "第 3—4 周", "goal": "描述与归因",
             "deliverable": "量价/结构归因 + 漏斗/队列"},
            {"window": "第 5—8 周", "goal": "因果与实验",
             "deliverable": "A/B 或 DiD + 稳健性"},
            {"window": "第 9—12 周", "goal": "策略与停止条件",
             "deliverable": "三情景 + 90 天动作 + 杀死标准"},
        ],
    }


def to_markdown(p: Dict[str, Any]) -> str:
    ind = p["industry"]
    lines: List[str] = []
    lines.append(f"# {p['intent']} · 领域作战计划（专家版）\n")
    lines.append("> 由 20 角色领域包 + 行业假设组装；不含未经核实的项目数字。")
    lines.append("> 行业基准只给区间，必须按项目校准；数据到位后再出数据报告。\n")

    lines.append("## 0. 一句话判断\n")
    lines.append(f"这条业务线的胜负手不在「做不做」，而在 **{ind['critical']}**。")
    lines.append(f"先验证：{ind['hypothesis']}。\n")

    lines.append("## 1. 任务编队（为什么是这几个角色）\n")
    lines.append("| 角色 | 能力域 | 在这条业务线负责什么 | 匹配到的词 |")
    lines.append("|---|---|---|---|")
    for r in p["roles"]:
        tag = "、".join(r["hits"]) or ("行业适配" if r.get("industry_fit") else "底座")
        lines.append(f"| {r['role']} {r['name']} | {r['domain']} | {r['title']} | {tag} |")
    lines.append("")

    lines.append("## 2. 行业假设与指标树（先定看什么）\n")
    lines.append("**关键问题**：")
    for q in ind["questions"]:
        lines.append(f"- {q}")
    lines.append("\n**指标**：" + "、".join(ind["kpis"]))
    lines.append("\n**基准（需校准）**：")
    for k, v in (ind["benchmarks"] or {}).items():
        lines.append(f"- {k}：{v}")
    lines.append("")

    lines.append("## 3. 每个角色的专家方法（怎么分析）\n")
    for r in p["roles"]:
        lines.append(f"### {r['role']} {r['name']} · {r['domain']}\n")
        for m in r["methods"]:
            lines.append(f"- **{m['name']}**：{m['formula']}（用于：{m['when']}）")
            sk = m.get("skill") or {}
            if sk.get("fit") in ("exact", "partial"):
                lines.append(f"  - 技能：`{sk['command']}`（{sk['fit']}；{sk['note']}）")
            else:
                lines.append(f"  - 新增：{sk.get('note', '现有技能无对应动作')}")
        lines.append("")

    cov = p.get("skill_coverage") or {}
    if cov:
        lines.append("## 3.5 技能接入（不是另起一套）\n")
        lines.append(f"本计划 {cov['total']} 条方法：已有技能直接做 **{cov['exact']}** 条、"
                     f"同域需扩字段 **{cov['partial']}** 条、需新增 **{cov['new']}** 条；"
                     f"接入率 {cov['coverage_rate']:.0%}。\n")
        lines.append("| 角色 | 方法 | 技能/动作 | 状态 |")
        lines.append("|---|---|---|---|")
        for row in cov["rows"]:
            where = f"`{row['skill']}{(' ' + row['action']) if row['action'] else ''}`"
            lines.append(f"| {row['role']} | {row['method']} | {where} | {row['fit']} |")
        lines.append("")
    lines.append("## 4. 分析设计（先定识别，再算数）\n")
    lines.append("| 问题 | 方法 | 需要的数据 | 最高证据等级 |")
    lines.append("|---|---|---|---|")
    for d in p["analysis_design"]:
        lines.append(f"| {d['question']} | {d['method']} | {d['needs']} | {d['level']} |")
    lines.append("\n> 没有对照组/没有前趋势，就只能到 L2，禁止写「导致/替代/驱动」。")
    lines.append("")

    lines.append("## 5. 三种情景与领先指标（远见从哪来）\n")
    ax1, ax2 = ind["scenarios"][0]
    lines.append(f"两个不确定性轴：**{ax1}** × **{ax2}**。\n")
    lines.append("| 情景 | 触发信号 | 动作 |")
    lines.append("|---|---|---|")
    lines.append(f"| 基准：{ax1}平稳、{ax2}不变 | 连续 2 期核心指标在 ±5% 内 | 按现模型扩量 |")
    lines.append(f"| 上行：{ax1}改善、{ax2}加速 | 领先指标连续 2 期超基线 10% | 加投，抢窗口 |")
    lines.append(f"| 下行：{ax1}恶化、{ax2}迁移 | 客单或复购连续 2 期下滑 | 收缩，保现金 |")
    lines.append("\n**领先指标**（比结果早 1—2 期）：")
    for r in p["roles"][:3]:
        for f in r.get("foresight", [])[:2]:
            lines.append(f"- {r['domain']}：{f}")
    lines.append("")

    lines.append("## 6. 90 天验证计划\n")
    lines.append("| 窗口 | 目标 | 交付 |")
    lines.append("|---|---|---|")
    for s in p["sprints"]:
        lines.append(f"| {s['window']} | {s['goal']} | {s['deliverable']} |")
    lines.append("\n**停止条件**：连续 2 个验证窗口核心指标未达基线，停止扩量；"
                 "因果结论在稳健性检验中不显著，撤回该结论，不换措辞硬写。")
    lines.append("")

    lines.append("## 7. 这个域最容易错的四件事\n")
    for r in p["roles"]:
        for f in r.get("failure_modes", [])[:1]:
            lines.append(f"- {r['domain']}：{f}")
    lines.append("")

    lines.append("## 8. 数据清单（拿到就能跑）\n")
    lines.append("| 表 | 字段 | 用途 |")
    lines.append("|---|---|---|")
    for t, f, u in ind["data"]:
        lines.append(f"| {t} | {f} | {u} |")
    lines.append("")

    lines.append("## 9. 数据到位后跑哪条产线\n")
    lines.append("```powershell")
    lines.append("cd \"D:\\蛙蛙呱呱\\蛙蛙呱呱agents团\"")
    lines.append(f"python guagua.py report produce --intent \"{p['intent']}\" "
                 f"--dir <项目目录> --out <输出目录>")
    lines.append("```")
    lines.append("\n方法引擎：`python -m core.analysis_lab --help`"
                 "（归因 / A/B / DiD / 弹性 / 队列）。")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="domain_pack")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    p = plan(a.intent)
    if a.json:
        text = json.dumps(p, ensure_ascii=False, indent=2)
    else:
        text = to_markdown(p)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
        if not a.json:
            jp = Path(a.out).with_suffix(".json")
            jp.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
            print(f"wrote {jp}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
