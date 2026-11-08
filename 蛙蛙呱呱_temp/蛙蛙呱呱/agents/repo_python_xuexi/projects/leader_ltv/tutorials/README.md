# 团长生命周期与用户LTV — 教程索引

## 学习路径

```
01 队列分析 → 同月注册的团长,随时间推移留存率怎么降?
02 生存分析 → Kaplan-Meier曲线 + Cox回归 → 什么影响团长存活?
03 LTV建模  → 月GMV × 预期存活 = 终身价值 → 获客成本值不值?
04 流失预警 → 4信号(GMV降/用户降/无订单/骤降) → 提前发现高危团长
05 用户LTV  → 按获客渠道对比LTV → BD激励策略优化
```

## 教程文件

| 文件 | 对应代码 | 核心技能 | 耗时 |
|------|---------|---------|------|
| [01-队列分析.md](01-队列分析.md) | 01_cohort_analysis.py | 留存矩阵/热力图 | 25min |
| [02-生存分析.md](02-生存分析.md) | 02_survival_analysis.py | K-M/Cox/删失 | 35min |
| [03-LTV建模.md](03-LTV建模.md) | 03_ltv_modeling.py | LTV/LTV分层/CAC | 25min |
| [04-团长流失预警.md](04-团长流失预警.md) | 04_churn_prediction.py | 预警信号/规则引擎 | 20min |
| [05-用户LTV渠道.md](05-用户LTV渠道.md) | 05_user_ltv.py | 渠道ROI对比 | 20min |

## 怎么跑

```bash
cd D:\python_xuexi\projects\leader_ltv
python generate_data.py && python 01_cohort_analysis.py && python 02_survival_analysis.py && python 03_ltv_modeling.py && python 04_churn_prediction.py && python 05_user_ltv.py
```
