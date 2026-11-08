"""模块01: 时序探索 + 季节分解"""
import pandas as pd, numpy as np, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose

plt.rcParams['font.sans-serif'] = ['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/daily_gmv.csv'); df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

print("="*60)
print("  模块01: GMV时序探索 + 季节分解")
print("="*60)

# 基本统计
print(f"\n  日均GMV: {df['gmv'].mean():.0f} | 标准差: {df['gmv'].std():.0f}")
print(f"  MAX: {df['gmv'].max()} (date: {df['gmv'].idxmax().strftime('%m-%d')})")
print(f"  MIN: {df['gmv'].min()} (date: {df['gmv'].idxmin().strftime('%m-%d')})")

# 按周几分组
dow_avg = df.groupby(df.index.dayofweek)['gmv'].mean()
dow_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
print(f"\n  周内效应:")
for i in range(7): print(f"    {dow_names[i]}: {dow_avg[i]:.0f}")

# 季节分解
result = seasonal_decompose(df['gmv'], model='multiplicative', period=7)

fig, axes = plt.subplots(4,1,figsize=(14,10))
result.observed.plot(ax=axes[0],title='Observed (原始GMV)')
result.trend.plot(ax=axes[1],title='Trend (趋势)')
result.seasonal.plot(ax=axes[2],title='Seasonal (季节-周内)')
result.resid.plot(ax=axes[3],title='Residual (残差)')
for ax in axes: ax.set_ylabel('')
plt.tight_layout(); plt.savefig(f'{DATA_DIR}/decomposition.png',dpi=150)
print(f'\n[图表已保存] data/decomposition.png')
