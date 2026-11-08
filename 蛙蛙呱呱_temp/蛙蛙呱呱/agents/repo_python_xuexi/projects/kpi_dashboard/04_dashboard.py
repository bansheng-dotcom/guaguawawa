"""
=============================================================================
模块04: Python经营看板 — 美团优选(保定) 2025年度
=============================================================================
三屏看板结构:
    屏1(高管概览): KPI卡片 + GMV趋势 + 北极星达成率
    屏2(经营分析): 品类GMV + 团长分层 + 城市维度
    屏3(异动监控): 履约成本/损耗率趋势 + 异常标记

输出: data/dashboard.png (6合1图表)
=============================================================================
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 70)
print("  模块04: Python经营看板")
print("=" * 70)

daily = pd.read_csv(f'{DATA_DIR}/daily_metrics.csv')
daily['date'] = pd.to_datetime(daily['date'])
category = pd.read_csv(f'{DATA_DIR}/category_monthly.csv')
leader = pd.read_csv(f'{DATA_DIR}/leader_monthly.csv')
city = pd.read_csv(f'{DATA_DIR}/city_monthly.csv')

# 月度汇总
monthly = daily.groupby('month').agg(
    gmv=('gmv', 'sum'),
    orders=('orders', 'sum'),
    users=('users', 'sum'),
    active_leaders=('active_leaders', 'mean'),
    fulfill_cost_rate=('fulfillment_cost_rate', 'mean'),
    loss_rate=('fresh_loss_rate', 'mean'),
    gmv_per_user=('gmv_per_user', 'mean'),
    items_per_user=('items_per_user', 'mean'),
).reset_index()
monthly['gmv_wan'] = monthly['gmv'] / 10000
monthly['mom_gmv_change'] = monthly['gmv'].pct_change() * 100

# ===========================================================================
# 6合1仪表盘
# ===========================================================================

fig = plt.figure(figsize=(22, 14))
fig.suptitle('美团优选(保定) 2025年经营看板', fontsize=18, fontweight='bold', y=0.98)

# --- 图1: GMV月度趋势 + 环比变化 (左上) ---
ax1 = plt.subplot(2, 3, 1)
months = range(1, 13)
bars = ax1.bar(months, monthly['gmv_wan'], color='#2ECC71', alpha=0.85, edgecolor='white')
ax1.set_ylabel('GMV(万元)', color='#2ECC71')
ax1.set_title('月度GMV趋势', fontsize=12, fontweight='bold')

# 环比变化折线
ax1b = ax1.twinx()
ax1b.plot(months, monthly['mom_gmv_change'], 'o-', color='#E74C3C', linewidth=2, markersize=6, label='环比变化%')
ax1b.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
ax1b.set_ylabel('环比变化(%)', color='#E74C3C')
ax1b.legend(loc='upper left', fontsize=8)

# 标注异常月
for m in [7, 9, 11]:
    if m <= len(monthly):
        ax1.annotate('暴雨' if m==7 else ('中秋' if m==9 else '双11'), (m, monthly['gmv_wan'].iloc[m-1]),
                    textcoords="offset points", xytext=(0, 15), ha='center', fontsize=9,
                    color='red', fontweight='bold')

# --- 图2: 北极星指标日历热力图 (右上) ---
ax2 = plt.subplot(2, 3, 2)
# 按月×周构建热力图矩阵
daily['week'] = daily['date'].dt.isocalendar().week.astype(int)
pivot_data = daily.pivot_table(values='gmv_per_user', index='month', aggfunc='mean')
# 简化: 按月日均GMV画达标情况
gmv_by_month = daily.groupby('month')['gmv_per_user'].mean()
colors_heat = ['#E74C3C' if v < 24 else ('#F39C12' if v < 26 else '#2ECC71') for v in gmv_by_month.values]
ax2.bar(months, gmv_by_month.values, color=colors_heat, alpha=0.85, edgecolor='white')
ax2.axhline(y=26, color='red', linestyle='--', linewidth=1.5, label='目标: 26元')
ax2.set_ylabel('人均GMV(元)')
ax2.set_title('北极星达成(月度均)', fontsize=12, fontweight='bold')
ax2.legend(fontsize=8)

# --- 图3: 履约成本率 & 损耗率趋势 (中左) ---
ax3 = plt.subplot(2, 3, 3)
ax3.fill_between(months, monthly['fulfill_cost_rate'], alpha=0.3, color='#E74C3C', label='履约成本率')
ax3.plot(months, monthly['fulfill_cost_rate'], 'o-', color='#E74C3C', linewidth=2, markersize=6)
ax3.axhline(y=8.5, color='red', linestyle='--', linewidth=1, alpha=0.7, label='红线: 8.5%')
ax3.plot(months, monthly['loss_rate'], 's-', color='#F39C12', linewidth=2, markersize=6, label='生鲜损耗率')
ax3.axhline(y=5.0, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='红线: 5.0%')
ax3.set_ylabel('比率(%)')
ax3.set_title('护栏指标: 履约成本率 & 损耗率', fontsize=12, fontweight='bold')
ax3.legend(fontsize=7, loc='upper left')

# --- 图4: 品类GMV占比 (中右) ---
ax4 = plt.subplot(2, 3, 4)
cat_annual = category.groupby('category')['gmv'].sum().sort_values(ascending=True)
colors_cat = ['#3498DB','#E74C3C','#2ECC71','#F39C12','#9B59B6','#1ABC9C','#E67E22']
wedges, texts, autotexts = ax4.pie(cat_annual.values, labels=cat_annual.index,
                                     autopct='%1.1f%%', colors=colors_cat,
                                     explode=(0, 0, 0, 0, 0, 0.05, 0.1))
for t in autotexts:
    t.set_fontsize(8)
ax4.set_title('品类GMV占比(全年)', fontsize=12, fontweight='bold')

# --- 图5: 团长分层GMV贡献 (左下) ---
ax5 = plt.subplot(2, 3, 5)
leader_pivot = leader.pivot(index='month', columns='leader_tier', values='gmv')
leader_pivot.plot(kind='bar', stacked=True, ax=ax5, color=['#2ECC71','#3498DB','#95A5A6'], alpha=0.85)
ax5.set_xlabel('月份')
ax5.set_ylabel('GMV(元)')
ax5.set_title('团长分层GMV贡献', fontsize=12, fontweight='bold')
ax5.legend(fontsize=8)

# --- 图6: 城市维度对比 (右下) ---
ax6 = plt.subplot(2, 3, 6)
city_monthly = city.groupby('month').agg(
    tier1_gmv=('gmv', lambda x: x.values[0] if len(x)>0 else 0),
    tier35_gmv=('gmv', lambda x: x.values[1] if len(x)>1 else 0),
).reset_index()

x = np.arange(1, 13)
width = 0.35
ax6.bar(x - width/2, city_monthly['tier1_gmv']/10000, width, label='一线/新一线', color='#2ECC71', alpha=0.85)
ax6.bar(x + width/2, city_monthly['tier35_gmv']/10000, width, label='三五线', color='#3498DB', alpha=0.85)
ax6.set_xlabel('月份')
ax6.set_ylabel('GMV(万元)')
ax6.set_title('城市等级GMV对比', fontsize=12, fontweight='bold')
ax6.legend(fontsize=10)

plt.tight_layout()
plt.savefig(f'{DATA_DIR}/dashboard.png', dpi=150, bbox_inches='tight')
print(f'[看板已保存] {DATA_DIR}/dashboard.png')
print()

# KPI摘要
total_gmv = daily['gmv'].sum() / 10000
avg_fulfill = daily['fulfillment_cost_rate'].mean()
avg_loss = daily['fresh_loss_rate'].mean()
avg_gmv_pu = daily['gmv_per_user'].mean()
yoy_growth = (daily[daily['month']==12]['gmv'].sum() / daily[daily['month']==1]['gmv'].sum() - 1) * 100

print(f'  2025年度KPI摘要:')
print(f'    年GMV: {total_gmv:.0f}万元')
print(f'    人均GMV均值: {avg_gmv_pu:.1f}元')
print(f'    履约成本率均值: {avg_fulfill:.2f}%')
print(f'    损耗率均值: {avg_loss:.2f}%')
print(f'    年均月环比增长: {yoy_growth:.1f}%')
print()
print("=" * 70)
print("  模块04完成 — 看板已生成")
print("  下一步: python 05_monthly_report.py")
print("=" * 70)
