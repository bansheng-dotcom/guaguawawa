# S01 财务报表与月结
> 蒸馏自: 补充技能/01-当前能力域/anthropics__financial-services/month-end-closer/SKILL.md
>


## 方法论（来源 month-end-closer / gl-reconciler / statement-auditor）

月结五步：应计入账 → roll-forward → 对账 → 差异注解 → 签核。
本 agent 覆盖前四步的确定性校验，签核永远留给人工（不代签）。

## roll-forward 恒等式

```
期初 X + 新增 A + 应计 B − 反转 C − 付款 D + 重分类 E + 外币折算 F = 期末 Y
```

- 容差 0.01；不平即 CRITICAL，**不得 plug（凭差额硬调）**
- 应计 = 基数 × 天数占比 − 已入账部分；应计仅进 staging，发布须 controller 批准

## 对账（gl-recon 四步）

1. normalize：GL 与子账统一键/金额/数量结构
2. match：全外连接，金额容差 0.01、数量容差 0
3. classify 六桶：matched / amount_break / quantity_break / timing_break /
   gl_only / subledger_only
4. 归因：fx（本币一致本位币不一致）/ fee_accrual（小额规律差）/
   timing / mapping / duplicate_missing_post / data_quality

匹配率 ≥ 95% 才可过关。

## 差异注解（variance-commentary）

- 触发 = |差异| ≥ max(行基数 × 5%, 固定下限)，或行 ∈ 总是评论清单
  （收入 / 人员成本 / 现金）
- driver 必须解释 **why**（如「客户续约提前确认」），只复述数字
  （「增加 3000 (12%)」）不合格

## 证据

对账工作底稿、roll-forward 表、差异注解、签核记录——留存见 S07。

## 已验证算例（run_tests.py T08，已对拍）

- **rollforward**：`examples/financial_rollforward.json` 两个账户，
  cash 账户期末对不上（`diff = -500.00`，`expected_closing` 对拍），
  `balanced=1 / broken=[cash]`；对账不平时**不得 plug**，只报 CRITICAL。
- **recon**：`examples/financial_recon.json` 6 笔 GL vs 子账 →
  `matched_pct=0.5`、`total=6`、六桶分布
  `matched=3 / amount_break=1 / timing_break=1 / subledger_only=1 / gl_only=0`、
  `break_count=3`；匹配率 50% < 95% 门槛 → `ok=false`。
  每笔差异均带 `likely_cause`（mapping / duplicate_missing_post / timing）。
- **variance**：`examples/financial_variance.json` → `flagged=3`
  （revenue/cash/marketing 恒评清单命中），`material_missing=1`
  （marketing 有差异但 driver 只复述数字未解释 why）。

## 实战踩坑

- 匹配率口径：分母用 **GL ∪ 子账的全外连接数**，不是 GL 单边数——
  早期用单边导致「子账多出的记录」不拉低匹配率，差异被漏。
- 归因优先级：`subledger_only` 必须先判 `duplicate_missing_post`
  而不是直接归 `timing`，否则重复过账被误判成时间性差异，掩盖真问题。
- 差异注解的 `why` 是硬门禁：driver 写「增加 3000 (12%)」只复述数字，判不合格；
  必须写「客户续约提前确认」这类成因。
