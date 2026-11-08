# 模块C · 用户故事与 PRD（S03）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：产品判断已定、要把它写成可执行、可验收、可评审的需求文档时。PRD 的核心
不是「写得多」，而是「八道门禁都过得了」——每道门禁对应一个会翻车的坑。

- **PRD 八门禁**：problem / user / value / scope / metric / acceptance / risk / read，
  逐门禁自检，任一不过即 FAIL。
- **用户故事 / Job story 句式**：故事不是「我要 XX」，而是三段句（As a / I want / so
  that，或 When / I want / so I can），验收标准条数有上下限，太少说明拆得不够。
- **验收标准**：Given / When / Then，可观察、可复现，且必须覆盖失败态。

## 二、可执行口径（与 skills/s03_prd.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| PRD 门禁 | `prd.gates`（8 项枚举） | 8 项全过才 ok；`passed_gates` 输出实过数 |
| 问题门禁 | 无阈值（固定） | problem 非空且非「支持/优化/增强/完善」短句 |
| 价值门禁 | 无阈值 | before/how/after/alternatives 或 experience_gain/cost_reduction 之一 |
| 范围门禁 | 无阈值 | p0 非空 **且** non_goals 非空 |
| 指标门禁 | 无阈值 | 有口径/数据源/基线之一，且无「提升用户体验」等空泛指标 |
| 验收门禁 | 无阈值 | acceptance_criteria 非空 |
| 风险门禁 | `prd.risk_hypotheses_min` | 承重假设 ≥3 |
| 可读门禁 | 无阈值 | executive_summary/conclusion 非空（结论先行） |
| 用户故事 AC | `prd.story_ac_min/max`（user 4-6）/ `prd.jobstory_ac_min/max`（job 6-8） | 超出区间 → BLOCKER |

输出键（contracts.py `prd` 契约）：`ok`、`checks` + 动作专属：
- `prd` → `gates`、`gate_ok`、`passed_gates`
- `story` → `kind`、`ac_count`、`ac_band`
- `acceptance` → `ac_count`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| PRD 八门禁 | `examples/prd.json`（新手引导 PRD） | ok=true，`passed_gates=8` |
| PRD 缺范围 | 改 `scope.p0=[]` | ok=false（范围门禁拦下） |
| 用户故事 4 AC | story 句 + 4 条 AC | ok=true，kind=user |
| 用户故事 1 AC | story 句 + 1 条 AC | ok=false（AC 少于 4 拦下） |
| 验收 GWT | `{"given":"g","when":"w","then":"t"}` | ok=true |
| 验收缺 Then | `{"given":"g","when":"w"}` | ok=false |

## 四、实战踩坑

1. **问题门禁的「短句豁免」要小心**：`_validate_prd` 判「优化/增强/完善」等词时，
   若 problem 长度 <20 会判 vague。写问题陈述要具体到「谁、在什么场景、遇到什么、代价
   是什么」，只写「优化某功能」必然 FAIL。
2. **范围门禁是「p0 与 non_goals 双非空」**：只给 p0 不给 non_goals 仍 FAIL——「不在范围」
   是防范围蔓延的关键，八门禁里最容易漏的是这一条。
3. **指标门禁拦「空泛指标」**：metrics 里出现「提升用户体验/提高效率/增加留存」直接 FAIL，
   即使其它字段齐全。指标必须落到「7 日激活率 + 数据源 + 基线 + 目标」这个粒度。
4. **risk 与 load_bearing_assumptions 是别名**：代码读 `data["risks"] or
   data["load_bearing_assumptions"]`，两种写法都认，但每条假设要带最小验证（validation）。
