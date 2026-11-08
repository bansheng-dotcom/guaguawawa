# 美团优选 经营分析指标体系与BI看板

## 业务场景

你是美团优选保定市的数据分析师。每个月要向城市总经理汇报经营状况。
你需要一个完整的经营分析体系：指标体系、异动监控、归因分析、可视化看板。

## 指标体系(OSM模型)

```
Objective(目标):        提升区域GMV和用户规模，同时控制履约成本与损耗
    │
Strategy(策略):        优化爆品推荐 → 提升转化率
                      优化供给匹配 → 降低履约成本
                      团长赋能     → 提升团长人均GMV
    │
Measurement(指标):
    北极星: 人均GMV、人均件数
    健康度: 履约成本率、生鲜损耗率、退货率
    规模:   订单量、用户数、活跃团长数
    效率:   团长人均GMV、件均履约成本
```

## 项目结构

```
kpi_dashboard/
├── README.md
├── generate_data.py          # 生成12个月经营数据(含异常注入)
├── 01_kpi_design.py          # 指标体系设计+OSM+北极星论证
├── 02_anomaly_detection.py   # 异动监控规则(10+条)
├── 03_root_cause.py          # 归因分析决策树
├── 04_dashboard.py           # Python经营看板(6合1图表)
├── 05_monthly_report.py      # 月度经营分析报告(Markdown)
├── data/                     # 数据+输出
└── tutorials/                # 完整教程(5篇)
```

## 快速开始

```bash
cd kpi_dashboard
python generate_data.py
python 01_kpi_design.py
python 02_anomaly_detection.py
python 03_root_cause.py
python 04_dashboard.py
python 05_monthly_report.py
```

## 简历可写成

> 基于OSM模型设计社区团购经营指标体系，覆盖北极星(GMV+件数)、
> 健康度(履约成本率/损耗率)、规模(订单/用户/团长)、效率(人均产出)四层15+指标；
> 设计10+条异动监控规则(含阈值+告警等级+归因方向)，
> 实现归因决策树(指标异动→维度拆解→根因定位)；
> 搭建Python经营看板(高管概览/经营分析/异动监控三屏)；
> 产出月度经营分析报告，为区域GMV年环比22%增长提供数据支撑。
