# W25：BI 与工程接口（1/12 — 1/18）

> 🎯 **本周目标**：BI 工具不是你分析工作的终点——它是你分析结果的"展示层"。本周你要理解 BI 和工程之间的接口——SQL→BI 的数据管道、Dashboard 的数据刷新策略、以及"为什么两个 Dashboard 上同一个指标数字不一样"的根因。学完这周，你能回答面试官："你做的报表怎么保证和数据库里的数一致？"
>
> 📎 **本周主课**：PowerBI/Tableau——数据接入/DAX/仪表盘设计/发布刷新
>
> 🏢 **本周场景**：鲜果多的运营总监现在每天打开你做的 Dashboard 看经营数据。有一天她发现 Dashboard 上的 GMV 和你昨天邮件里的不一样——差了几个小时的数据。你需要解释"为什么不一样"——以及建立策略让"不一样"不再发生。

---

## D1（周一 1/12）：BI 和 Python 分析的接口——不是"导出 CSV 再导入 BI"


---

---

### Python -> BI 的标准架构——松耦合的接口设计

数据分析师的 BI 架构不是"先分析再导入 BI"——是"分析结果写回数据库——BI 直读数据库"。

```
Python (每天 8:00 AM 跑):
  main.py -> 读 ODS -> 清洗 -> 聚合 -> 写 DWS 层的指标表

BI (用户随时打开):
  连接 DWS 层 -> 刷新 Dashboard -> 展示最新数据
```

这样 Python 不用知道 BI 的存在。BI 不用知道 Python 的存在。它们通过数据库的一张表来接口——这就是松耦合。

**在你还没装 BI 工具时——用 Python 模拟一个 Dashboard 的数据源层：**

```python
def prepare_dashboard_data(df: pd.DataFrame) -> dict:
    """为 BI 工具准备数据集市——每张输出表 = 一个 Dashboard 的数据源。

    输出表清单:
    1. daily_kpi: 日报核心指标——对应 Dashboard 的 KPI 数字区
       刷新频率: 每天 8:00 AM——数据延迟 T+1
    2. city_breakdown: 城市维度明细——对应 Dashboard 的城市柱状图
       刷新频率: 每天 8:00 AM——数据延迟 T+1
    3. cohort_retention: 用户留存队列——对应 Dashboard 的留存热力图
       刷新频率: 每周一 8:00 AM——数据延迟 T+1（周级别）
    """
    # 表1: 日报核心指标
    daily_kpi = df.groupby('date').agg(
        gmv=('amount', 'sum'),
        orders=('order_id', 'nunique'),
        users=('user_id', 'nunique'),
        avg_order_value=('amount', 'mean')
    ).reset_index()
    daily_kpi.to_parquet('output/daily_kpi.parquet')

    # 表2: 城市维度明细
    city_breakdown = df.groupby(['date', 'city']).agg(
        gmv=('amount', 'sum'),
        orders=('order_id', 'nunique')
    ).reset_index()
    city_breakdown.to_parquet('output/city_breakdown.parquet')

    # 表3: 用户留存队列
    df['cohort_month'] = df.groupby('user_id')['order_date'].transform('min').dt.to_period('M')
    df['order_month'] = df['order_date'].dt.to_period('M')
    cohort = df.groupby(['cohort_month', 'order_month'])['user_id'].nunique().unstack()
    cohort.to_parquet('output/cohort_retention.parquet')

    return {
        'daily_kpi': len(daily_kpi),
        'city_breakdown': len(city_breakdown),
        'cohort_retention': cohort.shape
    }
```

**面试时——面试官问"你怎么把分析结果呈现给业务方"——你打开这个函数——"我设计了 BI 就绪的数据集市——每张输出表对应 Dashboard 上的一个图表——刷新频率和延迟在 docstring 中标注。BI 工具直连这些表——每次打开 Dashboard 都是最新数据——不需要我手动导出 CSV。"**

> 📓 今日主课：BI 工具全景——PowerBI vs Tableau vs Metabase

---

### 🔴 认知冲突

你以前做分析——Python 处理完数据，`df.to_csv('output/report.csv')`，然后手动导入 BI 工具。每次数据更新——你都要手动重新导出、重新导入。这不是"自动化"——你成了 CSV 搬运工。

**问题**：BI 工具应该直接连数据库——不是连你导出的 CSV。为什么？因为 CSV 是"快照"——它在生成的那一刻就已经过时了。BI 工具直连数据库——每次打开 Dashboard 都是最新的数据。

---

### 📖 核心原理

**数据分析师的 BI 架构——不是"先分析再导入 BI"，是"分析结果写回数据库，BI 直读数据库"。**

```
Python (每天 8:00 AM 跑):
  main.py → 读 ODS → 清洗 → 聚合 → 写 DWS 层的指标表

BI (用户随时打开):
  连接 DWS 层 → 刷新 Dashboard → 展示最新数据
```

这样 Python 不用知道 BI 的存在。BI 不用知道 Python 的存在。它们通过**数据库的一张表**来接口——这就是松耦合。

**在你还没装 BI 工具时——用 Python 模拟一个 Dashboard 的"数据源层"：**

```python
def prepare_dashboard_data(df):
    """为 BI 工具准备数据集市——每张输出表 = 一个 Dashboard 的数据源。"""
    # 表1: 日报核心指标
    daily_kpi = df.groupby('date').agg({...}).reset_index()
    daily_kpi.to_parquet('output/daily_kpi.parquet')

    # 表2: 城市维度明细
    city_breakdown = df.groupby(['date', 'city']).agg({...}).reset_index()
    city_breakdown.to_parquet('output/city_breakdown.parquet')
```

每张表对应 Dashboard 上的一个图表——更新频率（每天/每小时）在 docstring 里标注。

---

### ✍️ 动手练习

1. 在你鲜果多项目中实现 `prepare_dashboard_data()`——输出至少 3 张"BI 就绪"的聚合表。
2. 每张表的 docstring 标注：刷新频率 + 数据延迟 + 对应 Dashboard 上的哪个图表。
3. `git add . && git commit -m "add BI-ready dataset preparation layer" && git push`

---

## D2（周二 1/13）：指标一致性——为什么两个地方的同一个指标不一样


---

---

### 指标一致性的完整解决方案——不是"检查一次"——是"持续监控"

指标一致性不是"上线时检查一次"就完了——数据管道在持续运行——口径可能漂移——刷新时间可能滞后。解决方案——把 check_metric_consistency() 加入日报流程——每天早上 Python 分析完成后——自动对比 Python 结果和 BI Dashboard 上的对应指标——差异超过阈值自动告警。

```python
def daily_consistency_check():
    """每日指标一致性检查——日报流程的最后一步。"""
    # Python 分析结果
    python_gmv = compute_gmv(orders_clean)
    python_orders = len(orders_clean)

    # BI Dashboard 数据——从同一张 DWS 表读取
    bi_data = pd.read_sql("SELECT * FROM dws_daily_kpi WHERE date = CURRENT_DATE - 1", engine)
    bi_gmv = bi_data['gmv'].sum()
    bi_orders = bi_data['orders'].sum()

    results = []
    for name, py_val, bi_val in [
        ('GMV', python_gmv, bi_gmv),
        ('订单数', python_orders, bi_orders)
    ]:
        result = check_metric_consistency(py_val, bi_val, name)
        results.append(result)
        if not result['consistent']:
            logger.warning(f'指标一致性检查失败: {name}——diff={result["diff_pct"]:.1f}%')
            for issue in result['issues']:
                if issue['status'] == 'fail':
                    logger.warning(f'  - {issue["check"]}: {issue.get("detail", "")}')

    all_consistent = all(r['consistent'] for r in results)
    if not all_consistent:
        send_alert_email(
            subject=f'指标一致性告警——{sum(1 for r in results if not r["consistent"])} 个指标不一致',
            body=format_consistency_results(results)
        )

    return {'all_consistent': all_consistent, 'results': results}
```

**这个函数的价值——不是"发现不一致"——是"在不一致影响决策之前就发现"。** 运营总监打开 Dashboard 之前——你已经知道 Python 和 BI 的数据是否一致——如果不一致——你已经收到了告警——并且在排查中了。

**面试时——面试官问"你怎么保证 Dashboard 的数据准确"——你回答——"我把指标一致性检查集成到了日报流程中——每天早上 Python 分析完成后——自动对比 Python 结果和 BI Dashboard 数据——差异超过 1% 自动告警。不是'运营总监发现不一致再来找我'——是'不一致发生时我已经在修了'。"**


---

---

### 指标一致性的完整检查清单与工程实现

```python
def check_metric_consistency(python_result: float, bi_result: float,
                             metric_name: str, tolerance: float = 0.01) -> dict:
    """指标一致性检查——Python 分析结果 vs BI Dashboard 结果。

    四个检查维度——逐项对比——报告差异。
    """
    diff_pct = abs(python_result - bi_result) / max(abs(python_result), 1) * 100
    issues = []

    # Check 1: 口径一致？
    # 这个检查需要人工确认——代码只能标记"请确认口径"
    issues.append({
        'check': '口径', 'status': 'manual',
        'action': f'确认 {metric_name} 的分子/分母/时间窗口在 Python 和 BI 中一致'
    })

    # Check 2: 刷新时间一致？
    issues.append({
        'check': '刷新时间', 'status': 'manual',
        'action': f'确认 Python 数据截止时间 = BI 数据截止时间'
    })

    # Check 3: 数据源一致？
    issues.append({
        'check': '数据源', 'status': 'manual',
        'action': f'确认 Python 和 BI 读的是同一张表/同一个文件'
    })

    # Check 4: 数值偏差在容差内？
    if diff_pct > tolerance * 100:
        issues.append({
            'check': '数值', 'status': 'fail',
            'detail': f'{metric_name}: Python={python_result:.2f}, BI={bi_result:.2f}, diff={diff_pct:.1f}%',
            'root_causes': [
                '口径差异——检查 WHERE 条件/JOIN 逻辑',
                '刷新时间差异——Python 8:00 跑的——BI 9:00 刷新的',
                '处理逻辑差异——Python 去重了——BI 没去重'
            ]
        })
    else:
        issues.append({
            'check': '数值', 'status': 'pass',
            'detail': f'{metric_name}: diff={diff_pct:.2f}% < {tolerance*100}%'
        })

    return {
        'metric': metric_name,
        'python_value': python_result,
        'bi_value': bi_result,
        'diff_pct': diff_pct,
        'consistent': diff_pct <= tolerance * 100,
        'issues': issues
    }
```

**这个函数的价值——不是"比较两个数字"——是"当两个数字不一致时——给出排查方向"。** 运营总监问"为什么 Dashboard 上的 GMV 和你邮件里不一样"——你跑这个函数——如果 diff > 1%——自动输出四个可能的根因——不需要从零排查。

**面试回答模板:** "我怎么保证 Dashboard 上的数据和我的分析结论一致——我写了一个 check_metric_consistency() 函数——每次 Python 分析完成后——自动对比 Python 结果和 BI Dashboard 上的对应指标——如果差异超过 1%——自动标记——并从口径/刷新时间/数据源/处理逻辑四个维度给出排查方向。"

> 📓 今日主课：PowerBI 数据接入——直连数据库 vs 导入模式

---

### 🔴 认知冲突

运营总监发现——Dashboard 上显示的 GMV 是 523 万，你邮件里的 GMV 是 518 万。同一个指标——两个数字。

排查后发现：
- Dashboard 用的是 `SUM(amount)`——WHERE 条件里没有排除测试用户
- 你邮件里的分析排除了一行 `user_id LIKE 'test_%'` 的测试订单
- Dashboard 的数据刷新时间是 9:00 AM，你邮件是 8:00 AM 跑的——中间隔了一个小时，ERP 新增了 200 个订单

**问题**：指标一致性不是技术问题——是**口径管理**问题。你 W12D1 学了指标口径三要素——现在把它应用到 BI 场景中。

---

### 📖 核心原理

**指标一致性检查清单——每次做 Dashboard 之前对照：**

| 检查项 | 问什么 | 示例 |
|--------|--------|------|
| **口径** | 分子/分母/时间窗口在两个地方一样吗？ | Python: `WHERE user_id NOT LIKE 'test_%'`; BI: 忘记加了 |
| **刷新时间** | 两个数据源的数据截止时间一样吗？ | Python: 8:00 AM 的 snapshot; BI: 9:00 AM 刷新 |
| **数据源** | 读的是同一张表/同一个文件吗？ | Python: DWS 表; BI: ODS 表（忘了跳一层） |
| **处理逻辑** | 有没有"你以为一样但其实不一样"的中间变换？ | Python: 去重; BI: 没去重 |

**面试标准回答**——当面试官问"你怎么保证 Dashboard 上的数据和你的分析结论一致"——你直接背诵这 4 个检查项。

---

### ✍️ 动手练习

1. 在 `docs/metric_consistency_checklist.md` 中写入上述 4 个检查项。
2. 对你已有的鲜果多项目——跑一遍一致性检查：`main.py` 的输出 vs 手动汇总的数据。
3. `git add docs/ && git commit -m "add metric consistency checklist for BI vs Python analysis" && git push`

---

## D3（周三 1/14）：Dashboard 的数据刷新策略——实时 vs 每小时 vs 每天


---

---

### Dashboard 刷新策略的完整决策框架

不是所有数据都需要实时刷新。刷新策略取决于"决策频率"和"数据量"和"计算成本"。

| 刷新频率 | 适用场景 | 数据量 | 计算成本 | 技术实现 | 面试怎么说 |
|---------|---------|--------|---------|---------|----------|
| 实时（秒级） | 运维监控、欺诈检测 | 每个事件都写入 | 高——需要流处理 | Kafka/Flink | "CEO 不需要每秒看 GMV——但风控系统需要" |
| 每小时 | 当日经营概览 | 增量计算 | 中——只算最近一小时 | cron + 增量 SQL | "运营下午 3 点看今天到现在的 GMV——判断今天能不能达标" |
| 每天 | 日报——"昨天正式结算了多少" | 全量计算 | 中——全量跑一次 | cron + python main.py | "财务每天早上 9 点需要昨天全天的最终数据——不能是'到目前为止'" |
| 每周/每月 | 周报/月报——复盘和策略调整 | 预聚合 | 低——从 DWS 聚合表取 | cron + SQL | "月报不需要每天刷新——每月 1 号跑一次就行——数据变化慢" |

**刷新策略选择的三步决策法:**

1. **决策者什么时候需要看这个数据？** 如果决策者每 4 小时看一次——4 小时刷新一次就够了——不需要实时。
2. **数据源什么时候更新？** 如果数据源是 T+1 的（如 ERP 日终跑批）——Dashboard 设"每小时刷新"没有意义——因为数据直到 T+1 才会变。
3. **计算成本是否值得？** 每次刷新扫描 5000 万行——耗时 3 分钟——每小时跑一次 = 每天浪费 72 分钟的数据库资源。每天跑一次 = 3 分钟。三倍差异——根据决策频率选择——而不是"越频繁越好"。

**面试时——面试官问"你的 Dashboard 多久刷新一次"——你不要说"每天"就结束了——你说"我根据决策频率、数据源更新频率、计算成本——综合考虑后选择了每天 8:00 AM 刷新——因为数据源是 T+1 的——更频繁的刷新没有增量价值。"**

> 📓 今日主课：Dashboard 设计——四象限/交互/故事线

---

### 📖 核心原理

**不是所有数据都需要实时刷新。刷新策略取决于"决策频率"：**

| 刷新频率 | 适用场景 | 数据量 | 面试怎么说 |
|---------|---------|--------|----------|
| 实时（秒级） | 运维监控、欺诈检测 | 每个事件都写入 | "CEO 不需要每秒看 GMV——但风控系统需要" |
| 每小时 | 当日经营概览——"今天到目前为止怎么样" | 增量计算 | "运营下午 3 点看今天到现在的 GMV 够不够目标" |
| 每天 | 日报——"昨天正式结算了多少" | 全量计算 | "财务每天早上 9 点需要昨天全天的最终数据" |
| 每周/每月 | 周报/月报——复盘和策略调整 | 预聚合 | "月报不需要每天刷新——每月 1 号跑一次就行" |

---

### ✍️ 动手练习

1. 在 README 的"数据全链路"表中，给每张输出表加"刷新频率"列。
2. 确认你项目中的每张输出表——真的需要按照声明的频率刷新吗？
3. `git add README.md && git commit -m "add refresh cadence to data lineage table" && git push`

---

## D4（周四 1/15）：SQL 片段管理——你的 BI 查询也应该版本控制


---

---

### SQL 片段管理的完整工作流——从 BI 工具到 Git 到 CI

**SQL 文件的版本管理不仅仅是"保存 .sql 文件"——是一个完整的工程流程:**

1. 在 BI 工具中写好 SQL——验证结果正确
2. 把 SQL 复制到 src/sql/ 目录——按用途命名——加标准化注释头
3. git commit——和 Python 代码一起提交
4. CI 中可选——用 sqlfluff 检查 SQL 风格一致性——类似 ruff 检查 Python

```sql
-- src/sql/daily_kpi.sql
-- ============================================================
-- Dashboard: 日报核心 KPI
-- 用途: 日报 Dashboard 的 KPI 数字区
-- 刷新频率: 每天 8:00 AM——数据延迟 T+1
-- 依赖表: dws_daily_city_kpi
-- 创建日期: 2026-01-15
-- 最后修改: 2026-01-16 (added avg_order_value)
-- ============================================================
SELECT
    date,
    SUM(gmv) AS total_gmv,
    SUM(orders) AS total_orders,
    COUNT(DISTINCT user_id) AS total_users,
    ROUND(SUM(gmv)::numeric / NULLIF(SUM(orders), 0), 2) AS avg_order_value
FROM dws_daily_city_kpi
WHERE date = CURRENT_DATE - INTERVAL '1 day'
  AND user_id NOT LIKE 'test_%'  -- W12D1 口径: 排除测试用户
GROUP BY date;
```

**面试时——面试官追问"你怎么保证 BI 里的 SQL 和代码库里的 SQL 是一致的"——你回答——"src/sql/ 是 SQL 的唯一真相来源。BI 工具里的 SQL 从 src/sql/ 复制过去——修改也在 src/sql/ 里修改——然后更新 BI。如果 BI 里的 SQL 和 src/sql/ 不一致——src/sql/ 是正确的——因为它是被 Git 管理的——有版本历史——BI 里的 SQL 随时可能被覆盖/丢失。"**


---

---

### SQL 片段管理的工程化实践——不只是"保存 .sql 文件"——是"让 SQL 和 Python 一样被管理"

**src/sql/ 目录的完整结构——每个 SQL 文件顶部有标准注释块:**

```sql
-- ============================================================
-- Dashboard: 日报核心 KPI
-- 用途: 鲜果多日报 Dashboard 的 KPI 数字区——GMV/订单数/用户数/客单价
-- 刷新频率: 每天 8:00 AM——数据延迟 T+1
-- 依赖表: dws_daily_city_kpi (DWS 层——每日聚合表)
-- 创建日期: 2026-01-15
-- 最后修改: 2026-01-15
-- ============================================================
SELECT
    date,
    SUM(gmv) AS total_gmv,
    SUM(orders) AS total_orders,
    SUM(users) AS total_users,
    SUM(gmv) / NULLIF(SUM(orders), 0) AS avg_order_value
FROM dws_daily_city_kpi
WHERE date = CURRENT_DATE - INTERVAL '1 day'
GROUP BY date;
```

**SQL 文件的版本管理规则——和 Python 代码一样:**

1. **改了 SQL 逻辑 -> 改注释中的"最后修改"日期 -> git commit。** 不要说"我只是改了 BI 里的 SQL——没改代码"——BI 里的 SQL 也是代码。
2. **新增 SQL 文件 -> 在注释中写清楚"用途/刷新频率/依赖表"——任何同事接手时不需要问"这个 SQL 是干什么的"。**
3. **废弃的 SQL -> 不要删除——在文件顶部加 `-- DEPRECATED: 替换为 xxx.sql`——保留历史——确保任何时候都可以回到旧版本。**

**面试时——面试官问"你怎么管理 BI 里的 SQL"——你回答——"我把所有 BI 查询保存为 .sql 文件——放在 src/sql/ 目录——用 Git 管理——和 Python 代码一样的版本控制。每个文件顶部有标准化注释块——用途/刷新频率/依赖表。任何同事接手时——打开 src/sql/——看到的不只是 SQL 代码——还有每个查询的'使用说明书'。"**

> 📓 今日主课：BI 综合实战

---

### 📖 核心原理

**你在 BI 工具里写的 SQL——和你的 Python 代码一样需要版本控制。**

最容易丢的就是 BI 工具里的 SQL——"我在 PowerBI 里写了一段很复杂的 DAX/度量值——然后 PowerBI 文件崩了——代码丢了。"

解法——把所有 BI 查询保存为 `.sql` 文件，放在 `src/sql/` 目录下，和 Python 代码一起用 Git 管理。

```
src/sql/
├── daily_kpi.sql
├── city_breakdown.sql
├── cohort_retention.sql
└── ab_test_report.sql
```

每个 `.sql` 文件顶部有注释——写清楚：这个查询给哪个 Dashboard 用、刷新频率、依赖哪些表。

---

### ✍️ 动手练习

1. 创建 `src/sql/` 目录——把你在鲜果多项目中用到的核心 SQL 查询保存为 `.sql` 文件。
2. 每个文件顶部写注释：用途 / Dashboard / 刷新频率 / 依赖表。
3. `git add src/sql/ && git commit -m "add version-controlled SQL queries for BI dashboards" && git push`

---

## D5（周五 1/16）：BI 综合实训——用 Python 生成一个 Dashboard 的 HTML


---

---

### Dashboard HTML 的完整展示——含 KPI 数字卡片 + 柱状图 + 趋势图 + 城市排名表

```python
def generate_full_dashboard(kpi_data, city_data, trend_data, cohort_data, output_path='output/dashboard.html'):
    """生成完整的 HTML Dashboard——4 个区域——浏览器打开即可查看。

    布局:
    - 顶部: 标题 + 数据截止时间 + 刷新时间
    - KPI 区: 4 个数字卡片——GMV/订单数/用户数/客单价——含环比变化
    - 图表区: 左侧柱状图(城市 GMV 排名) + 右侧折线图(7 天趋势)
    - 表格区: 城市排名表——含 GMV/订单数/客单价/环比变化
    """
    html = '<html><head><meta charset="utf-8"><title>鲜果多经营日报</title>'
    html += '<style>'
    html += 'body{font-family:Microsoft YaHei,Arial;max-width:1100px;margin:0 auto;padding:20px;background:#f5f7fa}'
    html += '.header{background:white;padding:20px;border-radius:8px;margin-bottom:20px}'
    html += '.kpi-row{display:flex;gap:20px;margin:20px 0}'
    html += '.kpi-card{flex:1;background:white;border-radius:8px;padding:20px;text-align:center;box-shadow:0 2px 4px rgba(0,0,0,.1)}'
    html += '.kpi-value{font-size:36px;font-weight:bold;color:#1a56db}'
    html += '.kpi-change{font-size:14px;margin-top:5px}'
    html += '.kpi-up{color:#059669} .kpi-down{color:#dc2626}'
    html += '.charts{display:flex;gap:20px;margin:20px 0}'
    html += '.chart-box{flex:1;background:white;border-radius:8px;padding:20px}'
    html += 'img{max-width:100%}'
    html += 'table{width:100%;border-collapse:collapse;background:white;border-radius:8px}'
    html += 'th{background:#f0f4ff;padding:12px;text-align:left;font-weight:600}'
    html += 'td{padding:12px;border-bottom:1px solid #e5e7eb}'
    html += '</style></head><body>'

    # Header
    html += f'<div class="header"><h1>鲜果多经营日报</h1>'
    html += f'<p>数据截止: {kpi_data["date"]} | 刷新时间: {kpi_data["refresh_time"]} | 数据延迟: T+1</p></div>'

    # KPI Row
    html += '<div class="kpi-row">'
    for name, value, change, unit in [
        ('GMV', kpi_data['gmv'], kpi_data['gmv_change'], '万元'),
        ('订单数', kpi_data['orders'], kpi_data['orders_change'], '单'),
        ('用户数', kpi_data['users'], kpi_data['users_change'], '人'),
        ('客单价', kpi_data['aov'], kpi_data['aov_change'], '元')
    ]:
        direction = 'up' if change > 0 else 'down'
        arrow = '↑' if change > 0 else '↓'
        html += f'<div class="kpi-card">'
        html += f'<div class="kpi-value">{value:,.1f}</div>'
        html += f'<div style="color:#666;margin:5px 0">{name} ({unit})</div>'
        html += f'<div class="kpi-change kpi-{direction}">{arrow} {abs(change):.1f}% vs 昨日</div>'
        html += f'</div>'
    html += '</div>'

    # Charts
    html += '<div class="charts">'
    # 城市柱状图
    fig, ax = plt.subplots(figsize=(5, 4))
    top5 = city_data.nlargest(5, 'gmv')
    ax.barh(top5['city'], top5['gmv'], color='steelblue')
    ax.set_title('Top 5 城市 GMV（万元）')
    buf = BytesIO(); fig.savefig(buf, format='png', dpi=100, bbox_inches='tight'); plt.close()
    html += f'<div class="chart-box"><img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"></div>'

    # 趋势图
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(trend_data['date'], trend_data['gmv'], marker='o', color='steelblue', linewidth=2)
    ax.fill_between(trend_data['date'], trend_data['gmv'], alpha=0.1, color='steelblue')
    ax.set_title('近 7 天 GMV 趋势（万元）')
    buf = BytesIO(); fig.savefig(buf, format='png', dpi=100, bbox_inches='tight'); plt.close()
    html += f'<div class="chart-box"><img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"></div>'
    html += '</div>'

    # 城市排名表
    html += '<table><tr><th>城市</th><th>GMV(万元)</th><th>订单数</th><th>客单价(元)</th><th>环比</th></tr>'
    for _, row in city_data.iterrows():
        direction = '↑' if row['gmv_change'] > 0 else '↓'
        color = '#059669' if row['gmv_change'] > 0 else '#dc2626'
        html += f'<tr><td>{row["city"]}</td><td>{row["gmv"]:,.1f}</td>'
        html += f'<td>{row["orders"]:,}</td><td>{row["aov"]:,.2f}</td>'
        html += f'<td style="color:{color}">{direction} {abs(row["gmv_change"]):.1f}%</td></tr>'
    html += '</table>'

    html += '</body></html>'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
```

**这个 HTML Dashboard 的价值——面试官打开它——看到的不只是"数据可视化"——而是——KPI 先行（4 个数字卡片含环比变化）、趋势辅助（7 天折线图）、明细可查（城市排名表）、交互设计（颜色编码——绿色涨红色跌）。** 这些是 Dashboard 设计的核心原则——无论用 Python/HTML 还是 PowerBI/Tableau——原则不变。


---

---

### HTML Dashboard 的面试展示价值

**generate_dashboard_html() 的面试策略——如果你没装 PowerBI/Tableau:**

面试官可能问"你用过 BI 工具吗"——如果你没用过——不要说"没用过"然后沉默——你说:

> "我理解 BI 工具的核心价值——把分析结果以决策者能理解的方式呈现。虽然我没用过商业 BI 工具——但我用 Python 生成了自包含的 HTML Dashboard——含 KPI 数字卡片、柱状图、趋势图、数据表——浏览器直接打开——不需要安装任何工具。这个 HTML 证明了——我理解 Dashboard 的设计原则——KPI 先行、趋势辅助、明细可查——这些原则在 PowerBI/Tableau 中完全适用——只是实现工具不同。"

**Dashboard 设计的四个核心原则——无论用什么工具——面试时都能说:**

1. **KPI 先行:** 打开 Dashboard——第一眼看到的是 4-5 个 KPI 数字卡片（GMV/订单数/用户数/客单价）——不是一堆图表。决策者在 5 秒内知道"今天的核心数字是多少"。

2. **趋势辅助:** KPI 之下——趋势图展示"这些数字在最近 7/30 天的变化"——决策者想知道的不只是"今天 GMV 523 万"——而是"和昨天比涨了还是跌了——和上周比呢"。

3. **明细可查:** 表格或下钻——决策者看到"北京 GMV 下降了 15%"后——能点击北京——看到是哪个品类/渠道导致的——不是"你告诉我结论"——是"我想自己探索"。

4. **交互反馈:** 点击/筛选/悬停——Dashboard 不是"静态的 PPT"——是"可以交互的探索工具"。

> **面试时——你说出这四个原则——面试官知道你理解 Dashboard 设计——不是"会用工具"——是"知道工具服务的目标是什么"。**


---

---

### Python 生成自包含 HTML Dashboard——完整实现

```python
def generate_dashboard_html(kpi_data: dict, city_data: pd.DataFrame,
                            trend_data: pd.DataFrame, output_path: str = 'output/dashboard.html'):
    """生成一个自包含的 HTML Dashboard——浏览器直接打开——不需要 BI 工具。

    布局:
    - 顶部: 4 个 KPI 数字卡片（GMV/订单数/用户数/客单价）
    - 左侧: 城市 GMV 柱状图
    - 右侧: 7 天 GMV 趋势折线图
    - 底部: 城市排名表

    面试时——面试官打开这个 HTML——看到的不只是"数据可视化"——
    而是"这个人理解 Dashboard 的设计原则——KPI 先行、趋势辅助、明细可查"。
    """
    import matplotlib.pyplot as plt
    import base64
    from io import BytesIO

    html = '<html><head><meta charset="utf-8"><title>鲜果多日报</title>'
    html += '<style>body{font-family:Arial;max-width:1000px;margin:0 auto;padding:20px}'
    html += '.kpi{display:flex;gap:20px;margin:20px 0}'
    html += '.kpi-card{flex:1;background:#f0f4ff;border-radius:8px;padding:20px;text-align:center}'
    html += '.kpi-value{font-size:32px;font-weight:bold;color:#1a56db}'
    html += '.kpi-label{font-size:14px;color:#666;margin-top:8px}'
    html += 'img{max-width:100%;margin:20px 0}</style></head><body>'

    # 标题
    html += '<h1>鲜果多经营日报</h1>'
    html += f'<p>数据截止: {kpi_data["date"]} | 刷新时间: {kpi_data["refresh_time"]}</p>'

    # KPI 数字卡片
    html += '<div class="kpi">'
    for name, value, unit in [
        ('GMV', kpi_data['gmv'], '万元'),
        ('订单数', kpi_data['orders'], '单'),
        ('用户数', kpi_data['users'], '人'),
        ('客单价', kpi_data['avg_order_value'], '元')
    ]:
        html += f'<div class="kpi-card"><div class="kpi-value">{value:,.1f}</div><div class="kpi-label">{name} ({unit})</div></div>'
    html += '</div>'

    # 柱状图——城市 GMV
    fig, ax = plt.subplots(figsize=(10, 5))
    city_data.sort_values('gmv', ascending=True).plot.barh(x='city', y='gmv', ax=ax, color='steelblue')
    ax.set_title('各城市 GMV（万元）')
    buf = BytesIO(); fig.savefig(buf, format='png', dpi=100, bbox_inches='tight'); plt.close()
    html += f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'

    # 趋势折线图
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(trend_data['date'], trend_data['gmv'], marker='o', color='steelblue', linewidth=2)
    ax.set_title('近 7 天 GMV 趋势（万元）')
    ax.fill_between(trend_data['date'], trend_data['gmv'], alpha=0.1, color='steelblue')
    buf = BytesIO(); fig.savefig(buf, format='png', dpi=100, bbox_inches='tight'); plt.close()
    html += f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'

    html += '</body></html>'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
```

**面试时——面试官问"你用过 BI 工具吗"——如果你没用过 PowerBI/Tableau——你回答——"我理解 BI 工具的核心价值——把分析结果以决策者能理解的方式呈现。虽然我没用过商业 BI 工具——但我用 Python 生成了自包含的 HTML Dashboard——含 KPI 数字卡片+柱状图+趋势图+数据表——浏览器直接打开——不需要安装任何工具。迁移到 PowerBI/Tableau 时——数据源层不变——只是展示层从 HTML 变成 BI 工具。"**

> 📓 今日主课：BI 综合——完整 Dashboard 交付

---

### 📖 核心原理

**在你本地没有 PowerBI 时——用 matplotlib 组图 + 保存为 HTML 报告 = 一个"模拟 Dashboard"。**

```python
def generate_dashboard_html(kpi_data, city_data, cohort_data, output_path):
    """生成一个自包含的 HTML Dashboard——含 4 个图表区域。
    这个 HTML 可以直接用浏览器打开——不需要 BI 工具。
    """
```

这是 L5 的思维——工具不重要，重要的是你知道 Dashboard 应该长什么样、包含什么内容、更新频率是什么。面试官不在乎你用的是 PowerBI 还是 Python——他在乎你能否设计一个"让业务方一目了然的展示层"。

---

### ✍️ 动手练习

1. 实现 `generate_dashboard_html()`——至少含 KPI 数字区 + 柱状图 + 折线图 + 表格。
2. 生成的 HTML 可以直接发给运营总监——浏览器打开就能看。
3. `git add . && git commit -m "add self-contained HTML dashboard generator" && git push`

---

## D6（周六 1/17）：周项目——BI 就绪的完整数据集市


---

---

### 数据集市 vs 数据仓库——面试时能说清楚的区别

**面试官可能追问——"你做的这些聚合表——和数仓的 DWS 层有什么区别？"**

| 维度 | 数仓 DWS 层 | 数据集市（Data Mart） |
|------|----------|-------------------|
| 服务对象 | 所有分析师——通用的聚合口径 | 特定 Dashboard/业务方——定制化的聚合 |
| 粒度 | 标准粒度——如"天x城市" | 可能是"天x城市x品类"——和 Dashboard 的图表一一对应 |
| 字段名 | 英文——`gmv`/`orders`/`users` | 可以带中文别名——Dashboard 上直接显示"成交总额" |
| 更新频率 | T+1——每天一次 | 可能是每小时——Dashboard 需要更频繁的刷新 |
| 生命周期 | 长期——只要公司在——DWS 层就在 | 中期——Dashboard 下线后——对应的数据集市可以删除 |

**你的回答——"DWS 层是公司级的统一口径——数据集市是 Dashboard 级的定制化视图。数据集市的数据源是 DWS 层——它不做清洗——只做'筛选+聚合+格式化'——确保 Dashboard 上显示的数据和 DWS 层一致——但又针对 Dashboard 的展示做了优化。"**


---

---

### W25 周项目验收——BI 就绪标准

**BI 就绪的 5 个标准——全部满足——鲜果多项目的 Dashboard 数据源就绪:**

| 标准 | 验证方法 | 如果不满足——业务方打开 Dashboard 会看到什么 |
|------|---------|--------------------------------------|
| 聚合表 >= 3 张 | 检查 output/ 目录 | Dashboard 上只有一张表——不够展示 KPI+趋势+明细 |
| 每张表标注刷新频率 | 打开 docstring——找"刷新频率" | 不知道数据是什么时候的——"这个 GMV 是今天的还是昨天的？" |
| SQL 查询文件化 | 检查 src/sql/ 目录 | BI 里的 SQL 丢了——重写一遍——口径可能和上次不一样 |
| 指标一致性 checklist | 打开 docs/ 目录 | Dashboard 和邮件数据不一致——开会时两个数字——争论 20 分钟 |
| 数据延迟在 T+1 以内 | 对比 output 文件的时间戳和 ERP 更新时间 | Dashboard 显示的是两天前的数据——运营基于过期数据做决策 |

**W25 面试速查卡——30 秒版:**

> "我设计了 BI 就绪的数据集市——Python 每天 8:00 AM 把分析结果写入 DWS 层的聚合表——BI 工具直连这些表——每次打开 Dashboard 都是最新数据。我写了指标一致性检查函数——自动对比 Python 结果和 BI 结果——差异超过 1% 自动告警。所有 BI 查询保存为 .sql 文件——用 Git 管理——和 Python 代码一样的版本控制。"

确认你的鲜果多项目"BI 就绪"——至少 3 张聚合表 / 每张标注刷新频率 / SQL 查询文件化 / 指标一致性 checklist 可用。

---

## D7（周日 1/18）：W25 审计


---

---

### W25 面试速查卡——完整版

**Q1:** Python 和 BI 的接口——为什么应该通过数据库而不是 CSV？

> **A:** CSV 是快照——生成的那一刻就已经过时了。BI 工具直连数据库——每次打开 Dashboard 都是最新数据。松耦合——Python 和 BI 通过数据库的一张表来接口——改 Python 不影响 BI——改 BI 不影响 Python。

**Q2:** 指标一致性检查的四个维度？

> **A:** 口径（分子/分母/时间窗口一样吗？）、刷新时间（数据截止时间一样吗？）、数据源（读的是同一张表吗？）、处理逻辑（去重/过滤/聚合一样吗？）。我把这四个检查集成到了日报流程——每天早上自动对比——差异 > 1% 自动告警。

**Q3:** Dashboard 刷新策略的三步决策法？

> **A:** (1) 决策者什么时候需要看？(2) 数据源什么时候更新？(3) 计算成本是否值得？不是越频繁越好——是根据决策频率选择。CEO 不需要每秒看 GMV——财务需要 T+1 的最终数据。

**Q4:** 面试官问"你用过 BI 工具吗"——如果你没用过 PowerBI/Tableau——怎么回答？

> **A:** "我理解 BI 工具的核心价值——把分析结果以决策者能理解的方式呈现。虽然我没用过商业 BI 工具——但我用 Python 生成了自包含的 HTML Dashboard——含 KPI 数字卡片、柱状图、趋势图——浏览器直接打开。这个 HTML 证明了——我理解 Dashboard 的四个设计原则——KPI 先行、趋势辅助、明细可查、交互反馈——这些原则在 PowerBI/Tableau 中完全适用——只是实现工具不同。"

**W25 面试 30 秒版:**

> "我设计了 BI 就绪的数据集市——Python 每天 8:00 AM 把分析结果写入 DWS 层的聚合表——BI 工具直连这些表——每次打开 Dashboard 都是最新数据。我写了指标一致性检查函数——每天早上自动对比 Python 结果和 BI 结果——差异超 1% 自动告警。所有 BI 查询保存为 .sql 文件——用 Git 管理——和 Python 代码一样的版本控制。用 Python 生成了自包含的 HTML Dashboard——展示了 Dashboard 设计的四个核心原则。"


---

---

### W25 闭卷自测 + 工程化交付物清单

**Q1:** Python 和 BI 的接口——为什么应该通过数据库而不是 CSV？

> **A:** CSV 是快照——生成的那一刻就已经过时了。BI 工具直连数据库——每次打开 Dashboard 都是最新数据。而且通过数据库接口——Python 和 BI 是松耦合的——改 Python 代码不影响 BI——改 BI 图表不影响 Python。如果通过 CSV——每次 Python 更新数据——你需要手动重新导入 BI——你是 CSV 搬运工。

**Q2:** 指标一致性检查的四个维度？

> **A:** 口径（分子/分母/时间窗口在两个地方一样吗？）、刷新时间（两个数据源的数据截止时间一样吗？）、数据源（读的是同一张表吗？）、处理逻辑（有没有"你以为一样但其实不一样"的中间变换？）。面试时——面试官问"Dashboard 上的数据和你的分析结论一致吗"——你直接背这四个检查项。

**Q3:** Dashboard 刷新策略的三步决策法？

> **A:** (1) 决策者什么时候需要看这个数据？(2) 数据源什么时候更新？(3) 计算成本是否值得？不是"越频繁越好"——是根据决策频率选择——CEO 不需要每秒看 GMV。

**W25 工程化交付物清单:**
- [ ] prepare_dashboard_data()——至少 3 张 BI 就绪的聚合表——每张标注刷新频率+延迟
- [ ] docs/metric_consistency_checklist.md——含 4 个检查维度
- [ ] README 数据全链路表——新增刷新频率列
- [ ] src/sql/——至少 3 个 SQL 文件——每个顶部有注释（用途/Dashboard/刷新频率/依赖表）
- [ ] generate_dashboard_html()——含 KPI 卡片+柱状图+趋势图——浏览器可直接打开

- 是否有 ≥ 3 张 BI 就绪的聚合表？
- 每张表标注了刷新频率？
- src/sql/ 是否有 ≥ 3 个 SQL 文件且含注释？
- 指标一致性 checklist 是否可用？
