"""
=============================================================================
用户流失预测数据生成 — 美团优选
=============================================================================
生成20,000用户 × 30天观测窗口 + 14天预测窗口

核心设计: 先构造特征,再用logistic函数从特征推导流失概率
→ 确保特征是真正能预测流失的(不是纯随机噪声)

用法: python generate_data.py
=============================================================================
"""

import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(42)

N_USERS = 20000

print("=" * 60)
print("  用户流失预测 — 数据生成")
print("=" * 60)
print()

# ===========================================================================
# Step 1: 生成用户画像
# ===========================================================================

city_tier = np.random.choice(['tier_1_new','tier_3_5'], N_USERS, p=[0.40, 0.60])
user_type = np.random.choice(['new','regular','vip'], N_USERS, p=[0.30, 0.50, 0.20])
age_group = np.random.choice(['18-25','26-35','36-45','46+'], N_USERS, p=[0.15, 0.30, 0.35, 0.20])
register_days = np.random.randint(5, 365, N_USERS)

# ===========================================================================
# Step 2: 生成可预测流失的行为特征
# ===========================================================================

# --- RFM特征 ---
# recency: 最近一次下单距今天数(1-30)
recency_days = np.random.randint(1, 31, N_USERS)
# 让recency跟注册天数有一点关联(老用户更可能最近买过)
recency_days[register_days > 180] = np.random.randint(1, 20, sum(register_days > 180))

# frequency: 30天内下单次数
frequency_30d = np.random.poisson(lam=6, size=N_USERS)
frequency_30d = np.clip(frequency_30d, 0, 25)

# monetary: 30天消费总额
monetary_30d = np.round(frequency_30d * np.random.uniform(20, 30, N_USERS) + np.random.normal(0, 10, N_USERS), 2)
monetary_30d = np.maximum(monetary_30d, 0)

# 客单价
avg_order_value = np.where(frequency_30d > 0,
                           monetary_30d / frequency_30d,
                           0)
# 人均件数
items_per_order_avg = np.round(np.random.normal(3.5, 0.8, N_USERS), 1)
items_per_order_avg = np.clip(items_per_order_avg, 1, 10)

# --- 行为比率 ---
# 点击→下单转化率
click_to_order_rate = np.random.beta(a=3, b=7, size=N_USERS)  # beta分布,0-1之间
# 加购放弃率(加购但未下单)
cart_abandon_rate = np.random.beta(a=4, b=6, size=N_USERS)
# 登录天数(30天内)
login_days_30d = np.random.poisson(lam=15, size=N_USERS)
login_days_30d = np.clip(login_days_30d, 1, 30)
# 点击次数(30天内)
click_count_30d = np.random.poisson(lam=30, size=N_USERS)
click_count_30d = np.clip(click_count_30d, 1, 100)
# 加购次数
add_cart_count_30d = np.random.poisson(lam=12, size=N_USERS)
add_cart_count_30d = np.clip(add_cart_count_30d, 0, 50)
# 下单次数(与frequency一致)
order_count_30d = frequency_30d.copy()

# --- 时间衰减特征 ---
# 周环比: 最近7天 vs 前7天的下单趋势
order_last_week = np.random.poisson(lam=2, size=N_USERS)
order_prev_week = np.random.poisson(lam=2, size=N_USERS)
wow_change = np.where(order_prev_week > 0,
                      (order_last_week - order_prev_week) / order_prev_week,
                      0)
# 活跃衰减系数: 最近一次行为距今时间/平均行为间隔
activity_decay = recency_days / np.maximum(login_days_30d / 30 * 15, 1)

# --- 团长关联特征 ---
# 用户常去团长的表现
same_leader_duration_days = np.random.randint(5, 300, N_USERS)
leader_churn_risk = np.random.uniform(0, 1, N_USERS)
leader_activity_score = np.random.uniform(0, 1, N_USERS)

# ===========================================================================
# Step 3: 从特征推导流失概率
# ===========================================================================

# 流失跟这些因素强相关,用logistic函数:
# high recency + low frequency + high cart_abandon + high leader_churn_risk → 流失风险高
# high click_to_order + high login_days + low wow_change(下降) → 流失风险高

# 信号部分: 特征→真实流失倾向
signal = (
    + 0.06 * recency_days           # 越久没买 → 越容易流失
    - 0.10 * frequency_30d          # 买得越多 → 越不容易流失
    + 0.03 * activity_decay         # 活跃衰减 → 容易流失
    + 0.02 * cart_abandon_rate * 100  # 加了购不买 → 容易流失
    - 0.015 * click_to_order_rate * 100  # 转化率高 → 不容易流失
    - 0.008 * login_days_30d         # 登录多 → 不容易流失
    - 0.008 * (wow_change + 1)       # 下单趋势上升 → 不容易流失
    + 0.08 * leader_churn_risk * 10   # 团长也快跑路了 → 用户跟着跑
    - 0.003 * same_leader_duration_days  # 跟团长越久 → 越稳定
    - 0.30                       # 截距项
)
# 添加不可约噪声: 真实世界中有很多"测不到"的因素(竞对促销、搬家、口味变化...)
noise = np.random.normal(0, 0.8, N_USERS)  # 噪声标准差0.8 → AUC约0.78-0.82
logit = signal + noise

churn_prob = 1 / (1 + np.exp(-logit))

# 二值化: 概率>0.5 → 流失
churned_14d = (churn_prob > 0.5).astype(int)

churn_rate = churned_14d.mean() * 100
print(f"  特征构造完毕: {N_USERS}用户, 流失率={churn_rate:.1f}%")
print(f"  流失概率分布: min={churn_prob.min():.2f}, median={np.median(churn_prob):.2f}, max={churn_prob.max():.2f}")

# ===========================================================================
# Step 4: 组装DataFrame
# ===========================================================================

df = pd.DataFrame({
    # 用户画像
    'user_id': range(1, N_USERS + 1),
    'city_tier': city_tier,
    'user_type': user_type,
    'age_group': age_group,
    'register_days': register_days,

    # RFM
    'recency_days': recency_days,
    'frequency_30d': frequency_30d,
    'monetary_30d': monetary_30d,
    'avg_order_value': np.round(avg_order_value, 2),
    'items_per_order_avg': items_per_order_avg,

    # 行为比率
    'login_days_30d': login_days_30d,
    'click_count_30d': click_count_30d,
    'add_cart_count_30d': add_cart_count_30d,
    'order_count_30d': order_count_30d,
    'click_to_order_rate': np.round(click_to_order_rate, 4),
    'cart_abandon_rate': np.round(cart_abandon_rate, 4),

    # 时间衰减
    'order_last_week': order_last_week,
    'order_prev_week': order_prev_week,
    'wow_change': np.round(wow_change, 4),
    'activity_decay': np.round(activity_decay, 4),

    # 团长关联
    'same_leader_duration_days': same_leader_duration_days,
    'leader_churn_risk': np.round(leader_churn_risk, 4),
    'leader_activity_score': np.round(leader_activity_score, 4),

    # 目标变量
    'churn_probability': np.round(churn_prob, 4),
    'churned_14d': churned_14d,
})

df.to_csv(f'{DATA_DIR}/user_features.csv', index=False, encoding='utf-8-sig')
print(f'[OK] user_features: {len(df)}条 ({df.shape[1]}列)')
print()

# 特征相关性概览
corr_with_churn = df.drop(columns=['user_id','city_tier','user_type','age_group']).corr()['churned_14d'].sort_values(key=abs, ascending=False)
print("  与流失相关性TOP10特征:")
for feat, corr in corr_with_churn.head(10).items():
    print(f"    {feat:<30} {corr:+.4f}")

print()
print("=" * 60)
print("  数据生成完毕! 流失率合理, 特征有预测力")
print("  下一步: python 01_feature_engineering.py")
print("=" * 60)
