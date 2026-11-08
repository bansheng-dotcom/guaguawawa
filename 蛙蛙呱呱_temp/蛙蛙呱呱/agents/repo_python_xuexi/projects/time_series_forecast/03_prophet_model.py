"""模块03: Prophet建模 — 自动处理节假日+周末效应"""
import pandas as pd, numpy as np, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

plt.rcParams['font.sans-serif'] = ['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/daily_gmv.csv'); df['date'] = pd.to_datetime(df['date'])
print("="*60)
print("  模块03: Prophet建模")
print("="*60)

try:
    from prophet import Prophet
    PROPHET_OK = True
except ImportError:
    print("  [WARNING] prophet未安装! pip install prophet")
    PROPHET_OK = False

if PROPHET_OK:
    # 准备数据(Prophet要求ds/y格式)
    prophet_df = df[['date','gmv']].rename(columns={'date':'ds','gmv':'y'})

    # 训练/测试划分
    train = prophet_df[:335]; test = prophet_df[335:]

    # 模型: 自动检测周季节 + 年季节
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,  # 趋势变化灵敏度
    )
    # 添加中国节假日
    m.add_country_holidays(country_name='CN')

    m.fit(train)

    # 预测
    future = m.make_future_dataframe(periods=30)
    forecast = m.predict(future)

    # 评估
    test_pred = forecast[-30:]['yhat'].values
    test_actual = test['y'].values
    mae = mean_absolute_error(test_actual, test_pred)
    mape = mean_absolute_percentage_error(test_actual, test_pred)*100
    print(f"  Prophet MAE: {mae:.0f}元 | MAPE: {mape:.1f}%")

    # 保存
    forecast[['ds','yhat','yhat_lower','yhat_upper']].to_csv(
        f'{DATA_DIR}/prophet_forecast.csv',index=False,encoding='utf-8-sig')
    print(f'[预测已保存] data/prophet_forecast.csv')

    # 组件分解
    fig = m.plot_components(forecast)
    plt.tight_layout(); plt.savefig(f'{DATA_DIR}/prophet_components.png',dpi=150)
    print(f'[图表已保存] data/prophet_components.png')
