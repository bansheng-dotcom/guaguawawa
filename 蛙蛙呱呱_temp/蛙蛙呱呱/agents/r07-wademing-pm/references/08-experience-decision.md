# 模块H · 经验检索与决策汇报（S08）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：要做产品取舍决策、要复用历史经验、要把需求规范地提交时。决策汇报把
「拍脑袋」变成「可评审的决策包」，经验检索把「上次踩过的坑」变成「可检索的规则」。

- **决策汇报三层**：产品判断 / 执行说明 / 决策门禁（成功判据 / 不在范围 / 停止条件）。
  好决策必须三层都答，尤其「停止条件」——说清「什么情况放弃」比「什么情况成功」更稀缺。
- **需求管理**：需求卡必填 7 字段（编号/问题/范围/不在范围/成功指标/验收/复核状态），
  未复核只能标「草稿」，不得作为正式开发输入。
- **经验检索（Experience RAG）**：经验卡五要素（触发/范围/规则/边界/来源可信度），
  L1 Gate 只看索引命中，重任务 L2 才开卡。

## 二、可执行口径（与 skills/s08_decision.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| 决策三层 | `decision.layers`（3 枚举） | product_judgment/execution_spec/decision_gate 俱全 |
| 决策门禁 | 无阈值（固定） | success/non_goals/stop_condition 俱全 |
| 需求卡 | 代码内固定 7 字段 | demand_id/problem/scope/non_goals/success_metric/acceptance/review_status |
| 草稿规范 | 无阈值（固定） | review_status ∈ 草稿/draft/未复核 且 submittable → BLOCKER |
| 经验卡五要素 | `experience.card_fields`（5 枚举） | trigger/scope/rule/boundary/source_credibility 俱全 |
| 经验 verified | 无阈值（固定） | verified=true 但无 source_credibility → BLOCKER |

输出键（contracts.py `decision` 契约）：`ok`、`checks` + 动作专属：
- `decision` → `layers`
- `demand` → `demand_required_fields`
- `experience` → `card_fields`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| 决策三层 | product_judgment + execution_spec + decision_gate（三子字段） | ok=true |
| 需求卡 | 7 字段 + review_status=已复核 | ok=true |
| 需求卡草稿提交 | review_status=草稿 + submittable=true | ok=false（拦下） |
| 经验卡五要素 | trigger/scope/rule/boundary/source_credibility | ok=true |
| 经验 verified 无来源 | verified=true 无 source_credibility | ok=false |

## 四、实战踩坑

1. **「候选经验 ≠ 已验证规则」是反模式**：`_experience` 只在 `verified=true` 且无
   `source_credibility` 时才拦；但更隐蔽的坑是「把项目事实当经验规则」——经验卡要写
   「可复用的规则」而非「这次做了什么」。这条靠 review 的 value_utility 兜底。
2. **草稿规范是「review_status 三值 + submittable 组合」**：`review_status` 空字符串
   也拦（缺复核状态）；「草稿/未复核」只有在 `submittable=true` 时才拦「草稿不能提交」，
   判读别把「草稿但不能提交」和「草稿本就不该提交」混为一谈。
3. **决策门禁的 stop_condition 最易漏**：`_decision` 对 decision_gate 强制 success/
   non_goals/stop_condition 三子字段，写决策时最容易只写 success 漏了 stop_condition。
4. **需求卡 review_status 是中文枚举**：`DEMAND_REQUIRED` 用「已复核」等中文值，
   提交时 review_status 写英文「reviewed」不会被草稿门禁认成「已复核」——口径要
   对齐案例 semantic_layer 的 terms 定义。
