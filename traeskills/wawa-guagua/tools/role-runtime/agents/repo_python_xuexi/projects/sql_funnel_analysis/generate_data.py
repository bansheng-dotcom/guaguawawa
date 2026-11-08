"""
=============================================================================
社区团购数据模型生成 — 美团优选(保定市)
=============================================================================
7张表模拟真实社区团购业务:
    group_leaders    团长
    users            用户
    products         商品
    orders           订单
    order_items      订单明细
    behavior_logs    用户行为日志(分享→点击→加购→下单)
    fulfillment      履约记录

用法: python generate_data.py  →  在 data/ 下生成7个CSV
=============================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 使用脚本自身所在目录 + /data 作为输出路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

np.random.seed(2024)

START_DATE = datetime(2025, 6, 1)
END_DATE = datetime(2025, 6, 30)  # 30天数据

# ===========================================================================
# 1. 团长表
# ===========================================================================

def create_group_leaders(n=200):
    communities = [f'community_{i}' for i in range(1, n+1)]
    names = [f'leader_{i}' for i in range(1, n+1)]
    city_tiers = np.random.choice(['tier_1_new','tier_3_5'], n, p=[0.4, 0.6])
    leader_density = np.random.choice(['high','mid','low'], n, p=[0.3, 0.4, 0.3])

    # 团长的历史表现参数(影响后续数据生成)
    base_traffic = np.random.lognormal(mean=4.5, sigma=0.6, size=n)  # 日均流量
    conversion_ability = np.random.beta(a=3, b=5, size=n)  # 转化能力(0-1)

    df = pd.DataFrame({
        'leader_id': range(1, n+1),
        'leader_name': names,
        'city_tier': city_tiers,
        'community_name': communities,
        'leader_density': leader_density,
        'join_date': [START_DATE - timedelta(days=np.random.randint(30, 365)) for _ in range(n)],
        'daily_traffic_base': np.round(base_traffic, 1),
        'conversion_ability': np.round(conversion_ability, 4),
        'status': np.random.choice(['active','active','active','paused'], n, p=[0.8, 0.1, 0.05, 0.05]),
    })
    df.to_csv(f'{DATA_DIR}/group_leaders.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] group_leaders: {len(df)}条')
    return df

# ===========================================================================
# 2. 用户表
# ===========================================================================

def create_users(leaders_df, n=30000):
    # 每个团长有不等数量的常客
    leader_traffic = leaders_df['daily_traffic_base'].values
    leader_weights = leader_traffic / leader_traffic.sum()

    assigned_leaders = np.random.choice(leaders_df['leader_id'].values, n, p=leader_weights)
    city_tiers = leaders_df.set_index('leader_id').loc[assigned_leaders, 'city_tier'].values

    df = pd.DataFrame({
        'user_id': range(1, n+1),
        'leader_id': assigned_leaders,
        'city_tier': city_tiers,
        'register_date': [START_DATE - timedelta(days=np.random.randint(1, 365)) for _ in range(n)],
        'user_type': np.random.choice(['new','regular','vip'], n, p=[0.35, 0.50, 0.15]),
        'age_group': np.random.choice(['18-25','26-35','36-45','46+'], n, p=[0.15, 0.30, 0.35, 0.20]),
    })
    df.to_csv(f'{DATA_DIR}/users.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] users: {len(df)}条')
    return df

# ===========================================================================
# 3. 商品表
# ===========================================================================

def create_products(n=800):
    categories = {
        'fresh_veg':    {'name': '蔬菜水果', 'weight': 0.25, 'price_range': (1, 15), 'shelf_life': 3, 'dist_range': (5, 30)},
        'fresh_meat':   {'name': '肉禽蛋奶', 'weight': 0.15, 'price_range': (8, 45), 'shelf_life': 3, 'dist_range': (5, 40)},
        'daily_use':    {'name': '日用百货', 'weight': 0.15, 'price_range': (3, 30), 'shelf_life': 365, 'dist_range': (10, 60)},
        'snacks':       {'name': '零食饮料', 'weight': 0.15, 'price_range': (2, 25), 'shelf_life': 180, 'dist_range': (10, 80)},
        'grain_oil':    {'name': '粮油调味', 'weight': 0.10, 'price_range': (5, 50), 'shelf_life': 365, 'dist_range': (10, 50)},
        'frozen':       {'name': '速冻食品', 'weight': 0.10, 'price_range': (5, 35), 'shelf_life': 180, 'dist_range': (10, 60)},
        'household':    {'name': '家清用品', 'weight': 0.10, 'price_range': (3, 25), 'shelf_life': 365, 'dist_range': (10, 80)},
    }

    rows = []
    product_id = 1
    for cat_key, cat_info in categories.items():
        n_cat = int(n * cat_info['weight'])
        for _ in range(n_cat):
            unit_price = np.round(np.random.uniform(*cat_info['price_range']), 2)
            rows.append({
                'product_id': product_id,
                'product_name': f'{cat_key}_item_{product_id}',
                'category': cat_key,
                'category_name': cat_info['name'],
                'unit_price': unit_price,
                'cost_price': np.round(unit_price * np.random.uniform(0.55, 0.80), 2),
                'shelf_life_days': cat_info['shelf_life'],
                'supplier_distance_km': np.random.randint(*cat_info['dist_range']),
                'is_perishable': 1 if 'fresh' in cat_key else 0,
                'is_hot_product': np.random.choice([0, 1], p=[0.7, 0.3]),
            })
            product_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(f'{DATA_DIR}/products.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] products: {len(df)}条')
    return df

# ===========================================================================
# 4. 行为日志表 (核心: 团长分享→点击→加购→下单)
# ===========================================================================

def create_behavior_logs(leaders_df, users_df, products_df, n_total=500000):
    """
    模拟社区团购用户行为漏斗:
        团长分享(impression) → 用户点击(click) → 加购物车(add_cart) → 下单(order)

    每个团长每天分享约10-20个商品到微信群
    一部分用户在群里看到后产生行为
    """
    logs = []
    days = (END_DATE - START_DATE).days

    # 预先计算每个团长的转化率参数
    leader_params = leaders_df.set_index('leader_id')

    for day_offset in range(days):
        current_date = START_DATE + timedelta(days=day_offset)

        # 当天活跃团长(80%活跃率)
        active_leaders = leaders_df[leaders_df['status'] == 'active'].sample(frac=0.85)

        for _, leader in active_leaders.iterrows():
            lid = leader['leader_id']
            traffic = int(leader['daily_traffic_base'] * np.random.uniform(0.5, 1.5))
            conv = leader['conversion_ability']

            # 该团长当天分享的商品
            n_shares = np.random.randint(8, 20)
            shared_products = np.random.choice(products_df['product_id'].values, n_shares, replace=False)

            for pid in shared_products:
                # 团长分享 → 一部分用户看到(impression)
                n_impressions = np.random.randint(5, max(6, traffic // n_shares + 5))
                impression_users = np.random.choice(users_df['user_id'].values, n_impressions)

                for uid in impression_users:
                    # Step 1: impression(曝光/分享)
                    logs.append({
                        'leader_id': lid, 'user_id': uid, 'product_id': pid,
                        'action': 'impression',
                        'action_time': current_date + timedelta(hours=np.random.randint(6, 22), minutes=np.random.randint(0, 60)),
                    })

                    # Step 2: click(有一定概率)
                    if np.random.random() < 0.35 * (1 + conv):
                        logs.append({
                            'leader_id': lid, 'user_id': uid, 'product_id': pid,
                            'action': 'click',
                            'action_time': current_date + timedelta(hours=np.random.randint(6, 22), minutes=np.random.randint(0, 60)),
                        })

                        # Step 3: add_cart(点击后有一定概率)
                        if np.random.random() < 0.30 * (1 + conv):
                            logs.append({
                                'leader_id': lid, 'user_id': uid, 'product_id': pid,
                                'action': 'add_cart',
                                'action_time': current_date + timedelta(hours=np.random.randint(6, 23), minutes=np.random.randint(0, 60)),
                            })

                            # Step 4: order(加购后有一定概率下单)
                            if np.random.random() < 0.45 * (1 + conv):
                                logs.append({
                                    'leader_id': lid, 'user_id': uid, 'product_id': pid,
                                    'action': 'order',
                                    'action_time': current_date + timedelta(hours=np.random.randint(7, 23), minutes=np.random.randint(0, 60)),
                                })

        if day_offset % 5 == 0:
            print(f'  生成行为日志中... day {day_offset+1}/{days}, 已累积{len(logs)}条')

    df = pd.DataFrame(logs)
    df = df.sort_values('action_time').reset_index(drop=True)
    df['log_id'] = range(1, len(df)+1)
    df = df[['log_id','leader_id','user_id','product_id','action','action_time']]
    df.to_csv(f'{DATA_DIR}/behavior_logs.csv', index=False, encoding='utf-8-sig')
    print(f'[OK] behavior_logs: {len(df)}条')
    return df

# ===========================================================================
# 5. 订单表 + 订单明细表
# ===========================================================================

def create_orders(behavior_logs_df, users_df, leaders_df, products_df):
    """
    基于行为日志中的order动作生成订单。
    每个order动作对应一个实际订单,但会合并同一用户同一天的行为。
    """
    # 提取所有order行为
    order_actions = behavior_logs_df[behavior_logs_df['action'] == 'order'].copy()

    # 按用户+日期聚合(模拟用户一次下单买多件)
    order_actions['order_date'] = order_actions['action_time'].dt.date

    # 为每个用户每天最多生成1-2个订单
    user_daily = order_actions.groupby(['user_id', 'order_date']).agg(
        n_items=('product_id', 'count'),
        leader_id=('leader_id', 'first'),
    ).reset_index()

    orders = []
    order_items = []
    order_id_counter = 1
    item_id_counter = 1
    fulfillment_records = []

    print(f'  生成订单... 共{len(user_daily)}个用户-日组合')

    product_prices = products_df.set_index('product_id')

    for _, row in user_daily.iterrows():
        uid = row['user_id']
        lid = row['leader_id']
        order_date = row['order_date']

        # 该用户这一天买了哪些品(从order actions中取)
        day_products = order_actions[
            (order_actions['user_id']==uid) &
            (order_actions['order_date']==order_date)
        ]['product_id'].values

        if len(day_products) == 0:
            continue

        # 用户可能分1-2单下(模拟追加购买)
        n_orders_today = np.random.choice([1, 2], p=[0.8, 0.2])
        np.random.shuffle(day_products)
        products_per_order = np.array_split(day_products, min(n_orders_today, len(day_products)))

        for order_products in products_per_order:
            if len(order_products) == 0:
                continue

            total_amount = 0
            item_count = 0

            for pid in order_products:
                if pid in product_prices.index:
                    price = product_prices.loc[pid, 'unit_price']
                    qty = np.random.choice([1, 1, 1, 2, 3], p=[0.5, 0.2, 0.1, 0.12, 0.08])
                    subtotal = np.round(price * qty, 2)
                    total_amount += subtotal
                    item_count += qty

                    order_items.append({
                        'order_id': order_id_counter,
                        'product_id': pid,
                        'quantity': qty,
                        'unit_price': price,
                        'subtotal': subtotal,
                    })
                    item_id_counter += 1

            if item_count == 0:
                continue

            # 判断是否首单
            user_reg = users_df[users_df['user_id']==uid]['register_date'].values
            is_first = 1 if (user_reg[0] and pd.Timestamp(order_date) - pd.Timestamp(user_reg[0]) <= timedelta(days=7)) else 0

            # 履约(T+1配送)
            delivery_date = pd.Timestamp(order_date) + timedelta(days=1)
            leader_row = leaders_df[leaders_df['leader_id']==lid]
            city_tier = leader_row['city_tier'].values[0] if len(leader_row)>0 else 'tier_3_5'
            density = leader_row['leader_density'].values[0] if len(leader_row)>0 else 'mid'

            # 履约距离: 团长密度越低,距离越远
            if density == 'high': dist = np.random.uniform(1, 4)
            elif density == 'mid': dist = np.random.uniform(3, 8)
            else: dist = np.random.uniform(6, 15)

            # 履约成本: 距离×件数×系数
            fulfill_cost = np.round(dist * item_count * 0.5 + np.random.uniform(0, 3), 2)

            # 损耗: 如果订单含生鲜品,有一定概率损耗
            item_pids = [oi['product_id'] for oi in order_items if oi['order_id']==order_id_counter]
            has_fresh = any(products_df[products_df['product_id']==p]['is_perishable'].values[0]==1
                           for p in item_pids if p in products_df['product_id'].values)

            if has_fresh and np.random.random() < 0.10:
                loss_amt = np.round(total_amount * np.random.uniform(0.01, 0.08), 2)
            else:
                loss_amt = 0.0

            fulfillment_records.append({
                'order_id': order_id_counter,
                'grid_warehouse_id': np.random.randint(1, 6),
                'delivery_distance_km': np.round(dist, 2),
                'delivery_date': delivery_date,
                'fulfillment_cost': fulfill_cost,
                'loss_amount': loss_amt,
                'status': np.random.choice(['completed','completed','completed','refund'], p=[0.88, 0.07, 0.03, 0.02]),
            })

            orders.append({
                'order_id': order_id_counter,
                'user_id': uid,
                'leader_id': lid,
                'order_date': order_date,
                'delivery_date': delivery_date,
                'total_amount': np.round(total_amount, 2),
                'item_count': item_count,
                'is_first_order': is_first,
            })

            order_id_counter += 1

    orders_df = pd.DataFrame(orders)
    items_df = pd.DataFrame(order_items)
    fulfill_df = pd.DataFrame(fulfillment_records)

    orders_df.to_csv(f'{DATA_DIR}/orders.csv', index=False, encoding='utf-8-sig')
    items_df.to_csv(f'{DATA_DIR}/order_items.csv', index=False, encoding='utf-8-sig')
    fulfill_df.to_csv(f'{DATA_DIR}/fulfillment.csv', index=False, encoding='utf-8-sig')

    print(f'[OK] orders: {len(orders_df)}条')
    print(f'[OK] order_items: {len(items_df)}条')
    print(f'[OK] fulfillment: {len(fulfill_df)}条')
    return orders_df, items_df, fulfill_df


# ===========================================================================
# 主入口
# ===========================================================================

if __name__ == '__main__':
    print('='*70)
    print('  美团优选社区团购数据模型生成')
    print('='*70)
    print()

    leaders_df = create_group_leaders(200)
    users_df = create_users(leaders_df, 30000)
    products_df = create_products(800)

    print()
    print('  生成行为日志(可能需要1-2分钟)...')
    behavior_df = create_behavior_logs(leaders_df, users_df, products_df, 500000)

    print()
    orders_df, items_df, fulfill_df = create_orders(behavior_df, users_df, leaders_df, products_df)

    print()
    print('='*70)
    print('  数据生成完毕!')
    print(f'  团长:{len(leaders_df)} | 用户:{len(users_df)} | 商品:{len(products_df)}')
    print(f'  订单:{len(orders_df)} | 明细:{len(items_df)} | 日志:{len(behavior_df)} | 履约:{len(fulfill_df)}')
    print('='*70)
