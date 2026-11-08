"""
=============================================================================
因果推断数据生成 — 含选择偏差的优惠券观测数据
=============================================================================
关键设计: 优惠券不是随机发放的!
    - 高活跃用户更可能收到券(选择偏差)
    - 即使没券,高活跃用户的GMV也更高
    - 如果直接比"收券 vs 没收券" → 会高估效果

真实因果效应: 优惠券使GMV提升约8%
朴素对比偏差: 会显示约15-20%的"伪效果"(因为收券用户本来就更活跃)
PSM/DID修正: 接近8%的真实效应
=============================================================================
"""
import pandas as pd, numpy as np, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
np.random.seed(42)

N = 10000

# 用户特征
pre_gmv = np.random.lognormal(mean=3.0, sigma=0.6, size=N)  # 发券前30天GMV
frequency = np.random.poisson(lam=4, size=N)  # 购买频次
recency = np.random.randint(1, 30, N)  # 最近购买天数
city_tier = np.random.choice([0,1], N, p=[0.4,0.6])  # 0=一线,1=三五线

# 核心: 获得优惠券的概率取决于用户特征(非随机!)
# 高GMV+高频+低recency → 更容易被运营选中发券
propensity = 1/(1+np.exp(-(0.5*(pre_gmv-25)/10 + 0.3*(frequency-4) - 0.2*(recency-10)/5 + 0.1*city_tier - 0.5)))
treated = np.random.binomial(1, propensity)

# 真实因果效应: 券使GMV提升8%
true_effect = 0.08
post_gmv = pre_gmv * (1 + true_effect*treated + np.random.normal(0,0.05,N))

df = pd.DataFrame({
    'user_id': range(1,N+1),
    'treated': treated,
    'pre_gmv': np.round(pre_gmv,2),
    'post_gmv': np.round(post_gmv,2),
    'frequency': frequency,
    'recency': recency,
    'city_tier': city_tier,
    'propensity': np.round(propensity,4),
})

df.to_csv(f'{DATA_DIR}/coupon_data.csv',index=False,encoding='utf-8-sig')
print(f'[OK] coupon_data: {N}用户 | 处理组{treated.sum()} | 对照组{(1-treated).sum()}')
print(f'  处理组pre_GMV均值: {df[treated==1]["pre_gmv"].mean():.1f}')
print(f'  对照组pre_GMV均值: {df[treated==0]["pre_gmv"].mean():.1f}')
print(f'  → 处理组基线更高 {((df[treated==1]["pre_gmv"].mean()/df[treated==0]["pre_gmv"].mean())-1)*100:.1f}% (选择偏差)')
