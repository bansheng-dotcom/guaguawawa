# 模块H · 数据洞察与业务归因分析方法论

> 蒸馏自: 
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/03-data-analysis-investigation/ab-test-analysis/SKILL.md
> - 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills/04-data-storytelling-visualization/visualization-builder/SKILL.md
> - 补充技能/01-当前能力域/py-why__dowhy/AGENTS.md
> - 补充技能/01-当前能力域/bzwh321__self-media-data-console-bzwh/skills/self-media-attribution/SKILL.md

> 核心主张：**分析不是跑数，而是业务决策。重依赖领域 = 严格数理门禁 + 业务逻辑约束 + 极简洞察表达。不设铁律，不算结论。**

## H1. 实验评估与统计门禁 (A/B Test Analysis)

实验评估的目的是为了提供明确的“发版/不发版/继续观察”建议，而非堆砌P值。任何实验结论必须经过严格的统计门禁。

### 1. 核心流程与铁律

1. **确立实验设计**：验证假设、随机化单元（User/Session/Device）、核心指标、护栏指标（Guardrail Metrics）、目标分流比。
2. **SRM (Sample Ratio Mismatch / 样本比例失调) 铁律**：**必须先跑卡方检验（Chi-square test）校验实际分流与预期分流的差异**。
   - **红线阈值：如果 $P < 0.01$，立即停机！** 此时禁止解读任何业务指标，必须先去排查随机化分流管线的Bug。
3. **显著性检验选择**：
   - 对于比率型指标（如转化率、点击率），使用**两样本比例 Z-test**。
   - 对于均值型指标（如人均时长、客单价），使用**Welch's t-test**（不假设方差齐性）。
4. **护栏指标一票否决**：核心指标哪怕涨破天，只要任何一个护栏指标（如崩溃率、页面加载耗时、用户退订率）出现统计显著的恶化，**一律Block**，不予发版。

### 2. 状态契约与交付要求

- 分析报告必须包含：MDE（最小可检测效应）、功效分析（Power）、核心指标置信区间（95% CI）、显著性结论。
- 拒绝在未达到样本量时“偷看”（Peeking）并基于P<0.05草率下发版结论。

## H2. 归因分析与自媒体运营 (Self-media Attribution & Console)

所有业务归因必须落地到真实场景和数据契约，杜绝黑盒逻辑，确保可溯源。

### 1. 平台数据接入与归一化规范
- **默认脱敏/模拟**：所有底层开发默认使用 `data/demo`。
- **字段契约与归一化**：必须对各个平台的数据进行统一的归一化处理。保持基础字段绝对稳定：`platform`, `month_net_followers`, `month_net_revenue`, `month_content_count`。
- **指标波动报警阈值**：每日同步后，必须计算核心指标波动率，一旦超出报警阈值，直接将日报状态置为 `failed` 阻断后续流程。
- **状态监控**：日报状态必须是 `ready`, `partial` (部分过期) 或 `failed`。

### 2. 结构化三行归因（涨粉模型）
必须按以下固定结构输出归因分析，每行聚焦一个降维视角：
- **Line 1: 平台贡献维度**
  `[最高平台] 贡献 [X.X]%（+N），是[次高平台]的 N.N 倍，其余平台贡献 [X.X]%`
  *(剔除 excluded=true 的平台，按 `grand_total_new_followers` 计算占比)*
- **Line 2: 体裁贡献维度**
  `[最高体裁] 贡献 [X.X]%（N条，条均+N），[次高体裁] 次之 [X.X]%，其余体裁合计 [X.X]%`
- **Line 3: 最佳爆款剖析**
  `🏆 [标题截断30字]... 涨粉 +N（X.X%） · [平台] · [体裁]，特征：[动态特征标签，如"互动率 X.X%"或"贡献超10%"]`

### 3. 可视化树形图规则
- **动态阈值剔除**：渲染阈值 = $min(10\% 总涨粉, 前10名最小贡献)$。小于此阈值的节点必须收拢为“其他小贡献 N 条”，保证图表清晰，防止长尾击穿视觉。
- **口径一致性校验**：`卡片加和 == 体裁加和 == 平台加和 == 总涨粉`，若等式不成立则判定数据计算失效。

## H3. 因果推断四步法 (Causal Inference via DoWhy)

当面临“到底是发红包拉升了留存，还是发红包的人本身就是高粘性用户？”这种相关性陷阱时，必须启用 DoWhy 的四步法。

1. **Model（建模）**：构建基于领域知识的有向无环图（DAG），明确干预变量（Treatment）、结果变量（Outcome）以及潜在的混淆变量（Common Causes）。
2. **Identify（识别）**：利用图模型推导识别策略（如 Backdoor Adjustment 后门分层、Instrumental Variables 工具变量）。**严禁跳过此步直接跑回归**。
3. **Estimate（估计）**：通过匹配（Matching）、倾向得分加权（IPW）或双重机器学习（DML）等手段计算干预效应。
4. **Refute（反驳/敏感性测试）**：**未经过反驳的因果效应是伪命题**。必须通过以下测试以验证鲁棒性：
   - **安慰剂反驳 (Placebo Treatment)**：将真实干预变量替换为随机噪声，效应必须显著趋近于0。
   - **随机混淆因子反驳 (Random Common Cause)**：加入随机生成的假混淆变量，原有效应估值应保持稳定。

## H4. 极简可视化与故事化洞察 (Visualization & Narrative)

图表是用于传递决策的载体，不是展示你跑了多少行的代码炫技场。

### 1. 图表极简主义原则
- **结论化标题 (Message-first title)**：标题必须直接陈述结论（如：“移动端流失率是PC端的2倍”），严禁使用“各设备流失率分布图”这种废话标题。
- **最大化墨水占比 (Data-ink Ratio)**：去掉所有不提供新信息的元素——去边框（Top/Right spines）、虚化网格线（Alpha 0.2）、拒绝非必要的3D效果和无意义的多色填充。
- **视觉层级 (Visual Hierarchy)**：把想强调的数据点用粗体/高亮色（如品牌色）标出，将次要基线数据灰度化（De-emphasise）。

### 2. 洞察合成法 (Insight Synthesis: So What -> Why -> Now What)
- 任何统计 finding 都不等于 insight。
- 每条核心洞察必须回答：
  - **So What?**：这在业务/财务上意味着多少量级的钱或用户盘子？
  - **Why?**：背后的归因是什么？（结合 H2 / H3 溯源）
  - **Now What?**：我们下周要调整哪个策略或砍掉哪个实验？
- 汇报优先级 = **Impact (业务影响) × Confidence (统计置信度) × Actionability (可执行性)**。只有三者皆高的发现才配放到报告第一页。
