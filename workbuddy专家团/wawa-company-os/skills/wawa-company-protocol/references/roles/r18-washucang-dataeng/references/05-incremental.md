# 05 · 批流与增量边界口径（incremental）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/process-optimization/SKILL.md
>


> 技能：`incremental` ｜ 动作：`strategy`（增量策略）、`backfill`（回填方案）
> 来源：airbyte sync mode（full_refresh / incremental）+ dbt incremental materialization + snapshot/CDC 语义

## 第一层：方法论

增量边界决定**「丢数还是重数」**。全量刷新每次覆盖，增量只拉新增，快照/CDC
捕捉变更。选错模式或多算少算，都直接反映在下游的每个数字上。把这段做成确定性
校验的价值，不在于"拉得更快"，而在于**让增量起点和重跑幂等有了明确的依据**。

三条方法论：

1. **水位字段决定增量起点**。`watermark_field`（如 `updated_at`）标记"上次拉到了
   哪个时点"。水位字段缺失 → 无法定位增量起点 → 要么重复拉全量、要么丢数。
   增量/cdc 模式必须有水位字段。
2. **幂等键决定重跑是否重复入账**。`idempotency_key`（如 `order_id`）让重跑可以
   识别"这行是否已存在"。缺了幂等键，重跑 = 重复入账。
3. **回填是高风险动作，必须授权**。回填（backfill）会重写历史数据，是不可逆的。
   必须显式 `authorized=true` + 有审批人，否则不放行（红线 2）。

**本角色只校验增量口径与策略**，**不擅自执行回填**——回填交 s07 审批后由人工执行。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| strategy.stream | 非空 | 流名 |
| strategy.mode | ∈ `incremental.modes` = `[full_refresh, incremental, snapshot, cdc]` | airbyte/dbt 增量模式 |
| strategy.partition | ∈ `incremental.partitions` = `[none, hourly, daily, monthly]` | 分区粒度 |
| strategy.watermark | mode ∈ {incremental, cdc} → 声明 `watermark_field` | 增量起点 |
| strategy.idempotency | mode ∈ {incremental, cdc} → 声明 `idempotency_key` | 重跑幂等 |
| strategy.late | `late_arrival_days ≥ 0` | 迟到容忍窗口 |
| backfill.operation | == `backfill` | 操作类型 |
| backfill.range | start/end 非空 | 回填区间 |
| backfill.order | `start ≤ end` | 区间顺序 |
| backfill.idempotency | 声明 `idempotency_key` | 重跑不重复 |
| backfill.authorized | `authorized == true` | R18 红线 2 |
| backfill.approver | 审批人非空 | R18 红线 2 |

**阈值单一真源**：`incremental.modes` / `incremental.partitions` 以
`experience/thresholds.json` 的 `incremental` 段为准。

## 第三层：已验证的算例

**算例 A（干净增量策略）**：`examples/incremental_strategy.json`
```
orders / incremental / daily / watermark_field=updated_at / idempotency_key=order_id / late_arrival_days=1
```
模式白名单、分区白名单、水位+幂等键齐、迟到容忍非负 → `ok=true`，`verdict=PASS`。

**算例 B（脏增量策略）**：`examples/incremental_strategy_dirty.json`
```
orders / incremental / daily / late_arrival_days=1（无 watermark/idempotency）
```
BLOCKER ×2：增量模式缺 `watermark_field`（`strategy.watermark`）与
`idempotency_key`（`strategy.idempotency`）。

**算例 C（脏回填）**：`examples/backfill_dirty.json`
```
backfill / start=2026-01-31 / end=2026-01-01 / authorized=false / approver=""
```
BLOCKER ×3：区间顺序倒挂（`backfill.order`）、未授权（`backfill.authorized`）、
审批人为空（`backfill.approver`）。对照 `backfill.json`
（start≤end + authorized=true + approver=R01）→ `ok=true`。

## 第四层：实战踩坑

1. **full_refresh 不要求水位/幂等键是刻意的**。全量刷新每次覆盖，不需要水位和
   幂等键。技能口径：非增量模式（full_refresh / snapshot）不强制这两项，记为 OK
   ——避免把合法的全量策略误拦。

2. **snapshot 与 cdc 的差异**。snapshot 是"定期拍全表快照"，cdc 是"持续捕获变更
   流"。两者都不等于 incremental：snapshot 不需要水位（拍全量），cdc 需要水位
   （捕获点）。**当前 R18 口径把 cdc 归入"需要水位"，snapshot 归入"不需要"**——
   这是与 dbt（snapshot 不依赖 watermark）+ airbyte（cdc 依赖 LSN/位点）对齐的结果。

3. **分区 `none` 是合法的**。不分区（`partition=none`）不是"没分区就错"——很多
   小表不分区。口径：`partition ∈ [none, hourly, daily, monthly]`，none 在列。

4. **回填区间是字符串日期比较**。`start ≤ end` 用字符串字典序比较（`"2026-01-31" >
   "2026-01-01"`）。这要求日期格式统一为 `YYYY-MM-DD`——格式混乱会导致比较失效
   （如 `"2026/1/1"` vs `"2026-01-01"`）。夹具必须用统一格式。

5. **`authorized` 必须是布尔 true，不是字符串 "true"**。JSON 里 `"authorized": "true"`
   是字符串，`is True` 判定为假 → 拦截。这是刻意的严格：字符串形式的授权状态
   容易被伪造/误读。

6. **回填幂等键与增量幂等键是同一个概念**。`strategy.idempotency_key` 和
   `backfill.idempotency_key` 都指向"重跑不重复"的依据，通常就是主键。分开设
   判据是为了让两个动作各自自足（不依赖对方被调用过）。

7. **不要在结论里写"我已完成回填 2026 全年数据"**。这是越权（`execution_gate`）。
   正确写法："产出回填方案 backfill.json（2026-01-01~2026-01-31，已授权，审批人
   R01），交人工执行。"

8. **迟到容忍窗口是"天数"不是"条数"**。`late_arrival_days=1` 表示容忍 1 天内的
   迟到数据。`≥ 0` 是唯一约束（不允许负数窗口）。当前 R18 不设上限——迟到窗口
   由业务定，不是角色能拍的。
