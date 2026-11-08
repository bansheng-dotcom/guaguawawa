"""模块04: ARIMA vs Prophet 精度对比"""
import pandas as pd, numpy as np, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

arima = pd.read_csv(f'{DATA_DIR}/arima_predictions.csv'); arima['date'] = pd.to_datetime(arima['date'])
prophet_path = f'{DATA_DIR}/prophet_forecast.csv'
PROPHET_OK = os.path.exists(prophet_path)
if PROPHET_OK:
    prophet = pd.read_csv(prophet_path); prophet['ds'] = pd.to_datetime(prophet['ds'])

test_dates = arima['date'].values
actual = arima['actual'].values
arima_pred = arima['arima_pred'].values
if PROPHET_OK:
    prophet_pred = prophet[prophet['ds'].isin(test_dates)]['yhat'].values[:len(test_dates)]

fig, axes = plt.subplots(1,2,figsize=(16,6))

# 图1: 预测 vs 实际
ax1 = axes[0]
ax1.plot(test_dates, actual, 'k-', linewidth=2, label='Actual')
ax1.plot(test_dates, arima_pred, 'o-', color='#E74C3C', markersize=4, label='ARIMA')
if PROPHET_OK and len(prophet_pred) == len(test_dates):
    ax1.plot(test_dates, prophet_pred, 's-', color='#3498DB', markersize=4, label='Prophet')
ax1.legend(); ax1.set_title('30-Day Forecast Comparison'); ax1.grid(True,alpha=0.3)

# 图2: 误差分布
ax2 = axes[1]
arima_errors = actual - arima_pred
ax2.hist(arima_errors, bins=20, alpha=0.5, label=f'ARIMA (MAE={np.abs(arima_errors).mean():.0f})', color='#E74C3C')
if PROPHET_OK:
    prophet_errors = actual[:len(prophet_pred)] - prophet_pred
    ax2.hist(prophet_errors, bins=20, alpha=0.5, label=f'Prophet (MAE={np.abs(prophet_errors).mean():.0f})', color='#3498DB')
ax2.axvline(x=0,color='black',linestyle='-'); ax2.legend(); ax2.set_title('Error Distribution')

plt.suptitle('ARIMA vs Prophet — GMV预测对比',fontsize=14,fontweight='bold')
plt.tight_layout(); plt.savefig(f'{DATA_DIR}/model_comparison.png',dpi=150)
print(f'[图表已保存] data/model_comparison.png')
print(f'  ARIMA  MAE: {np.abs(arima_errors).mean():.0f}')
if PROPHET_OK:
    print(f'  Prophet MAE: {np.abs(prophet_errors).mean():.0f}')
else:
    print(f'  Prophet: 未安装 (pip install prophet)')
