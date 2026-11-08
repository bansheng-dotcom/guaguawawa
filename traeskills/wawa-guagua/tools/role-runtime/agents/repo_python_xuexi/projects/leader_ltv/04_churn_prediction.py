"""
=============================================================================
模块04: 团长流失预警 — 基于行为信号的早期预警
=============================================================================
跟项目四的用户流失预测不同,这里用的是"基于规则+统计阈值"的方法
(因为团长样本量小,ML不太适用)

预警信号:
    1. GMV连续3月下降>15%     → 🔴 高风险
    2. 活跃用户数持续减少       → 🟡 关注
    3. 月订单量骤降>30%        → 🔴 高风险
    4. 出现连续无订单月         → 🔴 极高风险

这些信号在团长实际流失前1-3个月就会出现.
=============================================================================
"""

import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块04: 团长流失预警")
print("=" * 60)
print()

monthly = pd.read_csv(f'{DATA_DIR}/leader_monthly.csv')
leaders = pd.read_csv(f'{DATA_DIR}/leader_summary.csv')

# ===========================================================================
# 为每个团长计算近期行为信号
# ===========================================================================

# 取每个团长最近3个月的数据
recent = monthly.groupby('leader_id').tail(3)

signals = []
for lid in monthly['leader_id'].unique():
    leader_data = monthly[monthly['leader_id'] == lid].sort_values('month_index')
    if len(leader_data) < 3:
        continue

    last_3 = leader_data.tail(3)
    prev_3 = leader_data.tail(6).head(3)

    # 信号1: GMV连续下降
    gmv_trend = last_3['monthly_gmv'].values
    is_gmv_declining = (gmv_trend[0] > gmv_trend[1] > gmv_trend[2]) if len(gmv_trend)==3 else False

    # 信号2: 最近3月GMV vs 之前3月
    gmv_last_avg = last_3['monthly_gmv'].mean()
    gmv_prev_avg = prev_3['monthly_gmv'].mean() if len(prev_3) > 0 else gmv_last_avg
    gmv_drop_pct = (gmv_prev_avg - gmv_last_avg) / max(gmv_prev_avg, 1) * 100

    # 信号3: 有无连续无订单月
    has_inactive_months = (last_3['monthly_gmv'] == 0).any()

    # 信号4: 活跃用户数下降
    users_trend = last_3['monthly_users'].values
    is_users_declining = (users_trend[0] > users_trend[1] > users_trend[2]) if len(users_trend)==3 else False

    # 综合风险评分
    risk_score = 0
    if is_gmv_declining: risk_score += 3
    if gmv_drop_pct > 15: risk_score += 3
    if has_inactive_months: risk_score += 4
    if is_users_declining: risk_score += 2

    leader_info = leaders[leaders['leader_id']==lid]
    actual_churn = leader_info['is_churned'].values[0] if len(leader_info) > 0 else 0

    signals.append({
        'leader_id': lid,
        'gmv_declining': is_gmv_declining,
        'gmv_drop_pct': round(gmv_drop_pct, 1),
        'has_inactive': has_inactive_months,
        'users_declining': is_users_declining,
        'risk_score': risk_score,
        'actual_churn': actual_churn,
    })

signals_df = pd.DataFrame(signals)

# ===========================================================================
# 预警分级
# ===========================================================================

signals_df['risk_level'] = pd.cut(signals_df['risk_score'],
    bins=[-1, 3, 7, 12],
    labels=['低风险','中风险','高风险'])

print("  预警信号统计:")
for level in ['低风险','中风险','高风险']:
    subset = signals_df[signals_df['risk_level'] == level]
    if len(subset) > 0:
        actual_churn_rate = subset['actual_churn'].mean() * 100
        print(f"    {level}: {len(subset)}人, 实际流失率{actual_churn_rate:.1f}%")

print()
print("  高危团长TOP10 (风险分≥7):")
top_risk = signals_df[signals_df['risk_score'] >= 7].head(10)
for _, row in top_risk.iterrows():
    print(f"    leader_{row['leader_id']}: 得分{row['risk_score']}  GMV降{row['gmv_drop_pct']:.0f}%  实际流失={'是' if row['actual_churn'] else '否'}")

# 验证: 高风险组实际流失率 vs 低风险组
high_risk = signals_df[signals_df['risk_level'] == '高风险']
low_risk = signals_df[signals_df['risk_level'] == '低风险']
if len(high_risk) > 0 and len(low_risk) > 0:
    print(f"\n  预警验证: 高风险组实际流失率={high_risk['actual_churn'].mean()*100:.1f}% vs 低风险组={low_risk['actual_churn'].mean()*100:.1f}%")

signals_df.to_csv(f'{DATA_DIR}/leader_churn_signals.csv', index=False, encoding='utf-8-sig')
print(f"\n[信号已保存] data/leader_churn_signals.csv")
print()
print("=" * 60)
print("  模块04完成")
print("=" * 60)
