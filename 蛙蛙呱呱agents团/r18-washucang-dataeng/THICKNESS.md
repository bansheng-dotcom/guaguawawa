# R18 蛙数仓 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 10 篇 / 约 52.5KB（`check_role_thickness --report` 可复核） |
| 来源 | airbyte（connector/sync mode）、dbt（incremental/test/freshness）、Airflow |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 8 个能力域：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `elt` | 连接/同步 | 命名约定、sync mode、cursor、凭据隔离 |
| 2 | `transform` | SQL/模型 | 转换与血缘 |
| 3 | `pipeline` | DAG | 调度与依赖 |
| 4 | `quality` | 表/行集/新鲜度 | 完整性/唯一性/有效性/新鲜度 |
| 5 | `incremental` | 增量策略/回填 | 分区/水位/幂等/守恒 |
| 6 | `catalog` | 元数据 | 字段与 owner |
| 7 | `ops` | 运维请求 | 变更与审批 |
| 8 | `profile` | 行集 | 列画像 |

黄金链：`elt.connection → sync → quality.check → quality.fresh`；
`incremental.strategy → quality.check → quality.fresh`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（29 个） | 每动作配对，脏件断言被拦 |
| 行集夹具 | `examples/local_elt_rows.json` | 运行时引擎可实测 |
| 黄金成品 | `golden/elt-quality-report.html`、`golden/incremental-report.html` | 含夹具 sha256 与 37 条门禁 |
| 运行时引擎 | `engines/runtime_engine.py` | 真实行集重算与增量守恒 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 连接器命名/来源≠目的地 | `elt.connection` → `elt.source_prefix/destination_prefix/distinct` | BLOCKER |
| 连接配置无凭据字段 | `elt.connection/sync` → `no_credential` | BLOCKER |
| sync mode/cursor/频率 | `elt.sync` → `sync.*` | BLOCKER |
| 行数/空值率/重复率/无效值 | `quality.check` → `quality.*` | BLOCKER |
| 自报数字与实测不符 | `quality.check` → `quality.tamper` | BLOCKER |
| 新鲜度阈值 | `quality.fresh` → `fresh.age` | BLOCKER |
| 分区白名单 | `incremental.strategy` → `strategy.partition` | BLOCKER |
| 水位/幂等键 | `incremental.strategy` → `strategy.watermark/idempotency` | BLOCKER |
| 增量守恒 | `incremental.strategy` → `strategy.conservation` | BLOCKER |
| 回填须授权 | `incremental.backfill` → `backfill.authorized` | BLOCKER |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 覆盖全部动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（缺分区、重复主键） |
| 端到端 | `run_tests.py` T01–T17 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r18-washucang-dataeng/golden/build_golden.py`
- 产物：`elt-quality-report.html`（21 条门禁，0 未过）、
  `incremental-report.html`（16 条门禁，0 未过）
- 命令：`python r18-washucang-dataeng/run_tests.py`
- 结果：全绿（含厚度样本 T17）

## 7. 已知边界

- 只判「数据能不能进分析环境」，不判「数字说明什么」；
- 质量门禁是阻断器，不是报告器；
- 回填属高风险运维，必须人工审批，本角色不擅自执行。
