"""
=============================================================================
模块01: 特征工程 — 从原始字段构造30+预测特征
=============================================================================
特征工程是ML项目最重要的环节。模型好不好, 80%取决于特征。

本模块完成:
    1. 加载原始数据
    2. 构造衍生特征(RFM组合/行为比率平方/交叉特征/分箱)
    3. 处理分类变量(One-Hot编码)
    4. 特征标准化
    5. 训练集/测试集划分(时间序列安全划分)
=============================================================================
"""

import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

print("=" * 60)
print("  模块01: 特征工程")
print("=" * 60)
print()

# ===========================================================================
# 加载数据
# ===========================================================================

df = pd.read_csv(f'{DATA_DIR}/user_features.csv')
print(f"原始数据: {len(df)}条, {df.shape[1]}列")
print(f"流失率: {df['churned_14d'].mean()*100:.1f}%")

# ===========================================================================
# 构造衍生特征
# ===========================================================================

print("\n[构造衍生特征]")

# 1. RFM组合
df['rfm_score'] = (
    (30 - df['recency_days']) / 30 * 100 +   # R越小越好(转为正)
    df['frequency_30d'] / 25 * 100 +           # F越大越好
    df['monetary_30d'] / df['monetary_30d'].max() * 100  # M越大越好
) / 3
print("  + rfm_score (R+F+M综合评分)")

# 2. 行为比率增强
df['login_to_click_rate'] = df['click_count_30d'] / df['login_days_30d'].clip(lower=1)
df['avg_clicks_per_day'] = df['click_count_30d'] / 30
df['items_to_order_ratio'] = df['items_per_order_avg'] / df['avg_order_value'].clip(lower=1)

# 高频×高转化=超级用户
df['super_user_score'] = (df['frequency_30d'] / 25) * df['click_to_order_rate']
print("  + login_to_click_rate / avg_clicks_per_day / super_user_score")

# 3. 时间衰减加权分
df['recency_score'] = np.exp(-df['recency_days'] / 7)  # 指数衰减,半衰期7天
df['frequency_score'] = 1 - np.exp(-df['frequency_30d'] / 5)  # 频次的饱和曲线
df['engagement_score'] = df['recency_score'] * df['frequency_score']
print("  + recency_score / frequency_score / engagement_score (时间衰减)")

# 4. 价格敏感度
df['price_sensitivity'] = np.where(df['avg_order_value'] < 20, 1,  # 低价用户 → 价格敏感
                                  np.where(df['avg_order_value'] < 28, 0, -1))
df['high_value_flag'] = (df['monetary_30d'] > df['monetary_30d'].quantile(0.75)).astype(int)
print("  + price_sensitivity / high_value_flag")

# 5. 活跃下降特征
df['is_declining'] = (df['wow_change'] < -0.2).astype(int)
df['decline_severity'] = np.where(df['wow_change'] < 0, -df['wow_change'], 0)
print("  + is_declining / decline_severity")

# 6. 高危组合特征(交互)
df['high_risk_combo'] = (
    (df['recency_days'] > 20).astype(int) &
    (df['wow_change'] < -0.1).astype(int) &
    (df['leader_churn_risk'] > 0.5).astype(int)
).astype(int)
print("  + high_risk_combo (recency高 + 趋势降 + 团长不稳)")

# ===========================================================================
# 处理分类变量
# ===========================================================================

print("\n[处理分类变量]")

# Label Encoding (有序分类)
le = LabelEncoder()
df['user_type_encoded'] = le.fit_transform(df['user_type'])
# One-Hot Encoding (无序分类)
df = pd.get_dummies(df, columns=['city_tier', 'age_group'], prefix=['city','age'])
print(f"  city_tier → one-hot ({sum(df.columns.str.startswith('city_'))}列)")
print(f"  age_group → one-hot ({sum(df.columns.str.startswith('age_'))}列)")

# ===========================================================================
# 定义特征集
# ===========================================================================

FEATURE_COLS = [
    # RFM基础
    'recency_days', 'frequency_30d', 'monetary_30d',
    'avg_order_value', 'items_per_order_avg',
    # 行为比率
    'login_days_30d', 'click_count_30d', 'add_cart_count_30d',
    'order_count_30d', 'click_to_order_rate', 'cart_abandon_rate',
    # 时间衰减
    'order_last_week', 'order_prev_week', 'wow_change',
    'activity_decay',
    # 团长关联
    'same_leader_duration_days', 'leader_churn_risk', 'leader_activity_score',
    # 用户画像
    'register_days', 'user_type_encoded',
    # 衍生特征
    'rfm_score', 'login_to_click_rate', 'avg_clicks_per_day',
    'super_user_score', 'recency_score', 'frequency_score',
    'engagement_score', 'price_sensitivity', 'high_value_flag',
    'is_declining', 'decline_severity', 'high_risk_combo',
    # One-hot
    'city_tier_1_new', 'city_tier_3_5',
    'age_18-25', 'age_26-35', 'age_36-45', 'age_46+',
]

# 确保所有特征列存在
FEATURE_COLS = [c for c in FEATURE_COLS if c in df.columns]

TARGET_COL = 'churned_14d'

print(f"\n  总特征数: {len(FEATURE_COLS)}")
print(f"  目标变量: {TARGET_COL}")

# ===========================================================================
# 划分训练集/测试集
# ===========================================================================

X = df[FEATURE_COLS].copy()
y = df[TARGET_COL].copy()

# 分层抽样保持流失率一致
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

print(f"\n[数据集划分]")
print(f"  训练集: {len(X_train)}条 (流失率 {y_train.mean()*100:.1f}%)")
print(f"  测试集: {len(X_test)}条  (流失率 {y_test.mean()*100:.1f}%)")

# ===========================================================================
# 特征标准化
# ===========================================================================

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 保存处理后的数据
np.savez(f'{DATA_DIR}/processed_data.npz',
         X_train=X_train_scaled, X_test=X_test_scaled,
         y_train=y_train.values, y_test=y_test.values,
         feature_names=FEATURE_COLS)

# 保存scaler
import pickle
with open(f'{DATA_DIR}/scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# 保存特征名
with open(f'{DATA_DIR}/feature_names.txt', 'w') as f:
    for feat in FEATURE_COLS:
        f.write(feat + '\n')

print(f"\n[数据已保存] data/processed_data.npz")
print(f"[Scaler已保存] data/scaler.pkl")
print()
print("=" * 60)
print("  模块01完成 — 特征工程就绪")
print("  下一步: python 02_model_training.py")
print("=" * 60)
