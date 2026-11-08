# 03 Prophet模型

## 为什么需要Prophet？

ARIMA处理节假日很痛苦——需要手动构造哑变量。Prophet自动识别：
- 中国法定节假日（春节/国庆/中秋）
- 周末效应
- 趋势变点（增长率什么时候变了？）

## 核心参数

`changepoint_prior_scale=0.05` → 趋势变化的灵活度。越大越灵活（可能过拟合），越小越平滑。

## Prophet输出
- `yhat`: 点预测
- `yhat_lower/yhat_upper`: 80%置信区间
- 组件分解: 趋势+节假日+周季节

安装: `pip install prophet`

[← 02 ARIMA](02-ARIMA.md) | [→ 04 模型对比](04-模型对比.md)
