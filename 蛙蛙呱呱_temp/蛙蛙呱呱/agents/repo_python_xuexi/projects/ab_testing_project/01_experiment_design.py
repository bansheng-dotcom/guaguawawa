"""
=============================================================================
模块01: 实验设计 — 社区团购「今日爆品」A/B实验
=============================================================================
场景: 美团优选首页爆品坑位,运营手选 vs 算法推荐。
实验前需要回答:
    1. 每组要多少用户才能检出效果? (样本量)
    2. 实验要跑多久? (周期,要覆盖囤货周末效应)
    3. 用什么指标来评判? (北极星+护栏+探索)

社区团购 vs 普通电商的关键差异:
    - 客单价低(GMV ~25元 vs 电商45元) → 标准差占比更大 → 同等MDE需要更多样本
    - 用户行为有"周末囤货效应" → 实验必须覆盖完整周
    - 履约成本是命门 → 护栏指标必须纳入
=============================================================================
"""

import numpy as np
from scipy import stats
from statsmodels.stats.power import TTestIndPower
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 70)
print("  模块01: 实验设计 — 美团优选「今日爆品」")
print("=" * 70)
print()

# ===========================================================================
# 第一部分: 样本量计算
# ===========================================================================

ALPHA = 0.05
POWER = 0.80
MDE_RELATIVE = 0.02      # 检出2%的GMV变化
BASELINE_GMV = 25.0       # 社区团购客单价低,约25元
BASELINE_STD = 14.0       # 个体差异大(有人买一单,有人买一大堆)

print("[参数设定]")
print(f"  显著性水平(alpha): {ALPHA}")
print(f"  统计功效(Power):   {POWER}")
print(f"  最小可检测效应(MDE): {MDE_RELATIVE*100}%")
print(f"  基准GMV均值: {BASELINE_GMV:.1f} 元")
print(f"  基准GMV标准差: {BASELINE_STD:.1f} 元")
print()

mde_absolute = BASELINE_GMV * MDE_RELATIVE
cohens_d = mde_absolute / BASELINE_STD

print(f"  效应量(Cohen's d): {cohens_d:.4f} ({mde_absolute:.2f}元 / {BASELINE_STD:.1f}元)")
print(f"  注: 社区团购标准差/均值比例高(d偏小),所以样本量需求比电商大")
print()

power_analysis = TTestIndPower()
sample_size_per_group = power_analysis.solve_power(
    effect_size=cohens_d, alpha=ALPHA, power=POWER,
    ratio=1.0, alternative='two-sided'
)
sample_size_per_group = int(np.ceil(sample_size_per_group))

print(f"[样本量结果]")
print(f"  每组所需最小样本量: {sample_size_per_group:,}")
print(f"  总样本量:           {sample_size_per_group * 2:,}")
print()

# ===========================================================================
# 第二部分: MDE敏感性分析
# ===========================================================================

print("=" * 50)
print("  MDE vs 所需样本量 (给定 alpha=0.05, power=0.80)")
print("=" * 50)
print(f"  {'MDE(%)':<10} {'MDE(元)':<10} {'Cohen d':<10} {'每组样本量':<15}")
print(f"  {'-'*45}")

for mde_rel in [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]:
    mde_abs = BASELINE_GMV * mde_rel
    d = mde_abs / BASELINE_STD
    n = power_analysis.solve_power(effect_size=d, alpha=ALPHA, power=POWER, ratio=1.0, alternative='two-sided')
    print(f"  {mde_rel*100:<10.1f} {mde_abs:<10.2f} {d:<10.4f} {int(np.ceil(n)):<15,}")

print()

# 可视化
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax1 = axes[0]
mde_pcts = np.linspace(0.005, 0.10, 50)
sample_sizes = []
for mde_rel in mde_pcts:
    d = (BASELINE_GMV * mde_rel) / BASELINE_STD
    n = power_analysis.solve_power(effect_size=d, alpha=ALPHA, power=POWER, ratio=1.0, alternative='two-sided')
    sample_sizes.append(n)
ax1.plot(mde_pcts * 100, sample_sizes, 'b-', linewidth=2)
ax1.axvline(x=MDE_RELATIVE*100, color='r', linestyle='--', alpha=0.7, label=f'MDE={MDE_RELATIVE*100}%')
ax1.set_xlabel('MDE (%)')
ax1.set_ylabel('每组所需样本量')
ax1.set_title('MDE vs 所需样本量 (alpha=0.05, Power=0.80)')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2 = axes[1]
for n_label, n_size in [('n=5,000', 5000), ('n=10,000', 10000), ('n=20,000', 20000), ('n=50,000', 50000)]:
    effects = np.linspace(0.001, 0.15, 50)
    powers = [power_analysis.solve_power(effect_size=e, alpha=ALPHA, nobs1=n, ratio=1.0, alternative='two-sided')
              for e in effects]
    ax2.plot(np.array(effects)*BASELINE_GMV, powers, label=n_label, linewidth=2)
ax2.axhline(y=POWER, color='r', linestyle='--', alpha=0.7, label=f'Target Power={POWER}')
ax2.axvline(x=mde_absolute, color='g', linestyle='--', alpha=0.7, label=f'MDE={mde_absolute:.1f}元')
ax2.set_xlabel('绝对效应量(元)')
ax2.set_ylabel('统计功效(Power)')
ax2.set_title('不同样本量下的统计功效曲线')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('data/experiment_design_plots.png', dpi=150, bbox_inches='tight')
print("[图表已保存] data/experiment_design_plots.png")
print()

# ===========================================================================
# 第三部分: 实验周期估算
# ===========================================================================

print("=" * 50)
print("  实验周期估算")
print("=" * 50)

# 社区团购的日活逻辑
DAILY_UV = 8000            # 美团优选单城市日均DAU(中小城市)
HOME_PAGE_RATIO = 0.85     # 进入首页且看到爆品坑位的比例
EFFECTIVE_RATIO = 0.75     # 实际参与实验的比例
daily_effective = int(DAILY_UV * HOME_PAGE_RATIO * EFFECTIVE_RATIO)

total_needed = sample_size_per_group * 2
pure_days = int(np.ceil(total_needed / daily_effective))

# 社区团购的周末效应特别明显(用户周末囤货),必须覆盖完整周
MIN_CYCLE_WEEKS = 2
BEHAVIOR_WINDOW = 2  # 团长配送有T+1延迟,行为窗口2天
days_needed = max(pure_days, MIN_CYCLE_WEEKS * 7 + BEHAVIOR_WINDOW)

print(f"  单城市日均DAU: {DAILY_UV:,}")
print(f"  首页爆品曝光率: {HOME_PAGE_RATIO*100}%")
print(f"  有效实验流量比: {EFFECTIVE_RATIO*100}%")
print(f"  日均可用实验用户: {daily_effective:,}")
print(f"  总样本量需求: {total_needed:,}")
print(f"  纯流量积累天数: {pure_days} 天")
print(f"  建议实验周期: {days_needed} 天")
print(f"    (含{BEHAVIOR_WINDOW}天配送延迟窗口 + {MIN_CYCLE_WEEKS}周完整周期消除周末效应)")
print()

# ===========================================================================
# 第四部分: 指标体系
# ===========================================================================

print("=" * 50)
print("  评估指标体系(社区团购专属)")
print("=" * 50)
print("""
  实验目标: 评估算法个性化推荐是否优于城市运营手动选品

  +-- 北极星指标 --------------------------------------+
  |                                                    |
  |  1. 人均GMV         综合衡量推荐效果与变现能力       |
  |  2. 人均件数         社区团购核心——用户一次买几件    |
  |                                                    |
  +-- 护栏指标(绝对不能恶化)---------------------------+
  |                                                    |
  |  1. 履约成本率       命门——推了远距离供应商会爆     |
  |  2. 生鲜损耗率       推了高损耗品卖不完,次日烂掉     |
  |  3. 退货率           算法瞎推不合适的品会涨退货      |
  |                                                    |
  +-- 探索指标 ----------------------------------------+
  |                                                    |
  |  1. 爆品GMV贡献占比  这6-8个坑位贡献了多少GMV       |
  |  2. 首单转化率       新用户首次下单比例              |
  |                                                    |
  +----------------------------------------------------+

  社区团购 vs 普通电商 指标差异:
    电商关注"转化率+客单价", 团购更关注"件数+履约成本+损耗率"
    因为社区团购是"次日达+自提"模式,履约和损耗直接决定利润
""")

# ===========================================================================
# 总结
# ===========================================================================

print("=" * 70)
print("  实验设计总结")
print("=" * 70)
print(f"""
  | 参数                  | 数值                        |
  |-----------------------|-----------------------------|
  | 显著性水平(alpha)      | {ALPHA}                        |
  | 统计功效(Power)       | {POWER}                       |
  | 最小可检测效应(MDE)    | {MDE_RELATIVE*100}% ({mde_absolute:.1f}元)    |
  | 每组最小样本量         | {sample_size_per_group:,}                     |
  | 总样本量               | {sample_size_per_group*2:,}                     |
  | 建议实验周期           | {days_needed} 天 (覆盖周末囤货效应)     |
  | 分流比例               | 1:1 (运营手选 : 算法推荐)    |
  | 北极星指标             | 人均GMV + 人均件数            |
""")

print("=" * 70)
print("  模块01完成 — 实验设计就绪")
print("  下一步: python 02_aa_validation.py")
print("=" * 70)
