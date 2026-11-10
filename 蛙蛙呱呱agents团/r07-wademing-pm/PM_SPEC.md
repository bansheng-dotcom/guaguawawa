# R07 蛙得明 · 产品需求与规格基准账本 (PM_SPEC.md v1.0)
# Single Source of Truth (SSOT) for Product Management Specifications
# 对标开源标杆：Productboard / Pragmatic Institute / Reforge / Atlassian Agile Framework

## 一、 需求动机与 JTBD 准则规范 (Jobs-To-Be-Done Rules)
所有进入需求漏斗的产品诉求，必须严格按 JTBD 结构化表达，杜绝将“解决方案”伪装成“用户痛点”：
1. **Job Story 三段式规范**：
   - `Situation (场景上下文)`: 明确触发该需求的情境与触发器（例如："当新团队初次部署敏捷看板时"）。
   - `Motivation (用户动机/焦虑)`: 明确用户的心理障碍或工作摩擦（例如："希望一目了然看清各成员负载与阻塞点"）。
   - `Expected Outcome (期望成效)`: 明确可量化的价值结果（例如："以便在站会5分钟内确定今日优先级，减少协同损耗"）。
2. **Mom Test 访谈防幻觉校验**：
   - 访谈提问严禁包含假设性、迎合性词汇（如“你觉得好不好”、“将来你愿不愿意用”）。
   - 必须基于“过去已发生的真实行为与已付出的成本”进行有效性追问。

---

## 二、 优先级评分参数规范 (RICE & Opportunity Parameters)
统一 RICE 与 Opportunity 计算量纲与上下限，杜绝团队各成员主观打分漂移：
1. **RICE 参数基准**：
   - **Reach (触达用户数)**: 周期内直接受影响的用户数或事件数（取值范围：`>= 1`）。
   - **Impact (影响力系数)**: 对单个用户的价值增益。
     - `3.0`: 极大影响 (Massive)
     - `2.0`: 高影响 (High)
     - `1.0`: 中等影响 (Medium)
     - `0.5`: 低影响 (Low)
     - `0.25`: 微小影响 (Minimal)
   - **Confidence (置信度)**: 依据数据支撑强弱确定。
     - `100% (1.0)`: 有严谨的用户行为数据或 A/B 测试数据支持
     - `80% (0.8)`: 有用户定量调研或可用性测试佐证
     - `50% (0.5)`: 仅有零星定性反馈或间接推导
     - `< 50%`: 算作高风险假设，必须先进入 Spike 调研而非直接排期
   - **Effort (研发工时成本)**: 团队人月数（Person-Months）或人天，强制下限 `Effort >= 0.1`，杜绝零成本假设。
   - **RICE 公式**: `Score = (Reach * Impact * Confidence) / Effort`
2. **Opportunity Score (Dan Olsen 机会评分模型)**:
   - `Importance (重要度)`: 用户对该成果的看重程度 (1~10 分)
   - `Satisfaction (现状满意度)`: 用户对现有替代方案的满意度 (1~10 分)
   - **Opportunity 公式**: `Score = Importance + max(Importance - Satisfaction, 0)`

---

## 三、 PRD 8 门禁系统 (PRD 8 Quality Gates)
任何功能 PRD 必须通过以下 8 项确定性门禁方可流转至 R08/R09 评审排期：
1. **Gate 1 - Problem (痛点真实性)**: 明确陈述用户痛点，附带定性反馈或定量频次，非假想需求。
2. **Gate 2 - User (目标客群与画像)**: 明确受众细分（Segment/Persona），排除模糊的“所有用户”。
3. **Gate 3 - Value (商业与用户价值)**: 明确对北极星指标或业务收入/效率的正向贡献。
4. **Gate 4 - Scope (范围与边界清晰度)**: 明确列出 P0 (Must Have)、P1 (Should Have) 与 **Non-Goals (明确不做的边界)**。
5. **Gate 5 - Metric (成功指标体系)**: 必须定义核心北极星指标、正向引导指标及防御性反向护栏指标 (Guardrail Metrics)。
6. **Gate 6 - Acceptance (Given/When/Then 验收标准)**: 用户故事验收标准（AC）不得少于 4 条，且必须覆盖正常流、异常流与边界流。
7. **Gate 7 - Risk (前置风险与反思假设)**: 至少列出 3 项关键风险假设（价值风险、可用性风险、可行性风险）及证伪方案。
8. **Gate 8 - Read (可读性与交接清晰度)**: 杜绝黑话、假大空与未授权承诺，明确交付责任人与下游消费端口。

---

## 四、 OKR 3×3 对齐框架规范 (OKR 3x3 Framework)
1. **结构基准**：
   - 战略周期内最多聚焦 **3 个 Objective (目标)**。
   - 每一个 Objective 下强约束对应 **3 个 Key Results (关键成果)**，形成 3×3 矩阵。
2. **Key Results 量化法则**：
   - 严禁把“完成XX系统开发”这类交付动作当成 KR。
   - 每个 KR 必须包含：基线值 (Baseline)、目标值 (Target) 与统计口径 (Telemetry Metric)。
   - 置信度评估：起始置信度应保持在 `60% ~ 70%`，鼓励具备挑战性而非保守平庸。

---

## 五、 全链路埋点规范 (Telemetry Schema)
产品功能伴生的数据可观测性埋点标准：
1. **事件命名规范**：遵循 `object_action` 蛇形命名（例如：`onboarding_step_complete`, `export_report_click`）。
2. **必须上下文载荷 (Common Payload)**：
   - `user_id`: 用户唯一标识
   - `tenant_id`: 租户/组织标识 (SaaS 场景)
   - `session_id`: 会话追踪 ID
   - `timestamp`: UTC ISO-8601 标准时间戳
   - `event_version`: 埋点契约版本号 (e.g. "1.0.0")
3. **特征属性 (Properties)**：
   - `trigger_source`: 触发来源（如顶部导航、侧边栏、快捷键）
   - `duration_ms`: 停留或交互耗时
   - `result_status`: 成功 / 失败 / 中途放弃

---

## 六、 发布门禁服务等级协议 (Release Gate SLAs)
从 PRD 到上线的门禁流转与拦截阻断等级：
1. **Blocker (一级阻断)**: 
   - 存在 P0 安全合规漏洞、未通过八门禁核心门禁、埋点 Schema 缺失。
   - 动作：立即终止发布流，驳回 PRD。
2. **Critical (二级风险)**:
   - 存在未覆盖的边界异常流、性能压测不达标、护栏指标报警。
   - 动作：需产品负责人与技术负责人双重签字，限制灰度放量比例 <= 5%。
3. **Normal (常规通过)**:
   - 全部门禁 PASS，测试用例 100% 覆盖，灰度按 10% -> 30% -> 100% 梯次上线。
