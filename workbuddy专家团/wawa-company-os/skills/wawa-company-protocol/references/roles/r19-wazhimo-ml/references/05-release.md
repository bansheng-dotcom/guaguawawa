# 05 · 回归与发布候选口径（release）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-agent-improvement/SKILL.md
>


> 技能：`release` ｜ 动作：`regression`（回归报告）、`candidate`（发布候选）
> 来源：mlflow__mlflow（`mlflow-agent-improvement` 的 EXPLORE→PLAN→IMPLEMENT→VERIFY 四步、fail-before/pass-after、诊断层；`mlflow-evaluation` 的版本比较）

## 第一层：方法论

回归与发布候选是 R19 的**核心关卡**。新旧版本、证据、裁决、诊断层——这四样构成
「这个候选凭什么可以上线」的地基。把这段做成确定性校验的价值，不在于「放行得更快」，
而在于**让「效果看起来不错」的结论在关卡层就被拦下**。

三条方法论：

1. **回归必须证明「旧版失败、新版通过」**。`fail_before=true` 是左半证据（旧版
   在用例上失败），`pass_after=true` 是右半证据（新版同用例通过）。只有右半边
   （新版能跑通）不构成回归——那可能只是"本来就一直能用"。
2. **既有测试不回退是底线**。`existing_green=true` 证明新版没有破坏已有行为。
   修好了 A 却弄坏了 B，不是改进，是交换。
3. **发布裁决只有三种**。`PASS`（证据齐全，可交部署）、`BLOCK`（存在阻断缺陷）、
   `NEEDS_REVIEW`（证据不全，交人工复核）。**PASS 必须挂回归报告**——没有回归的
   PASS 就是"凭感觉放行"。

**本角色绝对不做的事**：**绝不把发布候选等同于生产部署**。candidate 只产出
"可发布的证据链"，实际部署 / 灰度 / 流量切分交 R09 + 人工。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| regression.candidate_id | 非空 | R19 发布口径 |
| regression.diagnosis_layer | ∈ `release.diagnosis_layers` = `[capability, data, routing, instruction, knowledge, reward]` | mlflow-agent-improvement |
| regression.versions | old_version 与 new_version 都非空 | 版本比较 |
| regression.fail_before | == true | mlflow-agent-improvement |
| regression.pass_after | == true | mlflow-agent-improvement |
| regression.existing_green | == true | mlflow-agent-improvement |
| candidate.candidate_id | 非空 | R19 发布口径 |
| candidate.verdict | ∈ `release.verdicts` = `[PASS, BLOCK, NEEDS_REVIEW]` | R19 发布口径 |
| candidate.evidence | ≥ 1 条 | R19 证据链要求 |
| candidate.regression_required | verdict=PASS 时 regression_id 必须非空 | R19 红线 2 |

**阈值单一真源**：`release.verdicts` / `release.diagnosis_layers` 以
`experience/thresholds.json` 的 `release` 段为准。

## 第三层：已验证的算例

**算例 A（干净回归）**：`examples/release_regression.json`
```
cand-2041-3 / instruction / v2→v3 / fail_before=T / pass_after=T / existing_green=T
```
六判据全过 → `ok=true`，`verdict=PASS`。

**算例 B（脏回归）**：`examples/release_regression_dirty.json`
```
cand-2041-3 / diagnosis_layer=prompt_vibes / v3→v3 / pass_after=F / existing_green=F
```
BLOCKER ×4：诊断层越界；新旧版本相同；pass_after=false；existing_green=false。

**算例 C（干净候选）**：`examples/release_candidate.json`
```
cand-2041-3 / verdict=PASS / 3 条证据 / regression_id=reg-2041-3
```
裁决合法、证据非空、PASS 挂回归 → `ok=true`。

**算例 D（脏候选）**：`examples/release_candidate_dirty.json`
```
cand-2041-3 / verdict=SHIP_IT / evidence=[] / regression_id=""
```
BLOCKER ×3：裁决越界；证据为空。

## 第四层：实战踩坑

1. **只有 pass_after 不是回归**。最常见的伪回归：报告里写"新版通过了所有测试"，
   却没有 fail_before——这说明不了任何改进。回归的价值恰恰在"旧版曾失败"这个
   对比上。

2. **诊断层是六个固定枚举**。`capability`（能力缺失）/`data`（数据问题）/
   `routing`（路由错误）/`instruction`（指令/prompt）/`knowledge`（知识库）/
   `reward`（奖励/反馈）。写 `prompt`（应为 instruction）或 `model`（不在枚举）
   都会被拦。

3. **新旧版本号必须不同**。`v3→v3` 的"回归"是自欺——同一个版本不可能既失败又
   通过。版本号相同直接 BLOCKER。

4. **PASS 不挂回归 = 红线**。这是 R19 最核心的红线 2：不许"效果看起来不错"直接
   上线。verdict=PASS 而 regression_id 为空，一律拦下退 BLOCK/NEEDS_REVIEW。

5. **BLOCK 不是失败，是正常裁决**。有硬缺陷时给 BLOCK 是评分器在正常工作，不是
   异常。别把"没通过"当成"工具坏了"。

6. **evidence 是结构化证据不是形容词**。`["效果不错"]` 不算证据；`["eval v1
   正确率 0.91→0.95", "回归 reg-2041-3 通过"]` 才算。证据要可指认、可复算。

7. **不要在结论里写"我已经把它发上线了"**。这是越权，触发 scope_boundary。正确
   写法："候选 cand-2041-3 裁决 PASS，证据链 3 条，实际发布交 R09。"
