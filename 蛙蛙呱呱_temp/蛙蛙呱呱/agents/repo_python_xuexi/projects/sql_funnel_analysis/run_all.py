"""
=============================================================================
美团优选 SQL分析全流程 — 在SQLite上执行所有分析
=============================================================================
用法: python run_all.py
前置: 先运行 python generate_data.py 生成数据

包含:
    01 数据探索        — 表结构、字段、基础聚合
    02 漏斗分析        — 团长分享→点击→加购→下单→自提 5步漏斗
    03 用户分群(RFM)   — 最近购买/频次/金额 三级分层
    04 留存复购        — 次日/7日/30日复购率
    05 团长归因        — 首次/末次触点归因、GMV贡献排名
=============================================================================
"""

import sqlite3
import pandas as pd
import numpy as np
import os

DB_PATH = 'data/community_groupbuy.db'
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# ===========================================================================
# 加载CSV到SQLite
# ===========================================================================

def load_to_sqlite():
    """将所有CSV导入SQLite"""
    conn = sqlite3.connect(DB_PATH)
    print("正在导入数据到SQLite...")

    tables = {
        'group_leaders': 'group_leaders.csv',
        'users': 'users.csv',
        'products': 'products.csv',
        'orders': 'orders.csv',
        'order_items': 'order_items.csv',
        'behavior_logs': 'behavior_logs.csv',
        'fulfillment': 'fulfillment.csv',
    }

    for table_name, csv_file in tables.items():
        path = os.path.join(DATA_DIR, csv_file)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f'  [OK] {table_name}: {len(df):,}行')

    conn.commit()
    print(f'  数据库: {DB_PATH}\n')
    return conn


# ===========================================================================
# 01 数据探索
# ===========================================================================

def analysis_01_exploration(conn):
    print('='*60)
    print('  01 数据探索')
    print('='*60)

    queries = {
        '各表行数': '''
            SELECT 'group_leaders' as table_name, COUNT(*) as rows FROM group_leaders
            UNION ALL SELECT 'users', COUNT(*) FROM users
            UNION ALL SELECT 'products', COUNT(*) FROM products
            UNION ALL SELECT 'orders', COUNT(*) FROM orders
            UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
            UNION ALL SELECT 'behavior_logs', COUNT(*) FROM behavior_logs
            UNION ALL SELECT 'fulfillment', COUNT(*) FROM fulfillment
        ''',
        '各品类商品数及均价': '''
            SELECT category_name, COUNT(*) as product_count,
                   ROUND(AVG(unit_price),2) as avg_price,
                   ROUND(AVG(cost_price),2) as avg_cost,
                   ROUND((AVG(unit_price)-AVG(cost_price))/AVG(unit_price)*100,1) as margin_pct
            FROM products GROUP BY category_name ORDER BY product_count DESC
        ''',
        '城市等级用户分布': '''
            SELECT city_tier,
                   CASE WHEN city_tier='tier_1_new' THEN '一线/新一线' ELSE '三五线' END as city_label,
                   COUNT(*) as user_count, ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(),1) as pct
            FROM users GROUP BY city_tier
        ''',
        '行为漏斗各环节总量': '''
            SELECT action, COUNT(*) as cnt,
                   COUNT(DISTINCT user_id) as unique_users
            FROM behavior_logs
            GROUP BY action ORDER BY
              CASE action WHEN 'impression' THEN 1 WHEN 'click' THEN 2
                          WHEN 'add_cart' THEN 3 WHEN 'order' THEN 4 END
        ''',
    }

    for name, sql in queries.items():
        print(f'\n[{name}]')
        df = pd.read_sql(sql, conn)
        print(df.to_string(index=False))

    return


# ===========================================================================
# 02 漏斗分析
# ===========================================================================

def analysis_02_funnel(conn):
    print('\n' + '='*60)
    print('  02 漏斗分析: 团长分享→点击→加购→下单→自提')
    print('='*60)

    # 计算每个用户在实验周期内经历的行为阶段
    funnel_sql = '''
        WITH user_funnel AS (
            SELECT
                user_id,
                MAX(CASE WHEN action='impression' THEN 1 ELSE 0 END) as has_impression,
                MAX(CASE WHEN action='click' THEN 1 ELSE 0 END) as has_click,
                MAX(CASE WHEN action='add_cart' THEN 1 ELSE 0 END) as has_add_cart,
                MAX(CASE WHEN action='order' THEN 1 ELSE 0 END) as has_order
            FROM behavior_logs
            GROUP BY user_id
        )
        SELECT
            COUNT(*) as total_users,
            SUM(has_impression) as impression_users,
            SUM(has_click) as click_users,
            SUM(has_add_cart) as add_cart_users,
            SUM(has_order) as order_users
        FROM user_funnel
    '''
    df = pd.read_sql(funnel_sql, conn)
    row = df.iloc[0]

    stages = ['impression_users','click_users','add_cart_users','order_users']
    stage_names = ['团长分享曝光','用户点击','加购物车','下单']

    print(f'\n  {"阶段":<16} {"用户数":<10} {"环节转化率":<14} {"整体转化率":<14}')
    print(f'  {"-"*54}')

    prev = row['total_users']
    first = row['impression_users']

    for i, (stage, name) in enumerate(zip(stages, stage_names)):
        val = int(row[stage]) if pd.notna(row[stage]) else 0
        step_rate = f'{val/prev*100:.2f}%' if prev > 0 else 'N/A'
        overall_rate = f'{val/first*100:.2f}%' if first > 0 else 'N/A'
        print(f'  {name:<16} {val:<10,} {step_rate:<14} {overall_rate:<14}')
        prev = val

    # 按城市等级拆分漏斗
    funnel_city_sql = '''
        WITH user_funnel_city AS (
            SELECT
                b.user_id,
                u.city_tier,
                MAX(CASE WHEN b.action='impression' THEN 1 ELSE 0 END) as has_impression,
                MAX(CASE WHEN b.action='click' THEN 1 ELSE 0 END) as has_click,
                MAX(CASE WHEN b.action='add_cart' THEN 1 ELSE 0 END) as has_add_cart,
                MAX(CASE WHEN b.action='order' THEN 1 ELSE 0 END) as has_order
            FROM behavior_logs b
            JOIN users u ON b.user_id = u.user_id
            GROUP BY b.user_id, u.city_tier
        )
        SELECT
            CASE WHEN city_tier='tier_1_new' THEN '一线/新一线' ELSE '三五线' END as city,
            COUNT(*) as users,
            ROUND(SUM(has_click)*100.0/SUM(has_impression),2) as impression_to_click,
            ROUND(SUM(has_add_cart)*100.0/SUM(has_click),2) as click_to_cart,
            ROUND(SUM(has_order)*100.0/SUM(has_add_cart),2) as cart_to_order,
            ROUND(SUM(has_order)*100.0/SUM(has_impression),2) as overall_conversion
        FROM user_funnel_city
        GROUP BY city_tier
    '''

    print(f'\n  [按城市等级拆分]')
    df_city = pd.read_sql(funnel_city_sql, conn)
    print(df_city.to_string(index=False))

    return


# ===========================================================================
# 03 用户分群(RFM)
# ===========================================================================

def analysis_03_rfm(conn):
    print('\n' + '='*60)
    print('  03 用户分群: 团购RFM模型')
    print('='*60)

    rfm_sql = '''
        WITH user_rfm AS (
            SELECT
                o.user_id,
                julianday('2025-07-01') - julianday(MAX(o.order_date)) as recency_days,
                COUNT(DISTINCT o.order_id) as frequency,
                ROUND(SUM(o.total_amount), 2) as monetary,
                COUNT(DISTINCT o.order_date) as active_days
            FROM orders o
            GROUP BY o.user_id
        ),
        rfm_scored AS (
            SELECT user_id, recency_days, frequency, monetary, active_days,
                -- R: 最近购买天数(越小越好)
                CASE WHEN recency_days <= 3 THEN 4
                     WHEN recency_days <= 7 THEN 3
                     WHEN recency_days <= 14 THEN 2
                     ELSE 1 END as r_score,
                -- F: 订单频次(越大越好)
                CASE WHEN frequency >= 8 THEN 4
                     WHEN frequency >= 4 THEN 3
                     WHEN frequency >= 2 THEN 2
                     ELSE 1 END as f_score,
                -- M: 消费金额(越大越好)
                CASE WHEN monetary >= 200 THEN 4
                     WHEN monetary >= 100 THEN 3
                     WHEN monetary >= 50 THEN 2
                     ELSE 1 END as m_score
            FROM user_rfm
        ),
        rfm_segments AS (
            SELECT user_id, recency_days, frequency, monetary, active_days,
                   r_score, f_score, m_score,
                   (r_score + f_score + m_score) as rfm_total,
                   CASE
                       WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN '高价值用户'
                       WHEN r_score >= 3 AND f_score >= 2 THEN '活跃用户'
                       WHEN r_score >= 2 AND f_score >= 2 THEN '潜力用户'
                       WHEN r_score <= 2 AND f_score <= 2 THEN '流失风险'
                       WHEN f_score >= 3 THEN '高频率低价值'
                       ELSE '低价值用户'
                   END as segment
            FROM rfm_scored
        )
        SELECT segment,
               COUNT(*) as user_count,
               ROUND(AVG(recency_days),1) as avg_recency,
               ROUND(AVG(frequency),1) as avg_frequency,
               ROUND(AVG(monetary),2) as avg_monetary
        FROM rfm_segments
        GROUP BY segment
        ORDER BY AVG(rfm_total) DESC
    '''

    df = pd.read_sql(rfm_sql, conn)
    print('\n[RFM用户分层结果]')
    print(df.to_string(index=False))

    # 保存RFM结果供可视化
    rfm_detail_sql = '''
        WITH user_rfm AS (
            SELECT o.user_id,
                   julianday('2025-07-01') - julianday(MAX(o.order_date)) as recency_days,
                   COUNT(DISTINCT o.order_id) as frequency,
                   ROUND(SUM(o.total_amount),2) as monetary
            FROM orders o GROUP BY o.user_id
        )
        SELECT user_id, recency_days, frequency, monetary FROM user_rfm
    '''
    rfm_detail = pd.read_sql(rfm_detail_sql, conn)
    rfm_detail.to_csv(f'{DATA_DIR}/rfm_detail.csv', index=False, encoding='utf-8-sig')
    print(f'\n[RFM明细已保存] data/rfm_detail.csv ({len(rfm_detail)}条)')

    return


# ===========================================================================
# 04 留存复购
# ===========================================================================

def analysis_04_retention(conn):
    print('\n' + '='*60)
    print('  04 留存复购分析')
    print('='*60)

    # 次日复购率: 用户第一次下单后,第二天是否再次下单
    retention_sql = '''
        WITH first_orders AS (
            SELECT user_id, MIN(order_date) as first_order_date
            FROM orders GROUP BY user_id
        ),
        repurchase AS (
            SELECT f.user_id, f.first_order_date,
                   COUNT(DISTINCT o.order_id) as day1_orders,
                   julianday(o.order_date) - julianday(f.first_order_date) as day_diff
            FROM first_orders f
            LEFT JOIN orders o ON f.user_id = o.user_id
                AND o.order_date > f.first_order_date
            GROUP BY f.user_id
        )
        SELECT
            COUNT(*) as total_first_time_users,
            SUM(CASE WHEN day1_orders >= 1 THEN 1 ELSE 0 END) as day1_repurchase,
            ROUND(SUM(CASE WHEN day1_orders >= 1 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) as day1_repurchase_rate,
            ROUND(AVG(day1_orders),2) as avg_repurchase_orders
        FROM repurchase
    '''
    df_ret = pd.read_sql(retention_sql, conn)
    print('\n[次日复购率]')
    print(df_ret.to_string(index=False))

    # 按城市等级的复购率
    retention_city_sql = '''
        WITH first_orders AS (
            SELECT o.user_id, MIN(o.order_date) as first_order_date, u.city_tier
            FROM orders o JOIN users u ON o.user_id = u.user_id
            GROUP BY o.user_id
        ),
        repurchase AS (
            SELECT f.user_id, f.city_tier, f.first_order_date,
                   COUNT(DISTINCT o2.order_id) as repurchase_count
            FROM first_orders f
            LEFT JOIN orders o2 ON f.user_id = o2.user_id
                AND o2.order_date > f.first_order_date
                AND julianday(o2.order_date) - julianday(f.first_order_date) <= 7
            GROUP BY f.user_id
        )
        SELECT
            CASE WHEN city_tier='tier_1_new' THEN '一线/新一线' ELSE '三五线' END as city,
            COUNT(*) as users,
            SUM(CASE WHEN repurchase_count > 0 THEN 1 ELSE 0 END) as repurchase_users,
            ROUND(SUM(CASE WHEN repurchase_count > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) as repurchase_rate_7d
        FROM repurchase
        GROUP BY city_tier
    '''
    df_ret_city = pd.read_sql(retention_city_sql, conn)
    print('\n[7日复购率 — 按城市等级]')
    print(df_ret_city.to_string(index=False))

    # 按用户类型
    retention_type_sql = '''
        WITH first_orders AS (
            SELECT o.user_id, MIN(o.order_date) as first_order_date, u.user_type
            FROM orders o JOIN users u ON o.user_id = u.user_id
            GROUP BY o.user_id
        ),
        repurchase AS (
            SELECT f.user_id, f.user_type,
                   COUNT(DISTINCT o2.order_id) as repurchase_count
            FROM first_orders f
            LEFT JOIN orders o2 ON f.user_id = o2.user_id
                AND o2.order_date > f.first_order_date
                AND julianday(o2.order_date) - julianday(f.first_order_date) <= 30
            GROUP BY f.user_id
        )
        SELECT user_type,
               COUNT(*) as users,
               ROUND(SUM(CASE WHEN repurchase_count>0 THEN 1 ELSE 0 END)*100.0/COUNT(*),2) as repurchase_rate_30d,
               ROUND(AVG(repurchase_count),2) as avg_repurchase_orders
        FROM repurchase
        GROUP BY user_type
    '''
    df_ret_type = pd.read_sql(retention_type_sql, conn)
    print('\n[30日复购率 — 按用户类型]')
    print(df_ret_type.to_string(index=False))

    return


# ===========================================================================
# 05 团长归因 & GMV贡献
# ===========================================================================

def analysis_05_attribution(conn):
    print('\n' + '='*60)
    print('  05 团长归因与GMV贡献分析')
    print('='*60)

    # 首次触点归因: 用户首次下单的团长获得"获客归因"
    first_touch_sql = '''
        WITH first_order AS (
            SELECT user_id, MIN(order_date) as first_date
            FROM orders GROUP BY user_id
        ),
        first_touch AS (
            SELECT o.leader_id, COUNT(DISTINCT o.user_id) as acquired_users,
                   ROUND(SUM(o.total_amount),2) as attributed_gmv
            FROM orders o
            JOIN first_order f ON o.user_id = f.user_id AND o.order_date = f.first_date
            GROUP BY o.leader_id
        )
        SELECT ft.*, gl.leader_name, gl.city_tier, gl.leader_density,
               ROUND(ft.attributed_gmv, 2) as gmv
        FROM first_touch ft
        JOIN group_leaders gl ON ft.leader_id = gl.leader_id
        ORDER BY ft.attributed_gmv DESC
        LIMIT 15
    '''
    df_ft = pd.read_sql(first_touch_sql, conn)
    print('\n[首次触点归因 TOP15团长]')
    print(df_ft.to_string(index=False))

    # 末次触点归因: 用户最近一次下单的团长获得"激活归因"
    last_touch_sql = '''
        WITH last_order AS (
            SELECT user_id, MAX(order_date) as last_date
            FROM orders GROUP BY user_id
        ),
        last_touch AS (
            SELECT o.leader_id, COUNT(DISTINCT o.user_id) as retained_users,
                   ROUND(SUM(o.total_amount),2) as attributed_gmv
            FROM orders o
            JOIN last_order l ON o.user_id = l.user_id AND o.order_date = l.last_date
            GROUP BY o.leader_id
        )
        SELECT lt.*, gl.leader_name, gl.city_tier, gl.leader_density
        FROM last_touch lt
        JOIN group_leaders gl ON lt.leader_id = gl.leader_id
        ORDER BY lt.attributed_gmv DESC
        LIMIT 15
    '''
    df_lt = pd.read_sql(last_touch_sql, conn)
    print('\n[末次触点归因 TOP15团长]')
    print(df_lt.to_string(index=False))

    # 团长GMV贡献排名(含履约成本)
    leader_gmv_sql = '''
        SELECT
            o.leader_id,
            gl.leader_name,
            gl.city_tier,
            COUNT(DISTINCT o.order_id) as order_count,
            COUNT(DISTINCT o.user_id) as unique_users,
            ROUND(SUM(o.total_amount),2) as total_gmv,
            ROUND(SUM(o.total_amount)*1.0/COUNT(DISTINCT o.order_id),2) as avg_order_value,
            ROUND(AVG(f.fulfillment_cost),2) as avg_fulfill_cost,
            ROUND(SUM(f.loss_amount),2) as total_loss
        FROM orders o
        JOIN group_leaders gl ON o.leader_id = gl.leader_id
        LEFT JOIN fulfillment f ON o.order_id = f.order_id
        GROUP BY o.leader_id
        ORDER BY total_gmv DESC
        LIMIT 20
    '''
    df_leader = pd.read_sql(leader_gmv_sql, conn)
    print('\n[团长GMV贡献 TOP20]')
    print(df_leader.to_string(index=False))
    df_leader.to_csv(f'{DATA_DIR}/leader_gmv_ranking.csv', index=False, encoding='utf-8-sig')

    return


# ===========================================================================
# 主入口
# ===========================================================================

if __name__ == '__main__':
    conn = load_to_sqlite()

    analysis_01_exploration(conn)
    analysis_02_funnel(conn)
    analysis_03_rfm(conn)
    analysis_04_retention(conn)
    analysis_05_attribution(conn)

    conn.close()

    print('\n' + '='*70)
    print('  全部SQL分析完成!')
    print(f'  数据库: {DB_PATH}')
    print(f'  中间结果: data/rfm_detail.csv, data/leader_gmv_ranking.csv')
    print('  下一步: python 06_python_visualization.py')
    print('='*70)
