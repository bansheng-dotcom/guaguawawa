# 美团优选 GMV时间序列预测

## 业务场景

每周一早上，城市总经理问："这周GMV预估多少？下周呢？" 你不能说"不知道"。

时间序列预测就是回答这个问题——基于历史365天数据，预测未来30天的GMV。

## 项目结构

```
time_series_forecast/
├── README.md
├── generate_data.py              # 生成365天GMV(含趋势/季节/节假日)
├── 01_eda_decomposition.py       # 时序探索+季节分解
├── 02_arima_model.py             # ARIMA建模+预测
├── 03_prophet_model.py           # Prophet建模(处理节假日)
├── 04_model_comparison.py        # ARIMA vs Prophet 精度对比
├── 05_forecast_output.py         # 未来30天预测+置信区间
├── data/
└── tutorials/                    # 教程(5篇)
```

## 核心方法

| 方法 | 特点 |
|------|------|
| 季节分解 | 趋势+周期+节假日+残差 → 理解GMV构成 |
| ARIMA | 经典统计模型,处理趋势和自相关 |
| Prophet | Facebook开源,自动处理节假日+周末效应 |

## 快速开始

```bash
cd time_series_forecast
python generate_data.py
python 01_eda_decomposition.py
python 02_arima_model.py
python 03_prophet_model.py
python 04_model_comparison.py
python 05_forecast_output.py
```
