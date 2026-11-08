# 美团优选 团长生命周期与用户LTV分析

## 业务场景

团长是社区团购的核心资产——他们拉新、维护用户、处理售后。
但团长也会流失——开店、关店、转去竞对。

你需要回答：
- 一个新团长平均能活跃多久？（6个月？1年？）
- 什么因素影响团长的存活？（城市等级/密度/初始GMV？）
- 一个团长的终身价值(LTV)是多少？获客成本是否合理？
- 用户的LTV按获客渠道（团长拉新 vs 自然流量）有差异吗？

## 项目结构

```
leader_ltv/
├── README.md
├── generate_data.py              # 生成团长24个月活动数据(含删失)
├── 01_cohort_analysis.py         # 队列留存热力图
├── 02_survival_analysis.py       # Kaplan-Meier生存曲线 + Cox模型
├── 03_ltv_modeling.py            # LTV计算 + 团长分层
├── 04_churn_prediction.py        # 团长流失预警(30天)
├── 05_user_ltv.py                # 用户LTV(按获客渠道对比)
├── data/                         # 数据+图表
└── tutorials/                    # 教程(5篇)
```

## 核心方法

| 方法 | 解决的问题 |
|------|----------|
| 队列分析(Cohort) | "每月注册的团长，存活率随时间如何衰减？" |
| Kaplan-Meier | "团长中位存活期是几个月？不同城市有差异吗？" |
| Cox比例风险 | "什么因素最影响团长存活？(多变量)" |
| LTV = 月GMV × 存活月数 | "一个团长值多少钱？值得花多少成本去招募？" |

## 快速开始

```bash
cd leader_ltv
python generate_data.py
python 01_cohort_analysis.py
python 02_survival_analysis.py
python 03_ltv_modeling.py
python 04_churn_prediction.py
python 05_user_ltv.py
```

## 简历可写成

> 分析美团优选团长生命周期：构建24个月队列留存热力图，
> Kaplan-Meier生存曲线显示团长中位存活X个月(一线Y月 vs 三五线Z月)；
> Cox回归识别存活关键因子(团长密度/初始GMV/城市等级)；
> LTV模型:月均GMV×预期存活=XXX元,指导团长招募预算上限；
> 按获客渠道对比用户LTV(团长拉新vs自然流量)，为BD考核提供数据依据。
