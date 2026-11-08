"""
=============================================================================
美团优选经营数据生成 — 保定市12个月(2025.01-2025.12)
=============================================================================
生成数据:
    1. daily_metrics.csv    — 每日经营指标(365天)
    2. category_monthly.csv — 品类月度拆分(7品类×12月)
    3. leader_monthly.csv   — 团长分层月度拆分(3层×12月)
    4. city_monthly.csv     — 城市等级月度拆分(2等级×12月)

异常注入:
    - 7月: GMV环比下降12%(生鲜季节性淡季+高温导致履约成本上升)
    - 9月: 履约成本率异常上升(暴雨天气,配送受阻)
    - 11月: 大幅回升(双11促销+冬季囤货)

用法: python generate_data.py
=============================================================================
"""

import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(2024)

# ===========================================================================
# 1. 每日经营指标 (365天)
# ===========================================================================

def generate_daily_metrics():
    """生成每日级别的经营数据,含趋势+季节+异常"""
    dates = pd.date_range('2025-01-01', '2025-12-31', freq='D')
    n = len(dates)
    day_of_week = dates.dayofweek  # 0=Mon, 6=Sun
    month = dates.month

    # --- 基础趋势: 年环比增长~20%,从1月到12月 ---
    trend = np.linspace(1.0, 1.20, n)

    # --- 周内效应: 周五-周日是高峰(囤货),周一是低谷 ---
    weekend_boost = np.ones(n)
    weekend_boost[(day_of_week >= 4)] = np.random.uniform(1.25, 1.50, sum(day_of_week >= 4))  # 周五-周日
    weekend_boost[day_of_week == 0] = 0.75  # 周一低谷

    # --- 月度季节因子 ---
    monthly_season = {
        1:1.05, 2:0.85, 3:1.00, 4:1.00, 5:1.05, 6:1.05,
        7:0.88,  # 7月淡季(高温,生鲜需求下降)
        8:0.92, 9:0.95, 10:1.05, 11:1.20, 12:1.25  # Q4旺季
    }
    seasonal = np.array([monthly_season[m] for m in month])

    # --- 随机波动 ---
    noise = np.random.normal(1.0, 0.05, n)

    # --- 合成基础GMV ---
    base_gmv = 25000  # 日均GMV 2.5万元(保定单城)
    daily_gmv = base_gmv * trend * weekend_boost * seasonal * noise

    # --- 衍生指标 ---
    # 订单量: GMV/客单价, 客单价~22-28元
    avg_order_value = 25 + trend * 2  # 从25到27.4
    daily_orders = (daily_gmv / avg_order_value).astype(int)

    # 用户数: 每用户日均消费~22元
    daily_users = (daily_gmv / 22).astype(int)

    # 活跃团长数: 用户/50(每个团长服务约50人)
    daily_active_leaders = (daily_users / 50).astype(int)

    # 履约成本率: 基础8%, 跟距离和天气相关
    base_fulfill_rate = 8.0 + np.random.normal(0, 0.3, n)
    # 7-9月高温+暴雨 → 履约成本上升
    base_fulfill_rate[(month >= 7) & (month <= 9)] += 0.8
    base_fulfill_rate = np.clip(base_fulfill_rate, 6, 12)

    # 生鲜损耗率: 基础5%, 夏季升高
    base_loss_rate = 5.0 + np.random.normal(0, 0.2, n)
    base_loss_rate[(month >= 6) & (month <= 9)] += 1.2  # 夏季损耗高
    base_loss_rate[month == 11] -= 0.5  # 冬季损耗低
    base_loss_rate = np.clip(base_loss_rate, 3, 10)

    # 退货率: 基础2%
    return_rate = 2.0 + np.random.normal(0, 0.1, n)
    return_rate = np.clip(return_rate, 1, 4)

    # 人均件数: 3-4件
    items_per_user = 3.5 + np.random.normal(0, 0.15, n)
    items_per_user = np.clip(items_per_user, 2.5, 5)

    # 爆品贡献占比: 30-40%
    hot_product_share = 35 + np.random.normal(0, 1.5, n)
    hot_product_share = np.clip(hot_product_share, 25, 50)

    # --- 注入特殊异常 ---
    # 7月: 连续暴雨一周,GMV骤降
    storm_days = (dates >= '2025-07-15') & (dates <= '2025-07-21')
    daily_gmv[storm_days] *= 0.70
    base_fulfill_rate[storm_days] += 2.5  # 配送成本暴涨
    base_loss_rate[storm_days] += 1.5      # 损耗增加

    # 9月: 中秋前一周,GMV暴涨
    mid_autumn = (dates >= '2025-09-25') & (dates <= '2025-09-30')
    daily_gmv[mid_autumn] *= 1.45
    daily_orders[mid_autumn] = (daily_orders[mid_autumn] * 1.45).astype(int)
    daily_users[mid_autumn] = (daily_users[mid_autumn] * 1.3).astype(int)

    # 11月: 双11大促周,GMV暴涨但履约成本也涨
    double11 = (dates >= '2025-11-10') & (dates <= '2025-11-16')
    daily_gmv[double11] *= 1.55
    base_fulfill_rate[double11] += 1.5  # 爆单导致履约成本上升
    daily_orders[double11] = (daily_orders[double11] * 2.0).astype(int)

    # --- 组装DataFrame ---
    df = pd.DataFrame({
        'date': dates,
        'month': month,
        'day_of_week': day_of_week,
        'gmv': np.round(daily_gmv, 0).astype(int),
        'orders': daily_orders,
        'users': daily_users,
        'active_leaders': daily_active_leaders,
        'fulfillment_cost_rate': np.round(base_fulfill_rate, 2),
        'fresh_loss_rate': np.round(base_loss_rate, 2),
        'return_rate': np.round(return_rate, 2),
        'items_per_user': np.round(items_per_user, 2),
        'hot_product_share': np.round(hot_product_share, 2),
    })

    # 派生字段
    df['avg_order_value'] = np.round(df['gmv'] / df['orders'], 2)
    df['gmv_per_user'] = np.round(df['gmv'] / df['users'], 2)
    df['gmv_per_leader'] = np.round(df['gmv'] / df['active_leaders'], 2)
    df['fulfillment_cost'] = np.round(df['gmv'] * df['fulfillment_cost_rate'] / 100, 0).astype(int)
    df['loss_amount'] = np.round(df['gmv'] * df['fresh_loss_rate'] / 100, 0).astype(int)
    df['week_label'] = dates.strftime('%W').astype(int)  # 周数

    df.to_csv(f'{DATA_DIR}/daily_metrics.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] daily_metrics: {len(df)}条 (365天)')
    return df


# ===========================================================================
# 2. 品类月度拆分
# ===========================================================================

def generate_category_monthly(daily_df):
    """7个品类×12个月的拆分数据"""
    categories = ['蔬菜水果','肉禽蛋奶','日用百货','零食饮料','粮油调味','速冻食品','家清用品']
    # 各品类GMV占比
    weights = [0.28, 0.18, 0.14, 0.12, 0.10, 0.10, 0.08]

    rows = []
    for month in range(1, 13):
        month_data = daily_df[daily_df['month'] == month]
        month_gmv = month_data['gmv'].sum()
        month_orders = month_data['orders'].sum()

        for cat, w in zip(categories, weights):
            cat_gmv = month_gmv * w * np.random.uniform(0.85, 1.15)
            cat_orders = month_orders * w * np.random.uniform(0.85, 1.15)
            cat_loss = cat_gmv * (0.08 if '生' in cat or '肉' in cat else 0.02) * np.random.uniform(0.8, 1.2)

            rows.append({
                'month': month,
                'category': cat,
                'gmv': round(cat_gmv, 0),
                'orders': round(cat_orders, 0),
                'loss_rate': round(cat_loss / cat_gmv * 100, 2) if cat_gmv > 0 else 0,
            })

    df = pd.DataFrame(rows)
    df.to_csv(f'{DATA_DIR}/category_monthly.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] category_monthly: {len(df)}条 (7品类×12月)')
    return df


# ===========================================================================
# 3. 团长分层月度拆分
# ===========================================================================

def generate_leader_monthly(daily_df):
    """3个团长层级×12个月的拆分"""
    tiers = ['top20%团长','中部60%团长','尾部20%团长']
    weights = [0.45, 0.40, 0.15]  # GMV贡献比例: 头部贡献大

    rows = []
    for month in range(1, 13):
        month_data = daily_df[daily_df['month'] == month]
        month_gmv = month_data['gmv'].sum()
        month_leaders = month_data['active_leaders'].mean()

        for tier, w in zip(tiers, weights):
            rows.append({
                'month': month,
                'leader_tier': tier,
                'gmv': round(month_gmv * w, 0),
                'active_leaders': round(month_leaders * (0.2 if 'top' in tier else (0.6 if '中部' in tier else 0.2)), 0),
                'gmv_per_leader': round(month_gmv * w / max(1, month_leaders * (0.2 if 'top' in tier else 0.6 if '60%' in tier else 0.2)), 0),
            })

    df = pd.DataFrame(rows)
    df.to_csv(f'{DATA_DIR}/leader_monthly.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] leader_monthly: {len(df)}条 (3层×12月)')
    return df


# ===========================================================================
# 4. 城市等级月度拆分
# ===========================================================================

def generate_city_monthly(daily_df):
    """一线/新一线 vs 三五线 月度拆分"""
    rows = []
    for month in range(1, 13):
        month_data = daily_df[daily_df['month'] == month]
        for city, ratio in [('一线/新一线', 0.42), ('三五线', 0.58)]:
            rows.append({
                'month': month,
                'city_tier': city,
                'gmv': round(month_data['gmv'].sum() * ratio, 0),
                'orders': round(month_data['orders'].sum() * ratio, 0),
                'users': round(month_data['users'].sum() * ratio, 0),
                'avg_fulfill_cost_rate': round(month_data['fulfillment_cost_rate'].mean() * (1.0 if '一线' in city else 1.15), 2),
                'avg_loss_rate': round(month_data['fresh_loss_rate'].mean() * (1.0 if '一线' in city else 1.10), 2),
            })

    df = pd.DataFrame(rows)
    df.to_csv(f'{DATA_DIR}/city_monthly.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] city_monthly: {len(df)}条 (2城市×12月)')
    return df


# ===========================================================================
# 主入口
# ===========================================================================

if __name__ == '__main__':
    print('='*70)
    print('  美团优选(保定) 经营数据生成 — 2025.01-2025.12')
    print('='*70)
    print()

    daily = generate_daily_metrics()
    cat = generate_category_monthly(daily)
    leader = generate_leader_monthly(daily)
    city = generate_city_monthly(daily)

    print()
    print('='*70)
    print(f'  数据生成完毕! 文件位于: {DATA_DIR}/')
    print(f'  daily_metrics | category_monthly | leader_monthly | city_monthly')
    print('='*70)
