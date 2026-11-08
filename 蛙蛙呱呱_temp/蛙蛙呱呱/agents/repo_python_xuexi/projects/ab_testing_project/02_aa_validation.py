"""
=============================================================================
模块02: AA验证 — 社区团购实验前提检查
=============================================================================
目的: 在正式实验前,用AA实验(两组都用运营手动选品)验证分流均匀性。

如果AA阶段两组就有显著差异 → 分流系统有偏 → A/B结果不可信。

验证维度(社区团购专属):
    1. 连续指标: GMV、件数、履约成本率、损耗率、退货率、爆品占比
    2. 二分类指标: 首单转化率
    3. 用户画像一致性: 城市等级分布、购买频次分布、团长密度分布
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
print("  模块02: AA验证 — 分流均匀性检查")
print("=" * 70)
print()

df = pd.read_csv('data/aa_data.csv')
print(f"数据加载: {len(df)}条, A组{(df['group']=='A').sum()}人, B组{(df['group']=='B').sum()}人")
print()

group_a = df[df['group'] == 'A']
group_b = df[df['group'] == 'B']

# ===========================================================================
# 第一部分: 连续指标t检验
# ===========================================================================

print("=" * 50)
print("  连续指标 — t检验(A组 vs B组)")
print("=" * 50)
print(f"  {'指标':<20} {'A组均值':<10} {'B组均值':<10} {'差异%':<8} {'p值':<10} {'结论':<8}")
print(f"  {'-'*68}")

aa_results = []

continuous_metrics = [
    ('gmv', '人均GMV'),
    ('items_per_order', '人均件数'),
    ('fulfillment_cost_rate', '履约成本率'),
    ('fresh_loss_rate', '生鲜损耗率'),
    ('return_rate', '退货率'),
    ('hot_product_gmv_share', '爆品GMV占比'),
]

for col, name in continuous_metrics:
    a_vals = group_a[col].values
    b_vals = group_b[col].values
    t_stat, p_val = stats.ttest_ind(a_vals, b_vals)

    a_mean, b_mean = a_vals.mean(), b_vals.mean()
    diff_pct = ((b_mean - a_mean)/a_mean)*100 if a_mean != 0 else 0
    conclusion = 'PASS' if p_val > 0.05 else 'FAIL'

    aa_results.append({'metric': name, 'type': 'continuous', 'p_value': p_val, 'conclusion': conclusion})
    print(f"  {name:<20} {a_mean:<10.2f} {b_mean:<10.2f} {diff_pct:<+8.2f} {p_val:<10.4f} {conclusion:<8}")

print()

# ===========================================================================
# 第二部分: 首单转化率卡方检验
# ===========================================================================

print("=" * 50)
print("  二分类指标 — 首单转化率 卡方检验")
print("=" * 50)

table = pd.crosstab(df['group'], df['is_new_conversion'])
chi2, p_val, dof, expected = stats.chi2_contingency(table)

a_rate = group_a['is_new_conversion'].mean() * 100
b_rate = group_b['is_new_conversion'].mean() * 100
conclusion = 'PASS' if p_val > 0.05 else 'FAIL'
aa_results.append({'metric': '首单转化率', 'type': 'binary', 'p_value': p_val, 'conclusion': conclusion})

print(f"  A组首单转化率: {a_rate:.2f}%")
print(f"  B组首单转化率: {b_rate:.2f}%")
print(f"  卡方p值: {p_val:.4f} → {conclusion}")
print()

# ===========================================================================
# 第三部分: 用户画像一致性
# ===========================================================================

print("=" * 50)
print("  用户画像分布一致性检查")
print("=" * 50)

for dim_col, dim_name in [
    ('city_tier', '城市等级'),
    ('purchase_freq', '购买频次'),
    ('leader_density', '团长密度'),
]:
    table = pd.crosstab(df['group'], df[dim_col], normalize='index') * 100
    chi2, p, _, _ = stats.chi2_contingency(pd.crosstab(df['group'], df[dim_col]))
    print(f"  {dim_name}分布 (p={p:.4f} → {'PASS' if p>0.05 else 'FAIL'}):")
    print(f"    {table.round(1).to_dict()}")
    aa_results.append({'metric': f'{dim_name}分布', 'type': 'categorical', 'p_value': p, 'conclusion': 'PASS' if p>0.05 else 'FAIL'})

print()

# ===========================================================================
# 第四部分: 分布可视化
# ===========================================================================

fig, axes = plt.subplots(2, 3, figsize=(16, 10))

plot_specs = [
    ('gmv', 'GMV(元)', axes[0, 0]),
    ('items_per_order', '件数', axes[0, 1]),
    ('fulfillment_cost_rate', '履约成本率(%)', axes[0, 2]),
    ('fresh_loss_rate', '生鲜损耗率(%)', axes[1, 0]),
    ('return_rate', '退货率(%)', axes[1, 1]),
]

for col, name, ax in plot_specs:
    ax.hist(group_a[col], bins=50, alpha=0.5, label='A组', color='#5B9BD5', density=True)
    ax.hist(group_b[col], bins=50, alpha=0.5, label='B组', color='#FF6B6B', density=True)
    ks_stat, ks_p = stats.ks_2samp(group_a[col], group_b[col])
    ax.set_title(f'{name}分布对比 (KS p={ks_p:.4f})')
    ax.legend(fontsize=8)
    ax.set_ylabel('密度')

axes[1, 2].axis('off')
plt.suptitle('AA验证: A组 vs B组 各指标分布', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('data/aa_validation_plots.png', dpi=150, bbox_inches='tight')
print("[图表已保存] data/aa_validation_plots.png")
print()

# ===========================================================================
# 结论
# ===========================================================================

pass_count = sum(1 for r in aa_results if r['conclusion'] == 'PASS')
fail_count = sum(1 for r in aa_results if r['conclusion'] == 'FAIL')

print("=" * 70)
print("  AA验证结论")
print("=" * 70)
for r in aa_results:
    print(f"  {r['metric']:<22} p={r['p_value']:.4f} → {r['conclusion']}")

if fail_count == 0:
    conclusion_text = "[PASS] AA验证通过 -- 分流系统均匀,可继续A/B实验"
else:
    conclusion_text = f"[FAIL] {fail_count}项未通过 -- 分流系统存在偏差,需排查"

print(f"\n  通过率: {pass_count}/{len(aa_results)}")
print(f"  最终结论: {conclusion_text}")
print()
print("=" * 70)
print("  模块02完成")
print("  下一步: python 03_hypothesis_testing.py")
print("=" * 70)
