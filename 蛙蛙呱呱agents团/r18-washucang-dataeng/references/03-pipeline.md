# 03 · 管道调度与编排口径（pipeline）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/system-design/SKILL.md
>


> 技能：`pipeline` ｜ 动作：`dag`（DAG 结构）、`run`（运行状态）
> 来源：apache__airflow（DAG 有向无环图、TaskInstanceState、upstream/downstream 依赖边、retries/backfill）

## 第一层：方法论

调度层（Airflow 层）定义**任务何时跑、按什么顺序跑、跑失败怎么算**。DAG 是
有向无环图：task 是节点，依赖边是有向边。把这段做成确定性校验的价值，不在于
"排得更快"，而在于**让死锁的环依赖和假装成功的失败进不了生产**。

三条方法论：

1. **DAG 必须无环**。环依赖（a→b→c→a）会让调度器死锁——每个任务都在等上游。
   用 Kahn 拓扑排序检测：能剥完所有节点则无环。
2. **失败不能假装成功**。`failed` 与 `upstream_failed` 是阻断信号——任何下游任务
   都不该在未修复上游的情况下继续。有任何一个 failed/upstream_failed 即阻断。
3. **依赖边必须指向已声明任务**。边 `[x, y]` 里的 x/y 必须在 `tasks` 列表里，
   否则是悬空边（调度器找不到节点）。

**本角色只校验调度结构与状态**，**不擅自触发回填**——回填是高风险运维动作
（红线 2），须人工授权，交 s07 审批。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| dag.dag_id | 非空 | airflow DAG id |
| dag.tasks | ≥ 1 且任务名唯一 | DAG 节点集 |
| dag.edge_integrity | 每条边的两端 ∈ tasks | airflow upstream/downstream |
| dag.acyclic | Kahn 拓扑可剥完 ⇒ 无环 | DAG 定义 |
| run.dag_id | 非空 | airflow DAG id |
| run.tasks | ≥ 1 个任务状态记录 | TaskInstance |
| run.state_whitelist | 状态 ∈ `pipeline.task_states` = `[success, failed, skipped, upstream_failed, running, queued]` | airflow TaskInstanceState |
| run.no_failure | 无 `failed` / `upstream_failed` | 阻断口径 |
| run.retries | `max_retries` ∈ `[0, pipeline.default_max_retries]` | airflow retries |

**阈值单一真源**：`pipeline.task_states` / `pipeline.default_max_retries` 以
`experience/thresholds.json` 的 `pipeline` 段为准。

## 第三层：已验证的算例

**算例 A（干净 DAG）**：`examples/dag.json`
```
daily_etl / tasks=[extract, load, transform] / edges=[[extract,load],[load,transform]]
```
线性链、边完整、无环 → `ok=true`，`verdict=PASS`。

**算例 B（脏 DAG）**：`examples/dag_dirty.json`
```
cyclic_etl / tasks=[a,b,c] / edges=[[a,b],[b,c],[c,a]]
```
BLOCKER ×1：`c→a` 让图成环，Kahn 剥不完（seen=0 < 3），`dag.acyclic` 拦。

**算例 C（脏运行）**：`examples/run_dirty.json`
```
daily_etl / tasks=[{extract,success},{load,failed}]
```
BLOCKER ×1：`load` 状态为 `failed`，`run.no_failure` 拦。对照 `run.json`
（全 success）→ `ok=true`。

## 第四层：实战踩坑

1. **Kahn 实现要防"假节点"**。`_has_cycle()` 只在边两端都在 `tasks` 里时才建边
   ——悬空边不参与拓扑（否则会把不存在的节点算进 indeg，误判成环）。悬空边由
   `edge_integrity` 单独拦，两条判据分工。

2. **`skipped` 不算失败，但 `upstream_failed` 算**。skipped 是"主动跳过"（如分支
   未选中），upstream_failed 是"上游炸了我没法跑"。两者都合法枚举，但只有
   failed/upstream_failed 触发 `no_failure` 阻断。

3. **`running`/`queued` 是正常中间态**。做运行状态校验时，任务还在跑不代表错。
   口径：只要没有 failed/upstream_failed，running/queued 都放行。

4. **重试次数是上限不是目标**。`max_retries > 3` 通常意味着"用重试掩盖不稳定"。
   R18 口径：≤ `default_max_retries`（3）。改上限只改 thresholds。

5. **边方向不能写反**。`[upstream, downstream]` 是约定：`[extract, load]` 表示
   extract 先跑、load 后跑。写反成 `[load, extract]` 会形成反环，Kahn 会拦——
   但若整图恰好无环，反边会**静默改变执行顺序**，属最隐蔽的坑。易错处靠
   `dag.json` 的样例方向做锚点。

6. **不要在结论里写"我已触发回填重跑"**。这是越权（`execution_gate`）。正确
   写法："产出 DAG 工件 dag.json，检测到 load 任务 failed，需修复后重跑；
   回填须走 s07 审批。"

7. **空 tasks 是脏数据不是空 DAG**。`tasks: []` 不是"空跑"，是没有任务的 DAG。
   口径：`tasks ≥ 1`。

8. **`run` 与 `dag` 是两套判据别混淆**。`dag` 判结构（建图）、`run` 判状态
   （看结果）。结构合法的 DAG 跑挂了，是 run 层的问题，不要回到 dag 层找。
