"""
=============================================================================
社区团购「今日爆品」A/B测试 — 数据生成脚本
=============================================================================
业务场景:
    美团优选首页"今日爆品"坑位(每日6-8个SKU)，当前由各城市运营团队手动选品。
    对照组(control): 城市运营手动选品 — 依赖运营经验+供应商排期表
    实验组(treatment): 算法个性化推荐 — 基于用户历史行为+社区画像+履约数据

生成两份数据:
    1. aa_data.csv — AA实验数据(两组都用运营手动选品)
    2. ab_test_data.csv — 正式A/B实验数据(运营 vs 算法)

核心指标(社区团购专属):
    - gmv                 人均GMV(元)
    - items_per_order     人均件数(件) — 社区团购核心,一次买几件
    - fulfillment_cost_rate 履约成本率(%) — 命门指标,推了远距离供应商的品会爆
    - fresh_loss_rate     生鲜损耗率(%) — 推了高损耗品卖不完,次日烂掉
    - return_rate         退货率(%) — 算法瞎推不合适的品
    - is_new_conversion   是否首单转化(0/1) — 新用户增长指标
    - hot_product_gmv_share 爆品GMV占比(%) — 这6-8个坑位贡献了多少

用户分层维度(辛普森悖论排查):
    - city_tier           城市等级(tier_1_new=一线新一线, tier_3_5=三五线)
    - purchase_freq       用户购买频次(高频=周均≥2单/中频/低频=月均≤2单)
    - leader_density      团长密度(高密/中密/低密)

辛普森悖论预设:
    整体: 算法组GMV ≈ +2%
    一线新一线: 算法组 +8.5%(用户数据丰富,供给稳定,履约半径可控)
    三五线:     算法组 -2.5%(数据稀疏,供给不稳定,团长密度低)
=============================================================================
"""

import pandas as pd
import numpy as np

np.random.seed(2024)

# ===========================================================================
# 第一部分: 生成AA实验数据
# ===========================================================================

def generate_aa_data(n_per_group=5000):
    """
    AA实验: 两组用户看到完全相同的"运营手动选品"。
    目的: 验证分流系统均匀——如果AA阶段两组就有显著差异,说明分流有偏。
    """
    n_total = n_per_group * 2

    # --- 用户画像 ---
    city_tier = np.random.choice(
        ['tier_1_new', 'tier_3_5'], size=n_total,
        p=[0.40, 0.60]  # 美团优选用户更多在低线城市
    )
    purchase_freq = np.random.choice(
        ['high', 'mid', 'low'], size=n_total,
        p=[0.25, 0.40, 0.35]
    )
    leader_density = np.random.choice(
        ['high', 'mid', 'low'], size=n_total,
        p=[0.30, 0.40, 0.30]
    )

    group = np.array(['A'] * n_per_group + ['B'] * n_per_group)

    # --- 指标模拟(两组参数完全相同——因为都是运营手选) ---
    # GMV: 对数正态, 社区团购客单价低,均值约25元
    gmv = np.random.lognormal(mean=3.10, sigma=0.50, size=n_total)

    # 件数: 泊松,均值约3.5件
    items_per_order = np.random.poisson(lam=3.5, size=n_total).astype(float)
    items_per_order = np.clip(items_per_order, 1, 15)

    # 履约成本率: 正态,均值8%,标准差2
    fulfillment_cost_rate = np.random.normal(loc=8.0, scale=2.0, size=n_total)
    fulfillment_cost_rate = np.clip(fulfillment_cost_rate, 2, 20)

    # 生鲜损耗率: 正态,均值5%,标准差1.5
    fresh_loss_rate = np.random.normal(loc=5.0, scale=1.5, size=n_total)
    fresh_loss_rate = np.clip(fresh_loss_rate, 0.5, 15)

    # 退货率: 正态,均值2%,标准差0.5
    return_rate = np.random.normal(loc=2.0, scale=0.5, size=n_total)
    return_rate = np.clip(return_rate, 0.1, 8)

    # 首单转化(新用户首次下单): 约12%
    is_new_conversion = np.random.binomial(1, 0.12, size=n_total)

    # 爆品GMV占比: 正态,均值35%,标准差8
    hot_product_gmv_share = np.random.normal(loc=35, scale=8, size=n_total)
    hot_product_gmv_share = np.clip(hot_product_gmv_share, 5, 75)

    # --- 组装 ---
    df = pd.DataFrame({
        'user_id': range(1, n_total + 1),
        'group': group,
        'city_tier': city_tier,
        'purchase_freq': purchase_freq,
        'leader_density': leader_density,
        'gmv': np.round(gmv, 2),
        'items_per_order': items_per_order.astype(int),
        'fulfillment_cost_rate': np.round(fulfillment_cost_rate, 2),
        'fresh_loss_rate': np.round(fresh_loss_rate, 2),
        'return_rate': np.round(return_rate, 2),
        'is_new_conversion': is_new_conversion,
        'hot_product_gmv_share': np.round(hot_product_gmv_share, 2),
    })

    df.to_csv('data/aa_data.csv', index=False, encoding='utf-8-sig')
    print("[OK] AA实验数据: data/aa_data.csv")
    print(f"    每组: {n_per_group}人, 合计: {n_total}人")
    print(f"    A组平均GMV: {df[df['group']=='A']['gmv'].mean():.2f}")
    print(f"    B组平均GMV: {df[df['group']=='B']['gmv'].mean():.2f}")
    return df


# ===========================================================================
# 第二部分: 生成正式A/B实验数据
# ===========================================================================

def generate_ab_test_data(n_per_group=20000):
    """
    A/B实验:
        control:   城市运营手动选品(当前方案)
        treatment: 算法个性化推荐(新方案)

    效果差异(基于社区团购真实逻辑):
        一线/新一线(40%用户):
            用户数据丰富,算法冷启动成本低;
            供应商集中在城郊,履约半径可控;
            算法能精准匹配用户偏好 → GMV+8.5%

        三五线(60%用户):
            用户购买数据稀疏(团长代下单普遍,用户画像不完整);
            供给不稳定——算法推的品当地网格仓可能没配货;
            团长密度低→履约路径长→算法忽略此约束反而推高成本;
            城市运营更了解"今天本地能拿到什么货" → 算法GMV-2.2%

    整体: 约+2.1% (40%×8.5% + 60%×-2.2% ≈ 2.1%)
    """
    n_total = n_per_group * 2

    # --- 用户画像 ---
    city_tier = np.random.choice(
        ['tier_1_new', 'tier_3_5'], size=n_total,
        p=[0.40, 0.60]
    )
    purchase_freq = np.random.choice(
        ['high', 'mid', 'low'], size=n_total,
        p=[0.25, 0.40, 0.35]
    )
    leader_density = np.random.choice(
        ['high', 'mid', 'low'], size=n_total,
        p=[0.30, 0.40, 0.30]
    )

    group = np.array(['control'] * n_per_group + ['treatment'] * n_per_group)

    is_treatment = (group == 'treatment')
    is_tier1 = (city_tier == 'tier_1_new')
    is_tier35 = (city_tier == 'tier_3_5')

    # =====================================================
    # GMV: 基础均值25, 对照组在不同城市等级有差异
    # =====================================================
    # 一线城市客单价略高,三五线略低(反映消费能力差异)
    gmv_base = np.random.lognormal(mean=3.10, sigma=0.50, size=n_total)
    gmv_base[is_tier1] *= 1.08   # 一线: 均值~27元
    gmv_base[is_tier35] *= 0.95  # 三五线: 均值~24元

    # 实验组lift: 一线+8.5%, 三五线-2.2%
    gmv_lift = np.ones(n_total)
    gmv_lift[is_treatment & is_tier1] = 1.085
    gmv_lift[is_treatment & is_tier35] = 0.978

    gmv = gmv_base * gmv_lift

    # =====================================================
    # 人均件数: 泊松, 一线baseline略高(家庭采购型)
    # =====================================================
    items_lam = np.full(n_total, 3.5)
    items_lam[is_tier1] = 3.8
    items_lam[is_tier35] = 3.3
    # 实验组: 算法在一线做连带推荐效果更好
    items_lam[is_treatment & is_tier1] *= 1.05    # 一线+5%
    items_lam[is_treatment & is_tier35] *= 0.985  # 三五线-1.5%

    items_per_order = np.array([np.random.poisson(lam=l) for l in items_lam]).astype(float)
    items_per_order = np.clip(items_per_order, 1, 15)

    # =====================================================
    # 履约成本率: baseline 8%, 算法在低线城市可能推高(忽略供给约束)
    # =====================================================
    fulfillment_base = np.random.normal(loc=8.0, scale=2.0, size=n_total)
    # 算法在一线: 考虑了履约成本优化 → 略降
    fulfillment_base[is_treatment & is_tier1] *= 0.97    # -3%
    # 算法在三五线: 推了远距离供应商的品 → 上升
    fulfillment_base[is_treatment & is_tier35] *= 1.06   # +6%
    fulfillment_cost_rate = np.clip(fulfillment_base, 2, 22)

    # =====================================================
    # 生鲜损耗率: baseline 5%, 算法推了易损耗品但三五线卖不完
    # =====================================================
    loss_base = np.random.normal(loc=5.0, scale=1.5, size=n_total)
    # 算法在一线: 销量预测准,避免过量推荐 → 降
    loss_base[is_treatment & is_tier1] *= 0.95    # -5%
    # 算法在三五线: 推荐了当地不好卖的品 → 升
    loss_base[is_treatment & is_tier35] *= 1.05   # +5%
    fresh_loss_rate = np.clip(loss_base, 0.5, 16)

    # =====================================================
    # 退货率: baseline 2%
    # =====================================================
    return_base = np.random.normal(loc=2.0, scale=0.5, size=n_total)
    return_base[is_treatment & is_tier1] *= 0.98     # -2%(精准推荐)
    return_base[is_treatment & is_tier35] *= 1.03    # +3%(推荐不匹配)
    return_rate = np.clip(return_base, 0.1, 9)

    # =====================================================
    # 首单转化率: baseline 12%
    # =====================================================
    conv_prob = np.full(n_total, 0.12)
    conv_prob[is_treatment & is_tier1] = 0.12 * 1.08    # 一线+8%
    conv_prob[is_treatment & is_tier35] = 0.12 * 1.00   # 三五线基本不变
    is_new_conversion = np.random.binomial(1, conv_prob)

    # =====================================================
    # 爆品GMV占比: baseline 35%
    # =====================================================
    hot_share_base = np.random.normal(loc=35, scale=8, size=n_total)
    # 算法在一线: 个性化推荐提升爆品命中率 → 占比升
    hot_share_base[is_treatment & is_tier1] *= 1.10     # +10%
    # 算法在三五线: 推荐不准,爆品贡献反而降 → 占比降
    hot_share_base[is_treatment & is_tier35] *= 0.96    # -4%
    hot_product_gmv_share = np.clip(hot_share_base, 5, 80)

    # --- 组装 ---
    df = pd.DataFrame({
        'user_id': range(1, n_total + 1),
        'group': group,
        'city_tier': city_tier,
        'purchase_freq': purchase_freq,
        'leader_density': leader_density,
        'gmv': np.round(gmv, 2),
        'items_per_order': items_per_order.astype(int),
        'fulfillment_cost_rate': np.round(fulfillment_cost_rate, 2),
        'fresh_loss_rate': np.round(fresh_loss_rate, 2),
        'return_rate': np.round(return_rate, 2),
        'is_new_conversion': is_new_conversion,
        'hot_product_gmv_share': np.round(hot_product_gmv_share, 2),
    })

    df.to_csv('data/ab_test_data.csv', index=False, encoding='utf-8-sig')
    print("[OK] A/B实验数据: data/ab_test_data.csv")
    print(f"    每组: {n_per_group}人, 合计: {n_total}人")
    print(f"    对照组平均GMV:        {df[df['group']=='control']['gmv'].mean():.2f}")
    print(f"    实验组平均GMV:        {df[df['group']=='treatment']['gmv'].mean():.2f}")
    overall_lift = ((df[df['group']=='treatment']['gmv'].mean() /
                      df[df['group']=='control']['gmv'].mean()) - 1) * 100
    print(f"    整体GMV lift:         {overall_lift:+.2f}%")

    # 分城市等级
    for tier_val, tier_name in [('tier_1_new', '一线/新一线'), ('tier_3_5', '三五线')]:
        seg = df[df['city_tier'] == tier_val]
        c_m = seg[seg['group']=='control']['gmv'].mean()
        t_m = seg[seg['group']=='treatment']['gmv'].mean()
        lift = ((t_m / c_m) - 1) * 100
        print(f"    {tier_name} GMV lift: {lift:+.2f}% (对照{c_m:.2f} vs 实验{t_m:.2f})")

    return df


# ===========================================================================
# 主入口
# ===========================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("  社区团购「今日爆品」A/B测试 — 数据生成")
    print("  场景: 美团优选首页爆品坑位 | 运营手选 vs 算法推荐")
    print("=" * 70)
    print()

    generate_aa_data(n_per_group=5000)
    print()
    generate_ab_test_data(n_per_group=20000)

    print()
    print("=" * 70)
    print("  数据生成完毕。按编号运行各分析模块。")
    print("=" * 70)
