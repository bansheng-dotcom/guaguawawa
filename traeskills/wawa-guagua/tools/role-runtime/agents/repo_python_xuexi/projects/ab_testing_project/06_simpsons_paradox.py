"""
=============================================================================
模块06: 辛普森悖论排查 — 城市等级交互效应
=============================================================================
社区团购场景下的辛普森悖论:

    整体: 算法推荐 GMV +~2%  (不错,上吧!)

    细分:
      一线/新一线: 算法 +7~8%  → 用户数据丰富,供给稳定,算法明显更强
      三五线城市:  算法 -2~3%  → 数据稀疏+供给不稳定+团长密度低,
                                  城市运营更了解"今天本地能拿到什么货"

    根源分析(跟你的拼多多买菜履历直接对应):
        1. 数据稀疏: 低线城市团长代下单普遍,用户画像不完整
        2. 供给约束: 算法推的品当地网格仓不一定有货(履约匹配失败)
        3. 履约半径: 团长密度低→自提点远→履约成本高
        4. 消费习惯: 低线城市用户更依赖团长推荐,而非算法推荐

排查维度:
    - 主维度: 城市等级(city_tier) — 一线/新一线 vs 三五线
    - 辅助维度: 团长密度(leader_density)、购买频次(purchase_freq)
    - 交互效应: city_tier × treatment 交互项检验
=============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 70)
print("  模块06: 辛普森悖论排查 — 城市等级交互效应")
print("=" * 70)
print()

df = pd.read_csv('data/ab_test_data.csv')
ALPHA = 0.05

# ===========================================================================
# 第一部分: 整体回顾
# ===========================================================================

control_all = df[df['group'] == 'control']
treatment_all = df[df['group'] == 'treatment']

gmv_c = control_all['gmv'].mean()
gmv_t = treatment_all['gmv'].mean()
_, p_all = stats.ttest_ind(treatment_all['gmv'], control_all['gmv'])
overall_lift = ((gmv_t - gmv_c) / gmv_c) * 100

print(f"  整体GMV: 运营{gmv_c:.2f} → 算法{gmv_t:.2f}  Lift={overall_lift:+.2f}% (p={p_all:.4e})")
print()

# ===========================================================================
# 第二部分: 按城市等级细分
# ===========================================================================

print("=" * 50)
print("  按城市等级细分分析")
print("=" * 50)

for tier_val, tier_name in [('tier_1_new', '一线/新一线'), ('tier_3_5', '三五线')]:
    seg = df[df['city_tier'] == tier_val]
    seg_c = seg[seg['group'] == 'control']
    seg_t = seg[seg['group'] == 'treatment']

    c_gmv = seg_c['gmv'].mean()
    t_gmv = seg_t['gmv'].mean()
    lift = ((t_gmv - c_gmv) / c_gmv) * 100 if c_gmv != 0 else 0
    _, p_val = stats.ttest_ind(seg_t['gmv'], seg_c['gmv'])

    c_items = seg_c['items_per_order'].mean()
    t_items = seg_t['items_per_order'].mean()
    items_lift = ((t_items - c_items) / c_items) * 100 if c_items != 0 else 0

    c_fulfill = seg_c['fulfillment_cost_rate'].mean()
    t_fulfill = seg_t['fulfillment_cost_rate'].mean()
    fulfill_lift = ((t_fulfill - c_fulfill) / c_fulfill) * 100 if c_fulfill != 0 else 0

    c_loss = seg_c['fresh_loss_rate'].mean()
    t_loss = seg_t['fresh_loss_rate'].mean()
    loss_lift = ((t_loss - c_loss) / c_loss) * 100 if c_loss != 0 else 0

    print(f"\n  [{tier_name}] (n={len(seg):,},占比{len(seg)/len(df)*100:.0f}%)")
    print(f"    GMV:          运营{c_gmv:.2f} → 算法{t_gmv:.2f}  Lift={lift:+.2f}%  p={p_val:.4e}")
    print(f"    人均件数:     运营{c_items:.1f} → 算法{t_items:.1f}  Lift={items_lift:+.2f}%")
    print(f"    履约成本率:   运营{c_fulfill:.2f}% → 算法{t_fulfill:.2f}%  {'上涨' if fulfill_lift>0 else '下降'}{fulfill_lift:+.2f}%")
    print(f"    生鲜损耗率:   运营{c_loss:.2f}% → 算法{t_loss:.2f}%  {'上涨' if loss_lift>0 else '下降'}{loss_lift:+.2f}%")

    # 辛普森悖论检测
    if (lift > 0) != (overall_lift > 0):
        print(f"    [WARNING] 辛普森悖论: 该群体Lift({lift:+.2f}%)与整体({overall_lift:+.2f}%)方向相反!")

print()

# ===========================================================================
# 第三部分: 按其他维度细分
# ===========================================================================

print("=" * 50)
print("  其他维度细分(GMV Lift)")
print("=" * 50)

for dim_col, dim_name in [('purchase_freq', '购买频次'), ('leader_density', '团长密度')]:
    print(f"\n  [{dim_name}]:")
    print(f"  {'群体':<12} {'运营GMV':<10} {'算法GMV':<10} {'Lift':<10} {'样本量':<10}")
    print(f"  {'-'*52}")
    for seg_val in df[dim_col].unique():
        seg = df[df[dim_col] == seg_val]
        c_m = seg[seg['group']=='control']['gmv'].mean()
        t_m = seg[seg['group']=='treatment']['gmv'].mean()
        lift = ((t_m-c_m)/c_m)*100 if c_m != 0 else 0
        print(f"  {seg_val:<12} {c_m:<10.2f} {t_m:<10.2f} {lift:<+10.2f} {len(seg):<10,}")

print()

# ===========================================================================
# 第四部分: 交互效应检验
# ===========================================================================

print("=" * 50)
print("  交互效应检验(城市等级 × 实验组)")
print("=" * 50)

df_reg = df.copy()
df_reg['is_treatment'] = (df_reg['group'] == 'treatment').astype(int)
df_reg['is_tier1'] = (df_reg['city_tier'] == 'tier_1_new').astype(int)
df_reg['interaction'] = df_reg['is_treatment'] * df_reg['is_tier1']

X = df_reg[['is_treatment', 'is_tier1', 'interaction']]
X = sm.add_constant(X)
y = df_reg['gmv']

model = sm.OLS(y, X).fit()

print("  回归模型: GMV ~ 1 + is_treatment + is_tier1 + treatment*tier1")
print()
print(model.summary().tables[1])
print()

interaction_coef = model.params['interaction']
interaction_p = model.pvalues['interaction']

print(f"  交互项系数: {interaction_coef:.4f} (p={interaction_p:.4f})")
if interaction_p < ALPHA:
    print(f"  → 存在显著的交互效应: 算法效果在城市等级间确有差异")
    print(f"  → 不能简单地全量一刀切! 需要分城市制定策略")
else:
    print(f"  → 交互效应不显著: 算法效果在不同城市等级间较为一致")

# 对履约成本率也做交互检验
y2 = df_reg['fulfillment_cost_rate']
model2 = sm.OLS(y2, X).fit()
fulfill_interact_p = model2.pvalues['interaction']
print()
print(f"  履约成本率交互项p值: {fulfill_interact_p:.4f}")
if fulfill_interact_p < ALPHA:
    print(f"  → 算法对履约成本的影响在不同城市等级间也有显著差异!")
    print(f"  → 低线城市的供给约束问题需要重点解决")
print()

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 图1: 城市等级 GMV lift
ax1 = axes[0]
tier_lifts = {}
for tier_val, tier_name in [('tier_1_new', '一线/新一线'), ('tier_3_5', '三五线')]:
    seg = df[df['city_tier']==tier_val]
    c_m = seg[seg['group']=='control']['gmv'].mean()
    t_m = seg[seg['group']=='treatment']['gmv'].mean()
    tier_lifts[tier_name] = ((t_m-c_m)/c_m)*100

segments = list(tier_lifts.keys())
lifts = list(tier_lifts.values())
bar_colors = ['#27AE60' if l>0 else '#E74C3C' for l in lifts]

bars = ax1.bar(segments, lifts, color=bar_colors, alpha=0.85, edgecolor='black')
ax1.axhline(y=0, color='black', linewidth=1)
ax1.axhline(y=overall_lift, color='#3498DB', linestyle='--', linewidth=2, label=f'整体Lift={overall_lift:+.2f}%')
ax1.set_ylabel('GMV Lift(%)')
ax1.set_title('城市等级: GMV变化(辛普森悖论)')
ax1.legend()
for bar, lift in zip(bars, lifts):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1, f'{lift:+.2f}%', ha='center', fontsize=12, fontweight='bold')

# 图2: 购买频次 GMV lift
ax2 = axes[1]
freq_lifts = {}
for fq in ['high', 'mid', 'low']:
    seg = df[df['purchase_freq']==fq]
    c_m = seg[seg['group']=='control']['gmv'].mean()
    t_m = seg[seg['group']=='treatment']['gmv'].mean()
    freq_lifts[fq] = ((t_m-c_m)/c_m)*100

freq_labels = {'high': '高频', 'mid': '中频', 'low': '低频'}
f_seg = [freq_labels[k] for k in freq_lifts.keys()]
f_lifts = list(freq_lifts.values())
f_colors = ['#27AE60' if l>0 else '#E74C3C' for l in f_lifts]

bars2 = ax2.bar(f_seg, f_lifts, color=f_colors, alpha=0.85, edgecolor='black')
ax2.axhline(y=0, color='black', linewidth=1)
ax2.set_ylabel('GMV Lift(%)')
ax2.set_title('购买频次: GMV变化')
for bar, lift in zip(bars2, f_lifts):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1, f'{lift:+.2f}%', ha='center', fontsize=11, fontweight='bold')

# 图3: 交互效应热力图
ax3 = axes[2]
combos = []
for tier in df['city_tier'].unique():
    for freq in df['purchase_freq'].unique():
        seg = df[(df['city_tier']==tier)&(df['purchase_freq']==freq)]
        c_m = seg[seg['group']=='control']['gmv'].mean()
        t_m = seg[seg['group']=='treatment']['gmv'].mean()
        lift = ((t_m-c_m)/c_m)*100 if c_m!=0 else 0
        combos.append({'city_tier': tier, 'purchase_freq': freq, 'lift': lift})

pivot = pd.DataFrame(combos).pivot(index='city_tier', columns='purchase_freq', values='lift')
pivot.index = ['一线/新一线' if x=='tier_1_new' else '三五线' for x in pivot.index]
pivot.columns = ['高频' if x=='high' else ('中频' if x=='mid' else '低频') for x in pivot.columns]

im = ax3.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=-5, vmax=15)
ax3.set_xticks(range(len(pivot.columns))); ax3.set_yticks(range(len(pivot.index)))
ax3.set_xticklabels(pivot.columns); ax3.set_yticklabels(pivot.index)
ax3.set_title('交互热力图: 城市等级 × 购买频次')
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        v = pivot.values[i, j]
        ax3.text(j, i, f'{v:+.2f}%', ha='center', va='center', fontsize=13, fontweight='bold',
                 color='white' if abs(v)>8 else 'black')
plt.colorbar(im, ax=ax3, label='GMV Lift(%)')

plt.suptitle('辛普森悖论与细分分析 — 美团优选今日爆品', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('data/simpsons_paradox_plots.png', dpi=150, bbox_inches='tight')
print("[图表已保存] data/simpsons_paradox_plots.png")
print()

# ===========================================================================
# 结论
# ===========================================================================

print("=" * 70)
print("  辛普森悖论排查结论")
print("=" * 70)

tier1_lift = tier_lifts.get('一线/新一线', 0)
tier35_lift = tier_lifts.get('三五线', 0)
has_simpson = (tier1_lift > 0 and tier35_lift < 0)

print(f"""
  核心发现:
    1. 整体GMV Lift = {overall_lift:+.2f}% (正向)
    2. 一线/新一线: {tier1_lift:+.2f}% (正向,{'显著' if abs(tier1_lift)>5 else '中等'})
    3. 三五线:      {tier35_lift:+.2f}% ({'正向' if tier35_lift>0 else '负向'})
    4. 交互效应: {'显著' if interaction_p<ALPHA else '不显著'}

  {'[WARNING] 检测到辛普森悖论!' if has_simpson else '未检测到辛普森悖论'}
""")

if has_simpson:
    print("""
  分城策略建议(直接对应你的拼多多买菜经验):
    一线/新一线:
      ✓ 率先全量——用户数据丰富,供给稳定,算法优势明显
      ✓ 重点关注履约成本率是否随GMV增长而恶化

    三五线城市:
      ✗ 暂不全量——算法推荐效果不如城市运营
      → 排查方向:
        1. 数据问题: 团长代下单比例? 用户画像完整度?
        2. 供给问题: 算法推荐商品与本地网格仓库存匹配率?
        3. 履约问题: 团长密度低导致履约路径长,算法是否考虑了这个约束?
        4. 行为问题: 低线城市用户更依赖团长推荐,而非算法推荐?
      → 改进方向:
        - 引入本地库存约束到推荐模型(供给感知推荐)
        - 降低冷启动用户的算法推荐权重,保留部分运营选品
        - 针对低线团长密度区域,优化履约成本模型
""")

print("=" * 70)
print("  模块06完成")
print("  下一步: python 07_final_report.py")
print("=" * 70)
