# model-release · 好结论范例

## 范例 1：模型卡五要素齐备

> support-qa-assistant 模型卡通过交付门禁。
> - 用途：客服一线问答辅助，答案需人工复核后发出。
> - 限制：不覆盖退款金额计算与法律咨询；不应用于自动对客发送。
> - 风险分层 medium；许可 proprietary；已知偏差：非中文提问质量下降、长尾政策覆盖不足。
> 移交：实际分发交 R09，风险与许可的法律判定交 R03。

## 范例 2：资产可溯源

> 资产清单 3 项全部可溯源：
> - runs:/run-88213/model（model_file）
> - runs:/run-88213/eval_report.json（eval_report）
> - runs:/run-88213/latency_chart.png（chart）
> 每项均绑定 run-88213，可回溯到产生它的实验运行。

## 范例 3：模型卡不合格退回

> support-qa-assistant 模型卡被拒收。
> - 限制为空：未写清「不能用来干什么」。
> - 风险分层填 none（不在白名单 {low,medium,high}）。
> - 许可填「免费随便用」（不在白名单）。
> 下一步：补齐五要素后重新提交。
