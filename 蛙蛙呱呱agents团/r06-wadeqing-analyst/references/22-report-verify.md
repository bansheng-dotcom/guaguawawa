# 22 · 报告验证链（verify）：CoV 六问与回流码

> R06 报告链第 7 段的领域依据。目的：把“写得像”变成“证据够不够”，不成立就回流，不许硬写。

## 1. 六问是什么

每条断言进入正文前必须回答：

| # | 问题 | 通过条件 | 失败去向 |
|---|---|---|---|
| 1 | 指标状态 | 指标、单位、分段明确 | text |
| 2 | 分子分母 | 分母同口径、非零、可追到计划 | analysis |
| 3 | 对照基准 | 有前后期/对照组/区间 | text |
| 4 | 驱动拆解 | 点名驱动必须给量价或明确说明不能拆 | analysis |
| 5 | 反证 | 至少 2 条替代解释，且各有检验与结论 | analysis |
| 6 | 边界 | 覆盖 ≥80%、质量分 ≥60、季节性不可验证已声明 | analysis |

## 2. 三种回流码 + 丢弃

- `analysis`：证据不支持（分母错、无拆解、无对照）→ 回分析链补证据；
- `text`：表达问题（单位缺失、陈述不清、行长超限）→ 回文字包重写；
- `chart`：图表承载不了断言（必绘系列缺失、标注放不下）→ 回图表包；
- `drop`：无报告价值（变化为 0、贡献低于停止阈值）→ 丢弃，不占正文。

回流码不是“备注”，而是下一步动作的唯一入口；没有 route 的失败一律视为未处理。

## 3. bounded_modules

证据有限但仍有信息量的单元，不进入主结论，放进 `bounded_modules`，可独立渲染、可被追问。
判定：缺量价拆解、样本不足、贡献低于停止阈值。

这条设计避免了两个极端：为了完整硬写（造假），或为了严谨全删（浪费信息）。

## 4. 与报告产线的关系

CoV 只产出 `verification.json`，不写报告。报告仍由 R01 出具，R04 终审。
R06 的角色边界不变：只交证据与验证结果，不越权签发。

## 5. 本仓落点

| 能力 | 代码 | 门禁 |
|---|---|---|
| 六问 | `analysis_chain/verify.py` | 六问齐全、主结论无硬失败 |
| 回流码 | 同上 | route ∈ pass/analysis/text/chart/drop |
| bounded | 同上 + `material_pack.py` | 主结论至少 1 条；bounded 不混入正文 |
| 可追 | `deliver.audit_trace` | 正文数字 100% 回到 material pack |

## 6. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 没有分母就写“增长 20%” | 可能是换分母制造增长 | denominator 缺失 → analysis |
| 点名“抖音下滑”但不拆量价 | 只是复述现象 | driver 无拆解且无原因 → bounded/analysis |
| 只有一条解释 | 确认偏误 | alternatives <2 → analysis |
| 覆盖只有 50% 仍写趋势 | 采集事实冒充业务事实 | boundary 失败 → analysis |
| 证据不足仍写进主结论 | 造假 | bounded 模块不得进入正文 |

## 7. 来源

- Dhuliawala, S. et al. (2023). Chain-of-Verification Reduces Hallucination in Large Language Models. *arXiv:2309.11495*.
- GRADE Working Group（Guyatt et al., 2008）：证据质量与推荐强度分级。
- Hernán & Robins, *Causal Inference: What If* (2020)：反事实与识别策略。
- 本仓 `_refs/dar/references/report_text_pack_contract.md`：单位写作与回流码的工程契约（只借结构，不复制文本）。
