# 证据分级与三角验证：GRADE / CEBM 的迁移用法

> 用途：R05 研究链第 4、5 段 `verify` 与 `triangulate` 的方法依据。目标是把“我觉得可信”变成可复核的等级、降级理由与矛盾记录。

## 方法要点

1. **先定证据等级，再谈结论。** GRADE 把证据质量分为高/中/低/极低，核心降级因素：偏倚风险、不一致性、间接性、不精确性、发表偏倚；升级因素：效应量大、剂量反应、混杂会削弱效应。CEBM（牛津证据等级）2011 版按研究设计分层，从系统综述/RCT 到机制推断与专家意见。
2. **迁移到商业研究时的四级近似：**
   - A：原始统计/全量数据库 + 可复算；
   - B：高质量二手（方法透明、样本清楚）+ 可回抓；
   - C：单一一手访谈/案例，或口径不清的二手；
   - D：三手转述、无方法说明的榜单。
3. **三角验证（triangulation）不是“多找几个链接”。** Denzin 区分数据三角、研究者三角、方法三角、理论三角；本仓至少要求“源层级三角 + 时间/口径一致”。
4. **结论置信度规则：** 高 = ≥2 个独立源且 ≥2 个层级且全部验证通过；中 = ≥2 源但层级单一或存在未验证；低 = 单源。单源必须显式标 `single_source`。
5. **矛盾必须保留。** 同一可比序列（同一指标、同一口径期）出现 >10% 极差时，记录 `open` 矛盾与处置（保留区间/说明口径差异），不允许静默取平均。

## 来源

- Guyatt GH, Oxman AD, Vist GE, et al. “GRADE: an emerging consensus on rating quality of evidence and strength of recommendations.” *BMJ*, 2008;336:924–926.
- OCEBM Levels of Evidence Working Group. *The Oxford 2011 Levels of Evidence*. Oxford Centre for Evidence-Based Medicine, 2011.
- Higgins JPT, Green S (eds). *Cochrane Handbook for Systematic Reviews of Interventions*, Version 5.1.0, 2011（偏倚风险与不一致性评估）。
- Denzin NK. *The Research Act: A Theoretical Introduction to Sociological Methods*, 1978（三角验证的四种类型）。
- Patton MQ. “Enhancing the quality and credibility of qualitative analysis.” *Health Services Research*, 1999;34(5):1189–1208（定性研究的三角与矛盾处理）。

## 适用边界

- GRADE/CEBM 为医学证据设计，商业研究很少有 RCT；迁移的是“降级理由”和“透明报告”，不是把访谈硬套成“病例对照”。
- 三角验证不能修复系统性偏差：三个同源转述仍是一个源。必须检查独立性（是否都引用同一份原始报告）。
- 置信度是“当前证据下的判断”，不是概率；不能写成“87% 可信”。
- 矛盾阈值 10% 是管理口径，不是统计显著性；对价格、份额等波动大的指标可放宽，但要在边界写明。
- 单源结论并非不能写，但只能作为“待验证假设”，不能进入高置信度结论或直接触发决策。

## 误用反例

| 反例 | 为什么错 | 本仓拦截 |
|---|---|---|
| 只有 1 条访谈，却写“高置信度、可立即放量” | 单源不能支撑高置信度，属于结论超出证据 | `tri:two_sources_or_single`、`tri:single_source_low_confidence` |
| 三个来源其实是同一篇报告的转载 | 非独立源，三角验证失效 | 置信度要求 ≥2 个 `source_type`，且人工复核 publisher |
| 两个数字口径不同（2025 实际 vs 2026 预测）却判矛盾 | 不可比序列制造伪冲突 | 按 `series`（指标+口径期）分组，而非按单位 |
| 发现矛盾后直接取平均 | 掩盖口径差异，产生“精确的错误” | `tri:contradictions_recorded` 必须记录且处置为保留区间 |
| 用“行业常识”补缺失证据 | 无来源断言 | 报告门禁要求结论来源存在于台账 |

## 与本仓落点

- 生产代码：`research_chain/verify.py`（回抓/复算/偏见/时效）、`research_chain/triangulate.py`（置信度、`series` 分组、矛盾记录）。
- 门禁：`verify:coverage`、`verify:disclosure`、`verify:four_dimensions`、`verify:recompute_done`、`tri:confidence_enum`、`tri:two_sources_or_single`、`tri:contradictions_recorded`。
- 误用样本：`misuse/overclaim.json` 被 `tri:two_sources_or_single` 拦下。
