"""模块02: ARIMA建模 + 滚动预测"""
import pandas as pd, numpy as np, os, warnings, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/daily_gmv.csv'); df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')
gmv = df['gmv']

print("="*60)
print("  模块02: ARIMA建模")
print("="*60)

# 训练/测试划分(时序不能随机!)
train = gmv[:335]  # 前11个月
test = gmv[335:]   # 最后30天

# ARIMA(7,1,1) — p=7天自回归,d=1阶差分,q=1天移动平均
model = ARIMA(train, order=(7,1,1))
fitted = model.fit()
print(f"  AIC: {fitted.aic:.0f}")

# 滚动预测(避免look-ahead bias)
forecasts = []
history = list(train)
for t in range(len(test)):
    m = ARIMA(history, order=(7,1,1))
    m_fit = m.fit()
    forecasts.append(m_fit.forecast()[0])
    history.append(test.iloc[t])

mae = mean_absolute_error(test, forecasts)
mape = mean_absolute_percentage_error(test, forecasts) * 100
print(f"  测试集 MAE: {mae:.0f}元 | MAPE: {mape:.1f}%")

# 保存预测结果
pd.DataFrame({'date':test.index,'actual':test.values,'arima_pred':forecasts}).to_csv(
    f'{DATA_DIR}/arima_predictions.csv',index=False,encoding='utf-8-sig')
print(f'[预测已保存] data/arima_predictions.csv')
