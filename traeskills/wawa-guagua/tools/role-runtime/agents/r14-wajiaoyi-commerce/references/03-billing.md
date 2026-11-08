# 03 · 订阅计量与账单口径（billing）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/finance/journal-entry/SKILL.md
>


> 技能：`billing` ｜ 动作：`plan`（计费方案）、`usage`（用量记录）、`invoice`（账单）
> 来源：getlago__lago（AGGREGATION_TYPES、CHARGE_MODELS、INTERVALS、Invoice STATUS）

## 第一层：方法论

订阅计费的本质是**三个口径的乘积**：

```
计费方案（怎么算）× 用量（用了多少）× 账单（收多少）
```

任何一环口径不明，账单争议就无法在确定性层面解决。所以本技能的设计原则是：
**把"怎么算"和"用了多少"都变成可复现的枚举 + 数值，让"收多少"成为可推导的结论。**

关键洞察：账单争议通常不是"数错了"，而是**口径不同**。客户说"我用了 800 次"，系统说"1200 次"，
差异往往来自：重复上报的事件、按不同聚合口径统计（count_agg vs unique_count_agg）、
或时间窗口不一致。因此本技能的首要动作不是裁决谁对，而是**把口径显式化**。

第二个洞察：**custom_agg 是不可复现的黑盒**。自定义聚合表达式一旦缺失，
账单在数学上就无法被第三方复算。因此 `custom_agg` 必须携带 `custom_expression`，
否则一律 BLOCKER——不是格式洁癖，是"不可复算的账单没有法律与审计价值"。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| aggregation_types | ∈ `{count_agg, sum_agg, max_agg, unique_count_agg, weighted_sum_agg, latest_agg, custom_agg}` | lago AGGREGATION_TYPES |
| charge_models | ∈ `{standard, graduated, package, percentage, volume, graduated_percentage}` | lago CHARGE_MODELS |
| plan_intervals | ∈ `{weekly, monthly, yearly, quarterly}` | lago INTERVALS |
| invoice_status | ∈ `{draft, finalized, voided, failed, pending}` | lago Invoice STATUS |
| usage_required | `metric_code`、`quantity` | thresholds.billing.usage_required |
| charge_required | `charge_model`、`amount`、`unit_amount` | thresholds.billing.charge_required |
| custom_agg 声明 | `aggregation_type == custom_agg` → 必须含非空 `custom_expression` | 可复现性要求 |
| 账单恒等式 | `total == Σ(line_items.amount)` | 交易语义公理 |

**各计费模型的复算方式（决定"用量 → 金额"的推导）**：

| charge_model | 复算公式 |
|---|---|
| standard | `amount ≈ quantity × unit_amount` |
| graduated | 按区间分段累加，每段用各自单价 |
| volume | 全部量套用所在区间单价 |
| package | `⌈quantity / package_size⌉ × unit_amount` |
| percentage | `base × rate` |
| graduated_percentage | 按区间分段，各段用各自比例 |

**账单状态语义**：`draft` 未定稿、可变更；`finalized` 已定稿、对外呈现；
`voided` 作废（需另开新账单）；`failed` 生成失败；`pending` 处理中。
对客户对账时必须用 `finalized` 及以上状态的账单。

## 第三层：已验证的算例

**算例 A（干净方案）**：`examples/plan.json`
```
code=pro_monthly, interval=monthly
charge1: standard,  amount=299.0, unit_amount=299.0, aggregation_type=count_agg    → PASS
charge2: percentage, amount=2.9,  unit_amount=0.029, aggregation_type=sum_agg      → PASS
```
两个 charge 的 `charge_model` 与 `aggregation_type` 均合法，`interval=monthly` 合法 → `ok=true`，
`charge_count=2`。

**算例 B（脏数据）**：`examples/plan_dirty.json`
```
code="", interval="daily", charge: {charge_model: "nonexistent", aggregation_type: "custom_agg", custom_expression: ""}
```
实际 4 条失败判据：`方案代码非空`、`计费周期='daily' 在白名单`、
`计费模型在白名单（越界 ['nonexistent']）`、`custom_agg 必须声明表达式（缺 ['nonexistent']）`。
（`计费规则 ≥1` 与 `聚合类型在白名单` 两条通过——`custom_agg` 本身是合法聚合类型。）

**算例 C（用量）**：`examples/usage.json`
```
api_calls / 1200 / count_agg   → PASS
tokens_in / 350000 / sum_agg   → PASS
```
`examples/usage_dirty.json`：`metric_code=""`、`quantity=0`、`aggregation_type` 未声明
→ BLOCKER ×3：`用量必填齐备（缺 ['']）`、`用量均为正（异常 ['']）`、
`聚合类型在白名单（越界 ['']）`。

**注意 `quantity=0` 会被拦截**（判据 `> 0`）。当月零用量不应写一条 `quantity=0` 的记录，
而应**不产生记录**——因为"零用量"和"用量上报失败/字段被清空"在数据上无法区分。
同行项目 `quantity ≤ 0` 的口径一致（见 02-order.md）。

**算例 D（账单）**：`examples/invoice.json`
```
inv_2026_11_001 / finalized / total=1046.0
line_items: 897.0 + 149.0 = 1046.0  → 恒等式成立 → PASS
```
`examples/invoice_dirty.json`：`id=""`、`status="weird"`、`total=0`、`line_items=[]`
→ BLOCKER ×4：`账单号非空`、`账单状态='weird' 在白名单`、`账单总额=0.0 为正`、`账单缺明细行`。
注意 `账单总额为正` 是独立判据（`> 0`），零额账单同样被拦。

## 第四层：实战踩坑

1. **plan 里 amount 与 unit_amount 的关系**：`standard` 模型下二者常相等（单价即金额），
   但 `graduated`/`package` 模型下 `amount` 可能是区间总价而 `unit_amount` 是单价。
   校验层只要求二者存在且为数值，**不要求相等**——强行要求相等会误杀合法方案。

2. **percentage 的两种写法**：`amount=2.9` + `unit_amount=0.029`（2.9% 与 0.029 的十进制形式）。
   两种写法都合法，看场景。校验层不做单位归一，只在复算时按同一口径取用。

3. **聚合口径导致的"用量差异"**：`count_agg` 数事件条数，`unique_count_agg` 去重后计数。
   同一批原始事件，两种聚合可以差出几倍。客户主张差异时，**先问聚合口径，再问时间窗**，
   最后才怀疑数据错误。这条经验能解决 80% 的用量争议。

4. **重放事件导致用量虚高**：上游 webhook 重试未做幂等 → 同一事件入账两次 → 用量翻倍。
   排查手法：检查关键事件是否带幂等键，检查同一 `entity_id` 是否在极短时间窗内重复出现。

5. **draft 账单拿去对账**：draft 可被随时修改，拿它和客户争执没有意义。约定：
   对外对账只认 `finalized`。若客户看到的是 draft，先确认是否最终会变更。

6. **不要把 billing 做成财务报表**：本技能只做"计费口径 → 账单金额"的确定性推导。
   收入确认时点、递延收入分摊、毛利核算全部属于 R03 财务。越界即 `scope_overlap`。
