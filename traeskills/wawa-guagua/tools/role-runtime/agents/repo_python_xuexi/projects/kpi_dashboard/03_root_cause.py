"""
=============================================================================
模块03: 归因分析决策树
=============================================================================
当异动监控发出告警时,用决策树快速定位根因。

社区团购GMV异动归因逻辑:
    GMV下降
    ├── 是"量"的问题还是"价"的问题?
    │   ├── 订单量下降 → 流量问题?
    │   │   ├── 用户数下降 → 是自然流失还是竞对抢客?
    │   │   └── 转化率下降 → 是供给问题还是价格问题?
    │   └── 客单价下降 → 件数少了还是价格低了?
    │       ├── 件数下降 → 爆品搭配不合理?
    │       └── 单价下降 → 促销力度太大?
    │
    ├── 哪个品类拖了后腿?
    │   ├── 生鲜类 → 品质问题? 价格问题?
    │   └── 标品类 → 供给问题? 竞对价格?
    │
    ├── 哪个团长层级出问题?
    │   ├── 头部20%团长 → 高价值团长流失? 立刻人工跟进!
    │   └── 尾部团长 → 自然流动,关注但不恐慌
    │
    └── 是供给端还是履约端?
        ├── 履约成本率上升 → 供给距离变长? 天气?
        └── 损耗率上升 → 冷链故障? 推荐策略问题?
=============================================================================
"""

import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 70)
print("  模块03: 归因分析决策树")
print("=" * 70)

daily = pd.read_csv(f'{DATA_DIR}/daily_metrics.csv')
category = pd.read_csv(f'{DATA_DIR}/category_monthly.csv')
leader = pd.read_csv(f'{DATA_DIR}/leader_monthly.csv')

# ===========================================================================
# 模拟: 7月GMV下降归因
# ===========================================================================

print("""
  案例: 2025年7月GMV环比下降分析
  =================================

  Step 1: 确认异动
""")

jul = daily[daily['month'] == 7]
jun = daily[daily['month'] == 6]

jul_gmv = jul['gmv'].sum()
jun_gmv = jun['gmv'].sum()
gmv_change = (jul_gmv - jun_gmv) / jun_gmv * 100

jul_orders = jul['orders'].sum()
jun_orders = jun['orders'].sum()
orders_change = (jul_orders - jun_orders) / jun_orders * 100

jul_users = jul['users'].sum()
jun_users = jun['users'].sum()
users_change = (jul_users - jun_users) / jun_users * 100

jul_aov = jul_gmv / jul_orders
jun_aov = jun_gmv / jun_orders
aov_change = (jul_aov - jun_aov) / jun_aov * 100

print(f"  7月GMV: {jul_gmv/10000:.1f}万 vs 6月: {jun_gmv/10000:.1f}万 ({gmv_change:+.1f}%)")
print(f"  订单量:  {orders_change:+.1f}%")
print(f"  用户数:  {users_change:+.1f}%")
print(f"  客单价:  {aov_change:+.1f}%")
print()

print("  Step 2: 拆解'量'vs'价'")
if abs(orders_change) > abs(aov_change):
    print(f"  → 主要是'量'(订单)的问题! 订单量变化{orders_change:+.1f}% > 客单价变化{aov_change:+.1f}%")
    print(f"  → 继续拆解: 用户数{users_change:+.1f}% → {'流量下降' if users_change < -3 else '正常波动'}")
else:
    print(f"  → 主要是'价'(客单价)的问题!")
print()

print("  Step 3: 品类归因")
jul_cat = category[category['month'] == 7]
jun_cat = category[category['month'] == 6]

for _, j_row in jul_cat.iterrows():
    cat = j_row['category']
    j_gmv = j_row['gmv']
    ju_row = jun_cat[jun_cat['category'] == cat]
    if len(ju_row) > 0:
        ju_gmv = ju_row['gmv'].values[0]
        cat_change = (j_gmv - ju_gmv) / ju_gmv * 100
        flag = ' ← 最大拖累!' if cat_change < -10 else ''
        print(f"    {cat:<10}: {cat_change:+.1f}%{flag}")

print()
print("  Step 4: 团长层级归因")
jul_leader = leader[leader['month'] == 7]
jun_leader = leader[leader['month'] == 6]

for _, j_row in jul_leader.iterrows():
    tier = j_row['leader_tier']
    j_gmv = j_row['gmv']
    ju_row = jun_leader[jun_leader['leader_tier'] == tier]
    if len(ju_row) > 0:
        ju_gmv = ju_row['gmv'].values[0]
        tier_change = (j_gmv - ju_gmv) / ju_gmv * 100
        flag = ' ← 需人工跟进!' if ('top' in tier and tier_change < -5) else ''
        print(f"    {tier:<16}: {tier_change:+.1f}%{flag}")

print()
print("  Step 5: 履约端归因")
jul_fulfill = jul['fulfillment_cost_rate'].mean()
jun_fulfill = jun['fulfillment_cost_rate'].mean()
fulfill_change = (jul_fulfill - jun_fulfill) / jun_fulfill * 100

jul_loss = jul['fresh_loss_rate'].mean()
jun_loss = jun['fresh_loss_rate'].mean()
loss_change = (jul_loss - jun_loss) / jun_loss * 100

print(f"    履约成本率: {jul_fulfill:.1f}% (6月{jun_fulfill:.1f}%, {fulfill_change:+.1f}%)")
print(f"    损耗率:     {jul_loss:.1f}% (6月{jun_loss:.1f}%, {loss_change:+.1f}%)")
print(f"    → {'履约成本上涨是重要因素! 检查供应商距离和天气影响' if fulfill_change > 5 else '履约端正常'}")

print(f"""
  =================================
  归因结论:
    7月GMV下降{gmv_change:+.1f}% → 根因定位:
    1. 季节性(夏季高温)导致生鲜需求下降 + 损耗率上升
    2. 7月15-21日暴雨导致配送受阻,履约成本飙升
    3. 蔬菜水果品类GMV下滑最明显(季节因素)
    → 建议: 夏季增加冷冻品/饮料占比,提前储备冷链运力
  =================================
""")

print("=" * 70)
print("  模块03完成 — 归因分析框架就绪")
print("  下一步: python 04_dashboard.py")
print("=" * 70)
