"""
=============================================================================
GMV时间序列数据生成 — 美团优选单城市 365天
=============================================================================
包含: 上升趋势 + 周末效应 + 月度季节 + 节日脉冲 + 噪声
=============================================================================
"""
import pandas as pd, numpy as np, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
np.random.seed(42)

dates = pd.date_range('2025-01-01','2025-12-31',freq='D')
n = len(dates)
dow = dates.dayofweek  # Mon=0, Sun=6

# 趋势: 年增25%
trend = np.linspace(1.0, 1.25, n)
# 周末效应: 周五-周日+40%
weekend = np.ones(n); weekend[dow>=4] = np.random.uniform(1.30,1.55,sum(dow>=4))
# 月度季节
monthly = {1:1.0,2:0.80,3:0.95,4:1.0,5:1.05,6:1.05,7:0.90,8:0.93,9:1.0,10:1.08,11:1.20,12:1.25}
seasonal = np.array([monthly[d.month] for d in dates])
# 节日脉冲
holiday = np.ones(n)
for start,end,mult in [('2025-02-08','2025-02-17',1.8),('2025-05-01','2025-05-05',1.3),
                        ('2025-10-01','2025-10-07',1.5),('2025-11-10','2025-11-12',1.6)]:
    mask = (dates>=start)&(dates<=end)
    holiday[mask] = mult
# 特殊事件
event = np.ones(n)
event[(dates>='2025-07-15')&(dates<='2025-07-21')] = 0.65  # 暴雨
noise = np.random.normal(1,0.06,n)

base_gmv = 28000
gmv = base_gmv * trend * weekend * seasonal * holiday * event * noise
gmv = np.round(gmv, 0).astype(int)

df = pd.DataFrame({'date':dates,'gmv':gmv,'dow':dow,'month':dates.month,
                    'is_weekend':(dow>=4).astype(int)})
df.to_csv(f'{DATA_DIR}/daily_gmv.csv',index=False,encoding='utf-8-sig')
print(f'[OK] daily_gmv: {len(df)}天 | 均值{gmv.mean():.0f} | 范围{gmv.min()}-{gmv.max()}')
