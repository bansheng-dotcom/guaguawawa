# 模块B · 数据清洗与质量门禁

> 蒸馏自: 
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/01-data-quality-validation/data-quality-audit/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/01-data-quality-validation/programmatic-eda/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/02-documentation-knowledge/metric-reconciliation/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/02-documentation-knowledge/semantic-model-builder/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/03-data-analysis-investigation/root-cause-investigation/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/04-data-storytelling-visualization/executive-summary-generator/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/04-data-storytelling-visualization/data-narrative-builder/SKILL.md

本模块真实承载数据流水线和分析洞察的“守门员”与“领航员”角色。核心主张：**质检是门禁，不是事后补救；洞察是故事，不是数据堆砌。** 通过高深度的质量计分板 (Scorecard)、根因下探框架以及高管汇报结构，本模块提供一套端到端的业务方法论。

## B1. 数据质量计分板（Scorecard）与六维度模型

每一项数据质量发现均归入以下维度并加权打分，生成最终的质量记分卡。

| 维度 | 权重 | 核心关注点与评估算法 |
|---|---|---|
| Completeness (完整性) | 20% | 空值率概览；重点关注结构性空值 vs 随机空值。超过设定阈值即标记风险。 |
| Accuracy (准确性) | 20% | 跨字段逻辑自洽（如 `shipped_date >= order_date`），财务恒等式复算（如 `净利润 = 收入 - 退款 - 折扣`）。 |
| Consistency (一致性) | 20% | 引用完整性（标准 FK 关系，统计孤儿记录率）；跨系统对账差异计算。 |
| Timeliness (及时性) | 15% | 验证流水线 SLA（最新记录时间戳距离当前时间）；回填延迟与管道事件断崖式掉量。 |
| Uniqueness (唯一性) | 15% | 键级唯一性（PK 和自然键重复率）；整行重复检查；辨别是版本迭代还是 Fan-out 错误。 |
| Validity (有效性) | 10% | 取值范围限制（年龄 0-120，百分比 0-1，枚举值一致性）；离群点与格式校验。 |

**评分机制：** 0=系统失败、5=半数通过、8=仅小问题可用、10=全数通过。
**严重度定级：** CRITICAL / HIGH / MEDIUM / LOW。
*(触发 CRITICAL 示例：核心营收出现负数、外键孤立率激增、数据延迟超过 2×SLA)*

## B2. 质量门禁：算法阈值与落地规则

针对核心指标和底层数据，实施硬性的质量拦截网，避免脏数据进入高管决策层：

- **空值容忍度**：核心业务字段（如交易金额、用户ID）空值率 >5% 警告，>30% 熔断 (FAIL)；非核心人口统计学特征（如偏好标签）可放宽至 50%。
- **重复与扩散 (Fan-out)**：整行重复率 >0% 触发预警排查，>1% 熔断 (FAIL)。必须清晰说明键级重复是业务设计（如版本控制 SCD2）还是错误多对多 JOIN。
- **离群点探测 (Outliers)**：采用基于 IQR 的非参数方法校验 `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]`，或针对正态分布应用 Z-score 阈值 `|z| > 3`。需定性判断：是真实业务信号、数据错误还是系统哨兵值（如 9999-12-31）。
- **指标对账容差**：两套报表/系统数据对账时，采用绝对差异和百分比差异双轨验证。允许的核心 KPI 计算差异容忍度应严格控制在 `<0.1%`，超此限度必须追踪计算路径。
- **关联共线性**：特征探索阶段，皮尔逊相关系数 `|r| >= 0.8` 提示共线性风险，`|r| >= 0.95` 判定为近乎同一度量，需进行降维或剔除。

## B3. 指标语义构建与对账 (Semantic Model & Reconciliation)

统一的语义层是消除“为什么两张报表数字不同”的唯一解：

1. **唯一真理来源**：定义指标必须明确分子、分母、过滤条件、时间维度（及所属时区）、业务粒度，形成标准 YAML/Markdown 文档。
2. **根因归因分层**：对账不一致的最常见原因按排查顺序为：
   - 过滤条件不一致 / 维度层级映射错乱。
   - 多对多 Join 导致的记录倍增 (Fan-out) 被 DISTINCT 错误掩盖。
   - 时间截断与聚合粒度不同。
   - NULL 值的隐式处理逻辑差异。

## B4. 根因下钻分析方法论 (Root Cause Investigation)

当核心 KPI 发生异动时，通过系统化框架进行归因，而非凭直觉盲猜：

1. **异常确认 (Validate the change)**：应用 Z-score 或滚动均值对比验证，判断是否属于 `±1.5` 标准差的正常波动。若在正常范围内，宣告波动合理并结案。
2. **基线偏移分解 (Decompose the metric)**：将指标拆解为构成公式。例如：`营收 = 流量 × 转化率 × 客单价`。锁定驱动变量。
3. **帕累托下钻 (Drill down systematically)**：沿主要业务维度（地域、渠道、端、用户分层）进行下钻。使用**绝对贡献度公式**评估每个维度属性的影响权重，排列优先级。
4. **假设检验 (Test hypotheses)**：提出明确的业务假设（例如：某区域引流质量下降），结合产品发布、营销活动或服务降级时间线进行论证。

## B5. 高管报告与可视化输出指南 (Data Storytelling & Executive Delivery)

分析的最后一公里是汇报。输出必须具备高度的商业敏锐度和决定导向：

1. **金字塔原理 (The Pyramid Principle)**：
   - **结论先行 (Answer-first)**：首句即点明核心洞察，例如“由于 iOS 渠道获客成本攀升，Q3 净利润损失 $800K”。
   - **自上而下**：先讲业务影响及行动建议，后陈述数据论据和下钻细节。绝对不要把结论埋在报告最后。
2. **SCQA 叙事框架**：
   - **Situation (情境)**：建立共识的基础业务背景。
   - **Complication (冲突)**：指出破坏现状的问题或异动。
   - **Resolution (解决)**：数据揭示的答案和具体行动策略。
3. **图表无术语化 (Chart Storytelling)**：
   - 图表标题禁止使用“按地区划分的销售额趋势”，必须替换为带洞察的行动标题，如“华东区销售额连续 3 周下滑，拉低整体大盘”。
   - 提供业务语境，将抽象数字具象化：提示“影响的用户规模”、“挽回的收入”等。
4. **决策块设计 (Decision Block)**：
   - 执行摘要（不超过 1-2 页）最后必须明确：需要高管批复什么？需要投入多少资源？预期回报是什么？Deadline 是什么时候？不提供无行动的虚无建议。
