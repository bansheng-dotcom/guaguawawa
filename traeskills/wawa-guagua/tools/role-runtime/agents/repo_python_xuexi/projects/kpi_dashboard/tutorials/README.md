# 经营分析指标体系与BI看板 — 教程索引

## 这个项目在讲什么

你是美团优选保定市的数据分析师。每月初要向城市总经理汇报上月经营情况。

城市总问的问题永远只有三个：
1. **"上个月做得好不好？"** — 你要有KPI来衡量
2. **"哪里出了问题？"** — 你要有异动监控来发现
3. **"问题出在哪个环节？"** — 你要有归因框架来定位

这套项目就把这三件事串起来——指标体系→异动监控→归因分析→看板→报告。

---

## 教程文件

| 文件 | 对应代码 | 内容 | 耗时 |
|------|---------|------|------|
| [01-指标体系.md](01-指标体系.md) | 01_kpi_design.py | OSM模型/北极星论证/指标分层 | 30min |
| [02-异动监控.md](02-异动监控.md) | 02_anomaly_detection.py | 10条监控规则/滚动窗口/z-score | 30min |
| [03-归因分析.md](03-归因分析.md) | 03_root_cause.py | 决策树归因/量价拆解/品类归因 | 35min |
| [04-看板搭建.md](04-看板搭建.md) | 04_dashboard.py | Python看板(6合1图表) | 25min |
| [05-经营报告.md](05-经营报告.md) | 05_monthly_report.py | 月度报告模板/汇报结构 | 20min |

---

## 怎么跑代码

```bash
cd D:\python_xuexi\projects\kpi_dashboard

python generate_data.py        # 生成12个月数据
python 01_kpi_design.py        # 指标体系设计
python 02_anomaly_detection.py # 异动监控
python 03_root_cause.py        # 归因分析
python 04_dashboard.py         # 生成看板
python 05_monthly_report.py    # 生成月报
```

---

## 学习节奏

- **Day 1**: 01 — 理解OSM模型，为什么选这些指标
- **Day 2**: 02+03 — 异动监控+归因分析(面试高频:怎么定位GMV下降?)
- **Day 3**: 04+05 — 看板+报告(落地)
