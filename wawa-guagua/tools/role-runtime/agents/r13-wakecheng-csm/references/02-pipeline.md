# s02 销售管道（pipeline / opp）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/pipeline-review/SKILL.md
>


来源沉淀：`twentyhq__twenty` —— `opportunity.workspace-entity.ts`（name/amount/closeDate/
stage/pointOfContact/company/owner）+ 标准阶段常量（NEW/SCREENING/MEETING/PROPOSAL/
NEGOTIATION/WON/LOST，见 dev-seeder 与 prefill 数据）+ `compute-standard-opportunity-view-groups`
的分组视图口径。

## 一、方法论（什么时候用、核心口径）

管道的核心问题不是「有几个商机」，而是**这些钱按概率折算后到底值多少、卡在哪、
集中在谁身上**。所以本能力域做三件事，全部确定性实算：

1. **加权管道值** = Σ(amount × stage_probability)，只对开放阶段求和；
2. **停滞识别** = 开放阶段且 days_in_stage > stall_days_max，必须写 stall_reason；
3. **客户集中度 HHI** = 按客户汇总开放金额后 Σ(占比²)，>0.5 判收入结构风险。

立场：**stage 只是一个人填的字符串，加权值才是决定资源投放的口径**。WON/LOST 不进
加权池——把已赢的单算进预测是销售预测最常见的高估来源。

边界：不替 R12 定投放策略、不替 R07 决定路线图优先级、不擅自承诺折扣与合同条件。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `pipeline` 节：

- `stages`：7 个标准阶段；`open_stages`：前 5 个；`terminal_stages`：`WON / LOST`
- `stage_probability`：`NEW 0.1 / SCREENING 0.2 / MEETING 0.4 / PROPOSAL 0.6 / NEGOTIATION 0.8 / WON 1.0 / LOST 0.0`
- `stall_days_max`：14；`stale_ratio_max`：0.3；`concentration_hhi_max`：0.5

**pipeline 校验规则**：
- 任一 `stage` 越界 → BLOCKER；任一 `amount` ≤ 0 → BLOCKER。
- 停滞占比 > 0.3 → BLOCKER；停滞商机缺 `stall_reason` → BLOCKER。
- 开放商机缺 `next_step` 或 `owner` → BLOCKER。
- HHI > 0.5 → BLOCKER。

**opp 校验规则**：名称/阶段/金额/成交日/负责人齐备；开放阶段必须有 `next_step`；
`days_in_stage > 14` 时必须有 `stall_reason`；封闭阶段以上三项豁免。

**输出键**：pipeline → `opp_count / stage_count / weighted_value / stale_count /
concentration_hhi`（`stage_count` 是**被使用的阶段数**，即阶段分布覆盖度）；
opp → `opp_count / weighted_value`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

`examples/pipeline.json` 四条开放商机：

| 商机 | 阶段 | 金额 | 概率 | 加权 |
|---|---|---|---|---|
| CRM 平台迁移 | PROPOSAL | 600000 | 0.6 | 360000 |
| 客服系统升级 | MEETING | 300000 | 0.4 | 120000 |
| NPS 调研工具 | NEGOTIATION | 450000 | 0.8 | 360000 |
| 数据看板接入 | SCREENING | 250000 | 0.2 | 50000 |

合计 `weighted_value=890000`，`stage_count=4`，HHI=0.4199 ≤ 0.5 → ok=true。
`opp.json`（PROPOSAL 600000）→ `weighted_value=360000`。
`pipeline_dirty.json`：阶段 `CLOSED_ILLEGAL` 越界 + 停滞 30 天无原因 + `next_step` 空 +
对两个客户 50/50 分配导致 HHI=0.5 边界——共 5 条 BLOCKER，ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **WON 进了加权池**：最典型的高估。已赢的单概率 1.0，加进去等于重复计入预测。
- **stage_count 口径歧义**：一开始写成「商机条数」，与 `opp_count` 重复且误导；
  改成「实际使用的阶段数」，才回答「管道是不是全压在一两个阶段」。
- **停滞率与停滞原因分开判**：占比合规不代表写得清楚；30 天不动却无归因的商机，
  下一步动作必然是错的。
- **HHI 要按客户聚合，不是按商机**：按商机算永远接近 0，看不出单一客户依赖。
- **金额单位要统一**：同一份数据里混入「万元」与「元」，加权值就失去意义。
