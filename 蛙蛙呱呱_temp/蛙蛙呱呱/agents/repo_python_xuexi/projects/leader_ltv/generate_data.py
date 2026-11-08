"""
=============================================================================
团长生命周期数据生成 — 美团优选 (2024.01-2025.12, 24个月)
=============================================================================
核心设计:
    - 500个团长,在不同月份注册
    - 每个团长有"存活时长"(部分在2025.12前流失,部分仍在活跃→删失)
    - 月度追踪: GMV/订单/用户数/是否活跃
    - 存活时长受: 城市等级/团长密度/初始GMV质量 影响

生存分析关键概念:
    删失(Censoring): 2025年12月仍在活跃的团长 → "至少活了这么久,但不知道还能活多久"
    事件(Event): 团长连续2个月无订单 → "流失"
=============================================================================
"""

import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(42)

N_LEADERS = 500
OBS_END = '2025-12-31'

print("=" * 60)
print("  团长生命周期数据生成 — 24个月")
print("=" * 60)
print()

# ===========================================================================
# Step 1: 生成团长基础信息
# ===========================================================================

city_tiers = np.random.choice(['tier_1_new','tier_3_5'], N_LEADERS, p=[0.4, 0.6])
densities = np.random.choice(['high','mid','low'], N_LEADERS, p=[0.3, 0.4, 0.3])

# 注册月份: 均匀分布在24个月
register_months = np.random.randint(1, 25, N_LEADERS)

# ===========================================================================
# Step 2: 生成存活时长 (Weibull分布)
# ===========================================================================

# Weibull参数: 尺度(scale)=中位存活, 形状(shape)>1→风险随时间增加
base_scale = 18.0  # 基础中位存活18个月
base_shape = 1.5   # 风险随时间递增(越久越容易流失)

# 不同特征对存活的影响
scale_mult = np.ones(N_LEADERS)
scale_mult[densities == 'high'] *= 0.75  # 高密度→竞争大→存活短
scale_mult[densities == 'mid'] *= 1.0
scale_mult[densities == 'low'] *= 1.20   # 低密度→独家→存活长
scale_mult[city_tiers == 'tier_1_new'] *= 1.10  # 一线消费力强→存活稍长
scale_mult[city_tiers == 'tier_3_5'] *= 0.95

# 团长个人能力(随机)
quality = np.random.uniform(0.6, 1.4, N_LEADERS)
scale_mult *= quality

# 生成真实存活月数(Weibull)
true_survival_months = np.random.weibull(base_shape, N_LEADERS) * (base_scale * scale_mult)

# 截断: 最短1个月, 最长36个月
true_survival_months = np.clip(true_survival_months, 1, 36)

print(f"  存活月数分布:")
print(f"    min={true_survival_months.min():.1f} | median={np.median(true_survival_months):.1f}")
print(f"    Q25={np.percentile(true_survival_months,25):.1f} | Q75={np.percentile(true_survival_months,75):.1f}")

# ===========================================================================
# Step 3: 逐月生成活动数据
# ===========================================================================

months = pd.date_range('2024-01-01', '2025-12-31', freq='MS')
n_months = len(months)

rows = []
for i in range(N_LEADERS):
    reg_month = register_months[i]  # 注册月份(1-24)
    survival = true_survival_months[i]
    city = city_tiers[i]
    density = densities[i]
    q = quality[i]

    # 初始GMV能力(团长质量+城市+密度)
    base_gmv = 8000  # 基础月GMV
    if city == 'tier_1_new': base_gmv *= 1.3
    if density == 'high': base_gmv *= 0.8  # 竞争激烈
    if density == 'low': base_gmv *= 1.2
    base_gmv *= q

    for m_idx in range(n_months):
        # 团长从注册月开始才有数据
        if m_idx + 1 < reg_month:
            continue

        months_active = m_idx + 1 - reg_month  # 已活跃月数

        # 判断是否还在活跃: months_active < true_survival
        is_active = 1 if months_active < survival else 0

        # 如果已经不活跃了,但还没到流失判定(有一两个月的缓冲)
        if months_active >= survival + 2:
            break  # 流失超过2个月就不再产生数据

        # GMV: 活跃期间有趋势(先增长后平稳),流失前骤降
        lifecycle_stage = months_active / max(survival, 1)
        if lifecycle_stage < 0.2:
            gmv_mult = 0.6 + 0.4 * (lifecycle_stage / 0.2)  # 爬坡期
        elif lifecycle_stage < 0.8:
            gmv_mult = 1.0 + np.random.normal(0, 0.08)  # 平稳期
        else:
            gmv_mult = 1.0 - 0.3 * ((lifecycle_stage - 0.8) / 0.2)  # 衰退期

        monthly_gmv = base_gmv * gmv_mult * np.random.uniform(0.85, 1.15)

        # 如果已流失,GMV=0
        if not is_active:
            monthly_gmv = 0

        rows.append({
            'leader_id': i + 1,
            'city_tier': city,
            'leader_density': density,
            'quality': round(q, 3),
            'register_month': int(reg_month),
            'year_month': months[m_idx].strftime('%Y-%m'),
            'month_index': m_idx + 1,
            'months_active': months_active,
            'is_active': is_active,
            'monthly_gmv': max(0, round(monthly_gmv, 0)),
            'monthly_orders': max(0, int(monthly_gmv / 25)) if is_active else 0,
            'monthly_users': max(0, int(monthly_gmv / 22)) if is_active else 0,
        })

df = pd.DataFrame(rows)

# 确定每个团长的最终状态
leader_summary = df.groupby('leader_id').agg(
    total_months=('is_active', 'sum'),
    last_month=('month_index', 'max'),
    register_month=('register_month', 'first'),
    city_tier=('city_tier', 'first'),
    leader_density=('leader_density', 'first'),
    quality=('quality', 'first'),
    total_gmv=('monthly_gmv', 'sum'),
).reset_index()

leader_summary['observed_months'] = leader_summary['last_month'] - leader_summary['register_month'] + 1
leader_summary['is_churned'] = (leader_summary['last_month'] < n_months).astype(int)

df.to_csv(f'{DATA_DIR}/leader_monthly.csv', index=False, encoding='utf-8-sig')
leader_summary.to_csv(f'{DATA_DIR}/leader_summary.csv', index=False, encoding='utf-8-sig')

# ===========================================================================
# Step 4: 生成用户LTV数据(用于模块05)
# ===========================================================================

n_users = 10000
# 获客渠道: leader_refer(团长拉新), organic(自然流量), promo(促销活动)
channels = np.random.choice(['leader_refer','organic','promo'], n_users, p=[0.45, 0.35, 0.20])
user_quality = np.random.uniform(0.5, 1.5, n_users)

# 不同渠道的用户质量不同(团长拉新的用户质量更高——团长筛选过)
quality_mult = np.ones(n_users)
quality_mult[channels == 'leader_refer'] = 1.15
quality_mult[channels == 'organic'] = 1.0
quality_mult[channels == 'promo'] = 0.80  # 促销来的用户质量较低

user_ltv_base = 150  # 基础LTV
user_ltv = user_ltv_base * quality_mult * user_quality
user_ltv = np.clip(user_ltv, 30, 600)

user_months = np.random.poisson(lam=8 * quality_mult, size=n_users)
user_months = np.clip(user_months, 1, 24)

user_monthly_gmv = np.random.uniform(15, 40, n_users) * quality_mult
user_monthly_gmv = np.clip(user_monthly_gmv, 5, 80)

users_df = pd.DataFrame({
    'user_id': range(1, n_users + 1),
    'channel': channels,
    'ltv': np.round(user_ltv, 2),
    'active_months': user_months,
    'avg_monthly_gmv': np.round(user_monthly_gmv, 2),
    'total_orders': np.random.poisson(lam=3 * user_months, size=n_users),
})

users_df.to_csv(f'{DATA_DIR}/user_ltv.csv', index=False, encoding='utf-8-sig')
print(f'[OK] leader_monthly: {len(df)}条 ({df["leader_id"].nunique()}团长 × {df["year_month"].nunique()}月)')
print(f'[OK] leader_summary: {len(leader_summary)}条')
print(f'[OK] user_ltv: {len(users_df)}条')

# 统计
churn_rate = leader_summary['is_churned'].mean() * 100
censored_rate = (1 - leader_summary['is_churned'].mean()) * 100
print(f'\n  团长流失率: {churn_rate:.1f}% | 删失率(仍活跃): {censored_rate:.1f}%')
print(f'  中位观察月数: {leader_summary["observed_months"].median():.1f}')
print()
print("=" * 60)
print("  数据生成完毕!")
print("  下一步: python 01_cohort_analysis.py")
print("=" * 60)
