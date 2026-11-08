# 用户流失预测模型 — 教程索引

## 这个项目在讲什么

美团优选每天有用户在流失——注册后30天不来了。获客成本50元/人，与其花钱拉新，不如**提前识别谁要走，发张优惠券挽留**。

这个项目带你从零搭建一个ML流失预测模型——特征工程→训练→评估→解释→业务落地。

---

## 学习路径

```
01 特征工程 → 从行为日志构造30+特征(RFM/行为比率/时间衰减/团长)
02 模型训练 → 逻辑回归(基线) vs 随机森林, 交叉验证
03 模型评估 → AUC/混淆矩阵/PR曲线/阈值调优/Lift曲线
04 特征解释 → 特征重要性 + SHAP → "什么行为最预示流失?"
05 业务输出 → TOP500高危名单 + 分级干预策略 + ROI估算
```

---

## 教程文件

| 文件 | 对应代码 | 核心技能 | 耗时 |
|------|---------|---------|------|
| [01-特征工程.md](01-特征工程.md) | 01_feature_engineering.py | 特征构造/标准化/One-hot | 35min |
| [02-模型训练.md](02-模型训练.md) | 02_model_training.py | LR/RF/交叉验证 | 30min |
| [03-模型评估.md](03-模型评估.md) | 03_model_evaluation.py | AUC/PR/阈值/Lift | 35min |
| [04-特征解释.md](04-特征解释.md) | 04_feature_importance.py | 特征重要性/SHAP | 25min |
| [05-业务落地.md](05-业务落地.md) | 05_business_output.py | 高危名单/ROI | 20min |

## 怎么跑

```bash
cd D:\python_xuexi\projects\churn_prediction
python generate_data.py && python 01_feature_engineering.py && python 02_model_training.py && python 03_model_evaluation.py && python 04_feature_importance.py && python 05_business_output.py
```
