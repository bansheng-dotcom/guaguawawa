"""
=============================================================================
模块02: 异动监控规则
=============================================================================
社区团购的异动监控重点:
    - GMV异动(骤降/骤升) — 是品类问题还是履约问题?
    - 履约成本率飙升 — 天气/距离/单量?
    - 损耗率异常 — 生鲜品滞销还是冷链故障?
    - 团长活跃度骤降 — 团长流失预警

每条规则包含: 触发条件 + 告警等级 + 归因方向 + 建议动作
=============================================================================
"""

import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 70)
print("  模块02: 异动监控规则设计")
print("=" * 70)
print()

daily = pd.read_csv(f'{DATA_DIR}/daily_metrics.csv')
daily['date'] = pd.to_datetime(daily['date'])

# 计算滚动指标(7日均值、标准差)
daily['gmv_7d_avg'] = daily['gmv'].rolling(7).mean()
daily['gmv_7d_std'] = daily['gmv'].rolling(7).std()
daily['fulfill_7d_avg'] = daily['fulfillment_cost_rate'].rolling(7).mean()
daily['loss_7d_avg'] = daily['fresh_loss_rate'].rolling(7).mean()

print("""
  +======================================================================+
  |  异动监控规则库 (共10条)                                              |
  +======================================================================+

  [规则1] GMV单日骤降
    条件: 当日GMV < 7日均值 - 2×标准差 (连续2天)
    等级: [HIGH] 高风险
    归因: 检查是否周末→工作日正常回落 / 是否全品类下跌 / 是否特定团长
    动作: 若全品类→排查APP/支付故障; 若特定品类→检查供给/价格

  [规则2] GMV单日骤升
    条件: 当日GMV > 7日均值 + 2×标准差
    等级: [LOW] 正常(可能是促销日)
    归因: 检查是否大促/节假日 / 是否个别爆品拉动
    动作: 确认非刷单后,记录爆品策略以便复用

  [规则3] 履约成本率连续上升
    条件: 履约成本率连续5日高于7日均值
    等级: [MID] 关注 → [HIGH] 高风险(持续10天)
    归因: 检查天气/配送距离/单均件数(批量折扣)
    动作: 联系网格仓确认运力; 排查远程供应商占比

  [规则4] 生鲜损耗率异常
    条件: 当日损耗率 > 7日均值 + 1.5倍(夏季)或2倍(其他季节)
    等级: [HIGH] 高风险
    归因: 是否特定品类? 冷链是否正常? 是否过度推荐易损耗品?
    动作: 暂停高损耗品推荐; 检查仓储温度

  [规则5] 退货率突增
    条件: 退货率连续3日 > 2.5%
    等级: [MID] 关注
    归因: 按品类/团长拆分,定位退货来源
    动作: 品控抽检高频退货品

  [规则6] 活跃团长连续下降
    条件: 活跃团长数连续7日下降且累计跌幅>10%
    等级: [HIGH] 高风险(团长流失预警!)
    归因: 按城市等级/团长层级拆分
    动作: 头部团长逐一联系; 检查佣金结算是否延迟

  [规则7] 人均件数异常
    条件: 人均件数 < 3.0 (连续3天) 或 > 5.0
    等级: [MID] 关注
    归因: 是否爆品结构变化? 是否客单价异常?
    动作: 检查爆品坑位的商品搭配

  [规则8] 周末效应异常
    条件: 周末GMV增幅 < 15%(正常应25-50%)
    等级: [MID] 关注
    归因: 是否竞对做了促销? 天气影响?
    动作: 对比竞对活动日历

  [规则9] 月末GMV冲量后回落
    条件: 月最后3天GMV显著高于月均,次月1-3日骤降>30%
    等级: [LOW] 正常(运营冲KPI)  ← 但需关注是否是刷单
    归因: 对比订单来源(团长分享 vs 用户主动打开)
    动作: 检查月末订单的复购率(冲量订单复购率通常低)

  [规则10] 爆品GMV贡献占比异常
    条件: 爆品占比连续5日 < 30%
    等级: [MID] 关注
    归因: 爆品选品失误? 竞对价格更低? 供给断货?
    动作: 对比竞对爆品价格; 检查爆品库存
""")

# ===========================================================================
# 从数据中检测异动
# ===========================================================================

print("=" * 50)
print("  2025年实际异动检测结果")
print("=" * 50)

# 规则1: GMV单日骤降
daily['gmv_zscore'] = (daily['gmv'] - daily['gmv_7d_avg']) / daily['gmv_7d_std']
gmv_drops = daily[
    (daily['gmv_zscore'] < -2) &
    (daily['gmv_zscore'].shift(1) < -2)
].dropna(subset=['gmv_zscore'])

print(f"\n  [规则1] GMV骤降(>2σ连续2天): {len(gmv_drops)}次")
if len(gmv_drops) > 0:
    for _, row in gmv_drops.iterrows():
        print(f"    {row['date'].strftime('%m-%d')}: GMV={row['gmv']:.0f}, z={row['gmv_zscore']:.1f}")

# 规则3: 履约成本率连续上升
daily['fulfill_rising'] = (daily['fulfillment_cost_rate'] > daily['fulfill_7d_avg']).astype(int)
# 找连续5天的上升段(简化)
for i in range(8, len(daily)):
    if daily['fulfill_rising'].iloc[i-4:i+1].sum() == 5:
        date_str = daily['date'].iloc[i].strftime('%m-%d')
        rate = daily['fulfillment_cost_rate'].iloc[i]
        if rate > 9.0:  # 只报告严重的
            print(f"\n  [规则3] 履约成本率连续上升: {date_str} 达{rate:.1f}%")
            break

# 规则4: 损耗率异常
daily['loss_zscore'] = (daily['fresh_loss_rate'] - daily['loss_7d_avg']) / daily['fresh_loss_rate'].rolling(7).std()
loss_spikes = daily[daily['loss_zscore'] > 2].dropna()
print(f"\n  [规则4] 损耗率异常(>2σ): {len(loss_spikes)}次")
if len(loss_spikes) > 0:
    for _, row in loss_spikes.head(3).iterrows():
        print(f"    {row['date'].strftime('%m-%d')}: 损耗率={row['fresh_loss_rate']:.2f}%")

# 规则6: 活跃团长下降
daily['leader_7d_avg'] = daily['active_leaders'].rolling(7).mean()
leader_decline = daily[daily['active_leaders'] < daily['leader_7d_avg'] * 0.9].dropna()
print(f"\n  [规则6] 活跃团长下降>10%: {len(leader_decline)}天")

print(f"\n  异动检测总结:")
print(f"    GMV骤降: {len(gmv_drops)}次 | 损耗异常: {len(loss_spikes)}次 | 团长流失: {len(leader_decline)}天")
print()

print("=" * 70)
print("  模块02完成 — 异动监控规则就绪")
print("  下一步: python 03_root_cause.py")
print("=" * 70)
