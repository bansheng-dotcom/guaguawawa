# 美团优选 社区团购 SQL漏斗分析

## 业务场景

美团优选单城市(假设为保定市)的完整用户行为链路：
团长在微信群分享商品 → 用户点击 → 加购 → 下单 → T+1自提 → 复购

本项目包含真实社区团购数据模型下的SQL分析全链路。

## 数据模型(7张表)

```
group_leaders(团长)  users(用户)  products(商品)
       │                  │            │
       │         ┌────────┼────────┐   │
       │         │        │        │   │
       ▼         ▼        ▼        ▼   ▼
 share_click_logs    orders ──── order_items
 (分享→点击→加购)      │              │
                        ▼              │
                   fulfillment ◄──────┘
                   (履约/损耗)
```

| 表 | 说明 | 行数 |
|----|------|------|
| group_leaders | 团长(姓名/城市/社区) | ~200 |
| users | 用户(城市/常购团长/注册日) | ~30,000 |
| products | 商品(品类/单价/保质期/供应商距离) | ~800 |
| orders | 订单(团长/金额/件数/T+1配送) | ~50,000 |
| order_items | 订单明细(商品/数量/金额) | ~180,000 |
| behavior_logs | 用户行为(分享→点击→加购→下单) | ~500,000 |
| fulfillment | 履约(网格仓/距离/成本/损耗) | ~50,000 |

## 分析模块

| 模块 | 内容 | 核心SQL技能 |
|------|------|-----------|
| 01 数据探索 | 表结构、字段含义、基础聚合 | SELECT/JOIN/GROUP BY |
| 02 漏斗分析 | 团长分享→点击→加购→下单→自提 5步漏斗 | CTE/窗口函数/转化率 |
| 03 用户分群 | 团购RFM模型(频次/金额/最近购买) | 窗口函数/CASE WHEN |
| 04 留存复购 | 次日复购率/7日留存/周度复购 | 自连接/日期函数 |
| 05 团长归因 | 首次/末次触点归因、团长GMV贡献 | 窗口函数/PARTITION BY |
| 06 可视化 | Python漏斗图/留存曲线/RFM热力图 | Pandas/Matplotlib/Seaborn |

## 快速开始

```bash
cd sql_funnel_analysis

# 1. 生成数据
python generate_data.py

# 2. 加载到SQLite并执行所有SQL分析
python run_all.py

# 3. 可视化
python 06_python_visualization.py
```

## 技术栈

- SQL: SQLite(标准SQL语法,兼容MySQL/PostgreSQL)
- Python: Pandas、NumPy、Matplotlib、Seaborn
- 数据库: sqlite3(Python内置,无需安装)

## 简历可写成

> 基于美团优选社区团购业务，搭建7表数据模型(团长/用户/商品/订单/明细/行为日志/履约)；
> 编写SQL实现团长分享→点击→加购→下单→自提5步转化漏斗分析，
> 定位最大流失环节(加购→下单转化率仅XX%)；
> 使用窗口函数实现RFM用户分层(K-means聚类)，识别高价值团长及用户群；
> 计算次日复购率、7日留存率，按城市等级与团长密度维度下钻；
> 搭建Python+Tableau可视化看板，覆盖漏斗/留存/用户分群/团长归因四大模块。
