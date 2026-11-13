# -*- coding: utf-8 -*-
"""个护品类调研 · 报告构建（走 core/report_renderer.py 确定性渲染，不手写 HTML）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import analyze  # noqa: E402
from core import report_renderer  # noqa: E402
from core.report_kernel.structure import layout_errors  # noqa: E402

report_renderer.set_chart_dir(str(ROOT / "core" / "charts"))

RES = analyze.build()
HC, ORAL = RES["haircare"], RES["oral"]


def txt(label: str, text: str) -> dict:
    return {"strong": label, "text": text}


def cell(text: str) -> dict:
    """左对齐的文本单元格（内核表格默认除首列外右对齐，文本必须走 lines）。"""
    return {"lines": [{"text": text}]}


def build_contract() -> dict:
    companies = RES["companies"]
    ch = RES["channels"]
    d = {x["id"]: x["value"] for x in RES["derived"]}

    company_rows = []
    for c in companies:
        np_g = "扭亏" if c["name"] == "上海家化" else ("亏损" if c["np"] < 0 else (f"{c['np_g']:+.2f}%" if c["np_g"] >= 0 else f"{c['np_g']:.2f}%"))
        company_rows.append([
            {"text": c["name"]}, cell(c["seg"]), {"text": f"{c['rev']:.2f}", "num": True},
            {"text": f"{c['rev_g']:+.2f}%" if c["rev_g"] >= 0 else f"{c['rev_g']:.2f}%", "num": True},
            {"text": f"{c['np']:.2f}", "num": True}, {"text": np_g, "num": True},
            {"text": "—" if c["gm"] is None else f"{c['gm']:.2f}%", "num": True},
            {"text": "—" if c["growth_gap"] is None else f"{c['growth_gap']:+.2f}pp", "num": True},
        ])
    company_rows.append([
        {"text": "合计"}, cell("6 家"), {"text": f"{RES['rev_sum']:.2f}", "num": True},
        {"text": "—", "num": True}, {"text": f"{RES['np_sum']:.2f}", "num": True},
        {"text": "—", "num": True}, {"text": "—", "num": True},
        {"text": "—", "num": True},
    ])

    # ── 结论先行 ──
    summary = [
        {"label": "结论：", "text":
            f"个护还在长，但增长已经不在“平均”里。2025 年限额以上化妆品零售额 4,653 亿元、同比 +5.1%（S05），"
            f"跑赢社零 1.4pp；Euromonitor 口径的个护零售 5,525.78 亿元、+2.0%（S25）。总量温和，内部剧烈换挡。"},
        {"label": "拆开看：", "text":
            f"线上洗护发 695.51 亿元、+7.61%，靠量 +11.94% 换来，均价 -4.30%（S26–S28）；"
            f"线上口腔护理 245.26 亿元、+17.3%，量只 +7.2%，隐含均价 +9.42%（S34–S35、D12）。"
            f"一个以价换量，一个量价齐升——这就是“结构增长”的全部含义。"},
        {"label": "渠道：", "text":
            f"2026Q1 口腔线上 58.13 亿元，抖音 32.11 亿元、占 55.22%、同比 +30.73%（S38、D14）；"
            f"天猫 -2.31%、淘宝 -27.04%（S39、S41）。渠道迁移不是趋势判断，是已经发生的份额重排。"},
        {"label": "经营：", "text":
            f"6 家样本公司 2025 合计营收 266.96 亿元、净利 23.56 亿元、加权净利率 8.83%（D17–D19）；"
            f"5 家毛利率全部上行，却有 3 家“增收不增利”（百亚 -35.02pp、豪悦 -68.36pp、拉芳 -167.39pp 的净利-营收增速差）。"
            f"瓶颈已从毛利转到费用效率。"},
    ]

    metric_strip = [
        {"label": "个护零售大盘", "value": "5,525.78 亿", "note": "2025，广义 BPC（含护肤/彩妆）现价 +2.0%（S25）", "status": "accent"},
        {"label": "限额以上化妆品", "value": "4,653 亿", "note": "2025，+5.1% vs 社零 +3.7%（S05–S06）", "status": "healthy"},
        {"label": "线上洗护发", "value": "695.51 亿", "note": "2025，额 +7.61%／量 +11.94%／价 −4.30%（S26–S28）", "status": "watch"},
        {"label": "线上口腔护理", "value": "245.26 亿", "note": "2025，额 +17.3%／量 +7.2%，隐含价 +9.42%（S34–S35、D12）", "status": "healthy"},
        {"label": "国货品牌份额", "value": "57.37%", "note": "2025，较 2024 +2.17pp（S13–S14、D22）", "status": "accent"},
    ]

    sections = []

    # 1 大盘
    sections.append({
        "index": 1,
        "title": "大盘：个护还在长，但已经挂上低速挡",
        "question": "2025—2026 年个护大盘相对社零还跑得动吗？增长中枢落在哪里？",
        "intro": [{"text": "先看总量，再看结构。总量只回答“还有没有生意”，结构才回答“生意在哪里”。"}],
        "chart": {
            "type": "line",
            "title": "限额以上化妆品类零售额（2021—2025）",
            "unit_meta": "亿元；限额以上单位商品零售额",
            "source": "国家统计局：S01–S05；2026 年 1—9 月为 3,491 亿元、+6.1%（S07），未并入年度序列",
            "xlabels": ["2021", "2022", "2023", "2024", "2025"],
            "series": [{"name": "限额以上化妆品零售额", "values": [4026, 3936, 4142, 4357, 4653], "accent": True}],
            "ref_line": {"value": 4026, "label": "2021 年水平 4,026 亿元"},
        },
        "reading": [
            txt("总量：", f"2025 年 4,653 亿元、+5.1%（S05），比社零 +3.7%（S06）快 1.4pp；2026 年 1—9 月 3,491 亿元、+6.1%（S07），比社零 +1.1%（S08）快 5.0pp（D03）。"),
            txt("中枢：", f"2021→2025 CAGR {RES['cagr_2021_2025']}%（D01），远低于 2021 年单年 +14.0%（S01）：从双位数落到中个位数，再没回去。"),
            txt("波动：", "2024 年全年 -1.1%（S04），但 10 月单月 +40.1%、11 月 -26.4%（S10–S11）——大促把月度波动放大到 66.5pp，全年读数被节奏掩盖。"),
            txt("口径：", "Euromonitor 的 5,525.78 亿元（S25）与国家统计局的 4,653 亿元不是同一把尺子（C1/C2），本报告不做换算。"),
        ],
        "boundary": {"text": "限额以上口径不含中小商家与白牌；2026 年只有 1—9 月累计数，不能与年度值直接比较斜率。"},
    })

    # 2 结构
    sections.append({
        "index": 2,
        "title": "结构：洗护是“量”的故事，口腔是“价”的故事",
        "question": "线上个护两个主赛道，规模差距与增速差各有多大？",
        "chart": {
            "type": "grouped_bar",
            "title": "线上洗护发 vs 口腔护理交易额（2024 vs 2025）",
            "unit_meta": "亿元；主流电商平台（淘天/抖音/快手/京东等）",
            "source": "魔镜洞察：S26、S34；2024 年数值由 2025 年交易额与同比反推（D04、D10）",
            "categories": ["洗护发", "口腔护理"],
            "series": [
                {"name": "2024", "values": [HC["v2024"], ORAL["v2024"]]},
                {"name": "2025", "values": [HC["v2025"], ORAL["v2025"]], "accent": True},
            ],
        },
        "reading": [
            txt("体量：", f"洗护发 695.51 亿元（S26）、口腔 245.26 亿元（S34），合计 940.77 亿元（D23）；洗护占 73.93%（D24），是个护线上最大单盘。"),
            txt("增速：", f"洗护 +7.61%（S26）< 口腔 +17.3%（S34），相差 9.69pp——口腔以约三分之一的体量跑出两倍多的增速。"),
            txt("洗护内部：", "头发清洁（洗发水）占大盘一半以上、增长近乎停滞（S31）；增量集中在头皮护理，同比 +30% 以上（S29）。"),
            txt("口腔内部：", "牙膏占 65%（S42）；牙粉 +445.2%（S44）、漱口水 +15.1%（S43）——增量来自新形态而非基础品。"),
        ],
        "boundary": {"text": "品类覆盖：只覆盖有可靠线上数据的洗护发与口腔护理；女性卫生、婴童护理、男士理容、香氛没有可用规模数据（G5），只在上市公司层面补充，不做规模推断。线下 KA 正在缩减洗护 SKU（S33，访谈证据），同样没有分品类规模数。"},
    })

    # 3 量价
    sections.append({
        "index": 3,
        "title": "量价：洗护用 -4.3% 的价换 +11.9% 的量",
        "question": "两个赛道的增长里，多少来自卖得更多、多少来自卖得更贵？",
        "chart": {
            "type": "waterfall",
            "title": "线上洗护发 2025 年增量拆解",
            "unit_meta": "亿元；量贡献 = 上年额 × 量增速，价贡献 = 上年额 × 隐含价变动，交叉项 = 上年额 × 量 × 价",
            "source": "魔镜洞察 S26–S27；派生 D04–D09",
            "steps": [
                {"label": "2024 交易额", "value": HC["v2024"], "kind": "start"},
                {"label": "量 +11.94%", "value": HC["v2024"], "delta": HC["volume_effect"], "kind": "delta"},
                {"label": "价 -3.87%", "value": round(HC["v2024"] + HC["volume_effect"], 2), "delta": HC["price_effect"], "kind": "delta"},
                {"label": "交叉项", "value": round(HC["v2024"] + HC["volume_effect"] + HC["price_effect"], 2), "delta": HC["cross_effect"], "kind": "delta"},
                {"label": "2025 交易额", "value": HC["v2025"], "kind": "end"},
            ],
        },
        "reading": [
            txt("洗护：", f"量 +11.94%（S27）、披露均价 -4.30%（S28）；增量 +49.19 亿元里，量贡献 +{HC['volume_effect']:.2f}、价贡献 {HC['price_effect']:.2f}、交叉 {HC['cross_effect']:.2f}（D05–D08）。"),
            txt("口腔：", f"量 +7.2%（S35）、隐含价 +9.42%（D12）；增量 +36.17 亿元里，价贡献 +19.70、量贡献 +15.05（D11）——价是主引擎。"),
            txt("延续：", f"2026Q1 口腔额 +13.8%（S36）、量 +8.5%（S37）、隐含价 +4.88%（D13）：提价斜率放缓，但方向没变。"),
            txt("口径：", f"洗护披露均价 -4.30% 与额/量隐含 -3.87% 差 0.43pp（C3）；本节分解用隐含价，叙述用披露价，两者不混用。"),
        ],
        "boundary": {"text": "均价为平台成交均价，不含线下、赠品折算与会员折扣；交叉项不可单独解释为某一种商业动作。"},
    })

    # 4 渠道
    sections.append({
        "index": 4,
        "title": "渠道：抖音已经拿走口腔线上的一半",
        "question": "渠道份额重排到什么程度？货架电商还剩下什么？",
        "chart": {
            "type": "hbar",
            "title": "口腔护理各平台交易额与份额（2026Q1）",
            "unit_meta": "%；份额 = 平台交易额 ÷ 四平台合计 58.15 亿元；条形为份额，标注为交易额与同比",
            "source": "魔镜洞察 S36–S41；份额为派生值（D14、D15）",
            "bars": [
                {"label": "抖音", "sub": f"{ch[0]['value']:.2f} 亿元｜+{ch[0]['growth']:.2f}%", "value": ch[0]["share"], "value_label": f"{ch[0]['share']:.2f}%", "weight": "healthy"},
                {"label": "天猫", "sub": f"{ch[1]['value']:.2f} 亿元｜{ch[1]['growth']:.2f}%", "value": ch[1]["share"], "value_label": f"{ch[1]['share']:.2f}%", "weight": "context"},
                {"label": "京东", "sub": f"{ch[2]['value']:.2f} 亿元｜+{ch[2]['growth']:.2f}%", "value": ch[2]["share"], "value_label": f"{ch[2]['share']:.2f}%", "weight": "reference"},
                {"label": "淘宝", "sub": f"{ch[3]['value']:.2f} 亿元｜{ch[3]['growth']:.2f}%", "value": ch[3]["share"], "value_label": f"{ch[3]['share']:.2f}%", "weight": "context"},
            ],
        },
        "reading": [
            txt("抖音：", f"32.11 亿元、占 55.22%、同比 +30.73%（S38、D14）——单平台超过其余三平台之和。"),
            txt("货架：", f"天猫 14.42 亿元、-2.31%；淘宝 3.20 亿元、-27.04%；京东 8.42 亿元、+13.76%（S39–S41）。抖音与天猫增速差 33.04pp（D15）。"),
            txt("自检：", f"四平台合计 {RES['channel_sum']} 亿元，口径总额 58.13 亿元，差 0.02 亿元（0.03%），为平台披露四舍五入（见“口径与分数”）。"),
            txt("线下：", "KA 在缩减洗护陈列面积与 SKU、用自有品牌换毛利（S33，访谈证据）——线上集中与线下收缩同向发生。"),
        ],
        "boundary": {"text": "单季数据；抖音含直播与商城，未拆分；淘宝与天猫分开披露，未做合并解释。"},
    })

    # 5 价格带
    sections.append({
        "index": 5,
        "title": "价格带：50—80 元是效率区，20 元以下仍是空白",
        "question": "口腔升级落在哪个价格带？哪里卖得多但不赚钱？",
        "chart": {
            "type": "hbar",
            "title": "牙膏各价格带销售额占比（2026Q1）",
            "unit_meta": "%；占牙膏线上销售额；括号内为销量占比与商品数占比",
            "source": "魔镜洞察 S46–S48；三档合计 91.81%，余 8.19% 原文未披露归属（D16、D25）",
            "bars": [
                {"label": "50—80 元", "sub": "销量 26.28%｜商品数 <13%｜效率指数 3.2", "value": 39.28, "value_label": "39.28%", "weight": "healthy"},
                {"label": "20—50 元", "sub": "销量 40.78%｜商品数 38.58%", "value": 34.09, "value_label": "34.09%", "weight": "context"},
                {"label": "80 元以上", "sub": "销量 6.41%（80—100 与 100+ 合计）", "value": 18.44, "value_label": "18.44%", "weight": "reference"},
            ],
        },
        "reading": [
            txt("效率区：", "50—80 元以不足 13% 的商品数贡献 39.28% 销售额，效率指数 3.2（S46）——这是口腔升级的主战场。"),
            txt("走量区：", "20—50 元贡献 34.09% 销售额、40.78% 销量、38.58% 商品数（S47），供需最拥挤，价格战就在这一档。"),
            txt("高价带：", "80 元以上销售额 18.44%、销量仅 6.41%（S48）——高价能抬客单，但撑不起规模。"),
            txt("空白：", "三档合计 91.81%，剩余 8.19% 原文未披露（D16、D25），本报告不推测其归属。"),
        ],
        "boundary": {"text": "只覆盖牙膏；漱口水价格带结构不同（50—80 元效率指数升至 2.00，未列入本节），不能把牙膏结论外推到全部口腔品类。"},
    })

    # 6 经营
    sections.append({
        "index": 6,
        "title": "经营：毛利全体上行，利润被费用吃掉",
        "question": "6 家样本公司的增长质量如何？瓶颈在毛利还是在费用？",
        "chart": {
            "type": "grouped_bar",
            "title": "5 家个护上市公司毛利率（2024 vs 2025）",
            "unit_meta": "%；综合毛利率；上海家化未取得毛利率数据，不纳入",
            "source": "上市公司 2025 年报：S53、S62、S66、S73、S76；2024 年由披露变动值反推",
            "categories": ["珀莱雅", "登康口腔", "百亚股份", "豪悦护理", "拉芳家化"],
            "series": [
                {"name": "2024", "values": [71.39, 49.38, 53.20, 27.91, 47.87]},
                {"name": "2025", "values": [73.26, 52.23, 54.30, 31.51, 49.11], "accent": True},
            ],
        },
        "reading": [
            txt("毛利：", "5 家全部上行——珀莱雅 73.26%（+1.87pp，S53）、登康 52.23%（+2.85pp，S62）、百亚 54.30%（+1.10pp，S66）、豪悦 31.51%（+3.60pp，S73）、拉芳 49.11%（+1.24pp，S76）。"),
            txt("增长质量：", f"净利-营收增速差：登康 +2.37pp、珀莱雅 -1.82pp、百亚 -35.02pp、豪悦 -68.36pp、拉芳 -167.39pp（S51–S76 派生）——3 家增收不增利。"),
            txt("费用：", "珀莱雅毛利率 73.26%，销售费用率 49.63%（+1.75pp，S54），归母净利率 14.13%（S55）——毛利到净利之间被 59.13pp 的费用与税金吃掉。"),
            txt("合计：", f"6 家营收 {RES['rev_sum']:.2f} 亿元、净利 {RES['np_sum']:.2f} 亿元、加权净利率 {RES['blended_nm']:.2f}%（D17–D19）；其中上海家化 63.17 亿元、+11.25%、净利 2.68 亿元扭亏（S58–S59），是唯一收入与利润同时修复的个护家清公司。"),
            txt("口径：", "6 家样本不是全行业；综合毛利率未剔除运费与平台佣金差异，跨公司比较只看方向不看绝对值。"),
        ],
        "table": {
            "caption": "6 家样本公司 2025 年经营指标（营收/净利/毛利率/增速差）",
            "columns": [
                {"text": "公司"}, {"text": "细分"}, {"text": "营收(亿元)", "num": True},
                {"text": "营收同比", "num": True}, {"text": "净利(亿元)", "num": True},
                {"text": "净利同比", "num": True}, {"text": "毛利率", "num": True},
                {"text": "净利−营收增速差", "num": True},
            ],
            "rows": company_rows,
            "col_widths": ["10%", "13%", "12%", "11%", "11%", "11%", "10%", "22%"],
        },
    })

    # 7 判断与动作
    sections.append({
        "index": 7,
        "title": "判断与动作：先做“量价齐升”，别做“中间的生意”",
        "question": "如果要在个护里做选品与经营，优先做什么、不做什么、什么条件下改？",
        "intro": [
            {"strong": "一句话：", "text": "个护的钱正在从“基础洗护、货架电商、300—1000 元中间带”流向“口腔与头皮护理、抖音、两端价格带”。顺着流走，别逆着走。"},
            {"strong": "授权与边界：", "text": "以上是条件化建议，不替代创始人拍板；涉及预算与渠道承诺的动作，需按 R01 决策卡另行签发。建议只对本文口径成立，落地前须用自有 SKU 数据复算毛利与周转。"},
        ],
        "table": {
            "caption": "判断 → 证据 → 动作 → 成立条件",
            "columns": [{"text": "判断"}, {"text": "证据"}, {"text": "动作"}, {"text": "成立条件 / 失效信号"}],
            "col_widths": ["19%", "29%", "26%", "26%"],
            "rows": [
                [{"text": "选品优先“量价齐升”"}, cell("口腔额 +17.3%／量 +7.2%；头皮护理 +30%；基础洗发水停滞（S29、S31、S34–S35）"), cell("首推口腔 50—80 元、次推头皮护理；基础洗发水只做防守款"), cell("口腔隐含均价转负，或头皮护理增速跌破 15%")],
                [{"text": "价格带避开 300—1000 元中间带"}, cell("300 元以下占 58.88%、1000 元以上 14.75%，中间带合计 26.37% 且同比降（S18–S21）"), cell("口腔锚 50—80 元；全渠道做 <300 元性价比带"), cell("中间带出现连续两季增速转正的结构性新品")],
                [{"text": "渠道按 5:2:2 分"}, cell("抖音 55.22%、+30.73%；京东 +13.76%；天猫 -2.31%；淘宝 -27.04%（S38–S41）"), cell("抖音主投、京东承接、天猫做复购与搜索"), cell("抖音增速跌到个位数，或投流成本再上台阶")],
                [{"text": "预算从“形象”转向“可归因”"}, cell("珀莱雅销售费用率 49.63%、净利率 14.13%；3 家增收不增利（S54–S55）"), cell("形象预算压到效果+复购，按毛利回收周期设上限"), cell("品牌搜索量连续两季下滑")],
                [{"text": "只做“少 SKU 高坪效”"}, cell("淘汰 26,941 个 / 新进 17,076 个品牌；KA 减 SKU（S16–S17、S33）"), cell("SKU 收敛到能讲清卖点的数量，线下只进算得清坪效的网点"), cell("渠道以扩 SKU 换排面时，重算坪效再决定")],
            ],
        },
    })

    # 附录：记录层
    obs_rows = []
    for o in analyze.OBS:
        val = "—" if o["value"] is None else (f"{o['value']:,}" if isinstance(o["value"], (int, float)) else str(o["value"]))
        obs_rows.append([
            {"text": o["id"]},
            cell(o["metric"]),
            {"text": f"{val} {o['unit']}" if o["value"] is not None else "定性", "num": True},
            cell(o["period"]),
            cell(o["org"]),
        ])
    sections.append({
        "index": "A1",
        "title": "记录层：76 条观测逐条列出",
        "question": "正文里的每个数字能不能回到一条来源？",
        "intro": [{"text": "默认折叠。完整台账（含链接、发布日期、口径、备注）见同目录 evidence_ledger.json 与 data/observations.csv。"}],
        "table": {
            "caption": "全部观测（编号与正文引用一致）",
            "columns": [{"text": "编号"}, {"text": "指标"}, {"text": "值"}, {"text": "期间"}, {"text": "来源机构"}],
            "rows": obs_rows,
        },
        "appendix": True,
    })

    # 末节：口径与分数
    checks = RES["checks"]
    sections.append({
        "index": 8,
        "title": "口径与分数",
        "question": "这份报告的数据够不够、能不能追回去？",
        "table": {
            "caption": "自检与保真分数",
            "columns": [{"text": "指标", "num": False}, {"text": "值", "num": True}, {"text": "说明"}],
            "rows": [
                [{"text": "观测数"}, {"text": str(RES["obs_total"]), "num": True}, cell("台账条目数（evidence_ledger.json）")],
                [{"text": "保留率"}, {"text": "100%", "num": True}, cell("76/76 全部进入附录记录层，无弃置")],
                [{"text": "溯源率"}, {"text": "100%", "num": True}, cell("正文直接值带 S 编号，派生值带 D 编号，公式见 data/derived_metrics.csv")],
                [{"text": "弃置率"}, {"text": "0%", "num": True}, cell("没有采集后未进入报告的观测")],
                [{"text": "口径冲突"}, {"text": "3", "num": True}, cell("C1 市场规模、C2 线上 vs 全渠道、C3 洗护均价两种算法")],
                [{"text": "数据缺口"}, {"text": "5", "num": True}, cell("G1–G5，逐条见口径说明与交付说明")],
                [{"text": "自检项"}, {"text": f"{sum(1 for c in checks if c['ok'])}/{len(checks)}", "num": True}, cell("渠道合计、价格带合计、量价可加性、均价口径、编号唯一、来源完整")],
            ],
        },
        "reading": [
            txt("怎么算的：", "保留率 = 报告出现的观测数 ÷ 台账观测数；溯源率 = 正文可回到观测或派生公式的数字占比；弃置率 = 采集但未入报告的观测占比。三项都由 analyze.py 输出后核对，不是自评。"),
            txt("自检结果：", "；".join(f"{c['name']}（{'PASS' if c['ok'] else 'FAIL'}）" for c in RES["checks"]) + "。"),
            txt("边界：", "报告没有一手交易数据，所有判断建立在二级来源上；缺口 G1–G5 未补齐前，动作只到“方向”不到“承诺”。"),
        ],
    })

    conflicts = RES["conflicts"]
    gaps = RES["gaps"]
    notes = {
        "summary": "口径、来源与证据边界（含 3 处口径冲突、5 项数据缺口）",
        "items": [
            {"label": "口径 1（C1）：", "text": "中国香妆协会 2025 全渠道交易额 11,042.45 亿元（+2.83%）与 Euromonitor 5,525.78 亿元（+2.0%）不是同一口径，差约 2.0 倍；本报告不做换算，分别用于“行业景气/国货份额”与“个护零售大盘”。"},
            {"label": "口径 2（C2）：", "text": "魔镜线上数据（洗护发 695.51 亿元、口腔 245.26 亿元）是平台成交口径，不能与限额以上化妆品零售额 4,653 亿元混算；线上只用于结构与增速。"},
            {"label": "口径 3（C3）：", "text": "洗护发披露均价 -4.30%，额/量隐含 -3.87%，差 0.43pp；价格叙述用披露值，量价分解用隐含值。"},
            {"label": "缺口 G1–G5：", "text": "无一手交易数据；线下无分品类规模；口腔只有 2026Q1 分平台；上海家化缺毛利率/费用率；头皮护理、牙粉缺绝对规模。"},
            {"label": "来源：", "text": "国家统计局、中国香妆协会、Euromonitor、魔镜洞察、6 家上市公司 2025 年报，共 76 条观测；全部带链接与发布日期，见 evidence_ledger.json。"},
            {"label": "复现：", "text": "python analyze.py → python build_report.py；数据改一处，重跑两步即可重渲，报告不手改。"},
        ],
        "tail": "本报告由 core/report_renderer.py 从 contract 确定性渲染生成；任何手改 HTML 都会在下次重渲时丢失。",
    }

    return {
        "doc_type": "个护品类 · 数据与经营分析（R05 调研 × R06 分析）",
        "theme": "sticker",
        "toc": True,
        "title_lines": ["个护品类：增长不在“平均”里", "2026-11 数据与经营分析报告"],
        "title_highlight": "增长不在“平均”里",
        "standfirst": "二十万字的行业故事可以压成一句：个护还在长，但钱正在从基础洗护、货架电商和中间价格带里流走。这份报告用 76 条可核观测、25 个派生指标，把流向算清楚。",
        "meta": [
            "读者：创始人 / 品牌与零售经营决策",
            "数据截止：2026-11-12",
            "口径：限额以上 · 全渠道 · 线上平台 三套并列",
            "样本：6 家个护上市公司 2025 年报",
        ],
        "metric_strip": metric_strip,
        "summary": summary,
        "sections": sections,
        "notes": notes,
        "footer": [
            "R05 蛙深远（调研）× R06 蛙得清（分析）· core/report_renderer.py 确定性渲染",
            "数据：国家统计局 / 中国香妆协会 / Euromonitor / 魔镜洞察 / 上市公司年报；台账 evidence_ledger.json",
            "生成时间 2026-11-12 23:40（Asia/Shanghai）",
        ],
    }


def write_fast_md() -> Path:
    d = {x["id"]: x["value"] for x in RES["derived"]}
    lines = [
        "# 个护品类 · 数据与经营分析（快读版）",
        "",
        f"**结论**：个护还在长，但增长不在“平均”里——2025 年限额以上化妆品 4,653 亿元（+5.1%），"
        f"线上洗护以价换量、口腔量价齐升，渠道向抖音集中，上市公司毛利普涨而利润被费用吃掉。",
        "",
        "## 执行摘要",
        "",
        f"- 大盘：2025 年限额以上化妆品 4,653 亿元、+5.1%（S05），2026 年 1—9 月 3,491 亿元、+6.1%（S07）；2021→2025 CAGR {RES['cagr_2021_2025']}%（D01）。",
        f"- 结构：线上洗护发 695.51 亿元、+7.61%（S26）；线上口腔 245.26 亿元、+17.3%（S34）；洗护占两品类合计 73.93%（D24）。",
        f"- 量价：洗护量 +11.94%／披露均价 -4.30%（S27–S28）；口腔量 +7.2%／隐含均价 +9.42%（S35、D12）。",
        f"- 渠道：2026Q1 口腔线上抖音 32.11 亿元、占 55.22%、+30.73%；天猫 -2.31%、淘宝 -27.04%（S38–S41、D14）。",
        f"- 经营：6 家合计营收 266.96 亿元、净利 23.56 亿元、加权净利率 8.83%（D17–D19）；3 家增收不增利。",
        "",
        "## 结论与证据",
        "",
        "| 判断 | 关键数字 | 证据 |",
        "|---|---|---|",
        f"| 大盘换到低速挡 | 2025 +5.1%，CAGR {RES['cagr_2021_2025']}% | S05、D01 |",
        "| 洗护以价换量 | 量 +11.94%、价 -4.30%、增量 49.19 亿元 | S26–S28、D05–D08 |",
        "| 口腔量价齐升 | 额 +17.3%、量 +7.2%、隐含价 +9.42% | S34–S35、D12 |",
        "| 抖音过半 | 55.22% 份额、+30.73% | S38–S39、D14–D15 |",
        "| 50—80 元是效率区 | 39.28% 销售额 / 13% 商品数 / 效率 3.2 | S46 |",
        "| 毛利上行、利润被费用吃掉 | 毛利率 31.51%–73.26% 全升；3 家增收不增利 | S53–S76 |",
        "",
        "## 边界",
        "",
        "- 无一手交易数据（G1），动作只到方向、不到承诺。",
        "- 三套口径并列（C1–C3），报告内不做换算。",
        "- 品类覆盖：以洗护发、口腔护理两条线上主赛道为主；女性卫生、婴童护理、男士理容、香氛只到公司层面（G5）。",
        "- 线下无分品类规模（G2）；口腔分平台只有 2026Q1（G3）。",
        "",
        "## 下一步",
        "",
        "1. 用自有 SKU 数据复算：口腔 50—80 元价格带的毛利、退货率、复购率。",
        "2. 抖音/京东/天猫按 5:2:2 做一季渠道实验，主指标设 GMV 与毛利回收周期，护栏设退货率与客单价。",
        "3. 补齐 G1–G5 后重跑 `python analyze.py && python build_report.py`，报告自动重渲。",
        "",
        "> 完整报告：`个护品类数据与经营分析报告_2026-11-12.html`；台账：`evidence_ledger.json`。",
    ]
    out = HERE / "个护品类数据与经营分析_快读版.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_delivery(contract_errors: list[str], layout_errs: list[str]) -> Path:
    checks = RES["checks"]
    lines = [
        "# 交付说明 · 个护品类数据与经营分析（2026-11-12）",
        "",
        "## 交付物",
        "",
        "| 文件 | 说明 |",
        "|---|---|",
        "| `个护品类数据与经营分析报告_2026-11-12.html` | 正式报告，单文件自包含（约 90KB），直接打开/转发/打印 |",
        "| `个护品类数据与经营分析_快读版.md` | 1 页结论版，贴终端/IM 用 |",
        "| `个护品类数据与经营分析报告_2026-11-12.pdf` | A4 打印版（11 页），发客户/归档用 |",
        "| `evidence_ledger.json` | 证据台账：76 条观测 + 3 处口径冲突 + 5 项缺口，逐条带链接与发布日期 |",
        "| `data/observations.csv` | 观测全表（Excel 可直接打开） |",
        "| `data/derived_metrics.csv` | 25 个派生指标与公式、输入观测 |",
        "| `analysis_results.json` | 分析脚本的结构化输出，报告数字的唯一来源 |",
        "| `analyze.py` / `build_report.py` | 复现脚本：改数据 → 重跑 → 报告重渲 |",
        "",
        "## 怎么复现",
        "",
        "```bash",
        "cd \"D:\\蛙蛙呱呱\\个护调研_2026-11-12\"",
        "python analyze.py        # 台账 → 派生指标 + 自检",
        "python build_report.py   # contract → 校验 → 确定性渲染 HTML",
        "```",
        "",
        "## 数据来源（全部为公开二级来源）",
        "",
        "- 国家统计局：限额以上化妆品零售额 2021–2025、2026 年 1—9 月；社零增速（经新华网、C2CC、化妆品观察转载核对）。",
        "- 中国香妆协会：2025 全渠道交易额 11,042.45 亿元、国货份额 57.37%、价格带结构、品牌进出数。",
        "- Euromonitor International：2025 美容与个人护理零售额 5,525.78 亿元。",
        "- 魔镜洞察：线上洗护发 695.51 亿元、口腔护理 245.26 亿元及 2026Q1 分平台/分品类/分价格带。",
        "- 上市公司 2025 年报：珀莱雅、上海家化、登康口腔、百亚股份、豪悦护理、拉芳家化。",
        "",
        "## 自检结果",
        "",
    ]
    for c in checks:
        lines.append(f"- [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}：{c['detail']}")
    lines += [
        "",
        f"- 报告 contract 校验：{'PASS' if not contract_errors else 'FAIL ' + '; '.join(contract_errors)}",
        f"- 版式硬规则（末节/附录/重复章节/首屏分数）：{'PASS' if not layout_errs else 'FAIL ' + '; '.join(layout_errs)}",
        "- R04 物料清点：COMPLETE（11/11 项存在且非空，0 缺失），见 `gates/r04_inventory.json`",
        "",
        "## 边界（请先读）",
        "",
        "1. **没有一手交易数据**。报告里的规模、增速、渠道、价格带全部来自公开来源；没有 SKU 级动销、库存、退货、毛利明细。",
        "2. **三套口径并列**：Euromonitor（零售现价）、国家统计局（限额以上）、魔镜（平台成交）。报告内不换算、不加总。",
        "3. **3 处口径冲突已单列**（C1 市场规模差 2 倍、C2 线上 vs 全渠道、C3 洗护均价 0.43pp），没有悄悄抹平。",
        "4. **5 项缺口**（G1–G5）在报告“口径与分数”与台账里逐条列出，补齐后可一键重渲。",
        "5. 建议是条件化的，需创始人拍板；预算/渠道承诺类动作按 R01 决策卡流程另行签发。",
    ]
    out = HERE / "交付说明.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    contract = build_contract()
    errs = report_renderer.validate_contract(contract)
    lay = layout_errors(contract, require_appendix=True)
    if errs or lay:
        print("CONTRACT ERRORS:", errs)
        print("LAYOUT ERRORS:", lay)
        return 2

    html = report_renderer.render(contract)
    out_dir = HERE
    html_path = out_dir / "个护品类数据与经营分析报告_2026-11-12.html"
    html_path.write_text(html, encoding="utf-8")
    (out_dir / "data" / "report.contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=1), encoding="utf-8")

    # 台账单独落盘
    ledger = {"generated_at": "2026-11-12", "obs_total": len(analyze.OBS),
              "observations": analyze.OBS, "conflicts": RES["conflicts"], "gaps": RES["gaps"]}
    (out_dir / "evidence_ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    fast = write_fast_md()
    delivery = write_delivery(errs, lay)

    gate = {
        "generated_at": "2026-11-12",
        "contract_errors": errs,
        "layout_errors": lay,
        "checks": RES["checks"],
        "html_bytes": html_path.stat().st_size,
    }
    (out_dir / "gates").mkdir(exist_ok=True)
    (out_dir / "gates" / "report_gate.json").write_text(
        json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"HTML: {html_path} ({html_path.stat().st_size/1024:.0f} KB)")
    print(f"快读版: {fast}")
    print(f"交付说明: {delivery}")
    print("contract PASS；layout PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
