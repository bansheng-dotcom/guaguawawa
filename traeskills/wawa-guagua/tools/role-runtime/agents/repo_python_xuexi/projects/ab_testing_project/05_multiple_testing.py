"""
=============================================================================
模块05: 多重检验校正 — 测了7个指标,有几个是真显著?
=============================================================================
问题: 同时检验7个指标,至少1个假阳性的概率 = 1-(1-0.05)^7 ≈ 30.2%

社区团购场景的特殊性:
    北极星指标有2个(GMV+件数),护栏指标有3个(履约成本+损耗+退货),
    探索指标有2个(爆品占比+首单转化)。
    按业界惯例:
        - 北极星: 不做校正(有明确先验假设)
        - 护栏: 不做校正(保守策略——宁可误报,不能漏报)
        - 探索: BH校正(控制FDR)

三种方法:
    1. Bonferroni: 最保守, p < alpha/m
    2. Holm-Bonferroni: 逐步法,比Bonf更powerful
    3. Benjamini-Hochberg: 控制FDR,适合探索性场景
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
print("  模块05: 多重检验校正")
print("=" * 70)
print()

df = pd.read_csv('data/ab_test_data.csv')
control = df[df['group'] == 'control']
treatment = df[df['group'] == 'treatment']
ALPHA = 0.05

# 原始检验
print("  原始检验(未校正):")
print(f"  {'指标':<22} {'p值':<14} {'alpha=0.05显著?':<16}")
print(f"  {'-'*52}")

raw_results = []

for col, name, is_binary in [
    ('gmv', '人均GMV', False),
    ('items_per_order', '人均件数', False),
    ('fulfillment_cost_rate', '履约成本率', False),
    ('fresh_loss_rate', '生鲜损耗率', False),
    ('return_rate', '退货率', False),
    ('is_new_conversion', '首单转化率', True),
    ('hot_product_gmv_share', '爆品GMV占比', False),
]:
    c_v, t_v = control[col].values, treatment[col].values
    if is_binary:
        table = pd.crosstab(df['group'], df[col])
        _, p_val, _, _ = stats.chi2_contingency(table)
    else:
        _, p_val = stats.ttest_ind(t_v, c_v)

    sig = 'YES' if p_val < ALPHA else 'NO'
    raw_results.append({'metric': name, 'p_value': p_val, 'sig_uncorrected': sig})
    print(f"  {name:<22} {p_val:<14.4e} {sig:<16}")

m = len(raw_results)
fwer = 1 - (1-ALPHA)**m
print(f"\n  同时检验{m}个指标,至少1个假阳性的概率(FWER): {fwer*100:.1f}%")
print()

# ===========================================================================
# Bonferroni
# ===========================================================================

print("=" * 50)
print("  Bonferroni校正")
print("=" * 50)
bonf_threshold = ALPHA / m
print(f"  校正阈值: {ALPHA}/{m} = {bonf_threshold:.4f}")
print(f"  {'指标':<22} {'原始p':<14} {'Bonf adj p':<14} {'显著?':<8}")
print(f"  {'-'*58}")

for r in raw_results:
    p_adj = min(r['p_value']*m, 1.0)
    sig = 'YES' if p_adj < ALPHA else 'NO'
    print(f"  {r['metric']:<22} {r['p_value']:<14.4e} {p_adj:<14.4e} {sig:<8}")

print()

# ===========================================================================
# Holm-Bonferroni
# ===========================================================================

print("=" * 50)
print("  Holm-Bonferroni校正(逐步)")
print("=" * 50)

sorted_r = sorted(raw_results, key=lambda x: x['p_value'])
holm_sig = {}
all_sig = True

print(f"  {'排名':<6} {'指标':<22} {'p值':<14} {'阈值':<14} {'显著?':<8}")
print(f"  {'-'*64}")

for k, r in enumerate(sorted_r, 1):
    threshold = ALPHA / (m - k + 1)
    sig = 'YES' if (r['p_value'] < threshold) and all_sig else 'NO'
    if sig == 'NO':
        all_sig = False
    holm_sig[r['metric']] = sig
    print(f"  {k:<6} {r['metric']:<22} {r['p_value']:<14.4e} {threshold:<14.4f} {sig:<8}")

print()

# ===========================================================================
# BH (FDR)
# ===========================================================================

print("=" * 50)
print("  Benjamini-Hochberg(FDR控制)")
print("=" * 50)

bh_mark = 0
for k, r in enumerate(sorted_r, 1):
    threshold = (k/m) * ALPHA
    if r['p_value'] <= threshold:
        bh_mark = k

bh_sig_set = set()
for k, r in enumerate(sorted_r, 1):
    if k <= bh_mark:
        bh_sig_set.add(r['metric'])

# BH adjusted p-values
bh_adj = np.zeros(m)
for i in range(m):
    bh_adj[i] = sorted_r[i]['p_value'] * m / (i+1)
for i in range(m-2, -1, -1):
    bh_adj[i] = min(bh_adj[i], bh_adj[i+1])
bh_adj = np.minimum(bh_adj, 1.0)

print(f"  {'排名':<6} {'指标':<22} {'p值':<14} {'BH adj p':<14} {'显著(FDR)?':<12}")
print(f"  {'-'*68}")

for k, (r, bha) in enumerate(zip(sorted_r, bh_adj), 1):
    sig = 'YES' if r['metric'] in bh_sig_set else 'NO'
    print(f"  {k:<6} {r['metric']:<22} {r['p_value']:<14.4e} {bha:<14.4e} {sig:<12}")

print()

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

p_vals = [r['p_value'] for r in raw_results]
labels = [r['metric'] for r in raw_results]

# Bonferroni
ax = axes[0]
colors = ['#E74C3C' if min(p*m,1.0)<ALPHA else '#95A5A6' for p in p_vals]
ax.barh(range(m), [-np.log10(p) if p>0 else 15 for p in p_vals], color=colors)
ax.axvline(x=-np.log10(bonf_threshold), color='red', linestyle='--', label=f'Bonf阈值')
ax.set_yticks(range(m)); ax.set_yticklabels(labels)
ax.set_xlabel('-log10(p)'); ax.set_title('Bonferroni'); ax.legend(fontsize=8)

# Holm
ax = axes[1]
s_labels = [r['metric'] for r in sorted_r]
s_pvals = [r['p_value'] for r in sorted_r]
colors_h = ['#E74C3C' if holm_sig[l]=='YES' else '#95A5A6' for l in s_labels]
ax.barh(range(m), [-np.log10(p) if p>0 else 15 for p in s_pvals], color=colors_h)
ax.set_yticks(range(m)); ax.set_yticklabels(s_labels)
ax.set_xlabel('-log10(p)'); ax.set_title('Holm-Bonferroni')

# BH
ax = axes[2]
colors_bh = ['#E74C3C' if l in bh_sig_set else '#95A5A6' for l in s_labels]
ax.barh(range(m), [-np.log10(p) if p>0 else 15 for p in s_pvals], color=colors_bh)
bh_line = [(k/m)*ALPHA for k in range(1,m+1)]
ax.plot([-np.log10(t) if t>0 else 15 for t in bh_line], range(m), 'b--', label='BH阈值线', linewidth=2)
ax.set_yticks(range(m)); ax.set_yticklabels(s_labels)
ax.set_xlabel('-log10(p)'); ax.set_title('Benjamini-Hochberg(FDR)'); ax.legend(fontsize=8)

plt.suptitle('三种多重检验校正方法对比', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('data/multiple_testing_plots.png', dpi=150, bbox_inches='tight')
print("[图表已保存] data/multiple_testing_plots.png")
print()

# ===========================================================================
# 总结
# ===========================================================================

print("=" * 70)
print("  校正方法对比总结")
print("=" * 70)
print(f"  {'指标':<22} {'原始':<8} {'Bonferroni':<12} {'Holm':<8} {'BH(FDR)':<10}  {'建议层级':<12}")
print(f"  {'-'*72}")

# 指标层级标注
metric_tiers = {
    '人均GMV': '北极星', '人均件数': '北极星',
    '履约成本率': '护栏', '生鲜损耗率': '护栏', '退货率': '护栏',
    '首单转化率': '探索', '爆品GMV占比': '探索',
}

for r in raw_results:
    name = r['metric']
    orig = r['sig_uncorrected']
    bonf = 'YES' if min(r['p_value']*m,1.0)<ALPHA else 'NO'
    holm = holm_sig.get(name, 'NO')
    bh = 'YES' if name in bh_sig_set else 'NO'
    tier = metric_tiers.get(name, '')
    print(f"  {name:<22} {orig:<8} {bonf:<12} {holm:<8} {bh:<10}  {tier:<12}")

print(f"""
  建议:
    - 北极星指标(人均GMV、人均件数): 不做校正,有明确先验假设
    - 护栏指标(履约成本率、损耗率、退货率): 不做校正,保守策略
    - 探索指标: 使用BH校正控制FDR
    - 如果GMV在Bonferroni校正后仍显著 → 核心结论非常稳健
""")

print("=" * 70)
print("  模块05完成")
print("  下一步: python 06_simpsons_paradox.py")
print("=" * 70)
