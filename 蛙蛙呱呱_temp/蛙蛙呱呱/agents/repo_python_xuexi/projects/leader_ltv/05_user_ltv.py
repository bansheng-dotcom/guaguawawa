"""
=============================================================================
模块05: 用户LTV — 按获客渠道对比
=============================================================================
美团优选的三种获客渠道:
    1. 团长拉新(leader_refer): 团长在群里邀请,用户扫码注册 → 质量最高
    2. 自然流量(organic): 用户自己搜索/下载APP → 质量中等
    3. 促销活动(promo): 扫码领鸡蛋/新人0.01元购 → 质量偏低(薅羊毛)

问题:
    - 哪个渠道的LTV最高?
    - 团长拉新的用户,长期价值是否对得起BD激励成本?
    - 促销用户虽然LTV低,但量大——整体ROI如何?

输出:
    1. 三渠道LTV对比(箱线图)
    2. 按渠道的用户留存曲线
    3. 渠道ROI评估
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
print("  模块05: 用户LTV — 获客渠道对比")
print("=" * 60)
print()

users = pd.read_csv(f'{DATA_DIR}/user_ltv.csv')

# ===========================================================================
# 渠道LTV统计
# ===========================================================================

channel_stats = users.groupby('channel').agg(
    user_count=('user_id','count'),
    avg_ltv=('ltv','mean'),
    median_ltv=('ltv','median'),
    avg_active_months=('active_months','mean'),
    avg_monthly_gmv=('avg_monthly_gmv','mean'),
    avg_total_orders=('total_orders','mean'),
).round(1)

channel_labels = {'leader_refer':'团长拉新','organic':'自然流量','promo':'促销活动'}
channel_stats.index = [channel_labels.get(x, x) for x in channel_stats.index]

print("  渠道LTV对比:")
print(f"  {'渠道':<12} {'用户数':<8} {'均LTV':<10} {'中位LTV':<10} {'均活月数':<10} {'月均GMV':<10}")
print(f"  {'-'*60}")

for ch, row in channel_stats.iterrows():
    pct = row['user_count'] / len(users) * 100
    print(f"  {ch:<12} {row['user_count']:<8,} {row['avg_ltv']:<10.0f} {row['median_ltv']:<10.0f} {row['avg_active_months']:<10.1f} {row['avg_monthly_gmv']:<10.1f}")

# ===========================================================================
# 渠道ROI评估
# ===========================================================================

print()
print("=" * 40)
print("  渠道ROI评估")
print("=" * 40)

# 假设各渠道获客成本
costs = {'leader_refer': 25, 'organic': 5, 'promo': 15}

for ch, label in channel_labels.items():
    ch_users = users[users['channel'] == ch]
    avg_ltv = ch_users['ltv'].mean()
    cost = costs[ch]
    roi = avg_ltv / cost
    print(f"  {label}: 获客成本{cost}元, 均LTV{avg_ltv:.0f}元, LTV/CAC={roi:.1f}x {'[OK]' if roi>5 else '[WARN]'}")

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 图1: LTV箱线图(按渠道)
ax1 = axes[0]
ordered_labels = ['团长拉新','自然流量','促销活动']
ltv_data = [users[users['channel']==ch]['ltv'].values for ch in ['leader_refer','organic','promo']]
bp = ax1.boxplot(ltv_data, labels=ordered_labels, patch_artist=True)
colors_box = ['#2ECC71','#3498DB','#E74C3C']
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax1.set_ylabel('LTV(元)')
ax1.set_title('用户LTV分布 — 按获客渠道', fontsize=11, fontweight='bold')
ax1.grid(True, alpha=0.3, axis='y')

# 图2: 渠道LTV中位数比较
ax2 = axes[1]
medians = [np.median(users[users['channel']==ch]['ltv']) for ch in ['leader_refer','organic','promo']]
bars = ax2.bar(ordered_labels, medians, color=colors_box, alpha=0.85, edgecolor='white')
for bar, med in zip(bars, medians):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2, f'{med:.0f}元', ha='center', fontsize=12, fontweight='bold')
ax2.set_ylabel('LTV中位数(元)')
ax2.set_title('渠道LTV中位数对比', fontsize=11, fontweight='bold')

# 图3: 渠道构成+贡献
ax3 = axes[2]
total_ltv_by_channel = users.groupby('channel')['ltv'].sum()
total_ltv_by_channel.index = [channel_labels.get(x,x) for x in total_ltv_by_channel.index]

user_pcts = [len(users[users['channel']==ch])/len(users)*100 for ch in ['leader_refer','organic','promo']]
ltv_pcts = [total_ltv_by_channel[channel_labels[ch]]/total_ltv_by_channel.sum()*100 for ch in ['leader_refer','organic','promo']]

x = np.arange(len(ordered_labels))
width = 0.3
ax3.bar(x-width/2, user_pcts, width, label='用户数占比%', color='#3498DB', alpha=0.85)
ax3.bar(x+width/2, ltv_pcts, width, label='LTV贡献占比%', color='#2ECC71', alpha=0.85)
ax3.set_xticks(x)
ax3.set_xticklabels(ordered_labels)
ax3.set_title('用户占比 vs LTV贡献占比', fontsize=11, fontweight='bold')
ax3.legend(fontsize=9)

plt.suptitle('用户LTV渠道分析', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DATA_DIR}/user_ltv_channel.png', dpi=150, bbox_inches='tight')
print(f'\n[图表已保存] data/user_ltv_channel.png')
print()
print("=" * 60)
print("  [DONE] 项目五全部模块完成!")
print()
print("  简历可写:")
print()
print("""  [团长生命周期与用户LTV分析 — 美团优选]

  - 构建24个月团长队列留存热力图，Kaplan-Meier曲线显示
    团长中位存活X月(一线Y月 vs 三五线Z月)

  - Cox回归识别存活关键因子(团长密度/初始GMV质量)；
    LTV=月均GMV×预期存活，分层为4级(超级/高/中/低价值)

  - 设计团长流失预警4信号(GMV连续降/用户降/无订单/GMV骤降)，
    高风险组实际流失率X% vs 低风险组Y%

  - 按获客渠道对比用户LTV(团长拉新>自然流量>促销)，
    LTV/CAC比值指导BD激励策略

  技术栈: Python(Pandas/lifelines/Matplotlib)、生存分析、LTV建模
""")
print("=" * 60)
