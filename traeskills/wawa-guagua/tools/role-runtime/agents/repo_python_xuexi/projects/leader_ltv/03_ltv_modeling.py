"""
=============================================================================
模块03: LTV建模 — 团长终身价值计算 + 分层
=============================================================================
LTV (Lifetime Value) = 月均GMV × 预期存活月数

两种计算方法:
    1. 简单法: 已观察到的总GMV (对有充足历史的老团长)
    2. 预测法: 月均GMV × K-M估计的预期存活月数 (对新团长)

团长分层:
    高价值团长: LTV > 15万
    中等价值团长: LTV 5-15万
    低价值团长: LTV < 5万

业务意义:
    如果团长获客成本(佣金+补贴) > LTV → 赔钱
    如果获客成本 < LTV的1/3 → 值得扩张
=============================================================================
"""

import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块03: LTV建模")
print("=" * 60)
print()

leaders = pd.read_csv(f'{DATA_DIR}/leader_summary.csv')
monthly = pd.read_csv(f'{DATA_DIR}/leader_monthly.csv')

# ===========================================================================
# 计算月均GMV + 预期存活
# ===========================================================================

# 月均GMV: 活跃月份的GMV平均
active_months = monthly[monthly['is_active'] == 1]
avg_monthly_gmv = active_months.groupby('leader_id')['monthly_gmv'].mean().reset_index()
avg_monthly_gmv.columns = ['leader_id', 'avg_monthly_gmv']

leaders = leaders.merge(avg_monthly_gmv, on='leader_id', how='left')
leaders['avg_monthly_gmv'] = leaders['avg_monthly_gmv'].fillna(0)

# 预期存活月数: 用已流失团长的平均存活时间推算
churned = leaders[leaders['is_churned'] == 1]
expected_survival = churned['observed_months'].median()

# LTV简单估计
leaders['ltv_simple'] = leaders['avg_monthly_gmv'] * expected_survival

# 更精细的LTV: 城市+密度分组的预期存活
grouped_survival = churned.groupby(['city_tier','leader_density'])['observed_months'].median().reset_index()
grouped_survival.columns = ['city_tier','leader_density','expected_months']

leaders = leaders.merge(grouped_survival, on=['city_tier','leader_density'], how='left')
leaders['expected_months'] = leaders['expected_months'].fillna(expected_survival)
leaders['ltv_advanced'] = leaders['avg_monthly_gmv'] * leaders['expected_months']

print(f"  已流失团长中位存活: {expected_survival:.1f} 个月")
print(f"  月均GMV中位数: {leaders['avg_monthly_gmv'].median():.0f} 元")
print(f"  LTV中位数(简单): {leaders['ltv_simple'].median():.0f} 元")
print(f"  LTV中位数(精细): {leaders['ltv_advanced'].median():.0f} 元")
print()

# ===========================================================================
# 团长LTV分层
# ===========================================================================

leaders['ltv_tier'] = pd.cut(leaders['ltv_advanced'],
    bins=[0, 50000, 100000, 150000, 999999],
    labels=['<5万(低价值)','5-10万(中等)','10-15万(高价值)','>15万(超级团长)'])

tier_stats = leaders.groupby('ltv_tier', observed=False).agg(
    leader_count=('leader_id','count'),
    avg_ltv=('ltv_advanced','mean'),
    avg_monthly_gmv=('avg_monthly_gmv','mean'),
    avg_survival=('expected_months','mean'),
).round(0)

print("  团长LTV分层:")
for tier, row in tier_stats.iterrows():
    pct = row['leader_count'] / len(leaders) * 100
    print(f"    {tier:<20}: {int(row['leader_count']):>4}人 ({pct:>5.1f}%)  LTV~{row['avg_ltv']:.0f}  月GMV~{row['avg_monthly_gmv']:.0f}")

# ===========================================================================
# 获客成本评估
# ===========================================================================

print()
print("=" * 40)
print("  获客成本合理性评估")
print("=" * 40)

# 假设: 团长招募成本(佣金补贴+BD奖励)约3000元/人
acquisition_cost = 3000
median_ltv = leaders['ltv_advanced'].median()
ltv_cac_ratio = median_ltv / acquisition_cost

print(f"  团长获客成本: {acquisition_cost} 元")
print(f"  团长LTV中位数: {median_ltv:.0f} 元")
print(f"  LTV/CAC: {ltv_cac_ratio:.1f}x")

if ltv_cac_ratio > 3:
    print(f"  → 健康(>3x),获客投入合理")
elif ltv_cac_ratio > 1:
    print(f"  → 边际(1-3x),需优化获客效率或团长质量")
else:
    print(f"  → 不健康(<1x),每招一个团长亏钱")

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 图1: LTV分布直方图
ax1 = axes[0]
ax1.hist(leaders['ltv_advanced']/10000, bins=40, color='#3498DB', alpha=0.8, edgecolor='white')
ax1.axvline(x=leaders['ltv_advanced'].median()/10000, color='red', linestyle='--', linewidth=2, label=f'Median={median_ltv/10000:.1f}万')
ax1.set_xlabel('LTV(万元)')
ax1.set_ylabel('团长数')
ax1.set_title('团长LTV分布', fontsize=11, fontweight='bold')
ax1.legend()

# 图2: 城市×密度 LTV对比
ax2 = axes[1]
grouped_ltv = leaders.groupby(['city_tier','leader_density'])['ltv_advanced'].mean().unstack()
grouped_ltv.index = ['一线/新一线' if x=='tier_1_new' else '三五线' for x in grouped_ltv.index]
grouped_ltv.columns = ['高密度','低密度','中密度']
grouped_ltv.plot(kind='bar', ax=ax2, color=['#E74C3C','#2ECC71','#3498DB'], alpha=0.85)
ax2.set_xlabel('')
ax2.set_ylabel('平均LTV(元)')
ax2.set_title('城市×密度 LTV对比', fontsize=11, fontweight='bold')
ax2.legend(fontsize=8)
ax2.tick_params(axis='x', rotation=0)

# 图3: LTV分层饼图
ax3 = axes[2]
ltv_tier_counts = leaders['ltv_tier'].value_counts()
colors_pie = ['#E74C3C','#F39C12','#2ECC71','#3498DB']
ax3.pie(ltv_tier_counts.values, labels=ltv_tier_counts.index, autopct='%1.1f%%',
        colors=colors_pie, explode=(0,0,0.05,0.1))
ax3.set_title('团长LTV分层占比', fontsize=11, fontweight='bold')

plt.suptitle('团长LTV分析', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DATA_DIR}/ltv_analysis.png', dpi=150, bbox_inches='tight')
print(f'\n[图表已保存] data/ltv_analysis.png')
print()
print("=" * 60)
print("  模块03完成")
print("  下一步: python 04_churn_prediction.py")
print("=" * 60)
