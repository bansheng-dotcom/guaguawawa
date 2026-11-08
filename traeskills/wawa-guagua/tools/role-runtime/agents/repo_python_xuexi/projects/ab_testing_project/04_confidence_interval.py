"""
=============================================================================
模块04: 置信区间 — 效果到底多大? 范围多少?
=============================================================================
p值告诉你"能不能信",置信区间告诉你"值不值得做"。

社区团购场景下的特殊考量:
    - 履约成本率即使CI下限只恶化0.5%,都可能吃掉GMV提升的利润
    - 生鲜损耗率的CI如果很宽(比如[-1%,+3%]),说明不确定性大,需要更大样本
    - 因为社区团购是薄利模式,对"效果精度"要求比电商更高

方法:
    1. 参数法(Delta Method) — 基于t分布
    2. Bootstrap(5000次) — 不依赖分布假设,做稳健性验证
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
print("  模块04: 置信区间分析 — 社区团购场景")
print("=" * 70)
print()

df = pd.read_csv('data/ab_test_data.csv')
control = df[df['group'] == 'control']
treatment = df[df['group'] == 'treatment']

ALPHA = 0.05
N_BOOTSTRAP = 5000

# ===========================================================================
# 参数法CI
# ===========================================================================

print("=" * 50)
print("  参数法95%置信区间(Lift)")
print("=" * 50)

def parametric_ci_lift(control_vals, treatment_vals, alpha=0.05):
    n_c, n_t = len(control_vals), len(treatment_vals)
    mean_c, mean_t = control_vals.mean(), treatment_vals.mean()
    se = np.sqrt(control_vals.var(ddof=1)/n_c + treatment_vals.var(ddof=1)/n_t)
    df_w = min(n_c-1, n_t-1)
    t_crit = stats.t.ppf(1 - alpha/2, df_w)
    diff = mean_t - mean_c
    ci_d_l = diff - t_crit * se
    ci_d_u = diff + t_crit * se
    ci_lift_l = (ci_d_l / mean_c) * 100
    ci_lift_u = (ci_d_u / mean_c) * 100
    return ci_lift_l, ci_lift_u

ci_results = {}

core_metrics = [
    ('gmv', '人均GMV'),
    ('items_per_order', '人均件数'),
    ('fulfillment_cost_rate', '履约成本率'),
    ('fresh_loss_rate', '生鲜损耗率'),
    ('return_rate', '退货率'),
    ('hot_product_gmv_share', '爆品GMV占比'),
]

print(f"  {'指标':<20} {'变化%':<10} {'95%CI':<26} {'CI宽度':<10} {'含0?':<8}")
print(f"  {'-'*76}")

for col, name in core_metrics:
    c_vals = control[col].values
    t_vals = treatment[col].values
    change = ((t_vals.mean()/c_vals.mean())-1)*100
    ci_l, ci_u = parametric_ci_lift(c_vals, t_vals, ALPHA)
    contains_zero = '是' if ci_l <= 0 <= ci_u else '否'

    ci_results[name] = {'change': change, 'ci_lower': ci_l, 'ci_upper': ci_u, 'contains_zero': contains_zero}
    print(f"  {name:<20} {change:<+10.2f} [{ci_l:+.2f}, {ci_u:+.2f}]      {ci_u-ci_l:<10.2f} {contains_zero:<8}")

print()

# ===========================================================================
# Bootstrap CI
# ===========================================================================

print("=" * 50)
print(f"  Bootstrap法({N_BOOTSTRAP}次)交叉验证")
print("=" * 50)

def bootstrap_ci_lift(control_vals, treatment_vals, n_bootstrap=5000, alpha=0.05):
    n_c, n_t = len(control_vals), len(treatment_vals)
    lifts = np.zeros(n_bootstrap)
    for i in range(n_bootstrap):
        c_s = np.random.choice(control_vals, size=n_c, replace=True)
        t_s = np.random.choice(treatment_vals, size=n_t, replace=True)
        lifts[i] = (t_s.mean()/c_s.mean() - 1) * 100
    ci_l = np.percentile(lifts, alpha/2*100)
    ci_u = np.percentile(lifts, (1-alpha/2)*100)
    return lifts, ci_l, ci_u

bootstrap_data = {}
gmv_boot = None

print(f"  {'指标':<20} {'参数法CI':<26} {'Bootstrap CI':<26} {'一致性':<8}")
print(f"  {'-'*82}")

for col, name in core_metrics:
    boot_lifts, ci_b_l, ci_b_u = bootstrap_ci_lift(control[col].values, treatment[col].values, N_BOOTSTRAP, ALPHA)
    bootstrap_data[name] = boot_lifts
    if col == 'gmv':
        gmv_boot = boot_lifts

    p_ci = f"[{ci_results[name]['ci_lower']:+.2f}, {ci_results[name]['ci_upper']:+.2f}]"
    b_ci = f"[{ci_b_l:+.2f}, {ci_b_u:+.2f}]"
    p_ex0 = ci_results[name]['contains_zero'] == '否'
    b_ex0 = not (ci_b_l <= 0 <= ci_b_u)
    consistent = '一致' if p_ex0 == b_ex0 else '需验证'
    print(f"  {name:<20} {p_ci:<26} {b_ci:<26} {consistent:<8}")

print()

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(2, 2, figsize=(18, 12))

# 图1: Forest Plot
ax1 = axes[0, 0]
metrics_list = list(ci_results.keys())
for i, (name, res) in enumerate(ci_results.items()):
    ax1.errorbar(res['change'], i, xerr=[[res['change']-res['ci_lower']], [res['ci_upper']-res['change']]],
                 fmt='o', color='#2C3E50', capsize=5, markersize=8, capthick=2)
    boot = bootstrap_data[name]
    ax1.errorbar(np.mean(boot), i+0.15,
                 xerr=[[np.mean(boot)-np.percentile(boot,2.5)], [np.percentile(boot,97.5)-np.mean(boot)]],
                 fmt='s', color='#E74C3C', capsize=5, markersize=6, capthick=2)

ax1.axvline(x=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
ax1.set_yticks(range(len(metrics_list)))
ax1.set_yticklabels(metrics_list)
ax1.set_xlabel('变化 (%)')
ax1.set_title('Forest Plot: 各指标变化及95%CI')
ax1.grid(True, alpha=0.3, axis='x')

# 图2: GMV Bootstrap分布
ax2 = axes[0, 1]
if gmv_boot is not None:
    ax2.hist(gmv_boot, bins=50, color='#3498DB', alpha=0.7, edgecolor='white')
    ax2.axvline(x=np.percentile(gmv_boot, 2.5), color='red', linestyle='--', label=f'2.5%: {np.percentile(gmv_boot,2.5):+.2f}%')
    ax2.axvline(x=np.percentile(gmv_boot, 97.5), color='red', linestyle='--', label=f'97.5%: {np.percentile(gmv_boot,97.5):+.2f}%')
    ax2.axvline(x=0, color='black', linewidth=1)
    ax2.set_xlabel('GMV变化(%)')
    ax2.set_ylabel('Bootstrap样本数')
    ax2.set_title(f'GMV变化Bootstrap分布({N_BOOTSTRAP}次)')
    ax2.legend()

# 图3: 绝对差异Forest Plot
ax3 = axes[1, 0]
for i, (col, name) in enumerate([
    ('gmv', 'GMV(元)'), ('items_per_order', '件数'),
    ('fulfillment_cost_rate', '履约成本率(%)'), ('fresh_loss_rate', '损耗率(%)'),
    ('return_rate', '退货率(%)'), ('hot_product_gmv_share', '爆品占比(%)')
]):
    diff = treatment[col].mean() - control[col].mean()
    se = np.sqrt(control[col].var(ddof=1)/len(control) + treatment[col].var(ddof=1)/len(treatment))
    ax3.errorbar(diff, i, xerr=[[diff-1.96*se], [1.96*se]], fmt='o', capsize=5, markersize=8, color='#2ECC71')
ax3.axvline(x=0, color='gray', linestyle='-', alpha=0.5)
ax3.set_yticks(range(6))
ax3.set_yticklabels(['GMV', '件数', '履约成本率', '损耗率', '退货率', '爆品占比'])
ax3.set_xlabel('绝对差异(实验组-对照组)')
ax3.set_title('绝对差异Forest Plot')
ax3.grid(True, alpha=0.3, axis='x')

# 图4: 样本量 vs CI精度
ax4 = axes[1, 1]
sample_sizes = [500, 1000, 2000, 5000, 10000, 20000]
ci_widths = []
for n in sample_sizes:
    s1 = control['gmv'].sample(min(n, len(control)), random_state=42)
    s2 = treatment['gmv'].sample(min(n, len(treatment)), random_state=42)
    se = np.sqrt(s1.var(ddof=1)/len(s1) + s2.var(ddof=1)/len(s2))
    ci_w = 2*1.96*se / s1.mean() * 100
    ci_widths.append(ci_w)

ax4.plot(sample_sizes, ci_widths, 'o-', color='#8E44AD', linewidth=2, markersize=8)
ax4.set_xlabel('每组样本量')
ax4.set_ylabel('95%CI宽度(lift%)')
ax4.set_title('样本量对CI精度的影响')
ax4.grid(True, alpha=0.3)

plt.suptitle('置信区间分析总览 — 美团优选今日爆品', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('data/confidence_interval_plots.png', dpi=150, bbox_inches='tight')
print("[图表已保存] data/confidence_interval_plots.png")
print()

# ===========================================================================
# 业务价值判断
# ===========================================================================

print("=" * 50)
print("  业务价值判断(社区团购 薄利模式)")
print("=" * 50)

# 社区团购毛利薄,对精度要求更高
GMV_THRESHOLD = 0.5   # 0.5%的GMV提升才有业务意义
COST_THRESHOLD = 0.3   # 履约成本/损耗率恶化不能超0.3%

print(f"  GMV实际重要阈值: {GMV_THRESHOLD}% (社区团购薄利,微小提升也值得做)")
print(f"  护栏恶化容忍上限: {COST_THRESHOLD}% (履约成本恶化超过此值则利润被吃掉)")
print()

for name, res in ci_results.items():
    change = res['change']
    ci_l, ci_u = res['ci_lower'], res['ci_upper']

    if name in ['人均GMV', '人均件数', '爆品GMV占比']:
        # 正向指标: 提升是好事
        if ci_l > GMV_THRESHOLD:
            verdict = '有价值——CI下限超阈值'
        elif ci_l > 0:
            verdict = '统计显著但效果小'
        elif res['contains_zero'] == '是':
            verdict = '不显著,需更多数据'
        else:
            verdict = 'CI排除0但接近0'
    else:
        # 护栏指标: 上升是坏事
        if ci_u < COST_THRESHOLD:
            verdict = '安全——恶化在容忍范围内'
        elif ci_l < 0:
            verdict = 'CI跨0,不确定性大'
        else:
            verdict = '需关注——可能存在恶化'

    print(f"  {name:<18} {change:+.2f}% [{ci_l:+.2f},{ci_u:+.2f}] → {verdict}")

print()
print("=" * 70)
print("  模块04完成")
print("  下一步: python 05_multiple_testing.py")
print("=" * 70)
