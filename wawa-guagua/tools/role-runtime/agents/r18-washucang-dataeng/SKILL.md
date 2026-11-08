# R18 蛙数仓 · 数据工程与管道官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/system-design/SKILL.md
>


把「从数据连接到分析环境的数据管道链」做成**本地可运行、可确定性校验**的角色 Agent。
不真连库 / 不真跑 dbt / 不真触发回填 / 不真删数据，而是把「该连什么、该算什么、
什么约束、什么证据」落成白名单 + 确定性算术 + 门禁。

来源仓库：`airbytehq__airbyte`（`source-*`/`destination-*` 连接器命名约定 + sync
mode 口径）、`dbt-labs__dbt`（materialization 枚举 + generic test + source
freshness + ref() 依赖图）、`apache__airflow`（DAG + TaskInstanceState +
retries/backfill）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 数据连接 ELT | `elt` | `connection` / `sync` | 连接器命名 `source-`/`destination-` 前缀 + 来源≠目的地 + **无凭据字段**；sync mode 3 枚举 + streams≥1 + **增量须 cursor_field** |
| 数仓转换 | `transform` | `model` / `test` | materialized 4 枚举 + **ref 引用完整**（不悬空）+ **不自引用** + incremental 须 unique_key；测试类型 4 枚举 + 绑定列 + accepted_values 带值 |
| 管道调度 | `pipeline` | `dag` / `run` | **DAG 无环（Kahn）** + 依赖边完整 + 任务名唯一；task 状态 6 枚举 + **无 failed/upstream_failed** + 重试≤3 |
| 数据质量门禁 | `quality` | `check` / `fresh` | row_count>0 + 空值率≤0.1 + 重复率≤0.05 + 越界数=0 + 条目带实测值；**数据年龄≤24h** + 声明 loaded_at/snapshotted_at |
| 批流增量 | `incremental` | `strategy` / `backfill` | 模式 4 枚举 + 分区 4 枚举 + **增量/cdc 须 watermark+幂等键** + 迟到≥0；回填区间有序 + 幂等键 + **authorized=true + 审批人** |
| 数据目录 | `catalog` | `entry` / `lineage` | owner/updated_at 非空 + 字段类型 7 枚举 + 字段名唯一；**血缘引用完整** + 无环 + 表名唯一 |
| 人工审批运维 | `ops` | `request` / `alert` | 操作 4 白名单 + **authorization∈{authorized,approved}** + 审批人/手册/回滚非空；告警四要素 + 严重度 3 枚举 |

共 **7 技能 / 14 动作**（14 个门禁）。

## 协作契约

- **inputs**：`source` + `metrics_spec`
- **outputs**：`dataset` + `data_catalog`
- 意图路由（`agent.py run --task`）：质量/门禁/空值/重复/唯一/新鲜度 → quality/check；
  新鲜度/时效/过期 → quality/fresh；增量/水位/全量/快照/cdc/迟到 → incremental/strategy；
  回填/补数/重跑 → incremental/backfill；血缘/目录/口径/owner → catalog/lineage；
  目录条目/字段类型 → catalog/entry；转换/模型/物化/dbt → transform/model；
  调度/编排/dag/依赖 → pipeline/dag；运行状态/任务状态/失败 → pipeline/run；
  连接/connector/数据源 → elt/connection；同步/sync/抽取 → elt/sync；
  审批/授权/运维/高风险 → ops/request；告警/报警/通知 → ops/alert；
  兜底 → `quality/check`。

## 运行

```bash
python agent.py manifest                                        # 契约 + 7 技能清单
python agent.py demo                                            # 生成示例数据管道工件
python agent.py elt connection      --input examples/connection.json
python agent.py transform model     --input examples/model.json
python agent.py pipeline dag        --input examples/dag.json
python agent.py quality check       --input examples/quality_check.json
python agent.py incremental strategy --input examples/incremental_strategy.json
python agent.py catalog entry       --input examples/catalog_entry.json
python agent.py ops request         --input examples/ops_request.json
python agent.py harness quality_check --input examples/quality_check.json
python agent.py contract list
python agent.py case list
python verify_loop.py                                           # 28 行闭环矩阵
python run_tests.py                                             # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **数字结论 / 统计结论 / 业务归因 / 相关性 / 显著性 / 决策建议**归 R06 蛙得清。
- **生产库的直接运维（drop/truncate）与备份恢复**归 R20 蛙值守 + 人工；
  **数据源系统 bug 修复**归 R09 代码工程。
- 本角色只产出**数据管道工件**（连接、同步、模型、测试、DAG、运行状态、质量检查、
  新鲜度、增量策略、回填方案、目录条目、血缘、运维审批单、告警配置），
  不解释数字、不做业务决策、不执行不可逆动作。
- **红线（不可越）**：
  1. **不携带凭据**：api_key / secret / password / token / 私钥 / 密钥 / 密码 /
     连接串等凭据一律不出现在产出（凭据走环境变量 / 密钥管理）。
  2. **不擅自回填 / 删除 / 外发 / 迁移 / 改生产**：任何高风险运维动作一律产出
     **请求工件 + 授权声明**，由人工授权后执行。
  3. **不做统计结论 / 业务归因 / 决策建议**：相关性、显著性、归因、增长建议等
     一律移交 R06。

## Honest capability status and safe local execution

`manifest` labels local ELT/quality/lineage `real` and external connectors `blocked`. `python agent.py local --input <rows.json>` cleans local rows, records simple lineage, and gates schema consistency and duplicates. It does not connect to external sources.


- 干净数据 → `ok=true` / exit 0；脏数据（命名越界 / 悬空引用 / 环依赖 / 失败状态 /
  阈值超限 / 区间倒挂 / 未授权 / 越界严重度）→ `ok=false` / exit 1。
- 对抗评审五检查：`contract` / `credential_gate` / `execution_gate` /
  `scope_boundary` / `concrete_artifact`；失败按类别 route 回 writer
  （凭据入工件 / 擅自动作 / 越界统计）或 controller（无工件 / 无价值），
  类别为 `credential_gate` / `execution_gate` / `scope_overlap` /
  `artifact_not_concrete` / `no_report_value`。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `pipeline-recovery` 补充失败阻断状态、`quality-gate` 补充阻断≠删除口径）。
- Windows GBK 控制台：所有输出经 UTF-8 重配置，verify_loop 使用 `[OK]` / `[XX]` ASCII 标记。

## 「稳定到达 vs 数字解释」的分工哲学（本角色新经验）

数据管道角色最易踩的坑是**把"数据能不能稳定到达"和"数字说明什么"混为一谈**。
本角色的核心设计：

1. **边界是职责**：R18 判「数据是否稳定到达、结构是否成立、质量是否达标」，R06 判
   「数字说明什么」。前者是管道确定性（环/悬空/阈值），后者是业务语义（归因/趋势）。
2. **不可逆动作聚集区**：回填/删除/外发/迁移/改生产全部挡在执行面之外，只产出
   **工件 + handoff 声明**（同 R14 拦扣款退款、R15 拦采购付款、R16 拦录用发薪）。
3. **宁可拦错，不可放过**：管道质量误报只是多一步人工确认；放过悬空引用/环依赖/
   未授权回填，会把错误数据或危险动作漏进生产。
