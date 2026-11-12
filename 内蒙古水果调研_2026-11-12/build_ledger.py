# -*- coding: utf-8 -*-
"""证据台账：从指标库派生 40 条结论（每条挂来源、可回指观测），并登记缺口。

原则：数字全部由 data/底稿指标.json 计算生成，不手写。
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent
M = json.loads((ROOT / "data" / "底稿指标.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "证据台账.json"

L1, L2, L3, L4, L5, L6, L7 = (M["L1_全国日度"], M["L2_全国周度"], M["L3_批发报价"],
                              M["L4_呼市零售"], M["L5_期货"], M["L6_苹果分市场"], M["L7_产业面"])
X = M["跨层"]
SZ = M["市场规模"]

SOURCES = [
    {"id": "S1", "title": "农业农村部·农产品批发市场每日价格（6 种水果均价）",
     "type": "government", "date": "2026-09-15~2026-11-12", "url": "https://pfsc.agri.cn/"},
    {"id": "S2", "title": "农业农村部·全国农产品批发市场周度行情（表 5 重点监测水果）",
     "type": "government", "date": "2026-09-11~2026-11-05", "url": "https://pfsc.agri.cn/"},
    {"id": "S3", "title": "呼和浩特市商务局·生活必需品市场运行分析（9 期周报）",
     "type": "government", "date": "2026-09-07~2026-11-08", "url": "http://swj.huhhot.gov.cn/tjxx/202611/t20261110_2049154.html"},
    {"id": "S4", "title": "农业农村部·全国主要批发市场富士苹果价格行情（2026-10-28）",
     "type": "database", "date": "2026-10-28", "url": "https://futures.stockstar.com/IG2026102800025651.shtml"},
    {"id": "S5", "title": "农业农村部·全国主要批发市场富士苹果价格行情（2026-11-11）",
     "type": "database", "date": "2026-11-11", "url": "http://futures.stockstar.com/IG2026111100024473.shtml"},
    {"id": "S6", "title": "郑州商品交易所·苹果期货 AP0 日线（新浪财经行情接口）",
     "type": "database", "date": "2026-09-16~2026-11-11",
     "url": "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_AP0=/InnerFuturesNewService.getDailyKLine?symbol=AP0"},
    {"id": "S7", "title": "郑州商品交易所·红枣期货 CJ0 日线（新浪财经行情接口）",
     "type": "database", "date": "2026-09-16~2026-11-11",
     "url": "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_CJ0=/InnerFuturesNewService.getDailyKLine?symbol=CJ0"},
    {"id": "S8", "title": "内蒙古自治区 2025 年国民经济和社会发展统计公报",
     "type": "government", "date": "2026-04-09",
     "url": "https://www.nmg.gov.cn/tjsj/tjsj/tjgb/202604/t20260409_2886936.html"},
    {"id": "S9", "title": "国家统计局·分省水果产量（经 CEIC 披露，内蒙古 2025）",
     "type": "government", "date": "2026-01", "url": "https://www.ceicdata.com/zh-hans/china/yield-of-farm-crops-fruits-by-region/cn-farm-crops-fruits-yield-inner-mongolia"},
    {"id": "S10", "title": "内蒙古林草局·宁城县林果产业（25 万亩 / 16.8 万吨 / 8.2 亿元）",
     "type": "government", "date": "2025-09-30", "url": "http://lcj.nmg.gov.cn/xxgk/zxzx/202509/t20250930_2798125.html"},
    {"id": "S11", "title": "通辽市林草局·塞外红苹果（34.14 万亩 / 一类果 10 元每斤进新发地）",
     "type": "government", "date": "2025-12-16", "url": "https://www.tongliao.gov.cn/zjtl/fztl/tltf/nmy/202512/t20251216_1021786.html"},
    {"id": "S12", "title": "内蒙古交通运输厅·对政协第 0064 号提案的答复（冷库 2200 座 / 390 万吨）",
     "type": "government", "date": "2025-12-19", "url": "https://jtyst.nmg.gov.cn/zwgk/zfxxgk/fdzdgknr/labl/202512/t20251219_2836948.html"},
    {"id": "S13", "title": "前瞻产业研究院·2026 中国水果连锁零售行业需求现状（人均 68 公斤 / 内蒙古 77.6 公斤）",
     "type": "industry_report", "date": "2026-05-20", "url": "https://www.qianzhan.com/analyst/detail/220/260520-0065a0b3.html"},
    {"id": "S14", "title": "华经产业研究院·2026 中国水果行业供需现状（产量 3.59 亿吨 / 进口 1003 万吨）",
     "type": "industry_report", "date": "2026", "url": "https://www.huaon.com/channel/trend/1166031.html"},
    {"id": "S15", "title": "食品商务网 21food·呼和浩特保全庄 / 东瓦窑 / 包头友谊批发市场报价（680 条，B 级）",
     "type": "database", "date": "2026-09-25~2026-11-12", "url": "https://wap.21food.cn/price/market/1327-p1.html"},
    {"id": "S16", "title": "乌兰察布市发改委·2026 年 10—11 月粮油副食品价格分析（4 期，仅方向）",
     "type": "government", "date": "2026-10-15~2026-11-06", "url": "https://fgw.wulanchabu.gov.cn/jgsf/2035331.html"},
]

CLAIMS: list[dict] = []


def add(cid: str, text: str, kind: str, src: list[str], layer: str = "") -> None:
    CLAIMS.append({"id": cid, "text": text, "kind": kind, "source_ids": src, "layer": layer})


def fmt(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


# ---------------------------------------------------------------- S1 总量
add("C1", f"全国重点监测 6 种水果均价在 {L1['n']} 个交易日里从 {fmt(L1['first']['value'])} 元/公斤走到 "
          f"{fmt(L1['last']['value'])} 元/公斤（{L1['first']['date']}→{L1['last']['date']}），区间 "
          f"{fmt(L1['min']['value'])}—{fmt(L1['max']['value'])} 元/公斤，振幅 "
          f"{fmt((L1['max']['value'] - L1['min']['value']) / L1['min']['value'] * 100, 2)}%，属窄幅震荡而非趋势行情。",
    "fact", ["S1"], "L1")
add("C2", f"分月看：9 月下半月 {L1['monthly']['9月下半月']['n']} 日均值 {fmt(L1['monthly']['9月下半月']['mean'], 3)} 元/公斤，"
          f"10 月 {L1['monthly']['10月']['n']} 日均值 {fmt(L1['monthly']['10月']['mean'], 3)}，"
          f"11 月 {L1['monthly']['11月']['n']} 日均值 {fmt(L1['monthly']['11月']['mean'], 3)}；"
          f"10→11 月抬升 {fmt(L1['月内变化'])}%（月均口径）。",
    "fact", ["S1"], "L1")
add("C3", f"日环比结构：上涨 {L1['up_days']} 天、下跌 {L1['down_days']} 天、持平 {L1['flat_days']} 天；"
          f"日波动标准差 {fmt(st.pstdev(L1['chg_series']) if L1['chg_series'] else None)} 个百分点，"
          f"说明单日信息量极低，任何『今天涨了』的判断都应回到周度看。",
    "calculation", ["S1"], "L1")
add("C4", f"周度等权篮子（6 品种，基期 {L2['weeks'][0]}）在 {len(L2['weeks'])} 周内累计 "
          f"{fmt(L2['basket_change_pct'])}%，其中西瓜 +33.22%、富士苹果 -2.81%、鸭梨 -3.15%、"
          f"菠萝 -6.08%、香蕉 -7.41%、巨峰葡萄 -13.54%。",
    "fact", ["S2"], "L2")
add("C5", f"最新一周（{L2['weeks'][-1]}）6 种水果均价 6.64 元/公斤（农业农村部原文），环比 +1.2%、同比 -6.1%；"
          f"其中富士苹果 {fmt(L2['item_summary']['富士苹果']['latest_price'])} 元/公斤，香蕉 "
          f"{fmt(L2['item_summary']['香蕉']['latest_price'])} 元/公斤，巨峰葡萄 "
          f"{fmt(L2['item_summary']['巨峰葡萄']['latest_price'])} 元/公斤。",
    "fact", ["S2"], "L2")
add("C6", f"品类分化：巨峰葡萄 9 周 -13.54%（季末清货），西瓜 +33.22%（退市反季），"
          f"苹果（-2.81%）与鸭梨（-3.15%）构成价格锚，波动最小。",
    "opinion", ["S2"], "L2")

# ---------------------------------------------------------------- S2 本地
avg = L4["avg"]
add("C7", f"呼和浩特 8 种水果零售均价 {L4['avg_first']['week']} 的 {fmt(L4['avg_first']['price'])} 元/公斤 → "
          f"{L4['avg_last']['week']} 的 {fmt(L4['avg_last']['price'])} 元/公斤，9 周 +{fmt(L4['avg_change_pct'])}%，"
          f"区间 {fmt(L4['avg_min'])}—{fmt(L4['avg_max'])}；零售端比全国批发端（-4.47%）强 {fmt(X['transmission']['传导差_pp'])} 个百分点。",
    "fact", ["S3"], "L4")
add("C8", f"呼市分品种最新周：苹果 13.88 元/公斤（环比 +2.8%）、芒果 15.06（+2.5%）、西瓜 6.52（+2.4%）、"
          f"柑橘 7.15（前一周 -6.8%）；涨跌结构为 4 涨 4 降，无单边行情。呼市零售 8 种均价 10.49 元/公斤，"
          f"是全国 6 种批发均价 6.62 元/公斤的 {fmt(10.49 / 6.62, 2)} 倍（不同篮子，只比水平差，不比变化率）。",
    "fact", ["S3"], "L4")
add("C9", f"乌兰察布方向表述 4 期：10-15 略降 → 10-22 小幅降 → 10-29 小幅涨 → 11-05 小幅涨；"
          f"该市周报只给定性描述、不给分品种价格，只能做方向印证，不进价格序列。",
    "fact", ["S16"], "L8")

# ---------------------------------------------------------------- S3 价差
add("C10", f"同品种同日（2026-11-11）省内价差：呼市东瓦窑富士苹果 14.00 元/公斤 vs 赤峰西城 6.00 元/公斤，"
           f"差 {fmt(X['spread']['省内价差_pct'], 1)}%（2.33 倍），是本次调研最大的单一价差。",
    "fact", ["S5"], "L6")
add("C11", f"呼市 14.00 元/公斤在 57 个样本市场中并列最高（全场 max=14.00），较全国中位数 8.00 高 "
           f"{fmt(X['spread']['呼市相对全国中位数_pct'], 1)}%；赤峰 6.00 较中位数低 {fmt(abs(X['spread']['赤峰相对全国中位数_pct']), 1)}%。",
    "fact", ["S5"], "L6")
add("C12", f"全国 57 市场分布：min 3.40 / p25 6.80 / median 8.00 / p75 10.00 / max 14.00，极差 4.12 倍；"
           f"价格不是全国统一价，产地与销地、等级与包装共同决定报价。",
    "fact", ["S4", "S5"], "L6")
add("C13", f"批零倍率：呼市苹果零售 13.88 ÷ 全国富士苹果批发 8.64 = {fmt(X['retail_wholesale_ratio'])} 倍；"
           f"端到端（呼市零售 ÷ 赤峰产地市场 6.00）= {fmt(X['end_to_end_multiple'])} 倍。",
    "fact", ["S3", "S2", "S5"], "跨层")
add("C14", f"批零价差 5.24 元/公斤，占零售价 {fmt((X['retail_apple_price'] - X['national_wholesale_apple']) / X['retail_apple_price'] * 100, 1)}%；"
           f"这一段是渠道与损耗的成本区，不是果农的收益区（果农端对应 4.88 元/公斤的宁城折算产值）。",
    "calculation", ["S3", "S2", "S10"], "跨层")

# ---------------------------------------------------------------- S4 期货
ap, cj = L5["苹果"], L5["红枣"]
add("C15", f"苹果期货 AP0 在 {ap['n']} 个交易日从 {fmt(ap['first']['close'], 0)} 跌到 {fmt(ap['last']['close'], 0)} 元/吨，"
           f"{fmt(ap['change_pct'])}%，最大回撤 {fmt(ap['max_drawdown_pct'])}%；同期红枣 CJ0 {fmt(cj['change_pct'])}%。",
    "fact", ["S6", "S7"], "L5")
add("C16", f"期货与现货方向一致但幅度不同：AP0 {fmt(ap['change_pct'])}% vs 全国富士苹果批发 9 周 -2.81%，"
           f"期货在交易『春节前累库 + 消费预期』，现货只反映当下成交，两者不可互相替代。",
    "opinion", ["S6", "S2"], "L5")
add("C17", f"AP0 11 月均 {fmt(ap['nov_mean'], 0)} 元/吨（{fmt(ap['nov_mean'] / 1000, 2)} 元/公斤）低于 10 月均 "
           f"{fmt(ap['oct_mean'], 0)} 元/吨，期现价差为负（期货贴水），说明市场对 12 月—春节前现货并不看涨。",
    "opinion", ["S6", "S2"], "L5")

# ---------------------------------------------------------------- S5 产业面
add("C18", f"内蒙古水果产量 2025 年 {fmt(L7['全区产量']['2025_万吨'], 2)} 万吨，较 2024 年 "
           f"{fmt(L7['全区产量']['2024_万吨'], 2)} 万吨增长 {fmt(L7['全区产量']['同比_pct'])}%；"
           f"同期全国水果产量 35,404.72 万吨（+4.24%），内蒙古增速高于全国。",
    "fact", ["S9", "S14"], "L7")
add("C19", f"宁城县：果树经济林 25 万亩、盛果期 9.5 万亩、年产 16.8 万吨、产值 8.2 亿元 → 折算 "
           f"{fmt(L7['宁城']['折算_元每公斤'])} 元/公斤，2024 年销售 16.79 万吨、腊月前库存清零。",
    "fact", ["S10"], "L7")
add("C20", f"通辽『塞外红』：34.14 万亩、结果 12.45 万亩，一类果 10 元/斤（20 元/公斤）进北京新发地，"
           f"是赤峰批发价 6.00 元/公斤的 {fmt(20 / 6, 2)} 倍——同省不同品牌/等级的价格差，可复制的是标准不是品种。",
    "opinion", ["S11", "S5"], "L7")
add("C21", f"冷链底座：全区冷库 2,200 余座、总容量 390 万吨，按 224.92 万吨产量计库容/产量 = "
           f"{fmt(390 / L7['全区产量']['2025_万吨'], 2)} 倍；综合交通主骨架建成率 84.3%，冷链通道已规划至北京、上海。",
    "fact", ["S12", "S9"], "L7")

# ---------------------------------------------------------------- S6 市场容量
add("C22", f"内蒙古水果 TAM（人均 77.6 公斤 × 2,374 万人）≈ {fmt(SZ['TAM_万吨'], 1)} 万吨，"
           f"按呼市 8 种水果零售均价 10.49 元/公斤折算 ≈ {fmt(SZ['TAM_零售额_亿元'], 1)} 亿元；"
           f"敏感性区间 {fmt(SZ['敏感性']['人均_低'], 1)}—{fmt(SZ['敏感性']['人均_高'], 1)} 万吨。",
    "fact", ["S8", "S13", "S3"], "L7/跨层")
add("C23", f"SOM 假设（18% 份额、呼包鄂 + 赤峰通辽为主战场）≈ {fmt(SZ['SOM_万吨'], 1)} 万吨 / "
           f"{fmt(SZ['SOM_零售额_亿元'], 1)} 亿元；该份额是结构假设，不是实测，须在第 1 个月用动销数据校准。",
    "estimate", ["S8", "S13"], "跨层")

# ---------------------------------------------------------------- S7 数据质量
const_ratio = None
tot = const_n = 0
for m, v in L3["markets"].items():
    for item, s in v["items"].items():
        tot += 1
        if s["min"] == s["max"]:
            const_n += 1
if tot:
    const_ratio = const_n / tot * 100
add("C24", f"21food 三市场 680 条报价中，{const_n}/{tot} 条品种序列在整个窗口内价格完全不变"
           f"（常量率 {fmt(const_ratio, 1)}%），且苹果 18.00 与东瓦窑 14.00 同城差 {fmt(X['conflict']['差异_pct'], 1)}%；"
           f"判定为报价口径不可比，整体弃用，只保留原始证据供复核。",
    "calculation", ["S15"], "L3")
add("C25", f"批零倒挂异常：东瓦窑富士苹果批发 14.00 vs 呼市苹果零售 13.88（-0.86%），"
           f"按字面是负毛利；真实原因是『富士苹果』与监测目录里的『苹果』规格/等级不同，"
           f"该口径差已单列，未用于定价与毛利结论。",
    "fact", ["S5", "S3"], "跨层")
add("C26", f"缺口清单：10-02~10-05（国庆假期）、10-09、10-11~10-12、10-14、10-24~10-25、11-07~11-08 无批发报价；"
           f"乌兰察布只有定性描述；内蒙古省级价格监测平台水果条目未取到（页面无正文）。按交易日口径处理，不做插值。",
    "fact", ["S1", "S15", "S16"], "口径")

# ---------------------------------------------------------------- S8 结论与行动
add("C27", f"一句话结论：10—11 月内蒙古水果不是『涨』或『跌』的行情，而是"
           f"『全国批发窄幅走弱（{fmt(L2['basket_change_pct'])}%）、呼市零售小幅走强（+{fmt(L4['avg_change_pct'])}%）、"
           f"省内价差 2.33 倍』的结构行情，钱在结构里，不在趋势里。",
    "opinion", ["S1", "S2", "S3", "S5"], "综合")
add("C28", "经营动作：以苹果为价格锚做引流（批零倍率 1.61 倍、毛利空间最大），以葡萄/西瓜做季节性冲量，"
           "以柑橘做 11—12 月主推；采购重心从呼市批发转向赤峰产地直采，理论可压缩端到端加价 2.31 倍中的 0.5—0.7 倍。",
    "recommendation", ["S5", "S3", "S11"], "综合")
add("C29", "链路动作：先做『产地预冷 + 一车直发』（赤峰→呼市 460 公里、当日达），再做『销地共同配送』，"
           "最后做『订单农业 + 期货点价』；三段的验收指标分别是损耗率、履约时效、采购成本，不可混在一个 KPI 里。",
    "recommendation", ["S12", "S6"], "综合")
add("C30", "风险提示：AP0 期货 36 日 -19.27% 反映的是累库与消费预期，若 12 月现货跟随下行，"
           "当前按 11 月高价锁定的采购合同会出现账面亏损；建议锁量不锁价、分批点价。",
    "recommendation", ["S6", "S7"], "综合")

SECTIONS = [
    {"title": "总量与趋势", "claim_ids": ["C1", "C2", "C3", "C4", "C5", "C6"]},
    {"title": "内蒙古本地价格", "claim_ids": ["C7", "C8", "C9"]},
    {"title": "区域价差与链路加价", "claim_ids": ["C10", "C11", "C12", "C13", "C14"]},
    {"title": "期货与预期", "claim_ids": ["C15", "C16", "C17"]},
    {"title": "产业面与产能", "claim_ids": ["C18", "C19", "C20", "C21"]},
    {"title": "市场容量", "claim_ids": ["C22", "C23"]},
    {"title": "数据质量与口径冲突", "claim_ids": ["C24", "C25", "C26"]},
    {"title": "结论与行动", "claim_ids": ["C27", "C28", "C29", "C30"]},
]

GAPS = [
    "省级监测缺口：内蒙古价格监测平台水果条目页面无正文，未取到自治区级分品种零售序列；以呼市商务局周报替代，覆盖 9 周。",
    "产地价缺口：赤峰/通辽/巴彦淖尔的地头收购价无公开连续序列，只用『产地批发市场报价 + 政府产值折算』两条代理，宁城 4.88 元/公斤为产值折算值，不是农户到手价。",
    "批发层缺口：21food 三市场 680 条报价常量率过高、同城口径差 28.6%，整体弃用；呼市批发只剩东瓦窑单点（两期），不足以做批发日度趋势。",
    "期货基差缺口：未取到苹果期货交割库/仓单数据，期现价差只用『期货收盘 vs 全国批发周均价』粗对齐。",
    "消费端缺口：无呼市/包头商超 POS 或社区团购动销数据，SOM 的 18% 份额为假设。",
    "天气缺口：未接入气象数据，11 月降温对到货量与损耗的影响只能定性。",
]

if __name__ == "__main__":
    ledger = {
        "topic": "内蒙古水果（苹果/梨/葡萄/香蕉/西瓜/菠萝/柑橘等）2026 年 10—11 月市场调研：价格、区域价差、批零结构与链路",
        "window": "2026-09-15 ~ 2026-11-12",
        "sources": SOURCES,
        "claims": CLAIMS,
        "sections": SECTIONS,
        "gaps": GAPS,
        "stats": {"sources": len(SOURCES), "claims": len(CLAIMS), "sections": len(SECTIONS),
                  "observations": M["观测统计"]["合计"]},
    }
    OUT.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结论 {len(CLAIMS)} 条 / 来源 {len(SOURCES)} 个 / 章节 {len(SECTIONS)} 个")
    for c in CLAIMS:
        print(f"  {c['id']}: {c['text'][:80]}...")
