# 自媒体字段映射与数据分析方法论

> 蒸馏自: 补充技能/nimrodfisher__data-analytics-skills/02-documentation-knowledge/schema-mapper/SKILL.md, 补充技能/nimrodfisher__data-analytics-skills/02-documentation-knowledge/sql-to-business-logic/SKILL.md, 补充技能/Starlitnightly__omicverse/WORKFLOW.md

本文档定义了自媒体分析体系中跨平台数据结构到核心业务逻辑（Business Logic）的映射关系。这不仅仅是应对门禁检查的字典，而是**一套支持可跨平台对比、可复算的「归一化契约」和「数据分析方法论」**。我们将遵循“一指标一真源”的铁律，并结合生信多组学数据分析中强后端的阈值标准和降维算法思维，构建高维度、高业务厚度的自媒体数据台。

## 一、 统一字段 Schema 映射 (Schema Mapper)

核心要义是将各平台（小红书、抖音、微信、知乎、B站）格式各异的“源表”字段，安全映射到统一的 Analytical Schema，消除歧义与冗余。

### 1. 目标 Schema (Target Schema)

经过数据清洗与转换，所有的输入源必须收敛至以下标准字段集，任何未在此定义中的私有字段均不直接进入默认的每日链路：

- **基础维度**：`platform` / `date` / `source_file` / `source_mtime`
- **受众指标**：`total_followers` / `new_followers` / `lost_followers` / `net_followers`
- **财务指标**：`gross_revenue` / `refund_amount` / `net_revenue`
- **互动指标**：`content_count` / `impression` / `engagement` / `updated_at`

### 2. 平台差异降级映射与源头冲突解决 (Source to Target Mapping)

当同一指标在多个数据源存在时，遵循**「一指标一真源」**，严禁使用“均值”或“加权”，防止业务逻辑稀释：

| Target Column | 平台/业务场景 | Source Column / 业务逻辑 | 映射规则与注意事项 |
| :--- | :--- | :--- | :--- |
| `net_followers` | 小红书 | 报名粉丝统计表 | 小红书“内容归因涨粉”具有滞后和不完全统计特征，**拒绝作为全局净增默认来源**。强制采用“报名粉丝统计表”计算。 |
| `total_followers` | 全平台 | 平台后台数据快照 | 取最新快照。**严禁**将快照字段误当做增长字段求和。 |
| `net_followers` | 全平台 (除小红书特例外) | 每日新增粉丝汇总 | 按日期范围求和（`SUM()`）。**严禁**取末端值代替增量。 |
| `net_revenue` | 商业化核算 | `gross_revenue` - `refund_amount` | 衍生映射。这是计算所有财务转化指标（如 ROI、客单价）的基石。必须保证恒等成立，对账容差必须小于 0.01。 |

> **溯源与审计要求**：保留 `source_file` 和 `source_mtime` 字段，实现数据谱系（Data Lineage）和追踪。

## 二、 从 SQL 结构到业务逻辑 (SQL to Business Logic)

自媒体数据的汇聚不是简单的 `SELECT * FROM tables`。我们需要明确每一个聚合和条件过滤背后的业务意义，确保给到决策层的看板能如实反映业务健康度。

### 1. 数据门禁与过滤 (WHERE & Filters)

通过业务规则进行强数据拦截，只有通过准确性校验的“干净数据”才能进入 `monthly/*` 的正常日报（Default Pipeline）。**未经校验的数据或 AI 产出的预测解读，只能作为旁注（Annotations），绝不允许污染核心数据源。**

- **新鲜度校验 (Freshness)**:
  - 核心逻辑：`DATEDIFF(CURRENT_DATE, date) <= 1` (fresh_days) 允许进入正常日报。
  - 过期阻断：`DATEDIFF(CURRENT_DATE, date) > 7` (stale_days) 数据被判定为过期，拒绝进入默认报表。

### 2. 聚合分析与生态健康度 (GROUP BY & Aggregations)

借鉴生信多组学数据（如转录组）在评估群体多样性时的阈值判定思路，我们采用赫芬达尔-赫希曼指数（Herfindahl-Hirschman Index, HHI）来评估**粉丝与收入的平台集中度**，而非简单的占比（Percentage）。这能更敏锐地捕捉到对单一平台的过度依赖。

- **HHI 集中度校验阈值设定**:
  - `HHI < 0.5`: **健康 (Healthy)**。平台生态具有良好的多样性和抗风险能力。
  - `HHI ≥ 0.5`: **高度集中 (High Concentration)**。系统需发出预警（Warning），提示多平台矩阵建设存在短板。
  - `HHI > 0.75`: **极端集中 (Extreme Concentration)**。平台生态高度脆弱，一旦主阵地限流将面临断崖式下跌。

> **阈值真源铁律**：曾经 HHI 存在 0.25 和 0.5 两套并存标准导致严重事故。现在，**所有的决策阈值（Thresholds）强制统一收敛于 `thresholds.json`**（针对本页特指 selfmedia 段）。两处配置冲突时，以 `thresholds.json` 为唯一真理。

## 三、 高阶分析：借鉴多组学分析的降维实践

在处理海量且高维的自媒体内容标签（Content Tags）、用户画像（Persona）及跨平台互动数据时，传统的关系型数据库统计往往力不从心。借鉴生信分析框架（如 `omicverse` 中处理单细胞和空间转录组的思路）：

1.  **强后端依赖**：复杂的互动网络和用户聚类分析必须挂载在强后端（如 Python `pandas`/`anndata` 栈）计算，避免在数据库层面执行全表扫描的高耗时分析。
2.  **降维与聚类最佳实践**：针对高频发布的内容矩阵，利用主成分分析（PCA）或 UMAP 对“内容表现特征向量”（如不同互动类型、时段、平台权重构成的多维向量）进行降维，识别出高转化率的内容模式集群（Clusters），从而指导下一步的内容生产策略。
3.  **多组学联合视角**：将“内容指标”（播放/阅读）、“互动指标”（转评赞）与“商业指标”（转化/退款）视为多组学数据，进行联合建模（Multi-omics integration）。不孤立看待单一指标，而是寻找引发商业转化的深层“基因通路”。

## 四、 生成交付物的叙事结构指南 (Narrative & Provenance)

交付数据分析报告时，不仅要给出数字，还要留下完整的“证据链”。

1.  **目的与上下文 (Context)**：明确本次数据分析回答的业务问题（Business Question）。
2.  **数据溯源 (Trace Linkage)**：展示数据如何从源系统流入目标 Schema，任何缺失数据的填补（Imputation）或抛弃必须有明确的记录。
3.  **核心发现与业务解读 (Key Findings)**：使用人类易懂的商业语言翻译 SQL 或 Python 的计算结果（SQL to Business Logic）。明确指出哪些是确定性的事实，哪些是基于模型的预测（AI 预测仅为参考）。
4.  **已知限制与异常预警 (Caveats)**：公开数据计算的容差范围，通报诸如 HHI 指数飙升或数据过期等系统阻断信息。明确提供后续行动指南（Actionable Insights）。
