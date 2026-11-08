"""
=============================================================================
模块03: 假设检验 — 算法推荐 vs 运营手选
=============================================================================
核心问题: 算法个性化推荐到底有没有比运营手动选品更好?

检验策略(社区团购指标):
    t检验:           GMV、履约成本率、损耗率、退货率、爆品占比(近似正态)
    Mann-Whitney U:  人均件数(计数型,偏态)
    卡方检验:        首单转化率(二分类)

社区团购的检验逻辑跟电商不太一样:
    - 北极星有两个(GMV+件数),需要两个都显著或至少GMV显著+件数不恶化
    - 护栏指标有三个,任何一个显著恶化都可能"否决"实验
    - 履约成本率升高=边际利润被吃掉 → 即使GMV涨了也可能不划算
=============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 70)
print("  模块03: 假设检验 — 算法推荐 vs 运营手选")
print("=" * 70)
print()

df = pd.read_csv('data/ab_test_data.csv')
print(f"数据: {len(df)}条, 对照组(运营):{(df['group']=='control').sum()}, 实验组(算法):{(df['group']=='treatment').sum()}")
print()

control = df[df['group'] == 'control']
treatment = df[df['group'] == 'treatment']
ALPHA = 0.05

# ===========================================================================
# 第一部分: 描述性统计
# ===========================================================================

print("=" * 50)
print("  描述性统计")
print("=" * 50)
print(f"  {'指标':<22} {'运营均值':<12} {'算法均值':<12} {'变化':<10}")
print(f"  {'-'*56}")

all_metrics = [
    ('gmv', '人均GMV(元)', False),
    ('items_per_order', '人均件数', False),
    ('fulfillment_cost_rate', '履约成本率(%)', False),
    ('fresh_loss_rate', '生鲜损耗率(%)', False),
    ('return_rate', '退货率(%)', False),
    ('is_new_conversion', '首单转化率(%)', True),
    ('hot_product_gmv_share', '爆品GMV占比(%)', False),
]

for col, name, is_binary in all_metrics:
    c_m = control[col].mean()
    t_m = treatment[col].mean()
    if is_binary:
        c_m *= 100; t_m *= 100
    change = ((t_m - c_m) / c_m) * 100 if c_m != 0 else 0
    print(f"  {name:<22} {c_m:<12.2f} {t_m:<12.2f} {change:+.2f}%")

print()

# ===========================================================================
# 第二部分: 正态性判断
# ===========================================================================

print("=" * 50)
print("  正态性判断(决定检验方法)")
print("=" * 50)
print(f"  {'指标':<20} {'偏度':<10} {'判定':<15} {'检验方法':<18}")
print(f"  {'-'*63}")

test_assignments = {}

for col, name, is_binary in all_metrics:
    if is_binary:
        test_assignments[col] = '卡方检验'
        print(f"  {name:<20} {'N/A':<10} {'二分类':<15} {'卡方检验':<18}")
    elif col == 'items_per_order':
        # 件数是计数数据,用Mann-Whitney U更合适
        test_assignments[col] = 'Mann-Whitney U'
        skew = df[col].skew()
        print(f"  {name:<20} {skew:<+10.4f} {'计数型/偏态':<15} {'Mann-Whitney U':<18}")
    else:
        test_assignments[col] = 't检验'
        skew = df[col].skew()
        verdict = '近似正态' if abs(skew) < 1.0 else '偏态'
        print(f"  {name:<20} {skew:<+10.4f} {verdict:<15} {'t检验':<18}")

print()

# ===========================================================================
# 第三部分: 正式检验
# ===========================================================================

print("=" * 50)
print("  正式假设检验")
print("=" * 50)
print(f"  {'指标':<22} {'检验方法':<16} {'p值':<12} {'显著?':<6} {'效应量':<10}")
print(f"  {'-'*68}")

results = []

for col, name, is_binary in all_metrics:
    c_vals = control[col].values
    t_vals = treatment[col].values

    if is_binary:
        # 卡方检验
        table = pd.crosstab(df['group'], df[col])
        chi2, p_val, dof, expected = stats.chi2_contingency(table)
        n = table.sum().sum()
        cramers_v = np.sqrt(chi2 / (n * min(table.shape[0]-1, table.shape[1]-1)))
        eff_size = cramers_v
        test_name = 'Chi-squared'
    elif test_assignments[col] == 'Mann-Whitney U':
        u_stat, p_val = stats.mannwhitneyu(t_vals, c_vals, alternative='two-sided')
        n1, n2 = len(t_vals), len(c_vals)
        rank_biserial = 1 - (2*u_stat) / (n1*n2)
        eff_size = rank_biserial
        test_name = 'Mann-Whitney U'
    else:
        t_stat, p_val = stats.ttest_ind(t_vals, c_vals)
        pooled_std = np.sqrt((c_vals.std(ddof=1)**2 + t_vals.std(ddof=1)**2)/2)
        cohens_d = (t_vals.mean() - c_vals.mean()) / pooled_std
        eff_size = cohens_d
        test_name = 't-test'

    sig = 'YES' if p_val < ALPHA else 'NO'
    change = ((treatment[col].mean() / control[col].mean()) - 1) * 100

    results.append({
        'metric': name, 'test': test_name, 'p_value': p_val,
        'significant': sig, 'effect_size': eff_size, 'change_pct': change,
        'col': col,
    })

    print(f"  {name:<22} {test_name:<16} {p_val:<12.4e} {sig:<6} {eff_size:<+10.4f}")

print()

# ===========================================================================
# 第四部分: 护栏指标专项检查
# ===========================================================================

print("=" * 50)
print("  护栏指标专项检查(社区团购命门)")
print("=" * 50)

guardrail_cols = ['fulfillment_cost_rate', 'fresh_loss_rate', 'return_rate']
guardrail_names = {'fulfillment_cost_rate': '履约成本率', 'fresh_loss_rate': '生鲜损耗率', 'return_rate': '退货率'}

guardrail_ok = True
for col in guardrail_cols:
    r = [x for x in results if x['col'] == col][0]
    change = r['change_pct']
    sig = r['significant']
    # 护栏指标: 上升是坏事
    if change > 0 and sig == 'YES':
        print(f"  [WARNING] {guardrail_names[col]}: 显著上升{change:+.2f}%! 算法可能不适用!")
        guardrail_ok = False
    elif change > 0:
        print(f"  [CAUTION] {guardrail_names[col]}: 上升{change:+.2f}%(不显著), 需持续关注")
    else:
        print(f"  [OK]     {guardrail_names[col]}: {change:+.2f}%")

print(f"\n  护栏总评: {'[PASS] 全部通过' if guardrail_ok else '[FAIL] 存在恶化'}")
print()

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(2, 3, figsize=(18, 12))

plot_data = results
labels = [r['metric'] for r in plot_data]
changes = [r['change_pct'] for r in plot_data]
colors = ['#27AE60' if r['significant']=='YES' else '#95A5A6' for r in plot_data]

# 图1: 各指标变化
ax1 = axes[0, 0]
bars = ax1.barh(labels, changes, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
ax1.axvline(x=0, color='black', linewidth=1)
ax1.set_xlabel('变化(%)')
ax1.set_title('各指标实验组 vs 对照组 变化(%)')
for bar, ch in zip(bars, changes):
    ax1.text(bar.get_width()+0.1, bar.get_y()+bar.get_height()/2, f'{ch:+.2f}%', va='center', fontsize=8)

# 图2: p值
ax2 = axes[0, 1]
p_vals = [r['p_value'] for r in plot_data]
p_colors = ['#E74C3C' if p < ALPHA else '#95A5A6' for p in p_vals]
ax2.barh(labels, [-np.log10(p) if p > 0 else 15 for p in p_vals], color=p_colors, alpha=0.8)
ax2.axvline(x=-np.log10(ALPHA), color='red', linestyle='--', label=f'alpha={ALPHA}')
ax2.set_xlabel('-log10(p-value)')
ax2.set_title('显著性(-log10 p)')
ax2.legend(fontsize=8)

# 图3: 效应量
ax3 = axes[0, 2]
eff_sizes = [abs(r['effect_size']) for r in plot_data]
ax3.barh(labels, eff_sizes, color='#3498DB', alpha=0.8)
ax3.set_xlabel('效应量')
ax3.set_title('各指标效应量')

# 图4-6: 核心指标分布对比
for idx, (col, name) in enumerate([
    ('gmv', 'GMV分布'), ('items_per_order', '件数分布'), ('fulfillment_cost_rate', '履约成本率分布')
]):
    ax = axes[1, idx]
    ax.hist(control[col], bins=60, alpha=0.5, label='运营手选', color='#5B9BD5', density=True)
    ax.hist(treatment[col], bins=60, alpha=0.5, label='算法推荐', color='#FF6B6B', density=True)
    ax.set_title(name)
    ax.legend(fontsize=8)

plt.suptitle('假设检验结果总览 — 运营手选 vs 算法推荐', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('data/hypothesis_testing_plots.png', dpi=150, bbox_inches='tight')
print("[图表已保存] data/hypothesis_testing_plots.png")
print()

# ===========================================================================
# 结论
# ===========================================================================

print("=" * 70)
print("  假设检验结论")
print("=" * 70)

sig_count = sum(1 for r in results if r['significant'] == 'YES')
gmv_r = results[0]
items_r = results[1]

print(f"""
  检验汇总:
  +---------------------+----------------+----------+----------+--------------+
  | 指标                | 检验方法       | p值      | 显著     | 变化         |
  |---------------------+----------------+----------+----------+--------------|
""")
for r in results:
    print(f"  | {r['metric']:<20} | {r['test']:<14} | {r['p_value']:<8.4e} | {r['significant']:<8} | {r['change_pct']:<+12.2f}% |")

print(f"""
  +---------------------+----------------+----------+----------+--------------+
  {sig_count}/{len(results)} 指标达到统计显著

  北极星指标:
    人均GMV:     {'显著提升' if gmv_r['significant']=='YES' else '未达显著'} {gmv_r['change_pct']:+.2f}%
    人均件数:    {'显著提升' if items_r['significant']=='YES' else '未达显著'} {items_r['change_pct']:+.2f}%

  护栏指标: {'全部通过' if guardrail_ok else '存在恶化——需进一步分析'}

  注: 这只是假设检验结果,还需置信区间(04)和多重检验校正(05)验证。
""")

print("=" * 70)
print("  模块03完成")
print("  下一步: python 04_confidence_interval.py")
print("=" * 70)
