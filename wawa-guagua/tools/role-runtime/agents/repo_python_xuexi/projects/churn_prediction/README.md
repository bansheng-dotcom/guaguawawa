# 美团优选 用户流失预测模型

## 业务场景

社区团购获客成本高、用户迁移成本低（换个团长就是竞对的用户）。
注册后30天内，约35%的用户不再下单。**如果在用户流失前7天发优惠券，召回成本只有流失后再拉回来的1/5。**

本项目的目标：基于用户过去30天的行为数据，**预测未来14天内是否会流失**。
输出TOP 500高危用户名单，供运营精准干预。

## 项目结构

```
churn_prediction/
├── README.md
├── generate_data.py              # 生成用户行为数据(含流失标签)
├── 01_feature_engineering.py     # 特征工程(30+特征)
├── 02_model_training.py          # 逻辑回归 + 随机森林
├── 03_model_evaluation.py        # AUC/混淆矩阵/PR曲线
├── 04_feature_importance.py      # SHAP值 + 特征重要性
├── 05_business_output.py         # 高危用户名单 + 干预建议
├── data/                         # 数据+模型+输出
└── tutorials/                    # 完整教程(5篇)
```

## 特征体系

| 特征类别 | 特征数 | 示例 |
|---------|--------|------|
| RFM衍生 | 5 | recency/frequency/monetary/客单价/件数 |
| 行为比率 | 6 | 点击→下单转化率/加购放弃率/周环比 |
| 时间衰减 | 3 | 时间加权活跃分/下单趋势/衰减系数 |
| 团长关联 | 3 | 团长流失风险/同团长时长/团长活跃度 |
| 用户画像 | 4 | 城市等级/用户类型/年龄段/注册天数 |

## 模型

| 模型 | 作用 | 优点 |
|------|------|------|
| 逻辑回归 | 基线+可解释 | 系数直接告诉你"什么行为最危险" |
| 随机森林 | 精度+非线性 | 捕捉特征交互,精度更高 |

## 快速开始

```bash
cd churn_prediction
python generate_data.py
python 01_feature_engineering.py
python 02_model_training.py
python 03_model_evaluation.py
python 04_feature_importance.py
python 05_business_output.py
```

## 简历可写成

> 构建美团优选用户流失预测模型：从用户行为日志构造30+特征(RFM衍生/
> 行为比率/时间衰减/团长关联)，训练逻辑回归+随机森林二分类模型，
> AUC达0.XX，top20%用户捕获XX%真实流失；
> 基于SHAP值解释特征重要性(recency/frequency为Top2)，输出高危流失名单TOP500+分级干预建议；
> 模型预测准确率可支撑周度自动预警，预计每月挽回流失用户XXX人。
