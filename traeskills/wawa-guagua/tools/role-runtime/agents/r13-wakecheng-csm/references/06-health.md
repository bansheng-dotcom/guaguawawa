# s06 客户健康与续约输入（health / risk）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/customer-health/SKILL.md
>


来源沉淀：`twentyhq__twenty`（使用与互动数据）+ `chatwoot__chatwoot`（工单量与 CSAT）
+ `formbricks__formbricks`（反馈分）。三源口径在本角色合并成一张健康表，不重复计数。

## 一、方法论（什么时候用、核心口径）

客户健康不是「客户经理的感觉」，而是**四个可量化的维度加权，并在单维崩坏时拒绝给出
healthy 结论**。所以本能力域做两件事：

- `health`：整张健康表——四维加权分、风险分带、续约窗口与候选、at_risk 归因。
- `risk`：单个客户——健康分、分带、分带一致性、at_risk 归因。

**加权口径**：`score = Σ(dim_score × weight/100)`，四维 `usage/support/voc/engagement`
权重 `30/25/25/20`，权重和恒等 100。

**分带**：`≥75 healthy`、`50-74 watch`、`<50 at_risk`。

**续约候选**：`renewal_in_days ≤ 90` 且 `score ≥ 70`，两条同时满足。

立场：**单维 ≤ 3 分时不得判 healthy**。总分是加权平均，一个维度归零只拉低 20 分，
很容易被其它三维的高分掩盖——这是健康分最危险的失效模式，所以单独加一条一致性门禁。

边界：只产出健康评估与续约建议，不承诺折扣/退款/合同条件（交 R03/R02）；
不做统计推断（交 R06）；续约触达执行交 R12。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `health` 节：

- `weights`：`{usage:30, support:25, voc:25, engagement:20}`
- `risk_bands`：`{healthy:75, watch:50, at_risk:0}`
- `renewal_window_days`：90；`renewal_score_min`：70
- `low_csat_max`：3；`ticket_spike_ratio`：2.0

**health 校验规则**：
- `customers` 非空；任一行无 `name` → BLOCKER（健康表不允许匿名行）。
- 权重和 ≠ 100 → BLOCKER。
- 任一 `at_risk` 客户缺 `risk_reason` → BLOCKER。
- 每行维度分经过 `clamp(0, 100)`，超出区间不会被放大。

**risk 校验规则**：`name` 非空；分带由分数算出；分带为 healthy 但存在维度 ≤ 3 →
BLOCKER；at_risk 必须有 `risk_reason`。

**输出键**：health → `customer_count / avg_health / at_risk_count /
renewal_candidates / health_rows`；risk → `customer_count / health_score / band`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

`examples/health.json` 四名客户：

| 客户 | usage | support | voc | engagement | 分数 | 分带 | 续约天数 |
|---|---|---|---|---|---|---|---|
| 云启科技 | 90 | 85 | 88 | 80 | 86.2 | healthy | 30 |
| 晨星零售 | 70 | 60 | 65 | 55 | 63.2 | watch | 60 |
| 山海物流 | 40 | 35 | 30 | 25 | 33.2 | at_risk | 20 |
| 北辰教育 | 85 | 90 | 80 | 75 | 83.2 | healthy | 120 |

平均 66.4；续约窗口内 3 名，达门槛候选 1 名（云启科技）→ ok=true。
`examples/risk.json`（85/80/78/70）→ 79.0 healthy，最小维度 70 无崩坏 → ok=true。
`examples/health_dirty.json`：匿名行 + at_risk 无归因 → `health.name` 与
`health.risk_reason` 双 BLOCKER。
`examples/risk_dirty.json`：100/100/100/0 → 80.0 被算出 healthy，但 engagement=0 →
`risk.band_consistency` BLOCKER，ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **高分掩盖单维塌陷**：这是本能力域存在的首要原因。四维 100/100/100/0 = 80 分，
  单看分带是 healthy，但客户已经完全不用产品了。
- **risk_reason 写成套话**：「客户有风险」不算归因，至少要有「使用骤降」「工单激增」
  这类可核对的事实；门禁只判非空，评审环节再判是否具体。
- **续约窗口与分数门槛要同时满足**：临近续约但健康分低，先救不续；健康分高但还早，
  也不该现在进谈判桌。
- **权重不要随手改**：改成 40/30/20/10 会让 usage 一票独大，support 塌陷被稀释；
  权重变更必须走阈值文件并留痕。
- **匿名行**：导出的健康表经常丢客户名（只有 ID），这会让风险名单无法行动。
