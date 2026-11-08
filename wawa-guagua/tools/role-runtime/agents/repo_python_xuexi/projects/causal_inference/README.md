# 美团优选 优惠券效果因果推断

## 业务场景

运营团队给一批"高活跃用户"发了满20-5优惠券。发完后这批用户的GMV涨了15%。

运营说："优惠券效果显著！全量发！"

你说："等等——这批用户本来就是高活跃的,不发券他们GMV也会涨。
你需要知道的是'如果不发券,他们GMV会是多少'——但我们永远观测不到这个反事实。"

这就是因果推断要解决的问题。

## 核心方法

| 方法 | 解决的问题 |
|------|----------|
| 朴素对比 | 收到券 vs 没收到券 —— 有选择偏差,不可信 |
| PSM | 匹配"倾向得分"相近的用户 → 近似随机对照 |
| DiD | 比较处理组和对照组"前后变化"的差异 → 消除时间趋势 |
| 敏感性分析 | "如果存在一个未观测的混淆变量,结论还成立吗？" |

## 项目结构

```
causal_inference/
├── README.md
├── generate_data.py              # 生成含选择偏差的观测数据
├── 01_naive_comparison.py        # 朴素对比(展示选择偏差)
├── 02_propensity_score.py        # PSM倾向得分匹配
├── 03_difference_in_diff.py      # DID双重差分
├── 04_sensitivity_analysis.py    # 敏感性分析
├── 05_causal_report.py           # 因果推断完整报告
├── data/
└── tutorials/                    # 教程(5篇)
```

## 快速开始

```bash
cd causal_inference
python generate_data.py
python 01_naive_comparison.py
python 02_propensity_score.py
python 03_difference_in_diff.py
python 04_sensitivity_analysis.py
python 05_causal_report.py
```
