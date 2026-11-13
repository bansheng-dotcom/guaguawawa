# -*- coding: utf-8 -*-
"""把 49 次技能调用组装成 6 份命题报告（全部走 core/report_renderer.py）。"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, str(ROOT))

from core import report_renderer  # noqa: E402
from core.report_kernel.structure import layout_errors  # noqa: E402

report_renderer.set_chart_dir(str(ROOT / "core" / "charts"))

D = HERE / "data"
R = HERE / "results"
OUT = HERE / "reports"
OUT.mkdir(exist_ok=True)


DIM_CN = {"completeness": ("完整性", "缺失字段"), "accuracy": ("准确性", "离群值"),
          "consistency": ("一致性", "字段互证"), "timeliness": ("及时性", "新鲜度 SLA 40 天"),
          "uniqueness": ("唯一性", "主键重复"), "validity": ("有效性", "类型 / 枚举")}


def load(name: str) -> dict:
    return json.loads((R / f"{name}.json").read_text(encoding="utf-8"))


def rows(name: str) -> list[dict]:
    with (D / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def txt(strong: str, text: str) -> dict:
    return {"strong": strong, "text": text}


def cell(text: str) -> dict:
    return {"lines": [{"text": str(text)}]}


def num(text, unit: str = "") -> dict:
    return {"text": f"{text}{unit}", "num": True}


def kpi(label: str, value: str, note: str, status: str = "none") -> dict:
    return {"label": label, "value": value, "note": note, "status": status}


def footer(role: str) -> list[str]:
    return [f"{role} · 数据分析能力演练（R06 蛙得清）",
            "渲染 core/report_renderer.py · 数据 results/*.json",
            "生成时间 2026-11-13（Asia/Shanghai）"]


def fidelity_section(index, stats: dict) -> dict:
    rows_ = []
    for k, v, note in stats["rows"]:
        rows_.append([cell(k), num(v), cell(note)])
    return {
        "index": index,
        "title": "口径与分数",
        "question": "这份报告的结论能追回到哪一步？哪些地方是模拟、哪些是真实？",
        "table": {"caption": "自检与数据边界", "columns": [{"text": "指标"}, {"text": "值", "num": True}, {"text": "说明"}],
                  "col_widths": ["22%", "14%", "64%"], "rows": rows_},
        "reading": [txt("怎么读：", stats["how"]), txt("边界：", stats["boundary"])],
    }


def appendix(index, title: str, items: list[tuple[str, str, str]], note: str) -> dict:
    return {
        "index": index,
        "title": title,
        "question": "这次实际跑了哪些技能、输出落在哪里？",
        "intro": [{"text": note}],
        "table": {
            "caption": "技能调用记录（可逐条复跑）",
            "columns": [{"text": "技能 / 动作"}, {"text": "输入"}, {"text": "关键输出"}],
            "col_widths": ["26%", "22%", "52%"],
            "rows": [[{"text": a}, cell(b), cell(c)] for a, b, c in items],
        },
        "appendix": True,
    }


# --------------------------------------------------------------------------- #
# P1 数据底座体检
# --------------------------------------------------------------------------- #
def p1() -> dict:
    q = load("quality_audit")
    qc = load("quality_clean")
    sv = load("semantics_validate")
    sc = load("semantics_compute")
    rp = load("semantics_reconcile_pass")
    rf = load("semantics_reconcile_fail")
    sd = load("scinlp_describe_revenue")
    be = load("scinlp_backend")
    vs = load("viz_spec")
    dl = load("domain_list")

    dims = q["dimension_score"]
    findings = q["findings"]
    gmv = sc["computed_measures"]["gmv"]
    aov = sc["computed_measures"]["aov"]
    order_cnt = sc["computed_measures"].get("order_count")
    desc = sd["describe"]

    dim_rows = [[cell(k), num(v), cell("六维之一")] for k, v in dims.items()]
    findings_rows = [[cell(f["dim"]), cell(f["sev"]), cell(f["note"])] for f in findings]

    sections = [
        {
            "index": 1,
            "title": "质量：8.1 分不是好消息，及时性是 0 分",
            "question": "这批订单数据能不能直接进分析？六个维度里哪一维最危险？",
            "chart": {
                "type": "hbar",
                "title": "数据质量六维得分（满分 10）",
                "unit_meta": "分；分母为各维度规则数",
                "source": "quality audit（R06 s02）；数据 orders.csv，20,000 行 × 17 列",
                "bars": [{"label": DIM_CN.get(k, (k, ""))[0], "sub": DIM_CN.get(k, ("", ""))[1], "value": v,
                          "value_label": f"{v}", "weight": "healthy" if v >= 9 else ("critical" if v == 0 else "context")}
                         for k, v in dims.items()],
            },
            "reading": [
                txt("总分：", f"{q['overall_score']}/10，评级「{q['grade']}」（{q['rows']:,} 行 × {q['fields']} 列）。"),
                txt("及时性 0 分：", "订单最新日期距统计日 40 天，超过 14 天 SLA——这不是数据错，是「日报口径」不成立；月末批量数据只能做月度分析。"),
                txt("准确性 8 分：", "unit_price 离群 522 个、revenue 离群 591 个，只标记不删除；离群集中在高价套装，删掉会低估客单价。"),
                txt("完整性/一致性/唯一性：", "缺失 0、重复 0，主键唯一，不需要清洗（clean 跑完 20,000 行未删一行）。"),
            ],
            "boundary": {"text": "质量分是规则命中率，不是业务正确性；「及时性 0」只说明数据不是当天的，不代表过期。"},
        },
        {
            "index": 2,
            "title": "语义：口径能落地，但对账必须显式",
            "question": "指标定义和真实数据对得上吗？对不上时系统能不能说清为什么？",
            "table": {
                "caption": "语义层校验与口径对账",
                "columns": [{"text": "检查项"}, {"text": "结果", "num": True}, {"text": "说明"}],
                "col_widths": ["24%", "16%", "60%"],
                "rows": [
                    [cell("语义模型校验"), num("PASS"),
                     cell(f"{sv['semantic_models']} 个模型 / {sv['measures']} 个 measure / {sv['metrics']} 个 metric，0 错误")],
                    [cell("GMV（sum revenue）"), num(f"{gmv:,.2f}", " 元"), cell("对 20,000 行订单直接求和")],
                    [cell("客单价（avg revenue）"), num(f"{aov:.2f}", " 元"), cell("GMV ÷ 订单数 = 95.19，与明细一致")],
                    [cell("GMV 对账（同口径）"), num("PASS"),
                     cell(f"两数差 {rp['pct_diff']}%，容差 {rp['tolerance_pct']}%，判定 {rp['status']}")],
                    [cell("市场规模对账（跨口径）"), num("FAIL"),
                     cell(f"4,653 亿 vs 11,042.45 亿，差 {rf['pct_diff']:.2f}%；系统给出 6 条根因（过滤/粒度/定义漂移等）")],
                ],
            },
            "reading": [
                txt("能落地：", f"validate 通过、compute 直接算出 GMV {gmv:,.2f} 元与客单价 {aov:.2f} 元，语义定义没有悬空。"),
                txt("能对账：", "同口径两数差 0% 判 pass；跨口径（统计局限额以上 4,653 亿 vs 香协全渠道 11,042.45 亿）判 fail 并给出根因清单，不让人误以为「数错了」。"),
                txt("已知缺陷：", "compute 的 count_distinct 返回去重值列表而不是计数（本次未把它写进结论）；这是技能实现缺陷，不是数据问题。"),
            ],
            "boundary": {"text": "语义层只覆盖 orders 一张表；跨表 join 的口径一致性没有纳入本次校验。"},
        },
        {
            "index": 3,
            "title": "分布：客单价右偏，均值不是典型值",
            "question": "用均值代表客单价会误导吗？哪些统计量更该报？",
            "chart": {
                "type": "hbar",
                "title": "客单价的关键分位（元）",
                "unit_meta": "元；订单级 revenue",
                "source": "scinlp describe（R06 s06）与 describe（s05）",
                "bars": [{"label": "P5", "value": round(desc["p5"], 1), "value_label": f"{desc['p5']:.1f}",
                          "weight": "reference", "sub": "最低 5% 的订单在此之下"},
                         {"label": "中位数", "value": round(desc["median"], 1), "value_label": f"{desc['median']:.1f}",
                          "weight": "healthy", "sub": "典型订单"},
                         {"label": "均值", "value": round(desc["mean"], 1), "value_label": f"{desc['mean']:.1f}",
                          "weight": "context", "sub": "被高价单抬高"},
                         {"label": "P95", "value": round(desc["p95"], 1), "value_label": f"{desc['p95']:.1f}",
                          "weight": "reference", "sub": "最高 5% 的订单在此之上"}],
            },
            "reading": [
                txt("右偏：", f"均值 {desc['mean']:.2f} 元、中位数 {desc['median']:.2f} 元，偏度 {desc['skew']:.2f}；P95 是 {desc['p95']:.0f} 元，均值被高价套单抬高。"),
                txt("报法：", "对外报客单价应同时给均值 + 中位数 + P95；只报均值会把「典型订单」说贵 25%。"),
                txt("后端：", f"scipy/statsmodels/numpy/pandas {be['backends']['scipy']}，spaCy {be['backends']['spacy']}；NLP 只有简易分词。"),
            ],
            "boundary": {"text": "分位数与偏度只对 orders.csv 成立；不同品类分布不同，不能跨品类套用。"},
        },
        {
            "index": 4,
            "title": "判断：这套数据能撑多强的结论",
            "question": "哪些结论可以直接用、哪些只能当方向？",
            "table": {
                "caption": "数据可用性分级",
                "columns": [{"text": "结论类型"}, {"text": "能不能下"}, {"text": "依据 / 限制"}],
                "col_widths": ["26%", "16%", "58%"],
                "rows": [
                    [cell("总量与结构（GMV、客单价、品类占比）"), num("可以"), cell("订单级明细完整、语义校验通过、对账 0 差")],
                    [cell("趋势与季节性"), num("方向"), cell("只有 39 周且为模拟；真实业务需 12 个月以上")],
                    [cell("因果（渠道/折扣的效果）"), num("不行"), cell("只有观测数据，没有随机分配；需实验或 DID（见 P5）")],
                    [cell("日报级实时性判断"), num("不行"), cell("最新日期距今 40 天，超过 14 天 SLA")],
                ],
            },
            "reading": [
                txt("结论：", "这套数据可以支撑「结构与对比」，不能支撑「因果与实时」；报告里凡是因果表述都必须换成实验或准实验设计。"),
                txt("可视化门禁：", f"viz spec 校验通过（{vs['chart_type_count']} 种图表类型可登记）；图表类型选错会被 schema 拦下。"),
                txt("专业域：", f"domain list 返回 {len(dl.get('skills', dl.get('items', [])))} 项生信技能，后端 omicverse 不在本机，登记为 blocked，不假装能跑。"),
            ],
            "boundary": {"text": "分级只针对本次 20,000 行模拟订单与 76 条个护台账；换数据要重跑质量与语义两道门。"},
        },
        appendix("A1", "记录层：质量与语义检查逐条", [
            ("quality audit", "orders.csv", f"总分 {q['overall_score']}，六维 {dims}"),
            ("quality clean", "orders.csv", f"删除重复 {qc['duplicate_rows_removed']} 行，缺失 {qc['missing']}"),
            ("semantics validate", "semantic_model.json", f"ok={sv['ok']}，errors={sv['errors']}"),
            ("semantics compute", "semantic_model.json + orders.csv", f"gmv={gmv}，aov={aov}，order_count 类型={type(order_cnt).__name__}"),
            ("semantics reconcile ×2", "GMV 对 / 市场规模跨口径", f"pass={rp['status']}，fail={rf['status']}"),
            ("scinlp describe", "orders.csv revenue", f"mean={desc['mean']}，median={desc['median']}，skew={desc['skew']}"),
            ("viz spec", "chart_spec.json", f"ok={vs['ok']}，canonical={vs['canonical']}"),
            ("viz report", "metrics_for_viz.json", "生成 results/viz_report.md（QA 清单 5 项）"),
        ], "每条命令与完整 JSON 见 results/_run_log.json 与 results/*.json；重跑 scripts/run_skills.py 即可复现。"),
        fidelity_section(8, {
            "rows": [("技能调用", "12", "P1 共 12 次 R06 调用，全部 exit 0"),
                     ("数据规模", "20,000 行", "orders.csv；另有 76 条个护真实台账用于口径对账"),
                     ("真实 / 模拟", "1 / 1", "对账用的 4,653 亿与 11,042.45 亿是真实公开数；订单是模拟"),
                     ("未采用输出", "1", "count_distinct 返回值类型异常，未写入结论")],
            "how": "质量分、语义校验、分布统计都是技能直接输出；报告只做格式化，没有二次计算。",
            "boundary": "本报告不评价业务好坏，只回答「数据能不能用、能用到什么程度」。",
        }),
    ]

    return {
        "doc_type": "命题 1 · 数据底座体检（R06 数据分析能力演练）",
        "theme": "sticker",
        "title_lines": ["这套数据能撑多强的结论？", "个护订单 + 市场台账的六维体检"],
        "title_highlight": "能撑多强的结论？",
        "standfirst": "先别急着算指标。20,000 行订单 + 76 条市场台账，先过质量、语义、对账三道门：能过的结论留下，过不了的当场降级。",
        "meta": ["读者：需要拿数据做决策的人", "数据：orders.csv（模拟 2 万单）+ 个护台账（真实 76 条）",
                 "口径：订单级明细 + 限额以上/全渠道两套市场口径", "技能：quality / semantics / scinlp / viz"],
        "metric_strip": [
            kpi("订单行数", "20,000", "17 列，主键唯一（quality）", "accent"),
            kpi("质量总分", f"{q['overall_score']}/10", "六维规则命中，及时性 0 分", "watch"),
            kpi("语义校验", "PASS", f"{sv['measures']} measure / {sv['metrics']} metric", "healthy"),
            kpi("GMV", f"{gmv/1e4:,.1f} 万", "明细直接求和，可复算", "accent"),
            kpi("跨口径对账", "FAIL", f"差 {rf['pct_diff']:.1f}%，已给根因", "critical"),
        ],
        "summary": [
            {"label": "结论：", "text": "这套数据能支撑「结构与对比」，支撑不了「因果与实时」。质量 8.1 分但及时性 0 分，语义层能落地、跨口径对账会失败——失败本身是功能，不是 bug。"},
            {"label": "能用：", "text": f"20,000 行订单完整、无重复、GMV {gmv:,.2f} 元与客单价 {aov:.2f} 元可逐行复算；语义模型 4 个 measure、3 个 metric 全部通过校验。"},
            {"label": "不能用：", "text": "最新订单距统计日 40 天，超过 14 天 SLA，不能用来做日报；订单是模拟数据，任何对外结论都必须标注来源。"},
        ],
        "sections": sections,
        "notes": {"summary": "口径、模拟标注与已知缺陷",
                  "items": [{"label": "真实 vs 模拟：", "text": "orders.csv 为按固定 seed 生成的模拟数据（洗护均价≈53 元、抖音占比 40% 等锚点对齐 2025 公开数据）；4,653 亿、11,042.45 亿为真实公开数。"},
                            {"label": "已知缺陷：", "text": "semantics compute 的 count_distinct 返回去重值列表而非计数；本报告未使用该输出。"},
                            {"label": "复现：", "text": "python scripts/gen_data.py && python scripts/derive.py && python scripts/run_skills.py"}],
                  "tail": "报告由 core/report_renderer.py 从 contract 确定性渲染；手改 HTML 会在重渲时丢失。"},
        "footer": footer("P1 数据底座体检"),
    }


# --------------------------------------------------------------------------- #
# P2 增长量价拆解
# --------------------------------------------------------------------------- #
def p2() -> dict:
    el = load("elasticity_weekly")["elasticity"]
    rg = load("regression_price_qty")["regression"]
    co = load("correlate_discount_revenue")["correlation"]
    dr = load("rootcause_drilldown")
    ts = load("scinlp_textstats")
    dp = load("describe_unit_price")["describe"]["unit_price"]

    hc = rows("haircare_annual.csv")
    real_2024 = float([r for r in hc if r["year"] == "2024"][0]["gmv_yi"])
    real_2025 = float([r for r in hc if r["year"] == "2025"][0]["gmv_yi"])
    vol = 11.94
    price_pct = (1 + 0.0761) / (1 + vol / 100) - 1
    vol_eff = real_2024 * vol / 100
    price_eff = real_2024 * price_pct
    cross = real_2024 * (vol / 100) * price_pct

    wk = rows("price_qty_weekly.csv")
    points = [{"x": float(r["avg_price"]), "y": float(r["units"])} for r in wk]

    sections = [
        {
            "index": 1,
            "title": "量价：+7.61% 里，量给了 +11.94%，价拿走 -3.87%",
            "question": "线上洗护发的增长，多少来自卖得更多、多少来自卖得更贵？",
            "chart": {
                "type": "waterfall",
                "title": "线上洗护发 2025 年增量拆解（亿元）",
                "unit_meta": "亿元；量贡献 = 上年额 × 量增速，价贡献 = 上年额 × 隐含价变动，交叉项 = 上年额 × 量 × 价",
                "source": "真实数据：魔镜洞察 2024/2025 洗护发（695.51 亿、+7.61%、量 +11.94%）",
                "steps": [
                    {"label": "2024", "value": round(real_2024, 2), "kind": "start"},
                    {"label": "量 +11.94%", "value": round(real_2024, 2), "delta": round(vol_eff, 2), "kind": "delta"},
                    {"label": "价 -3.87%", "value": round(real_2024 + vol_eff, 2), "delta": round(price_eff, 2), "kind": "delta"},
                    {"label": "交叉项", "value": round(real_2024 + vol_eff + price_eff, 2), "delta": round(cross, 2), "kind": "delta"},
                    {"label": "2025", "value": round(real_2025, 2), "kind": "end"},
                ],
            },
            "reading": [
                txt("拆解：", f"{real_2024:.2f} 亿元 → {real_2025:.2f} 亿元，增量 {real_2025-real_2024:.2f} 亿元里，量贡献 +{vol_eff:.2f}、价贡献 {price_eff:.2f}、交叉 {cross:.2f}。"),
                txt("口径：", "披露均价 55.75→53.35 元（-4.30%）与额/量隐含价（-3.87%）差 0.43pp；本节分解用隐含价，与披露值的差异属于加权均价口径，不是算错。"),
                txt("含义：", "洗护发的增长是「以价换量」；同样的 1 元增量，含金量低于口腔护理（P3/P5 用同一套口径）。"),
            ],
            "boundary": {"text": "真实数据只有 2024 与 2025 两个年度点；量价分解是两点分解，不是逐月路径。"},
        },
        {
            "index": 2,
            "title": "弹性：价格每降 1%，周销量约涨 1.34%",
            "question": "价格弹性有多大？降价换量在量级上划不划算？",
            "chart": {
                "type": "scatter",
                "title": "洗护发：周均价 vs 周销量（39 周）",
                "unit_meta": "元/件 vs 件；每周一点",
                "source": "模拟订单按周聚合（2026 年 1—9 月，洗护发 7,892 单）；elasticity log-log OLS",
                "points": points,
            },
            "reading": [
                txt("弹性：", f"{el['elasticity']}（R² {el['r2']}，n={el['n']}）——富有弹性，降价 1% 对应销量约 +1.34%。"),
                txt("盈亏平衡：", "若毛利率 50%，降价 1% 需要销量至少 +2.0% 才能保住毛利；1.34% 不够——单纯降价换量在毛利口径下是亏的。"),
                txt("口径：", "弹性是周度 log-log 近似；周均价波动被促销周放大，不能线性外推到 −10%。"),
            ],
            "boundary": {"text": "弹性用模拟周度数据估计；真实弹性需按 SKU/价格带分别估，且要控制促销与流量变化。"},
        },
        {
            "index": 3,
            "title": "微观证据：单价与件数负相关，但解释力只有 2%",
            "question": "订单级的「价格—数量」关系支持上面的弹性吗？",
            "chart": {
                "type": "hbar",
                "title": "订单级回归与相关的效应量",
                "unit_meta": "0—1；R² / |r| / |标准化 beta|",
                "source": "regression（R06 s05）：qty ~ unit_price，n=20,000；correlate：discount vs revenue",
                "bars": [{"label": "价格→件数 R²", "value": round(rg["r_squared"], 4), "value_label": f"{rg['r_squared']:.3f}",
                          "weight": "context", "sub": f"斜率 {rg['slope']:.4f}，t={rg['t']:.1f}"},
                         {"label": "价格→件数 |r|", "value": round(abs(rg["pearson_r"]), 4), "value_label": f"{abs(rg['pearson_r']):.3f}",
                          "weight": "healthy", "sub": "方向：负相关"},
                         {"label": "折扣→金额 |r|", "value": round(abs(co["pearson_r"]), 4), "value_label": f"{abs(co['pearson_r']):.3f}",
                          "weight": "reference", "sub": f"{co['strength']}相关"}],
            },
            "reading": [
                txt("回归：", f"斜率 {rg['slope']:.5f}（p≈0，t={rg['t']:.1f}），R² 只有 {rg['r_squared']}——价格能解释件数差异的 2.2%，其余是品类/促销/用户差异。"),
                txt("折扣：", f"折扣与金额相关 r={co['pearson_r']}（{co['strength']}）；高折扣订单金额略低，说明折扣更多用在低价单上，不是「越折越贵」。"),
                txt("结论：", "方向与弹性一致（负相关、显著），但订单级解释力弱；对外只报方向，不报「降价多少就涨多少」。"),
            ],
            "boundary": {"text": "OLS 未控制品类、渠道、促销；系数是条件相关，不是因果。"},
        },
        {
            "index": 4,
            "title": "结构：80% 的 GMV 由 4 个品类贡献",
            "question": "增长集中在哪几个品类？谁在拖后腿？",
            "chart": {
                "type": "hbar",
                "title": "品类对 GMV 的贡献（份额 %）",
                "unit_meta": "%；按品类聚合；帕累托前 4 到 80%",
                "source": "rootcause drilldown（R06 s04），orders.csv 20,000 单",
                "bars": [{"label": i["segment"], "value": i["share_pct"], "value_label": f"{i['share_pct']:.2f}%",
                          "weight": "healthy" if i["rank"] <= 3 else "context",
                          "sub": f"{i['value']:,.0f} 元｜累计 {i['cum_share_pct']:.1f}%"} for i in dr["items"]],
            },
            "reading": [
                txt("集中：", f"洗护发 {dr['items'][0]['share_pct']}%、口腔 {dr['items'][1]['share_pct']}%、身体 {dr['items'][2]['share_pct']}%；前 {dr['pareto_top_n_for_80pct']} 个品类贡献 80%。"),
                txt("文本：", f"商品标题词频前三是 {ts['top_words'][0]['word']}、{ts['top_words'][1]['word']}、{ts['top_words'][2]['word']}；bigram 里「控油蓬松」「去屑止痒」成对出现，卖点结构清晰。"),
                txt("用法：", "结构决定预算优先级：先守住洗护/口腔两大盘，再谈身体护理的增量。"),
            ],
            "boundary": {"text": "品类结构来自模拟订单的品类分布（洗护 40%、口腔 25%），不是真实市场份额。"},
        },
        appendix("A1", "记录层：39 周价格/销量逐周列出", [
            ("describe unit_price", "orders.csv", f"mean {dp['mean']}，median {dp['median']}，skew {dp['skew']}"),
            ("elasticity", "price_qty_weekly.csv", f"elasticity {el['elasticity']}，R² {el['r2']}，n {el['n']}"),
            ("regression", "orders.csv", f"slope {rg['slope']}，R² {rg['r_squared']}，t {rg['t']}"),
            ("correlate", "orders.csv", f"r {co['pearson_r']}（{co['strength']}）"),
            ("rootcause drilldown", "orders.csv category", f"前 {dr['pareto_top_n_for_80pct']} 品类到 80%"),
            ("scinlp textstats", "sku_titles.csv", f"{ts['doc_count']} 条标题、{ts['token_count']} 词、{ts['vocab_size']} 词表"),
        ], "周度明细见 data/price_qty_weekly.csv；完整技能输出见 results/*.json。"),
        fidelity_section(6, {
            "rows": [("技能调用", "8", "P2：describe×2 / regression / correlate / elasticity / rootcause×2 / scinlp"),
                     ("真实 / 模拟", "2 点真实 + 39 周模拟", "量价分解用真实年度值；弹性用模拟周度"),
                     ("可复算", "全部", "周度 CSV 与回归参数都可重跑"),
                     ("结论等级", "结构=可用；弹性=方向", "弹性不能外推到大幅降价")],
            "how": "量价分解由年度真实值按恒等式拆解（量+价+交叉=增量）；弹性由周度 log-log OLS 估计。",
            "boundary": "模拟周度数据只能证明「方法跑得通」，不能替代真实价格实验。",
        }),
    ]

    return {
        "doc_type": "命题 2 · 增长拆解（R06 数据分析能力演练）",
        "theme": "sticker",
        "title_lines": ["增长是「卖得多」还是「卖得贵」？", "洗护发量价拆解与价格弹性"],
        "title_highlight": "还是「卖得贵」？",
        "standfirst": "695.51 亿元、+7.61%，听起来是增长；拆开看是量 +11.94% 与价 -3.87% 的对冲。这篇回答：钱从哪来，降价换量到底划不划算。",
        "meta": ["读者：定价 / 品类运营", "数据：魔镜洗护发年度值（真实）+ 2 万单模拟订单（弹性）",
                 "口径：线上平台成交；量价分解用隐含价", "技能：describe / regression / correlate / elasticity / rootcause / scinlp"],
        "metric_strip": [
            kpi("2025 线上洗护发", "695.51 亿", "真实数据，+7.61%", "accent"),
            kpi("量贡献", "+11.94%", "交易量增速（真实）", "healthy"),
            kpi("价贡献", "-3.87%", "隐含均价变动", "critical"),
            kpi("价格弹性", f"{el['elasticity']}", f"R² {el['r2']}，n={el['n']}（模拟）", "watch"),
            kpi("前 4 品类 GMV 占比", "80%", "帕累托阈值", "none"),
        ],
        "summary": [
            {"label": "结论：", "text": f"洗护发的增长是「以价换量」：2025 年 695.51 亿元里，量贡献 +{vol_eff:.1f} 亿元、价拿走 {price_eff:.1f} 亿元，净增 {real_2025-real_2024:.1f} 亿元。"},
            {"label": "弹性：", "text": f"模拟周度数据估出弹性 {el['elasticity']}（R² {el['r2']}）：降价 1% 换 1.34% 的量；若毛利率 50%，这个交换在毛利上是亏的。"},
            {"label": "结构：", "text": f"前 {dr['pareto_top_n_for_80pct']} 个品类贡献 80% GMV，洗护发占 {dr['items'][0]['share_pct']}%；预算优先级应按这个顺序排。"},
        ],
        "sections": sections,
        "notes": {"summary": "口径与模拟标注",
                  "items": [{"label": "真实数据：", "text": "695.51 亿元、+7.61%、量 +11.94%、均价 55.75→53.35 元，来自魔镜洞察 2025 洗护发数据（个护调研台账 S26–S28）。"},
                            {"label": "模拟数据：", "text": "周度价格/销量、订单级回归、品类结构来自按 seed=42 生成的模拟订单，锚点对齐真实均价与渠道结构。"},
                            {"label": "盈亏平衡算法：", "text": "毛利率 50% 假设：Δ毛利/毛利 ≈ 量增速×(1-毛利率) − 价格降幅；1.34%×0.5 − 1% = −0.33%。"}],
                  "tail": "弹性是两点/周度近似，不能替代价格实验；正式调价前应做 A/B（见 P4）。"},
        "footer": footer("P2 增长拆解"),
    }


# --------------------------------------------------------------------------- #
# P3 定价与门槛
# --------------------------------------------------------------------------- #
def p3() -> dict:
    rd = load("rdd_paid_value")["rdd"]
    an = load("anova_revenue_category")["anova"]
    ch = load("chi2_category_returned")["chi2"]
    bands = rows("price_bands.csv")

    # RDD 断点两侧 ±5 元带的实付均值（只做展示，估计值仍用局部线性）
    rdd_rows = rows("rdd_carts.csv")
    left = [float(r["paid_value"]) for r in rdd_rows if 94 <= float(r["cart_value"]) < 99]
    right = [float(r["paid_value"]) for r in rdd_rows if 99 <= float(r["cart_value"]) <= 104]
    left_mean, right_mean = sum(left) / len(left), sum(right) / len(right)
    left_n, right_n = len(left), len(right)

    sections = [
        {
            "index": 1,
            "title": "价格带：50—80 元用 13% 的商品数拿走 39% 的销售额",
            "question": "口腔的价格升级落在哪一档？哪一档卖得多但不赚钱？",
            "chart": {
                "type": "hbar",
                "title": "牙膏各价格带销售额占比（2026Q1）",
                "unit_meta": "%；占牙膏线上销售额；副标为销量占比与商品数占比",
                "source": "真实数据：魔镜洞察 2026Q1 牙膏价格带（个护调研台账 S46–S48）",
                "bars": [
                    {"label": "50—80 元", "sub": "销量 26.28%｜商品数 <13%｜效率 3.2", "value": 39.28, "value_label": "39.28%", "weight": "healthy"},
                    {"label": "20—50 元", "sub": "销量 40.78%｜商品数 38.58%｜效率 0.88", "value": 34.09, "value_label": "34.09%", "weight": "context"},
                    {"label": "80 元以上", "sub": "销量 6.41%", "value": 18.44, "value_label": "18.44%", "weight": "reference"},
                ],
            },
            "reading": [
                txt("效率区：", "50—80 元以不足 13% 的商品数贡献 39.28% 销售额，效率指数 3.2——这是升级的主战场。"),
                txt("走量区：", "20—50 元贡献 34.09% 销售额、40.78% 销量、38.58% 商品数，供给最拥挤，价格战在这里。"),
                txt("缺口：", "三档合计 91.81%，剩余 8.19% 原文未披露；不推测。"),
            ],
            "boundary": {"text": "只覆盖牙膏；漱口水价格带结构不同（50—80 元效率指数 2.00），不能外推。"},
        },
        {
            "index": 2,
            "title": "客单价：品类差异显著，但只解释 5.9% 的方差",
            "question": "品类是不是客单价差异的主因？换品类能提客单吗？",
            "chart": {
                "type": "vbar",
                "title": "品类客单价均值（元）",
                "unit_meta": "元；订单级 revenue",
                "source": "anova（R06 s05），orders.csv 20,000 单；F=314.09，η²=0.059",
                "vbars": [{"label": k, "value": round(v["mean"], 1), "value_label": f"{v['mean']:.0f}"}
                          for k, v in sorted(an["groups"].items(), key=lambda kv: -kv[1]["mean"])],
            },
            "reading": [
                txt("显著：", f"F={an['f_statistic']}（df {an['df_between']}/{an['df_within']}），η²={an['eta_squared']}（{an['effect_grade']}）——品类确实影响客单价。"),
                txt("但不大：", "η² 只有 5.9%，94% 的客单价差异来自品类内部（价格带、件数、折扣），换品类不等于提客单。"),
                txt("排序：", "婴童 126.8 元 > 身体 115.0 元 > 口腔 92.0 元 > 洗护 88.8 元 > 女性 76.3 元。"),
            ],
            "boundary": {"text": "单因素 ANOVA 未控制渠道与折扣；η² 是组间方差占比，不是「提客单的杠杆率」。"},
        },
        {
            "index": 3,
            "title": "退货：与品类无关，别把退货算到某个品类头上",
            "question": "退货率差异是品类造成的吗？",
            "table": {
                "caption": "品类 × 退货 卡方检验",
                "columns": [{"text": "统计量"}, {"text": "值", "num": True}, {"text": "判读"}],
                "col_widths": ["30%", "18%", "52%"],
                "rows": [
                    [cell("卡方统计量"), num(f"{ch['chi2_statistic']:.2f}"), cell(f"临界值 {ch['critical_0.05']}（df={ch['df']}）")],
                    [cell("p 判读"), num("不显著"), cell("未拒绝「品类与退货独立」")],
                    [cell("Cramér's V"), num(ch["cramers_v"]), cell(f"效应量 {ch['effect_grade']}")],
                ],
            },
            "reading": [
                txt("结论：", f"卡方 {ch['chi2_statistic']} < 临界 {ch['critical_0.05']}，品类与退货率独立（V={ch['cramers_v']}，可忽略）。"),
                txt("用法：", "退货治理按渠道/物流/尺码做，不按品类做；按品类扣退货率会误伤洗护这种低退货品类。"),
            ],
            "boundary": {"text": "退货字段是 0/1 标记；未区分「质量问题退货」与「无理由退货」。"},
        },
        {
            "index": 4,
            "title": "门槛：满 99 减 10 带来 +12.6 元实付，净赚 2.6 元/单",
            "question": "满减门槛设 99 值不值？断点两侧的实付差多少？",
            "chart": {
                "type": "hbar",
                "title": "断点两侧 ±5 元带的实付均值（元）",
                "unit_meta": "元；未扣价格斜率，局部线性估计已扣",
                "source": "rdd（R06 s05），12,000 个购物车；局部线性 +12.62 元（se 0.26）",
                "bars": [{"label": "断点左侧（94—99）", "value": round(left_mean, 1), "value_label": f"{left_mean:.2f}",
                          "weight": "context", "sub": f"{left_n} 个购物车"},
                         {"label": "断点右侧（99—104）", "value": round(right_mean, 1), "value_label": f"{right_mean:.2f}",
                          "weight": "healthy", "sub": f"{right_n} 个购物车"}],
            },
            "reading": [
                txt("断点：", f"局部线性估计 +{rd['estimate']:.2f} 元（se {rd['se']:.2f}）；带宽网格 50—126 元范围内估计稳定在 {min(g['estimate'] for g in rd['bandwidth_grid']):.3f}—{max(g['estimate'] for g in rd['bandwidth_grid']):.3f} 元。"),
                txt("检验：", f"密度检验 p={rd['density_p']}（无操纵迹象）；协变量最大 SMD {rd['covariate_balance']['max_abs_smd']}（平衡）；二次项估计 {rd['quadratic_estimate']}。"),
                txt("净效应：", "减 10 元带来 +12.62 元实付，收入口径单均净 +2.62 元；毛利口径（按 50% 毛利）增量毛利约 6.3 元，仍低于 10 元折扣，差 -3.7 元/单，需用复购或提价补。"),
            ],
            "boundary": {"text": "断点回归只识别门槛附近的局部效应；未做安慰剂检验（robust=false），不能外推到 129 元门槛。"},
        },
        appendix("A1", "记录层：价格带、ANOVA、卡方、RDD", [
            ("describe ×2", "price_bands.csv", "销售额占比 / 销量占比分布"),
            ("anova", "orders.csv", f"F {an['f_statistic']}，η² {an['eta_squared']}"),
            ("chi2", "orders.csv category × returned", f"chi2 {ch['chi2_statistic']}，V {ch['cramers_v']}"),
            ("rdd", "rdd_carts.csv", f"estimate {rd['estimate']}，se {rd['se']}，density p {rd['density_p']}"),
            ("describe", "rdd_carts.csv paid_value", "断点两侧分布"),
        ], "完整 RDD 输出（带宽网格、协变量平衡、二次项）见 results/rdd_paid_value.json。"),
        fidelity_section(6, {
            "rows": [("技能调用", "6", "P3：describe / anova / chi2 / rdd"),
                     ("真实 / 模拟", "价格带真实；RDD/订单模拟", "价格带来自魔镜；断点与订单为模拟"),
                     ("断点样本", "12,000", "购物车金额 30—220 元，断点 99 元"),
                     ("稳健性", "部分", "带宽网格稳定；未做安慰剂，robust=false")],
            "how": "效率指数 = 销售额占比 ÷ 商品数占比；断点估计是局部线性，带宽网格用于敏感性。",
            "boundary": "满减结论只对 99 元门槛附近成立；129 元门槛需另跑一次。",
        }),
    ]

    return {
        "doc_type": "命题 3 · 定价与门槛（R06 数据分析能力演练）",
        "theme": "sticker",
        "title_lines": ["50—80 元是利润区吗？", "价格带效率、客单价结构与满减断点"],
        "title_highlight": "是利润区吗？",
        "standfirst": "定价不是选一个数字。先看真实价格带的效率，再看客单价差异来自哪里，最后用断点回归算清「满 99 减 10」到底赚不赚。",
        "meta": ["读者：定价 / 电商运营", "数据：魔镜牙膏价格带（真实）+ 2 万单 / 12,000 购物车（模拟）",
                 "口径：线上平台；断点为 99 元满减", "技能：describe / anova / chi2 / rdd"],
        "metric_strip": [
            kpi("50—80 元销售额占比", "39.28%", "真实；商品数不足 13%", "healthy"),
            kpi("效率指数", "3.2", "销售额占比 ÷ 商品数占比", "accent"),
            kpi("品类 η²", f"{an['eta_squared']}", "客单价方差被品类解释的比例", "watch"),
            kpi("满减断点效应", f"+{rd['estimate']:.2f} 元", f"se {rd['se']:.2f}，12,000 购物车", "accent"),
            kpi("退货 × 品类", "不显著", f"χ²={ch['chi2_statistic']:.2f}", "none"),
        ],
        "summary": [
            {"label": "结论：", "text": "50—80 元确实是效率区（真实数据，效率 3.2）；但客单价差异只有 5.9% 由品类解释，提客单不能靠换品类；满减 99 元带来 +12.6 元实付，单均净 +2.6 元。"},
            {"label": "定价：", "text": "主推价格带锚 50—80 元，20—50 元只做走量防守；用「加购凑单」把 20—50 元客户推到 50—80 元，而不是直接降价。"},
            {"label": "门槛：", "text": "满 99 减 10 的净效应为正，但毛利覆盖不足，必须用 30 天复购补；129 元门槛没有数据，不要照搬。"},
        ],
        "sections": sections,
        "notes": {"summary": "口径与模拟标注",
                  "items": [{"label": "真实：", "text": "牙膏三档价格带的销售额/销量/商品数占比来自魔镜洞察 2026Q1（个护调研台账 S46–S48）。"},
                            {"label": "模拟：", "text": "订单客单价、退货、购物车与满减断点均按 seed=42 生成；断点真实效应设为 +12.5 元，估计 +12.62 元。"},
                            {"label": "效率指数：", "text": "销售额占比 ÷ 商品数占比；>1 表示该价格带单位供给的产出更高。"}],
                  "tail": "RDD 未做安慰剂，robust=false；对外引用只报「局部 +12.6 元」，不报「所有门槛都该这么设」。"},
        "footer": footer("P3 定价与门槛"),
    }


# --------------------------------------------------------------------------- #
# P4 A/B 实验
# --------------------------------------------------------------------------- #
def p4() -> dict:
    pn = load("power_n")["power"]
    pm = load("power_mde")["power"]
    ac = load("abtest_convert")["abtest"]
    ak = load("abtest_click")["abtest"]
    srm = load("abtest_srm")["abtest"]
    tt = load("ttest_revenue")["welch_t"]
    cd = load("chi2_device_convert")["chi2"]

    sections = [
        {
            "index": 1,
            "title": "设计：先算样本量，再看结果",
            "question": "这个实验能检出多大的效果？样本够不够？",
            "chart": {
                "type": "vbar",
                "title": "功效设计：所需样本量 vs 实际样本量（万/组）",
                "unit_meta": "万/组；MDE 0.22pp 见读图",
                "source": "power（R06 s05）：baseline 3.2%，alpha 0.05，power 0.8",
                "vbars": [{"label": "所需样本/组", "value": round(pn["required_n_per_group"] / 10000, 2), "value_label": "8.07 万"},
                          {"label": "实际样本/组", "value": 10.0, "value_label": "10 万", "weight": "healthy"}],
            },
            "reading": [
                txt("样本量：", f"基线 3.2%、绝对 MDE 0.25pp，需要每组 {pn['required_n_per_group']:,} 个样本（80% 功效）；本次每组 10 万，刚够。"),
                txt("可检出下限：", f"每组 10 万时 MDE 为 {pm['mde_solvable']*100:.2f}pp（相对 {pm['mde_solvable']/0.032*100:.1f}%）；小于这个量级的效果检不出来。"),
                txt("纪律：", "先写主指标与 MDE，再开实验；事后改主指标就是 p-hacking。"),
            ],
            "boundary": {"text": "功效按双比例 z 检验正态近似；实际检测用了更保守的 Welch 口径。"},
        },
        {
            "index": 2,
            "title": "读出：CTR +3.1%、CVR +2.4%，都不显著",
            "question": "主图改版承诺的 +8% 兑现了吗？该不该发？",
            "chart": {
                "type": "hbar",
                "title": "A/B 两组的主指标（%）",
                "unit_meta": "%；CTR = click，CVR = convert",
                "source": "abtest（R06 s05），ab_clean.csv 200,000 会话",
                "bars": [{"label": "CTR · A", "value": round(ak["control_mean"] * 100, 2), "value_label": f"{ak['control_mean']*100:.2f}%",
                          "weight": "context", "sub": f"lift {ak['lift_pct']}%，p={ak['p_value_approx']}"},
                         {"label": "CTR · B", "value": round(ak["treatment_mean"] * 100, 2), "value_label": f"{ak['treatment_mean']*100:.2f}%",
                          "weight": "healthy", "sub": "新版"},
                         {"label": "CVR · A", "value": round(ac["control_mean"] * 100, 2), "value_label": f"{ac['control_mean']*100:.2f}%",
                          "weight": "context", "sub": f"lift {ac['lift_pct']}%，p={ac['p_value_approx']}"},
                         {"label": "CVR · B", "value": round(ac["treatment_mean"] * 100, 2), "value_label": f"{ac['treatment_mean']*100:.2f}%",
                          "weight": "healthy", "sub": "新版"}],
            },
            "reading": [
                txt("CTR：", f"{ak['control_mean']*100:.2f}% → {ak['treatment_mean']*100:.2f}%，lift {ak['lift_pct']}%，p={ak['p_value_approx']}（不显著）。"),
                txt("CVR：", f"{ac['control_mean']*100:.2f}% → {ac['treatment_mean']*100:.2f}%，lift {ac['lift_pct']}%，p={ac['p_value_approx']}，判定 {ac['decision']}。"),
                txt("兑现：", "承诺 +8% 相对提升，实测 +3.1% / +2.4%，且都在噪声范围内；不能宣布成功。"),
            ],
            "boundary": {"text": "CVR 只统计会话级转化；未覆盖复购与退款，不能代表 GMV 收益。"},
        },
        {
            "index": 3,
            "title": "SRM：分流 52/48 的实验，结果再好看也不能用",
            "question": "样本比例失配时，显著结果能不能采信？",
            "table": {
                "caption": "两个实验的 SRM 与决策",
                "columns": [{"text": "实验"}, {"text": "SRM χ²", "num": True}, {"text": "lift", "num": True}, {"text": "决策"}],
                "col_widths": ["26%", "16%", "16%", "42%"],
                "rows": [
                    [cell("ab_clean（50/50）"), num(f"{ac['srm_chi2']:.2f}"), num(f"{ac['lift_pct']}%"), cell(f"{ac['decision']}（无 SRM）")],
                    [cell("ab_srm（52/48）"), num(f"{srm['srm_chi2']:.1f}"), num(f"{srm['lift_pct']}%"), cell(f"{srm['decision']}（显著也不采信）")],
                ],
            },
            "reading": [
                txt("SRM：", f"ab_srm 的 χ²={srm['srm_chi2']:.1f}，远超临界 {srm['srm_critical_chi2']}——分流代码或埋点有问题。"),
                txt("纪律：", "SRM 异常时先查分流与去重，不能因为 p<0.05 就宣布胜利；这是实验平台最常见的事故。"),
                txt("正确动作：", "重跑实验，确认 50/50 后再读主指标。"),
            ],
            "boundary": {"text": "SRM 只查总量比例；分层后的比例失衡需要额外检查。"},
        },
        {
            "index": 4,
            "title": "分层：设备间没有交互，收入差异也不显著",
            "question": "效果是否集中在某类设备？收入有没有变化？",
            "table": {
                "caption": "分层与收入检验",
                "columns": [{"text": "检验"}, {"text": "统计量", "num": True}, {"text": "判读"}],
                "col_widths": ["26%", "18%", "56%"],
                "rows": [
                    [cell("设备 × 转化（卡方）"), num(f"{cd['chi2_statistic']:.2f}"), cell(f"临界 {cd['critical_0.05']}，不显著（V={cd['cramers_v']}）")],
                    [cell("收入（Welch t）"), num(f"{tt['t']:.2f}"), cell(f"p={tt['p_value_approx']}，d={tt['cohens_d']}（{tt['effect_grade']}）")],
                ],
            },
            "reading": [
                txt("设备：", "iOS/Android/PC 的转化差异不显著，改版效果没有集中在某一端。"),
                txt("收入：", f"两组收入差异 {tt['diff']:.2f} 元、p={tt['p_value_approx']}；即使 CVR 小幅上升，也没有转化为可测的收入增量。"),
                txt("结论：", "不 ship；把预算留给下一次改版，或把样本量提到 20 万/组再测。"),
            ],
            "boundary": {"text": "分层检验未做多重比较校正；设备维度只有 3 层，检验力有限。"},
        },
        appendix("A1", "记录层：4 次实验读数", [
            ("power ×2", "baseline 3.2% / n=10 万", f"n={pn['required_n_per_group']}；MDE={pm['mde_solvable']}"),
            ("abtest convert", "ab_clean.csv", f"lift {ac['lift_pct']}%，p {ac['p_value_approx']}，{ac['decision']}"),
            ("abtest click", "ab_clean.csv", f"lift {ak['lift_pct']}%，p {ak['p_value_approx']}"),
            ("abtest SRM", "ab_srm.csv", f"χ² {srm['srm_chi2']}，{srm['decision']}"),
            ("ttest", "ab_clean.csv revenue", f"diff {tt['diff']}，p {tt['p_value_approx']}"),
            ("chi2", "ab_clean.csv device × convert", f"χ² {cd['chi2_statistic']}，不显著"),
        ], "实验数据为模拟（seed=42），但分流与效应结构按真实实验规范构造。"),
        fidelity_section(6, {
            "rows": [("技能调用", "7", "P4：power×2 / abtest×3 / ttest / chi2"),
                     ("样本", "200,000", "10 万/组；SRM 版 19.6 万"),
                     ("真实 / 模拟", "全模拟", "按真实实验规范生成，结论只演示方法"),
                     ("决策", "no_ship", "主指标不显著，SRM 版判 rerun")],
            "how": "lift = (处理−对照)/对照；SRM 用卡方检验分流比例；MDE 由功效公式反解。",
            "boundary": "模拟实验不能替代线上真实实验；但流程与判定规则可直接复用。",
        }),
    ]

    return {
        "doc_type": "命题 4 · A/B 实验（R06 数据分析能力演练）",
        "theme": "sticker",
        "title_lines": ["主图改版能不能把转化提上去？", "一次 20 万人 A/B 的设计、读出与 SRM 门禁"],
        "title_highlight": "能不能把转化提上去？",
        "standfirst": "实验不是「跑完看 p 值」。先算 MDE，再看 SRM，最后才读 lift——这篇用一次 20 万人的模拟实验，把顺序走一遍。",
        "meta": ["读者：增长 / 产品", "数据：200,000 会话（模拟，seed=42）",
                 "口径：会话级 CTR/CVR；80% 功效，alpha 0.05", "技能：power / abtest / ttest / chi2"],
        "metric_strip": [
            kpi("样本", "20 万", "10 万/组，满足 80,735/组", "accent"),
            kpi("CTR lift", f"{ak['lift_pct']}%", f"p={ak['p_value_approx']}", "watch"),
            kpi("CVR lift", f"{ac['lift_pct']}%", f"p={ac['p_value_approx']}", "watch"),
            kpi("SRM（clean）", "通过", f"χ²={ac['srm_chi2']:.2f}", "healthy"),
            kpi("决策", "不 ship", "主指标不显著", "critical"),
        ],
        "summary": [
            {"label": "结论：", "text": f"主图改版的 CTR +{ak['lift_pct']}%、CVR +{ac['lift_pct']}%，都不显著；承诺的 +8% 没有兑现，判定 no_ship。"},
            {"label": "为什么：", "text": f"这次只够检出 {pm['mde_solvable']*100:.2f}pp 的绝对提升，实测差异在噪声内；不是「改版无效」，是「证据不够」。"},
            {"label": "门禁：", "text": f"另一个 52/48 分流的实验 lift {srm['lift_pct']}%、p<0.01，但 SRM χ²={srm['srm_chi2']:.1f}，直接判 rerun——显著不等于可信。"},
        ],
        "sections": sections,
        "notes": {"summary": "模拟实验与判定规则",
                  "items": [{"label": "模拟：", "text": "200,000 会话按 seed=42 生成；基线 CTR 3.2%、CVR 2.1%，与公开个护电商基准同量级。"},
                            {"label": "判定：", "text": "ship 需同时满足：显著正、lift≥3%、无 SRM；否则 no_ship；SRM 异常一律 rerun。"},
                            {"label": "复现：", "text": "results/abtest_*.json 保留了每组均值、p 值、SRM χ² 与决策。"}],
                  "tail": "模拟实验只证明流程可跑；真实上线前仍需按同一 MDE 重新设计。"},
        "footer": footer("P4 A/B 实验"),
    }


# --------------------------------------------------------------------------- #
# P5 预算迁移因果
# --------------------------------------------------------------------------- #
def p5() -> dict:
    did = load("did_twfe")
    stag = load("did_staggered")
    m = load("matched_psm")["matched"]
    rf = load("matched_psm")["refute"]
    ca = load("causal_backdoor")["causal"]

    panel = rows("panel_did.csv")
    weeks = sorted({int(r["week"]) for r in panel})
    series = {"treat": [], "control": []}
    for w in weeks:
        for g, key in (("1", "treat"), ("0", "control")):
            v = [float(r["gmv"]) for r in panel if int(r["week"]) == w and r["treat"] == g]
            series[key].append(round(sum(v) / len(v) / 1e4, 1))

    att = did["did"]["att"]
    es = did.get("event_study", {}).get("coefficients", {})

    sections = [
        {
            "index": 1,
            "title": "平行趋势：处理组与对照组在切换前同涨同跌",
            "question": "两组在预算迁移前有没有系统性差异？DID 的前提成立吗？",
            "chart": {
                "type": "line",
                "title": "处理组 vs 对照组周均 GMV（万元）",
                "unit_meta": "万元；40 城，处理组第 10 周起切换预算",
                "source": "panel_did.csv（模拟，seed=42）；线性预趋势检验 p=0.26",
                "xlabels": [str(w) for w in weeks],
                "series": [{"name": "处理组", "values": series["treat"], "accent": True},
                           {"name": "对照组", "values": series["control"]}],
                "ref_line": {"value": round(sum(series["treat"][:9]) / 9, 1), "label": "切换前处理组均值"},
            },
            "reading": [
                txt("趋势：", f"线性预趋势系数 p={did['did']['pretrend']['p']}（>0.05），不拒绝平行趋势。"),
                txt("水平：", "切换前处理组均值略低于对照组（约 -5 万/周），DID 用双向固定效应吸收城市固定差异，不要求水平相同。"),
                txt("注意：", "只证明了「没有线性预趋势」，不等于没有其他混杂；下面用安慰剂与 PSM 交叉验证。"),
            ],
            "boundary": {"text": "40 个城市、26 周，单位数偏少；聚类标准误只有 40 个簇，p 值应谨慎解读。"},
        },
        {
            "index": 2,
            "title": "DID：切换后周均 GMV 多出约 9.9 万元",
            "question": "预算迁移带来的增量有多大？显著吗？",
            "chart": {
                "type": "hbar",
                "title": "事件研究系数（万元，相对 -1 期）",
                "unit_meta": "万元；双向固定效应 + 聚类 SE",
                "source": "did --event-study；以 -1 期为基准，pre 系数应接近 0",
                "bars": [{"label": f"第 {k} 期", "value": round(v["coef"] / 1e4, 1), "sub": f"p={v['p']}",
                          "value_label": f"{v['coef']/1e4:+.1f}", "weight": "critical" if v["coef"] < 0 else "healthy"}
                         for k, v in sorted(es.items(), key=lambda kv: int(kv[0]))],
            },
            "reading": [
                txt("ATT：", f"+{att:,.0f} 元/周（聚类 SE {did['did']['se_cluster']:,.0f}，t={did['did']['t']}，p<0.001），约 +8.9%。"),
                txt("安慰剂：", f"100 次随机打乱处理标签，主效应 p={did['placebo']['p_perm']}——不是随机标签造成的。"),
                txt("交错处理：", f"分三批第 8/12/16 周进入，简化 CS 估计 {stag['staggered']['att']:,.0f} 元（se {stag['staggered']['se']:,.0f}），与 TWFE 同向但更小。"),
                txt("事件研究的口径：", "系数以「窗口外所有期」为基准，含季节基期；pre 期 -2 期系数 -3.0 万与线性预趋势 p=0.26 不一致，不能直接读作预趋势。"),
            ],
            "boundary": {"text": "TWFE 假设处理效应同质；交错处理下 TWFE 可能高估，CS 估计 6.2 万更保守。"},
        },
        {
            "index": 3,
            "title": "PSM：匹配后 ATT 6.0pp，协变量仍未完全平衡",
            "question": "用可观测协变量匹配后，增量还剩下多少？",
            "table": {
                "caption": "PSM 匹配与反驳",
                "columns": [{"text": "指标"}, {"text": "值", "num": True}, {"text": "说明"}],
                "col_widths": ["28%", "18%", "54%"],
                "rows": [
                    [cell("ATT（pp）"), num(f"{m['att']}"), cell(f"95% CI [{m['ci95'][0]}, {m['ci95'][1]}]")],
                    [cell("匹配对数"), num(f"{m['n_matched']}/{m['n_treat']}"), cell(f"卡尺 {m['caliper_logit']}")],
                    [cell("SMD 匹配前/后"), num(f"{m['smd_before_max']} → {m['smd_after_max']}"), cell("仍 >0.1，未完全平衡")],
                    [cell("反驳：安慰剂"), num(f"{rf['placebo_att']}"), cell(f"远小于主效应 {rf['original_att']}，pass={rf['passed']}")],
                    [cell("反驳：子集"), num(f"{rf['subset_att']}"), cell("与主效应同向")],
                ],
            },
            "reading": [
                txt("结果：", f"PSM ATT {m['att']}pp，CI 不含 0；比 DID 的 +8.9% 低，说明部分增量来自可观测差异。"),
                txt("平衡：", f"最大 SMD 从 {m['smd_before_max']} 降到 {m['smd_after_max']}，仍高于 0.1——匹配不完美，ATT 只能当区间下沿。"),
                txt("反驳：", f"安慰剂 {rf['placebo_att']}pp、子集 {rf['subset_att']}pp，方向一致，未见明显造假信号。"),
            ],
            "boundary": {"text": "PSM 只平衡观测到的协变量；未观测混杂（如城市经营能力）无法消除。"},
        },
        {
            "index": 4,
            "title": "后门调整：混杂偏差约 0.88pp，调整后 5.6pp",
            "question": "如果不做因果调整，直接比均值会高估多少？",
            "table": {
                "caption": "后门调整分解",
                "columns": [{"text": "项"}, {"text": "值（pp）", "num": True}, {"text": "说明"}],
                "col_widths": ["28%", "18%", "54%"],
                "rows": [
                    [cell("未调整差"), num(f"{ca['estimate']['unadjusted_effect']}"), cell("处理组均值 − 对照组均值")],
                    [cell("混杂偏差"), num(f"{ca['estimate']['confounding_bias']}"), cell("由协变量不平衡贡献")],
                    [cell("调整后效应"), num(f"{ca['estimate']['adjusted_effect']}"), cell("分层后门调整（观测混杂）")],
                    [cell("使用层数"), num(f"{ca['estimate']['strata_used']} / 37"), cell("样本小，多数层被跳过")],
                ],
            },
            "reading": [
                txt("分解：", f"naive {ca['estimate']['unadjusted_effect']}pp = 效应 {ca['estimate']['adjusted_effect']}pp + 偏差 {ca['estimate']['confounding_bias']}pp。"),
                txt("不稳定：", "40 个城市分 4 个协变量后只剩 2 层可比，调整值不稳定；它是方向校验，不是精确估计。"),
                txt("合并判断：", "DID 8.9%、PSM 6.0pp、后门调整 5.6pp、交错处理 6.2 万——增量存在，区间约 5.6—8.9pp。"),
            ],
            "boundary": {"text": "后门调整依赖「无未观测混杂」假设；本数据无法验证该假设。"},
        },
        appendix("A1", "记录层：DID / PSM / 因果调整", [
            ("did --event-study --placebo", "panel_did.csv", f"ATT {att:.0f}，pre p={did['did']['pretrend']['p']}，placebo p={did['placebo']['p_perm']}"),
            ("did --staggered", "panel_staggered.csv", f"TWFE {stag['did']['att']:.0f}，CS {stag['staggered']['att']:.0f}"),
            ("matched --refute", "cities_treat/control.csv", f"ATT {m['att']}pp，balanced={m['balanced']}"),
            ("causal", "cities_all.csv", f"adjusted {ca['estimate']['adjusted_effect']}pp，bias {ca['estimate']['confounding_bias']}"),
        ], "城市级面板与截面均为模拟；完整输出见 results/did_*.json、matched_psm.json、causal_backdoor.json。"),
        fidelity_section(8, {
            "rows": [("技能调用", "4", "P5：did×2（含 event/placebo/staggered）/ matched / causal"),
                     ("面板", "40 城 × 26 周", "1,040 行；处理组 20 城"),
                     ("真实 / 模拟", "全模拟", "真实效应 +8%（TWFE）/ +10%（交错）"),
                     ("估计区间", "5.6—8.9pp", "DID / PSM / CS / 后门调整交叉")],
            "how": "ATT 为双向固定效应 + 聚类 SE；PSM 用 logit 倾向得分 + 卡尺匹配；后门调整为分层加权。",
            "boundary": "四种方法都不消除未观测混杂；对外表述用「区间」不用「精确值」。",
        }),
    ]

    return {
        "doc_type": "命题 5 · 预算迁移的因果增量（R06 数据分析能力演练）",
        "theme": "sticker",
        "title_lines": ["把预算搬到抖音，有增量吗？", "DID + PSM + 后门调整的四重交叉"],
        "title_highlight": "有增量吗？",
        "standfirst": "「抖音涨得快」是相关性；「因为搬到抖音才涨」才是因果。这篇用 40 城 × 26 周的模拟面板，把 DID、PSM、交错处理与后门调整都跑一遍，看四个估计能不能对上。",
        "meta": ["读者：增长 / 渠道预算负责人", "数据：40 城 × 26 周面板 + 40 城截面（模拟，seed=42）",
                 "口径：城市周 GMV；切换时点第 10 周", "技能：did / matched / causal"],
        "metric_strip": [
            kpi("TWFE ATT", f"+{att/1e4:.1f} 万/周", f"约 +8.9%，p<0.001", "accent"),
            kpi("预趋势", "p=0.26", "不拒绝平行趋势", "healthy"),
            kpi("安慰剂", f"p={did['placebo']['p_perm']}", "100 次置换", "healthy"),
            kpi("PSM ATT", f"{m['att']}pp", f"CI [{m['ci95'][0]}, {m['ci95'][1]}]", "watch"),
            kpi("后门调整", f"{ca['estimate']['adjusted_effect']}pp", "混杂偏差 0.88pp", "watch"),
        ],
        "summary": [
            {"label": "结论：", "text": f"预算迁移的增量存在，但幅度在 5.6—8.9pp 之间，不是一个精确值：TWFE +8.9%、PSM 6.0pp、交错处理 6.2 万/周、后门调整 5.6pp。"},
            {"label": "可信度：", "text": "预趋势 p=0.26、安慰剂 p=0.00、PSM 反驳通过；但事件研究 pre 期系数与线性预趋势不一致，PSM 协变量仍未完全平衡——按区间下沿做预算。"
            },
            {"label": "动作：", "text": "按 5.6% 的保守增量建模，先投 30% 预算做一轮真实灰度；达到 5% 再追加，低于 3% 停止。"},
        ],
        "sections": sections,
        "notes": {"summary": "模拟面板与估计口径",
                  "items": [{"label": "模拟：", "text": "40 城 × 26 周，处理组第 10 周起 GMV +8%；交错版分 8/12/16 周三批、+10%。"},
                            {"label": "方法：", "text": "TWFE（unit+time FE，聚类到城市）、事件研究、置换安慰剂、PSM（logit+卡尺）、后门分层调整。"},
                            {"label": "事件研究：", "text": "系数以窗口外期为基准，含季节基期；与线性预趋势检验口径不同，两者冲突时按更保守的读。"}],
                  "tail": "所有估计都只对观测到的混杂成立；真实投放还应做地理实验（geo test）验证。"},
        "footer": footer("P5 预算迁移因果"),
    }


# --------------------------------------------------------------------------- #
# P6 用户留存与内容
# --------------------------------------------------------------------------- #
def p6() -> dict:
    fn = load("funnel")
    co = load("cohort")
    rfm = load("rfm")
    seg = load("segment")
    mt = load("metrics_ecommerce")
    tt = load("ttest_new")["welch_t"]
    ch = load("chi2_channel_returned")["chi2"]
    sm = load("selfmedia_dashboard")
    saas = load("explore_saas")

    # RFM 聚合
    segs = rfm["segments"]
    rfm_counts = {}
    for s in segs:
        key = s["rfm"]
        rfm_counts[key] = rfm_counts.get(key, 0) + 1
    top_rfm = sorted(rfm_counts.items(), key=lambda kv: -kv[1])[:6]
    champions = sum(1 for s in segs if s["r"] >= 4 and s["f"] >= 4 and s["m"] >= 4)
    at_risk = sum(1 for s in segs if s["r"] <= 2)

    # cohort heatmap：保留 p1..p5
    periods = co["periods"]
    last_complete = "2026-09"          # 9 月之后只有零星订单，不能当完整月
    cohorts = [c for c in co["matrix"] if c["cohort_size"] >= 200][:8]
    cols = ["p1", "p2", "p3", "p4", "p5"]
    cells = []
    for c in cohorts:
        i = periods.index(c["cohort"]) if c["cohort"] in periods else None
        row = []
        for k in range(1, 6):
            target = periods[i + k] if i is not None and i + k < len(periods) else None
            v = c.get(f"p{k}")
            if v is None or target is None or target > last_complete:
                row.append(None)
            else:
                row.append(round(v / c["cohort_size"] * 100, 1))
        cells.append(row)

    sections = [
        {
            "index": 1,
            "title": "漏斗：曝光到支付 3.3%，最大漏损在点击前",
            "question": "用户在哪一步流失最多？先修哪一段？",
            "chart": {
                "type": "funnel",
                "title": "曝光 → 支付 五级漏斗",
                "unit_meta": "人；同一批用户的累计到达数",
                "source": "explore funnel（R06 s03）；funnel.csv 69,050 条用户-阶段记录",
                "stages": [{"label": s["stage"], "value": s["count"]} for s in fn["stages"]],
            },
            "reading": [
                txt("整体：", f"曝光 {fn['stages'][0]['count']:,} → 支付 {fn['stages'][-1]['count']:,}，整体转化 {fn['stages'][-1]['conversion_overall']*100:.1f}%。"),
                txt("漏损：", "曝光→点击 76% 流失、点击→加购 70%、加购→下单 50%；前三段都触发 drop_alert（≥20%）。"),
                txt("优先：", "先修曝光→点击（素材与人群），再修点击→加购（详情页与价格）；支付段只流失 8.3%，不是瓶颈。"),
            ],
            "boundary": {"text": "漏斗是累计到达口径；未去重跨设备，也没有归因窗口。"},
        },
        {
            "index": 2,
            "title": "留存：首月后稳定在 33% 左右，没有「二次下滑」",
            "question": "用户的复购节奏是什么样？哪个月入组的用户更值钱？",
            "chart": {
                "type": "heatmap",
                "title": "月度 cohort 留存率（%）",
                "unit_meta": "%；行=入组月，列=入组后第 N 月",
                "source": "explore cohort（R06 s03），orders.csv 5,345 个用户",
                "rows": [c["cohort"] for c in cohorts],
                "cols": ["第 1 月", "第 2 月", "第 3 月", "第 4 月", "第 5 月"],
                "cells": cells,
            },
            "reading": [
                txt("留存：", "入组后第 1 月留存约 33%，之后基本持平（32%—36%），说明复购是「月度节奏」而不是持续衰减。"),
                txt("cohort：", f"1 月入组 {co['matrix'][0]['cohort_size']:,} 人最大，9 月只有 {co['matrix'][-2]['cohort_size']} 人——越晚入组规模越小，渠道获客在收缩。"),
                txt("含义：", "留存曲线平，说明用户不是「用完就走」；增长瓶颈在获客（漏斗前段），不在留存。"),
            ],
            "boundary": {"text": "cohort 以「有订单」定义活跃，未区分浏览/加购；10 月只有零星订单（数据截止 9 月底），末列留空；9 月 cohort 观察期不足，不参与比较。"},
        },
        {
            "index": 3,
            "title": "分群：0.6% 的鲸鱼用户贡献 13 倍人均订单",
            "question": "用户结构长什么样？预算该给哪一群人？",
            "chart": {
                "type": "hbar",
                "title": "K-means 四群规模（人）",
                "unit_meta": "人；特征：订单数/金额/最近购买/客单价",
                "source": "explore segment（R06 s03），k=4，silhouette 0.496",
                "bars": [{"label": f"{c['segment']}（{c['strategy']}）", "sub": f"占 {c['size_pct']}%｜订单均值 {c['profile']['orders']['mean']:.1f}",
                          "value": c["size"], "value_label": f"{c['size']:,}", "weight": "healthy" if c["size_pct"] > 30 else "context"}
                         for c in seg["clusters"]],
            },
            "reading": [
                txt("结构：", f"{seg['clusters'][0]['size']} 人（0.56%）人均 {seg['clusters'][0]['profile']['orders']['mean']:.0f} 单，是鲸鱼群；{seg['clusters'][3]['size_pct']}% 是待唤醒群。"),
                txt("RFM：", f"R/F/M 全 4 分以上的核心客 {champions} 人（{champions/len(segs)*100:.1f}%）；R≤2 的流失风险客 {at_risk} 人（{at_risk/len(segs)*100:.1f}%）。"),
                txt("预算：", "鲸鱼群做专属服务保留存；待唤醒群用低成本触达；不要给全量发大额券。"),
            ],
            "boundary": {"text": "k-means 对量纲敏感，本次特征已同尺度；silhouette 0.496 表示分群可用但不算强分离。"},
        },
        {
            "index": 4,
            "title": "首单折扣客并不更值钱，退货差异在渠道不在折扣",
            "question": "首单折扣拉来的用户，客单与留存有差异吗？",
            "table": {
                "caption": "新客与退货的两个检验",
                "columns": [{"text": "检验"}, {"text": "统计量", "num": True}, {"text": "判读"}],
                "col_widths": ["28%", "18%", "54%"],
                "rows": [
                    [cell("新客 vs 老客客单价（Welch t）"), num(f"{tt['t']:.2f}"), cell(f"p={tt['p_value_approx']}，d={tt['cohens_d']}；无显著差异")],
                    [cell("渠道 × 退货（卡方）"), num(f"{ch['chi2_statistic']:.1f}"), cell(f"p<0.001，V={ch['cramers_v']}；抖音退货率更高")],
                ],
            },
            "reading": [
                txt("折扣：", f"新客客单价 {tt['mean_a']:.1f} 元 vs 老客 {tt['mean_b']:.1f} 元，差 {tt['diff']:.2f} 元、p={tt['p_value_approx']}——首单折扣没有把客单拉低到显著程度。"),
                txt("退货：", "渠道与退货显著相关（χ²=80.1），抖音退货率最高；治理要按渠道做，不是按新老客做。"),
                txt("结论：", "首单折扣不是「养出低质用户」的元凶；真正要管的是渠道退货与获客成本。"),
            ],
            "boundary": {"text": "新客定义是「首次下单」，不是「领券用户」；折扣力度未单独建模。"},
        },
        {
            "index": 5,
            "title": "内容：3 个平台、16 万粉，只能算 partial",
            "question": "内容侧的数据够不够发日报？哪个平台贡献最大？",
            "table": {
                "caption": "自媒体看板与状态",
                "columns": [{"text": "指标"}, {"text": "值", "num": True}, {"text": "说明"}],
                "col_widths": ["30%", "18%", "52%"],
                "rows": [
                    [cell("粉丝总量"), num(f"{sm['total_fans']:,.0f}"), cell(f"{sm['platform_count']} 个平台")],
                    [cell("新增粉丝"), num(f"{sm['total_new_fans']:,.0f}"), cell("当日增量")],
                    [cell("当日收入"), num(f"{sm['total_revenue']:,.0f}", " 元"), cell("三平台快照")],
                    [cell("平台集中度 HHI"), num(f"{sm['hhi']}"), cell(f"{sm['hhi_grade']}；抖音占 {sm['by_platform'][1]['fans']/sm['total_fans']*100:.0f}%")],
                    [cell("看板状态"), num(sm["status"]), cell("缺 2 个平台，不能当 ready 日报")],
                ],
            },
            "reading": [
                txt("集中：", f"抖音 {sm['by_platform'][1]['fans']:,.0f} 粉占 {sm['by_platform'][1]['fans']/sm['total_fans']*100:.0f}%，HHI {sm['hhi']} 判「{sm['hhi_grade']}」——单平台依赖明显。"),
                txt("状态：", "normalize 只拿到 3 个平台（小红书/抖音/知乎），dashboard 判 partial；缺 B站/公众号，日报不能发。"),
                txt("SaaS 对照：", f"顺手跑了一次订阅模型：MRR 50 万、1,200 活跃、4% 月流失 → LTV {saas['ltv']:,.0f} 元、ARPU {saas['arpu']:,.0f} 元，用于和一次性电商模型对比。"),
            ],
            "boundary": {"text": "内容是快照数据，不做趋势；HHI 只反映粉丝分布，不代表收入集中度。"},
        },
        appendix("A1", "记录层：漏斗、cohort、RFM、分群、看板", [
            ("explore funnel", "funnel.csv", f"{len(fn['stages'])} 级，整体 {fn['stages'][-1]['conversion_overall']*100:.1f}%"),
            ("explore cohort", "orders.csv", f"{len(co['matrix'])} 个 cohort"),
            ("explore rfm", "orders.csv", f"{rfm['user_count']} 用户；Top combos {top_rfm[:3]}"),
            ("explore segment", "customer_features.csv", f"k={seg['k']}，silhouette {seg['silhouette']}"),
            ("explore metrics", "orders.csv", f"GMV {mt['gmv']:.0f}，AOV {mt['aov']}，复购订单占比 {mt['repeat_purchase_share']}"),
            ("explore saas", "标量", f"LTV {saas['ltv']}，ARPU {saas['arpu']}"),
            ("selfmedia normalize/dashboard/report", "selfmedia_raw.json", f"{sm['platform_count']} 平台，状态 {sm['status']}"),
        ], "完整输出见 results/funnel.json、cohort.json、rfm.json、segment.json、selfmedia_*.json。"),
        fidelity_section(8, {
            "rows": [("技能调用", "12", "P6：funnel/cohort/rfm/segment/metrics/time_series/ttest/chi2/saas/selfmedia×3"),
                     ("用户", "5,345", "订单 20,000；cohort 9 个月"),
                     ("真实 / 模拟", "全模拟", "seed=42；留存与分群结构按真实电商节奏设定"),
                     ("看板状态", sm["status"], "3/5 平台，缺 2 个")],
            "how": "留存 = 当月活跃用户 ÷ cohort 规模；RFM 按 R/F/M 四分位打分；HHI = Σ份额²。",
            "boundary": "模拟用户行为不能替代真实留存；结论只演示方法，不承诺复购率。",
        }),
    ]

    return {
        "doc_type": "命题 6 · 用户留存与内容（R06 数据分析能力演练）",
        "theme": "sticker",
        "title_lines": ["首单折扣客值不值得投？", "漏斗、留存、分群与自媒体看板"],
        "title_highlight": "值不值得投？",
        "standfirst": "用户侧的问题从来不是「留存多少」，而是「哪一段漏水、哪群人不该再花钱」。这篇把漏斗、cohort、RFM、K-means 和内容看板串成一条链路。",
        "meta": ["读者：增长 / 用户运营 / 内容", "数据：2 万单 + 5,345 用户 + 3 平台快照（模拟）",
                 "口径：订单级；cohort 按月；RFM 四分位", "技能：explore / ttest / chi2 / selfmedia"],
        "metric_strip": [
            kpi("整体转化", f"{fn['stages'][-1]['conversion_overall']*100:.1f}%", "曝光→支付", "watch"),
            kpi("次月留存", "33%", "cohort 第 1 月", "healthy"),
            kpi("复购订单占比", f"{mt['repeat_purchase_share']*100:.1f}%", "第 2 单及以后 ÷ 总订单", "accent"),
            kpi("核心客（RFM≥444）", f"{champions}", f"占 {champions/len(segs)*100:.1f}%", "accent"),
            kpi("内容看板", sm["status"], "3/5 平台，不能发日报", "critical"),
        ],
        "summary": [
            {"label": "结论：", "text": f"漏斗整体 {fn['stages'][-1]['conversion_overall']*100:.1f}%，瓶颈在曝光→点击（76% 流失）；留存首月后稳定 33%，问题不在留存，在获客。"},
            {"label": "人群：", "text": f"0.56% 的鲸鱼用户人均 {seg['clusters'][0]['profile']['orders']['mean']:.0f} 单；{seg['clusters'][3]['size_pct']}% 是待唤醒群；预算应按群分层，不按全量发券。"},
            {"label": "内容：", "text": f"3 个平台 16 万粉，抖音占 {sm['by_platform'][1]['fans']/sm['total_fans']*100:.0f}%，HHI {sm['hhi']}；缺平台导致看板 partial，日报不能发。"},
        ],
        "sections": sections,
        "notes": {"summary": "模拟用户与看板口径",
                  "items": [{"label": "模拟：", "text": "订单/用户/内容快照均按 seed=42 生成；留存与 RFM 分布按真实电商节奏设定，不承诺复购率。"},
                            {"label": "复购口径：", "text": "repeat_purchase_share =（订单数 − 独立客户数）÷ 订单数，是「第 2 单及以后的订单占比」，不是复购用户占比，也不是留存率。"},
                            {"label": "看板：", "text": "selfmedia 的快照不求和、增长按时段求和；缺平台判 partial，不能当 ready 发日报。"}],
                  "tail": "RFM 与 k-means 是分群工具，不是因果；分层后的增量仍需实验验证（见 P4）。"},
        "footer": footer("P6 用户留存与内容"),
    }


DEFS = [("P1", "01_数据底座体检", p1), ("P2", "02_增长量价拆解", p2), ("P3", "03_定价与门槛", p3),
        ("P4", "04_主图AB实验", p4), ("P5", "05_预算迁移因果", p5), ("P6", "06_用户留存与内容", p6)]


def main() -> int:
    index_items = []
    for key, name, fn in DEFS:
        contract = fn()
        errs = report_renderer.validate_contract(contract)
        lay = layout_errors(contract, require_appendix=True)
        if errs or lay:
            print(f"[FAIL] {key} contract={errs} layout={lay}")
            return 2
        html = report_renderer.render(contract)
        out = OUT / f"{name}.html"
        out.write_text(html, encoding="utf-8")
        (OUT / f"{name}.contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=1), encoding="utf-8")
        index_items.append({"key": key, "name": name, "title": contract["title_lines"][0],
                            "sub": contract["title_lines"][1], "doc_type": contract["doc_type"],
                            "kpis": contract["metric_strip"]})
        print(f"[OK] {key} {out.name} {out.stat().st_size/1024:.0f} KB")

    (OUT / "_index.json").write_text(json.dumps(index_items, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
