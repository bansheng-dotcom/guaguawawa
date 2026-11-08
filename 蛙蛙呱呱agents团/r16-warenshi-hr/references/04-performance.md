# 04 · 绩效与目标口径（performance）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/performance-review/SKILL.md
>


> 技能：`performance` ｜ 动作：`appraisal`（绩效评估）、`goal`（目标）
> 来源：frappe__hrms（Appraisal / AppraisalCycle / Goal 的 Select 枚举与区间）

## 第一层：方法论

绩效是**薪酬/晋升的输入，但评分是管理动作不是数学结论**。R16 只校验评分是否落在
合法区间、目标是否可追溯，**不替人定档、不写评级结论**（评级结论交 R01 决策 + R03 合规）。

三条方法论：

1. **评分区间即合法性边界**。`total_score` 与各 KRA 单项分必须落在 [score_min, score_max]
   （默认 [0, 5]）。越界的评分无法映射到任何薪酬/晋升口径，一律 BLOCKER。
2. **目标进度是百分制事实**。`progress ∈ [0, 100]`；`Completed` 的目标进度必须满 100。
   完成态却不满进度，是"伪完成"。
3. **KRA 引用完整 = 可追溯**。每个关键结果（KRA）必须有可量化结果（measurable_result）
   或关键结果（key_result），否则目标无法度量。

**本角色绝对不做的事**：不替人定档、不写评级结论、不做晋升/淘汰建议。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| appraisal.appraisal_cycle | 非空 | hrms Appraisal 必填 |
| appraisal.cycle_status | ∈ `{Not Started, In Progress, Completed}`（若提供） | hrms AppraisalCycle.status |
| appraisal.total_score | `∈ [score_min, score_max]`（默认 [0,5]） | thresholds.appraisal |
| appraisal.kra_scores | 各 KRA 单项分 `∈ [score_min, score_max]` | 同区间 |
| appraisal.kra_complete | 有 KRA 则每个必须有分数 | 打分完整 |
| goal.status | ∈ `{Pending, In Progress, Completed, Archived, Closed}` | hrms Goal.status |
| goal.progress | `∈ [progress_min, progress_max]`（默认 [0,100]） | thresholds.goal |
| goal.kra_ref | 每个 KRA 含 `measurable_result` 或 `key_result` | 可度量 |
| goal.completed | `status==Completed` → `progress ≥ 100` | 防伪完成 |

**绩效周期状态速查**：
- `Not Started`：周期未启动，不应有评分。
- `In Progress`：正在评估，评分进行中。
- `Completed`：周期结束，评分应齐备。

## 第三层：已验证的算例

**算例 A（干净评估）**：`examples/appraisal.json`
```
2026-H2 / In Progress / total=4.2 / KRA[交付质量=4.5, 协作=3.9]
```
周期非空、状态合法、总分与单项分均在 [0,5]、无缺分 → `ok=true`。

**算例 B（脏评估）**：`examples/appraisal_dirty.json`
```
2026-H2 / Bogus / total=9.0 / KRA[交付质量=7.0, 协作=""]
```
BLOCKER ×3：周期状态越界、总分 9.0 > 5、KRA「协作」缺分数。

**算例 C（干净目标）**：`examples/goal.json`
```
交付零缺陷 / Completed / progress=100 / KRA[上线无阻塞(measurable), 响应及时(key_result)]
```
状态合法、进度满 100、KRA 引用完整 → `ok=true`。

**算例 D（脏目标）**：`examples/goal_dirty.json`
```
交付零缺陷 / Completed / progress=40 / KRA[上线无阻塞(无量化结果)]
```
BLOCKER ×2：Completed 但进度 40 < 100（伪完成）、KRA 缺量化结果。

## 第四层：实战踩坑

1. **评分制式混淆**。有的系统用 0–5 分，有的用百分制（score_max=100）。
   本口径默认 5 分制，百分制须在 thresholds 覆盖。混用会导致 85 分被判越界。

2. **KRA 有名字没度量**。`{"name": "提升效率"}` 没有 measurable_result，无法验证。
   这类"口号型 KRA"是绩效失效的常见原因。

3. **Completed 的伪完成**。目标标 Completed 但进度 40%，通常是"提前归档"。
   本口径要求 Completed 必须 progress ≥ 100。

4. **周期状态与评分的一致性**。`Not Started` 的周期不应有 final_score；
   本技能暂不强制，但上层可加这层勾稽。

5. **不要在结论里写"这个员工绩效优秀，建议晋升"**。评级与晋升是 R01 决策。
   正确写法："评估 2026-H2 总分 4.2 ∈ [0,5]，KRA 打分完整；评级结论交 R01。"

6. **Archived vs Closed**。`Archived` 是归档（主动归档），`Closed` 是关闭（自然结束），
   语义不同但都属终态，本口径均接受。

7. **目标进度的小数**。允许小数（如 66.7），但必须在 [0,100]。100.1 越界。
