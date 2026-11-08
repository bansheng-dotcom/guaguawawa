# 06 · 模型监控接口口径（monitor）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-trace-metrics/SKILL.md
>


> 技能：`monitor` ｜ 动作：`metrics`（指标查询口径）、`drift`（漂移监控需求）
> 来源：mlflow__mlflow（`mlflow-trace-metrics` 的聚合指标查询：latency/token/count/quality 趋势；`mlflow-evaluation` 的 online monitoring：质量/漂移/延迟/成本）

## 第一层：方法论

监控接口是 R19 的**交接点**，不是监控本身。指标名、视图、聚合方式、时间窗、
告警阈值——这几样构成「交给 R20 持续观察」的需求规格。把这段做成确定性校验的
价值，不在于「监控得更全」，而在于**让说不清楚的监控需求在交接层就发不出来**。

三条方法论：

1. **监控接口是「需求规格」不是「监控实现」**。R19 定义"该监控哪些质量/漂移/
   延迟/成本指标、告警阈值设多少"，实际持续监控与告警由 R20 蛙值守执行。
2. **指标名、视图、聚合方式三件套必须齐**。指标名（monitor 什么）、视图
   （从哪看：TRACES / SPANS / ASSESSMENTS）、聚合方式（怎么算：COUNT / SUM /
   AVG / P95）——缺任一，这个指标查询口径就不成立。
3. **时间窗必须显式声明**。mlflow-trace-metrics 的铁律：查询必须带起止，否则在
   大规模 trace 库上是全表扫描。

**本角色绝对不做的事**：**绝不部署监控、不定义生产告警**。R19 只产出监控需求
工件；持续监控、告警触发、值班响应归 R20 蛙值守。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| metrics.metric_name | ∈ `monitor.metric_names` = `[total_tokens, latency, trace_count, assessment_value]` | mlflow-trace-metrics |
| metrics.view | ∈ `monitor.metric_views` = `[TRACES, SPANS, ASSESSMENTS]` | mlflow-trace-metrics |
| metrics.aggregation | ∈ `monitor.aggregations` = `[COUNT, SUM, AVG, P95]` | mlflow-trace-metrics |
| metrics.time_window | start 与 end 都非空 | mlflow-trace-metrics |
| drift.metric | 非空（漂移指标） | R19 监控口径 |
| drift.threshold | 非空（告警阈值描述） | R19 监控口径 |
| drift.channel | 非空（通知渠道） | R19 监控口径 |
| drift.owner | 非空（监控责任方，R20） | 交接要求 |
| drift.threshold_numeric | threshold_value 为数值 | 告警须可量化 |

**阈值单一真源**：`monitor.metric_views` / `monitor.aggregations` /
`monitor.metric_names` 以 `experience/thresholds.json` 的 `monitor` 段为准。

## 第三层：已验证的算例

**算例 A（干净指标）**：`examples/monitor_metrics.json`
```
latency / TRACES / P95 / 2026-10-01 ~ 2026-10-31
```
指标名、视图、聚合全在白名单、时间窗声明 → `ok=true`，`verdict=PASS`。

**算例 B（脏指标）**：`examples/monitor_metrics_dirty.json`
```
overall_wow_factor / DASHBOARD / MAX / 时间窗为空
```
BLOCKER ×4：指标名越界、视图越界、聚合越界、时间窗缺失。

**算例 C（干净漂移）**：`examples/monitor_drift.json`
```
answer_relevance / 阈值 3.5 / 渠道 值班群+邮件 / owner=R20 / threshold_value=3.5
```
四要素齐、阈值可量化 → `ok=true`。

**算例 D（脏漂移）**：`examples/monitor_drift_dirty.json`
```
threshold_value="低" / channel="" / owner=""
```
BLOCKER ×3：阈值不可量化、渠道为空、责任方为空。

## 第四层：实战踩坑

1. **"不限"没有 placeholders**。metric_name 不在白名单内一律拦，没有"其他"这个
   逃生口。要监控自定义指标，须先把它加进 thresholds.json 白名单。

2. **视图与聚合是正交的**。`TRACES` 视图可以用 `COUNT`/`AVG`/`P95`，`SPANS`
   视图同理，但 `MAX`/`MIN` 不在白名单内——R19 只认这四种聚合方式。

3. **P95 是分位不是平均**。延迟监控用 P95 而不是 AVG 是刻意选择：平均值会掩盖
   长尾。这是口径不是bug。

4. **threshold 描述与 threshold_value 数值是两个字段**。前者是人话描述
   （"均值 < 3.5 持续 1 小时"），后者是机器可判的数值（3.5）。只有描述没有数值，
   R20 无法写自动化告警。

5. **owner 必须是 R20**。R19 定义监控需求，R20 执行持续监控。owner 填 R19 自己
   是角色错位——等于"我定义需求我来监控"，违背交接本意。

6. **不要在结论里写"我已配置好告警"**。这是越权（监控归 R20）。正确写法：
   "产出监控需求 monitor_drift（answer_relevance < 3.5），移交 R20 部署告警。"

7. **指标查询的 start/end 是时间语义不是字符串比较**。校验只查非空（避免依赖
   日期解析库），但口径上要求是 ISO 日期或毫秒时间戳，能与监控后端的查询窗口对齐。
