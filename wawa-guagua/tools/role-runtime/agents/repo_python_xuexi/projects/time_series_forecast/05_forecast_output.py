"""模块05: 未来30天GMV预测 + 周报自动生成"""
import pandas as pd, numpy as np, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("="*60)
print("  模块05: 未来30天GMV预测")
print("="*60)

prophet = pd.read_csv(f'{DATA_DIR}/prophet_forecast.csv'); prophet['ds'] = pd.to_datetime(prophet['ds'])
forecast = prophet[prophet['ds'] > '2025-12-31']

print(f"\n  未来30天GMV预测(Prophet):")
print(f"  {'日期':<14} {'预测GMV':<12} {'下限':<12} {'上限':<12}")
print(f"  {'-'*50}")

weekly_summary = []
for i, (_, row) in enumerate(forecast.iterrows()):
    print(f"  {row['ds'].strftime('%m-%d'):<14} {row['yhat']:<12.0f} {row['yhat_lower']:<12.0f} {row['yhat_upper']:<12.0f}")
    if (i+1) % 7 == 0:
        week_gmv = forecast.iloc[i-6:i+1]['yhat'].sum()
        weekly_summary.append((row['ds'], week_gmv))

print(f"\n  周度汇总:")
for ds, gm in weekly_summary:
    print(f"    {ds.strftime('%m-%d')}周: {gm:.0f}元")

total = forecast['yhat'].sum()
ci_l = forecast['yhat_lower'].sum()
ci_u = forecast['yhat_upper'].sum()
print(f"\n  30天总GMV预测: {total:.0f}元 (80%CI: {ci_l:.0f} ~ {ci_u:.0f})")
print(f"  日均: {forecast['yhat'].mean():.0f}元")
