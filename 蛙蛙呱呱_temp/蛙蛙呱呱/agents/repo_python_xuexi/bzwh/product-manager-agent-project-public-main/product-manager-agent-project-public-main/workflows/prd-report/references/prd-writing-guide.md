# PRD 写作质量指南

## 1. 好 PRD 的定义

好 PRD 不是功能清单，而是让用户、产品、设计、工程、测试能对同一件事形成共同判断的决策报告。

它必须回答三层问题：

| 层级 | 必答 | 不合格表现 |
| --- | --- | --- |
| 产品判断 | 为什么要做、给谁做、现在为什么做、验证什么 | 只写“支持/优化/增强某功能” |
| 执行说明 | 用户怎么进入、怎么操作、系统怎么响应、数据怎么变化 | 只有愿景，没有动作和状态 |
| 决策门禁 | 做到什么算成功、什么不做、什么情况停止或转向 | 指标空泛、没有不在范围、没有风险 |

## 2. PRD 写作前的产品判断

写正文前先过 8 个问题。回答不清时，不要硬写成已确认需求。

| 问题 | 写进 PRD 的位置 |
| --- | --- |
| 真正的问题是什么？ | Executive Summary / Background |
| 目标用户是谁，谁使用、谁购买、谁受影响？ | Users / Segments / JTBD |
| 用户在哪个场景中行动？ | Scenario / Entry / User Journey |
| 方案提升了什么体验，降低了什么成本？ | Value Proposition / Product Strength |
| MVP 要验证哪个核心假设？ | MVP / Release Plan / Assumptions |
| 产品规则保护谁、鼓励什么、拒绝什么？ | Product Rules / Non-goals / Risk |
| 数据怎么验证？ | Success Metrics / Go-No-Go |
| 是否符合阶段取舍和长期壁垒？ | Strategy / Trade-offs / Not in Scope |

## 3. 推荐结构

轻量 PRD 保留 7 段；复杂 PRD 再补战略、机会树和红队。

| 段落 | 目的 | 必须写清 |
| --- | --- | --- |
| Executive Summary | 让用户 30 秒内判断方向 | 这是什么、给谁、为什么现在、MVP 验证什么 |
| Background & Why Now | 解释需求成立原因 | 触发变化、现状痛点、证据或假设、不做代价 |
| Objectives & Metrics | 避免目标空泛 | 北极星、输入指标、护栏指标、基线、目标、数据源 |
| Users / JTBD | 防止“所有用户” | 分群、场景、现有替代方案、行动成本 |
| Value Proposition | 说明产品强度 | Before、How、After、Alternatives、体验提升、成本降低 |
| Solution & Scope | 让后续执行者看懂 | 入口、流程、状态、数据变化、P0/P1/P2、不在范围 |
| Acceptance & Risks | 让需求可验收 | Given/When/Then、失败态、承重假设、最小验证、开放问题 |

复杂 PRD 可补：

- Opportunity Solution Tree：目标 -> 机会 -> 方案 -> 实验，防止直接跳功能。
- Product Strategy Canvas：愿景、分群、取舍、指标、增长、能力、壁垒。
- Impact Matrix：对核心指标的正向影响、负向影响和缓解措施。
- Red-team：3-5 个承重假设，写清 Fails if、证据、Kill criterion、Cheapest test。

## 4. 来自 pm-skills 的融合规则

| 方法 | 融合方式 |
| --- | --- |
| create-prd 8 段结构 | 保留 Summary、Background、Objective、Segments、Value、Solution、Release |
| write-prd | 从模糊输入提取已知信息，只问影响方向的缺口；主动收紧 P0 |
| metrics-dashboard | 指标必须有定义、基线、目标、数据源、门禁；不用虚荣指标充数 |
| opportunity-solution-tree | 复杂需求先写机会树，至少比较多个方案，不要第一想法直达 PRD |
| value-proposition | 用 Who / Why / Before / How / After / Alternatives 写价值 |
| user-stories / job-stories | 方向确认后再拆故事；故事必须小、独立、可验收 |
| strategy-red-team | 只攻击承重假设，不输出泛泛风险清单 |

## 5. 来自 OmniReport 样例的可复用做法

| 做法 | 适用场景 |
| --- | --- |
| Why Now + 竞品格局 + 差异化定位 | 需求涉及市场窗口、竞品压力、战略差异 |
| North Star + OKR + 护栏指标 | 需求会影响增长、留存、收入或核心体验 |
| 按 JTBD 写 persona | 不能只写年龄、职业，要写任务、痛点和期望收益 |
| Value Curve / Before-How-After | 需要说明为什么用户会选这个方案 |
| 前端入口 + 后端逻辑 + 数据影响 | 需求跨页面、数据、AI、任务流 |
| 正负向影响矩阵 | 新功能可能挤压旧指标或带来商业化副作用 |
| 核心假设表 | 方案依赖用户行为、模型质量、成本、合规或合作方 |
| 分期 + Go/No-Go | 不能一次做完，需要明确每期验证什么 |

## 6. 写作门禁

PRD 交付前至少自查：

| 门禁 | 通过标准 |
| --- | --- |
| 问题门禁 | 能用一句话说清真实问题，不只是表层功能诉求 |
| 用户门禁 | 明确目标用户、场景、当前替代方案和行动成本 |
| 价值门禁 | 写清体验提升、成本降低和替代方案差异 |
| 范围门禁 | P0/P1/P2 和不在范围清楚；P0 能验证核心假设 |
| 指标门禁 | 指标可定义、可采集、会改变决策；缺基线要标“待补” |
| 验收门禁 | 每条核心需求有用户动作、系统行为、数据/状态变化 |
| 风险门禁 | 至少列 3 个承重假设，并给最小验证方式 |
| 可读门禁 | 先讲人话结论，再讲执行细节；术语第一次出现要解释 |

## 7. 常见反模式

- 把用户说“想要”直接写成需求成立。
- 只有功能，没有用户场景和行动成本。
- MVP 写成“小一点的完整产品”。
- 指标只有“提升体验、提高效率、增加留存”，没有定义和数据源。
- 不写不在范围，导致后续范围膨胀。
- 风险清单很长，但没有承重假设和最小验证。
- 给机器看的内容很多，给人拍板的结论很少。
