"""
=============================================================================
06 Python可视化 — 社区团购漏斗分析
=============================================================================
产出6张图:
    1. 转化漏斗图    — 团长分享→点击→加购→下单 漏斗
    2. 城市漏斗对比  — 一线 vs 三五线各环节转化率
    3. RFM分布       — 用户R/F/M三维散点图
    4. 复购率对比    — 不同用户类型30日复购率
    5. 团长GMV排名   — TOP20团长GMV贡献柱状图
    6. 品类分析       — 各品类GMV贡献+毛利率
=============================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = 'data'

# 从SQLite读取数据
import sqlite3
conn = sqlite3.connect(f'{DATA_DIR}/community_groupbuy.db')

# ===========================================================================
# 图1: 转化漏斗
# ===========================================================================

fig = plt.figure(figsize=(20, 14))

# 1-1 整体漏斗 (左上)
ax1 = plt.subplot(2, 3, 1)

funnel_data = pd.read_sql('''
    SELECT action, COUNT(DISTINCT user_id) as users
    FROM behavior_logs
    GROUP BY action
    ORDER BY CASE action WHEN 'impression' THEN 1 WHEN 'click' THEN 2
              WHEN 'add_cart' THEN 3 WHEN 'order' THEN 4 END
''', conn)

stages_cn = {'impression': '团长分享\n(曝光)', 'click': '用户点击',
             'add_cart': '加购物车', 'order': '下单'}

funnel_users = [int(funnel_data[funnel_data['action']==a]['users'].values[0])
                if a in funnel_data['action'].values else 0
                for a in ['impression','click','add_cart','order']]
funnel_labels = ['团长分享\n(曝光)','用户点击','加购物车','下单']

colors = ['#3498DB','#2ECC71','#F39C12','#E74C3C']
bar_height = 0.5
y_pos = range(len(funnel_labels))

for i, (users, label, color) in enumerate(zip(funnel_users, funnel_labels, colors)):
    ax1.barh(i, users, bar_height, color=color, alpha=0.85, edgecolor='white', linewidth=1.5)
    rate = f'{users/funnel_users[0]*100:.1f}%' if i == 0 else f'{users/funnel_users[0]*100:.1f}% ({users/funnel_users[i-1]*100:.1f}%)'
    ax1.text(users + 500, i, f'{users:,} ({rate})', va='center', fontsize=10, fontweight='bold')

ax1.set_yticks(y_pos)
ax1.set_yticklabels(funnel_labels)
ax1.set_xlabel('用户数')
ax1.set_title('整体转化漏斗', fontsize=12, fontweight='bold')
ax1.invert_yaxis()
ax1.set_xlim(0, max(funnel_users)*1.3)

# 1-2 城市漏斗对比 (右上)
ax2 = plt.subplot(2, 3, 2)

city_funnel = pd.read_sql('''
    SELECT
        CASE WHEN u.city_tier='tier_1_new' THEN '一线/新一线' ELSE '三五线' END as city,
        b.action, COUNT(DISTINCT b.user_id) as users
    FROM behavior_logs b
    JOIN users u ON b.user_id = u.user_id
    GROUP BY u.city_tier, b.action
    ORDER BY city,
      CASE b.action WHEN 'impression' THEN 1 WHEN 'click' THEN 2
                    WHEN 'add_cart' THEN 3 WHEN 'order' THEN 4 END
''', conn)

for i, city in enumerate(['一线/新一线', '三五线']):
    city_data = city_funnel[city_funnel['city'] == city]
    users_list = [int(city_data[city_data['action']==a]['users'].values[0])
                  if a in city_data['action'].values else 0
                  for a in ['impression','click','add_cart','order']]
    rates = [f'{u/users_list[0]*100:.1f}%' for u in users_list]
    color = '#2ECC71' if i == 0 else '#E74C3C'
    x_pos = np.arange(len(users_list)) + i*0.15
    ax2.plot(range(len(users_list)), users_list, 'o-', color=color, linewidth=2.5,
             markersize=10, label=city)
    for j, (u, r) in enumerate(zip(users_list, rates)):
        ax2.annotate(f'{u:,}\n({r})', (j, u), textcoords="offset points",
                     xytext=(0, 15), ha='center', fontsize=8, fontweight='bold', color=color)

ax2.set_xticks(range(len(funnel_labels)))
ax2.set_xticklabels(['曝光','点击','加购','下单'])
ax2.set_ylabel('用户数')
ax2.set_title('城市漏斗对比', fontsize=12, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# ===========================================================================
# 图2: RFM分析 (左下)
# ===========================================================================

ax3 = plt.subplot(2, 3, 3)

rfm = pd.read_csv(f'{DATA_DIR}/rfm_detail.csv')
# 抽样以提高散点图可读性
rfm_sample = rfm.sample(min(3000, len(rfm)), random_state=42)

sc = ax3.scatter(rfm_sample['recency_days'], rfm_sample['frequency'],
                 c=rfm_sample['monetary'], cmap='RdYlGn', alpha=0.6,
                 s=rfm_sample['monetary']/5, edgecolors='black', linewidth=0.3)
ax3.set_xlabel('最近购买距今天数')
ax3.set_ylabel('购买频次(单)')
ax3.set_title('用户RFM分布 (颜色=金额, 大小=金额)', fontsize=11, fontweight='bold')
plt.colorbar(sc, ax=ax3, label='消费金额(元)')
ax3.axhline(y=rfm['frequency'].median(), color='gray', linestyle='--', alpha=0.5, label='频次中位数')
ax3.axvline(x=rfm['recency_days'].median(), color='gray', linestyle='--', alpha=0.5, label='最近天数中位数')

# ===========================================================================
# 图3: 品类分析 (中下)
# ===========================================================================

ax4 = plt.subplot(2, 3, 4)

category_data = pd.read_sql('''
    SELECT p.category_name,
           COUNT(DISTINCT oi.order_id) as order_count,
           ROUND(SUM(oi.subtotal),2) as total_gmv,
           ROUND(AVG(p.unit_price - p.cost_price),2) as avg_margin
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.category_name
    ORDER BY total_gmv DESC
''', conn)

colors_cat = ['#3498DB','#E74C3C','#2ECC71','#F39C12','#9B59B6','#1ABC9C','#E67E22']
bars = ax4.barh(range(len(category_data)), category_data['total_gmv'].values,
                color=colors_cat[:len(category_data)], alpha=0.85, edgecolor='white')
ax4.set_yticks(range(len(category_data)))
ax4.set_yticklabels(category_data['category_name'].values)
ax4.set_xlabel('GMV(元)')
ax4.set_title('各品类GMV贡献', fontsize=11, fontweight='bold')
for i, (gmv, margin) in enumerate(zip(category_data['total_gmv'].values, category_data['avg_margin'].values)):
    ax4.text(gmv + 500, i, f'{gmv:,.0f} (毛利{margin:.1f})', va='center', fontsize=9)

# ===========================================================================
# 图4: 团长GMV TOP10 (右上)
# ===========================================================================

ax5 = plt.subplot(2, 3, 5)

leader_gmv = pd.read_csv(f'{DATA_DIR}/leader_gmv_ranking.csv').head(10)
colors_leader = ['#E74C3C' if t == 'tier_1_new' else '#3498DB' for t in leader_gmv['city_tier']]

bars5 = ax5.barh(range(len(leader_gmv)), leader_gmv['total_gmv'].values,
                 color=colors_leader, alpha=0.85, edgecolor='white')
ax5.set_yticks(range(len(leader_gmv)))
ax5.set_yticklabels([f'{n}' for n in leader_gmv['leader_name'].values], fontsize=8)
ax5.set_xlabel('GMV(元)')
ax5.set_title('团长GMV TOP10 (红=一线 蓝=三五线)', fontsize=11, fontweight='bold')
for i, (gmv, n_users) in enumerate(zip(leader_gmv['total_gmv'].values, leader_gmv['unique_users'].values)):
    ax5.text(gmv + 200, i, f'{gmv:,.0f}({n_users}人)', va='center', fontsize=8)

# ===========================================================================
# 图5: 复购率和履约分析 (右下)
# ===========================================================================

ax6 = plt.subplot(2, 3, 6)

# 各城市等级的履约成本 vs 损耗
fulfill_city = pd.read_sql('''
    SELECT u.city_tier,
           ROUND(AVG(f.fulfillment_cost),2) as avg_cost,
           ROUND(AVG(f.loss_amount),2) as avg_loss,
           ROUND(AVG(f.delivery_distance_km),2) as avg_distance
    FROM fulfillment f
    JOIN orders o ON f.order_id = o.order_id
    JOIN users u ON o.user_id = u.user_id
    GROUP BY u.city_tier
''', conn)

x = np.arange(len(fulfill_city))
width = 0.25
city_labels = ['一线/新一线' if t=='tier_1_new' else '三五线' for t in fulfill_city['city_tier']]

ax6.bar(x - width, fulfill_city['avg_cost'], width, label='平均履约成本(元)', color='#E74C3C', alpha=0.8)
ax6.bar(x, fulfill_city['avg_loss'], width, label='平均损耗(元)', color='#F39C12', alpha=0.8)
ax6.bar(x + width, fulfill_city['avg_distance'], width, label='平均配送距离(km)', color='#3498DB', alpha=0.8)
ax6.set_xticks(x)
ax6.set_xticklabels(city_labels)
ax6.set_title('履约成本/损耗/距离 — 按城市', fontsize=11, fontweight='bold')
ax6.legend(fontsize=8)

for i in range(len(fulfill_city)):
    ax6.text(i - width, fulfill_city['avg_cost'].values[i] + 0.1,
             f'{fulfill_city["avg_cost"].values[i]:.1f}', ha='center', fontsize=8)
    ax6.text(i + width, fulfill_city['avg_distance'].values[i] + 0.1,
             f'{fulfill_city["avg_distance"].values[i]:.1f}', ha='center', fontsize=8)

plt.suptitle('美团优选 社区团购SQL漏斗分析 — 完整Dashboard', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f'{DATA_DIR}/funnel_analysis_dashboard.png', dpi=150, bbox_inches='tight')
print(f'[图表已保存] {DATA_DIR}/funnel_analysis_dashboard.png')

conn.close()
print('可视化完成!')
