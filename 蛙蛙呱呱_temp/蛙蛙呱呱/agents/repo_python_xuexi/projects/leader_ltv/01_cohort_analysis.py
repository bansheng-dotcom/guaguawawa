"""
=============================================================================
模块01: 队列分析 — 团长月度留存热力图
=============================================================================
队列(Сohort): 按注册月份分组的团长,追踪他们随时间推移的留存率

热力图的读法:
    行 = 注册队列(2024年1月注册的团长...2024年12月注册的团长)
    列 = 已活跃月数(第1个月...第12个月)
    颜色 = 留存率(深绿=高,浅绿=低)
    对角线往下看 = 同一批团长随时间的变化

典型模式:
    - 第一列都是100%(全部团长在注册月都是活跃的)
    - 越往右(时间越久),颜色越浅(留存率下降)
    - 2024年1月的团到第12个月,可能只剩40%活跃

输出:
    1. 队列留存热力图
    2. 按城市等级的留存率对比
=============================================================================
"""

import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块01: 队列分析 — 团长留存热力图")
print("=" * 60)
print()

df = pd.read_csv(f'{DATA_DIR}/leader_monthly.csv')

# ===========================================================================
# 构造队列留存矩阵
# ===========================================================================

# 每个团长在每个月的数据 → 按注册月份和活跃月数透视
df['register_cohort'] = df['register_month']

# 保留最多18个月的留存
max_months_show = 18
cohort_matrix = df.pivot_table(
    index='register_cohort',
    columns='months_active',
    values='is_active',
    aggfunc='mean'
).iloc[:, :max_months_show] * 100

print("  队列留存矩阵 (前6个月 × 前6个活跃月):")
print(f"  {'Cohort':<12}", end="")
for j in range(1, 7):
    print(f"  M{j:<5}", end="")
print(f"\n  {'-'*50}")

for idx in cohort_matrix.index[:6]:
    print(f"  {int(idx):<12}", end="")
    for j in range(1, 7):
        val = cohort_matrix.loc[idx, j] if j in cohort_matrix.columns else np.nan
        if pd.notna(val):
            print(f"  {val:>5.0f}%", end="")
        else:
            print(f"  {'':>5}", end="")
    print()

# ===========================================================================
# 可视化: 热力图
# ===========================================================================

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# 图1: 队列留存热力图
ax1 = axes[0]
# 只显示前12个队列,前18个活跃月
plot_matrix = cohort_matrix.head(18).copy()
sns.heatmap(plot_matrix, annot=False, cmap='YlOrRd', ax=ax1,
            vmin=0, vmax=100, cbar_kws={'label': 'Retention %'})
ax1.set_xlabel('Months Active')
ax1.set_ylabel('Registration Cohort (Month)')
ax1.set_title('Leader Cohort Retention Heatmap', fontsize=12, fontweight='bold')

# 图2: 按城市等级的留存曲线对比
ax2 = axes[1]

for city, label, color in [('tier_1_new', '一线/新一线', '#E74C3C'), ('tier_3_5', '三五线', '#3498DB')]:
    city_df = df[df['city_tier'] == city]
    city_cohort = city_df.pivot_table(
        index='register_cohort', columns='months_active',
        values='is_active', aggfunc='mean'
    )

    # 取各活跃月数的平均留存率
    avg_retention = [city_cohort[c].mean() * 100 for c in range(1, 19) if c in city_cohort.columns]
    ax2.plot(range(1, len(avg_retention)+1), avg_retention, 'o-', color=color,
             label=label, linewidth=2, markersize=4)

# 标注中位存活月(留存率降到50%的月数)
ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% Retention')
ax2.set_xlabel('Months Active'); ax2.set_ylabel('Avg Retention %')
ax2.set_title('Retention Curve by City Tier', fontsize=12, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

plt.suptitle('团长队列留存分析', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DATA_DIR}/cohort_analysis.png', dpi=150, bbox_inches='tight')
print(f'\n[图表已保存] data/cohort_analysis.png')
print()
print("=" * 60)
print("  模块01完成")
print("  下一步: python 02_survival_analysis.py")
print("=" * 60)
