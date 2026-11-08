"""
=============================================================================
模块02: 生存分析 — Kaplan-Meier曲线 + Cox比例风险
=============================================================================
核心方法:

    Kaplan-Meier估计:
        "一个团长能活过第N个月的概率是多少?"
        - 考虑删失(观测结束时仍在活跃的团长)
        - 每一步: 存活概率 = (期初人数 - 事件数) / 期初人数
        - 累积存活概率 = 每步存活概率连乘

    Cox比例风险模型:
        "什么因素影响团长的存活风险(hazard)?"
        - 城市等级? 团长密度? 初始GMV能力?
        - 输出: 风险比(Hazard Ratio)
            HR>1 → 这个因素增加流失风险
            HR<1 → 这个因素降低流失风险

    中位存活期: 存活概率降到50%的时间点

用法: python 02_survival_analysis.py
要求: pip install lifelines
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
print("  模块02: 生存分析 — K-M曲线 + Cox模型")
print("=" * 60)
print()

# 加载团长汇总数据
leaders = pd.read_csv(f'{DATA_DIR}/leader_summary.csv')

# 检查lifelines是否可用
try:
    from lifelines import KaplanMeierFitter, CoxPHFitter
    LIFELINES_OK = True
except ImportError:
    print("  [WARNING] lifelines未安装! pip install lifelines")
    print("  将使用简化版手动计算K-M\n")
    LIFELINES_OK = False

# ===========================================================================
# Kaplan-Meier估计
# ===========================================================================

# 准备生存数据: (duration, event_observed)
# duration = observed_months (从注册到流失 or 到观察结束)
# event = is_churned (1=流失, 0=删失-仍在活跃)
T = leaders['observed_months'].values  # 存活/观察时长
E = leaders['is_churned'].values       # 事件标记

print(f"  样本量: {len(leaders)}")
print(f"  流失事件: {E.sum()} ({E.mean()*100:.0f}%)")
print(f"  删失: {(1-E).sum()} ({(1-E).mean()*100:.0f}%)")
print()

if LIFELINES_OK:
    kmf = KaplanMeierFitter()
    kmf.fit(T, E, label='All Leaders')

    # 中位存活期
    median_survival = kmf.median_survival_time_
    print(f"  中位存活期: {median_survival:.1f} 个月")
    print(f"  12个月存活概率: {kmf.survival_function_at_times(12).values[0]*100:.1f}%")
    print(f"  24个月存活概率: {kmf.survival_function_at_times(24).values[0]*100:.1f}%")
else:
    # 手动K-M计算(简化版)
    # 按时间排序
    order = np.argsort(T)
    T_sorted = T[order]
    E_sorted = E[order]

    surv_prob = 1.0
    n_at_risk = len(T_sorted)
    surv_curve = [(0, 1.0)]

    i = 0
    while i < len(T_sorted):
        t = T_sorted[i]
        # 统计该时间点的事件数
        n_events = 0
        while i < len(T_sorted) and T_sorted[i] == t:
            n_events += E_sorted[i]
            i += 1
        # 更新存活概率
        if n_events > 0 and n_at_risk > 0:
            surv_prob *= (1 - n_events / n_at_risk)
        surv_curve.append((t, surv_prob))
        n_at_risk -= n_events

    surv_curve = np.array(surv_curve)
    print("  (使用手动K-M计算)")
    # 找中位存活
    median_idx = np.argmax(surv_curve[:, 1] < 0.5)
    if surv_curve[median_idx, 1] < 0.5:
        print(f"  中位存活期: {surv_curve[median_idx, 0]:.1f} 个月")
    print(f"  12个月存活概率: {surv_curve[surv_curve[:,0]>=12, 1].min()*100:.1f}%")

print()

# ===========================================================================
# 按城市等级/团长密度分层K-M
# ===========================================================================

print("=" * 40)
print("  分层K-M曲线")
print("=" * 40)

if LIFELINES_OK:
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # 图1: 按城市等级
    ax1 = axes[0]
    for city, label, color in [('tier_1_new','一线/新一线','#E74C3C'),('tier_3_5','三五线','#3498DB')]:
        mask = leaders['city_tier'] == city
        kmf_city = KaplanMeierFitter()
        kmf_city.fit(T[mask], E[mask], label=label)
        kmf_city.plot_survival_function(ax=ax1, color=color)
        med = kmf_city.median_survival_time_
        print(f"  {label}: 中位存活{med:.1f}月")
    ax1.set_title('K-M by City Tier', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Survival Probability')
    ax1.grid(True, alpha=0.3)

    # 图2: 按团长密度
    ax2 = axes[1]
    for dens, label, color in [('high','高密度','#E74C3C'),('mid','中密度','#F39C12'),('low','低密度','#2ECC71')]:
        mask = leaders['leader_density'] == dens
        kmf_d = KaplanMeierFitter()
        kmf_d.fit(T[mask], E[mask], label=label)
        kmf_d.plot_survival_function(ax=ax2, color=color)
        med = kmf_d.median_survival_time_
        print(f"  {label}: 中位存活{med:.1f}月")
    ax2.set_title('K-M by Leader Density', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # 图3: 按团长质量(quality)分位数
    ax3 = axes[1]  # placeholder
    ax3 = axes[2]
    leaders['quality_group'] = pd.qcut(leaders['quality'], 3, labels=['低质量','中等','高质量'])
    for qg, color in [('高质量','#2ECC71'),('中等','#F39C12'),('低质量','#E74C3C')]:
        mask = leaders['quality_group'] == qg
        kmf_q = KaplanMeierFitter()
        kmf_q.fit(T[mask], E[mask], label=qg)
        kmf_q.plot_survival_function(ax=ax3, color=color)
        med = kmf_q.median_survival_time_
        print(f"  {qg}: 中位存活{med:.1f}月")
    ax3.set_title('K-M by Quality', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3)

    plt.suptitle('团长生存分析 — Kaplan-Meier曲线', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{DATA_DIR}/survival_km.png', dpi=150, bbox_inches='tight')
    print(f'\n[图表已保存] data/survival_km.png')

# ===========================================================================
# Cox比例风险模型
# ===========================================================================

print()
print("=" * 40)
print("  Cox比例风险模型")
print("=" * 40)

if LIFELINES_OK:
    # 准备特征
    cox_data = leaders[['observed_months','is_churned','city_tier','leader_density','quality']].copy()
    cox_data['is_tier1'] = (cox_data['city_tier'] == 'tier_1_new').astype(int)
    cox_data['is_high_density'] = (cox_data['leader_density'] == 'high').astype(int)
    cox_data['is_low_density'] = (cox_data['leader_density'] == 'low').astype(int)

    cph = CoxPHFitter()
    cph.fit(
        cox_data[['observed_months','is_churned','is_tier1','is_high_density','is_low_density','quality']],
        duration_col='observed_months',
        event_col='is_churned',
    )

    print()
    print(cph.summary[['exp(coef)','p']].round(4))
    print()
    print("  解读:")
    for _, row in cph.summary.iterrows():
        hr = row['exp(coef)']
        p = row['p']
        name = row.name
        if p < 0.05:
            if hr > 1:
                print(f"    {name}: HR={hr:.2f} (>1) → 增加流失风险 {((hr-1)*100):.0f}%")
            else:
                print(f"    {name}: HR={hr:.2f} (<1) → 降低流失风险 {((1-hr)*100):.0f}%")
        else:
            print(f"    {name}: HR={hr:.2f} (p={p:.3f} → 不显著)")
else:
    print("  (需要lifelines库,跳过Cox回归)")

print()
print("=" * 60)
print("  模块02完成")
print("  下一步: python 03_ltv_modeling.py")
print("=" * 60)
