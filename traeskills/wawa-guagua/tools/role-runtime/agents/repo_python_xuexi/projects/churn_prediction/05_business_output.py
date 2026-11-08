"""
=============================================================================
模块05: 业务输出 — 高危用户名单 + 分级干预建议
=============================================================================
模型的价值不在AUC数字,而在"能帮运营做什么"。

输出:
    1. 流失概率TOP500用户名单(含特征快照)
    2. 用户分级: 高风险/中风险/低风险
    3. 各等级用户特征画像 + 针对性干预建议
    4. 预期干预ROI估算
=============================================================================
"""

import numpy as np
import pandas as pd
import os
import pickle

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块05: 业务输出 — 高危用户名单")
print("=" * 60)
print()

# 加载原始数据
df = pd.read_csv(f'{DATA_DIR}/user_features.csv')

# 加载模型
with open(f'{DATA_DIR}/best_model.pkl', 'rb') as f:
    best_model = pickle.load(f)

# 加载标准化器和特征
data = np.load(f'{DATA_DIR}/processed_data.npz')
with open(f'{DATA_DIR}/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

with open(f'{DATA_DIR}/feature_names.txt', 'r') as f:
    feature_names = [line.strip() for line in f]

# ===========================================================================
# 对全量用户预测流失概率
# ===========================================================================

# 重新构造全量特征(使用01模块的逻辑)
from sklearn.preprocessing import LabelEncoder

# One-hot
df_encoded = pd.get_dummies(df, columns=['city_tier', 'age_group'], prefix=['city','age'])
le = LabelEncoder()
df_encoded['user_type_encoded'] = le.fit_transform(df['user_type'])

# 构造跟01模块一样的衍生特征
df_encoded['rfm_score'] = ((30 - df['recency_days']) / 30 * 100 + df['frequency_30d'] / 25 * 100 + df['monetary_30d'] / df['monetary_30d'].max() * 100) / 3
df_encoded['login_to_click_rate'] = df['click_count_30d'] / df['login_days_30d'].clip(lower=1)
df_encoded['avg_clicks_per_day'] = df['click_count_30d'] / 30
df_encoded['super_user_score'] = (df['frequency_30d'] / 25) * df['click_to_order_rate']
df_encoded['recency_score'] = np.exp(-df['recency_days'] / 7)
df_encoded['frequency_score'] = 1 - np.exp(-df['frequency_30d'] / 5)
df_encoded['engagement_score'] = df_encoded['recency_score'] * df_encoded['frequency_score']
df_encoded['price_sensitivity'] = np.where(df['avg_order_value'] < 20, 1, np.where(df['avg_order_value'] < 28, 0, -1))
df_encoded['high_value_flag'] = (df['monetary_30d'] > df['monetary_30d'].quantile(0.75)).astype(int)
df['is_declining'] = (df['wow_change'] < -0.2).astype(int)
df_encoded['decline_severity'] = np.where(df['wow_change'] < 0, -df['wow_change'], 0)
df_encoded['high_risk_combo'] = ((df['recency_days'] > 20) & (df['wow_change'] < -0.1) & (df['leader_churn_risk'] > 0.5)).astype(int)

# 确保所有特征存在
for feat in feature_names:
    if feat not in df_encoded.columns:
        df_encoded[feat] = 0

X_full = df_encoded[feature_names].fillna(0)
X_full_scaled = scaler.transform(X_full)

# 预测
df['churn_prob'] = best_model.predict_proba(X_full_scaled)[:, 1]

# ===========================================================================
# 1. TOP500高危用户
# ===========================================================================

top500 = df.nlargest(500, 'churn_prob')[
    ['user_id', 'recency_days', 'frequency_30d', 'monetary_30d',
     'churn_prob', 'user_type', 'city_tier', 'wow_change', 'leader_churn_risk']
].copy()

top500['risk_level'] = pd.cut(top500['churn_prob'],
                                bins=[0, 0.4, 0.6, 0.8, 1.0],
                                labels=['低风险','中风险','高风险','极高风险'])

top500.to_csv(f'{DATA_DIR}/top500_churn_risk.csv', index=False, encoding='utf-8-sig')
print(f"[1] TOP500高危用户名单: data/top500_churn_risk.csv")
print(f"    流失概率范围: {top500['churn_prob'].min():.3f} ~ {top500['churn_prob'].max():.3f}")

# ===========================================================================
# 2. 用户分级 + 特征画像
# ===========================================================================

print()
print("[2] 用户分级画像")

df['risk_level'] = pd.cut(df['churn_prob'],
                           bins=[0, 0.3, 0.5, 0.7, 1.0],
                           labels=['低风险','中风险','高风险','极高风险'])

risk_profile = df.groupby('risk_level', observed=False).agg(
    user_count=('user_id', 'count'),
    avg_recency=('recency_days', 'mean'),
    avg_frequency=('frequency_30d', 'mean'),
    avg_monetary=('monetary_30d', 'mean'),
    avg_wow_change=('wow_change', 'mean'),
    pct_declining=('is_declining', 'mean'),
)

print(f"\n  {'风险等级':<10} {'用户数':<8} {'占比':<8} {'avg_recency':<12} {'avg_freq':<10} {'avg_monetary':<14} {'趋势降%':<10}")
print(f"  {'-'*72}")

for level, row in risk_profile.iterrows():
    pct = row['user_count'] / len(df) * 100
    print(f"  {level:<10} {row['user_count']:<8,} {pct:<8.1f}% {row['avg_recency']:<12.1f} {row['avg_frequency']:<10.1f} {row['avg_monetary']:<14.1f} {row['pct_declining']*100:<10.1f}%")

# ===========================================================================
# 3. 分级干预建议
# ===========================================================================

print()
print("[3] 分级干预建议")
print("""
  +------------+----------------+------------------------------------------+
  | 风险等级   | 预计人数       | 干预策略                                 |
  +------------+----------------+------------------------------------------+
  | 极高风险   | ~{n_very_high:}人       | 48h内Push+短信+优惠券(满20-5), 团长私聊   |
  | 高风险     | ~{n_high:}人       | 72h内Push+社群专属爆品推送                |
  | 中风险     | ~{n_mid:}人       | 周度优惠券包+个性化推荐, 不紧急干预        |
  | 低风险     | ~{n_low:}人       | 保持正常运营节奏                           |
  +------------+----------------+------------------------------------------+

  预期ROI:
    - 极高风险用户如果没有干预, 60-80%会在14天内流失
    - 满20-5优惠券成本: 5元/张
    - 挽留一个用户的价值: 月均消费~75元, 预期存活3个月 → LTV~225元
    - 如果挽留成功率30% → 极高风险用户挽留ROI = 225×30%/5 = 13.5倍
""".format(
    n_very_high=risk_profile.loc['极高风险','user_count'] if '极高风险' in risk_profile.index else 'N/A',
    n_high=risk_profile.loc['高风险','user_count'] if '高风险' in risk_profile.index else 'N/A',
    n_mid=risk_profile.loc['中风险','user_count'] if '中风险' in risk_profile.index else 'N/A',
    n_low=risk_profile.loc['低风险','user_count'] if '低风险' in risk_profile.index else 'N/A',
))

print()
print("=" * 60)
print("  [DONE] 全部模块运行完毕!")
print()
print("  你的简历可以这样写:")
print()
print("""  [用户流失预测模型 — 美团优选]

  - 从用户行为日志构造30+特征(RFM衍生/行为比率/时间衰减/团长关联)，
    预测14天内流失概率(AUC=XX, precision=XX)

  - 训练逻辑回归(基线)+随机森林，5折交叉验证评估稳定性；
    阈值调优后F1达XX，TOP20%用户捕获XX%真实流失

  - 基于SHAP+特征重要性解释模型(recency/frequency为Top2驱动因子)，
    输出高危流失用户TOP500分级名单+差异化干预策略(优惠券/Push/团长私聊)

  - 预期挽留ROI为13.5倍:挽留成功率30%×LTV225元/成本5元

  技术栈: Python(Pandas/scikit-learn/SHAP/Matplotlib)、特征工程、分类模型
""")
print("=" * 60)
