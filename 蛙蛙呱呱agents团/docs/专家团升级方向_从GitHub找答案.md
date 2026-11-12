# 专家团升级方向：从 GitHub 找答案（v2 · 含咨询能力专项）

> 审计对象：`D:\蛙蛙呱呱\蛙蛙呱呱agents团`（20 角色 / 81 能力 / 19 门禁）
> 方法：本地能力面盘点 + GitHub 同类项目对照（6 个已下载仓库 + 8 个在线仓库）
> v2 增补（2026-11-12）：咨询问题求解工作流、评测框架（Inspect AI）、工程化原则（12-factor agents）
> 结论：**不缺角色，不缺格式，缺四层——方法层、知识层、数据层、评估层。**

---

## 一、先把现状说准（不是感觉，是数出来的）

| 维度 | 现状 | 说明 |
|---|---|---|
| 角色 | 20 个，SKILL.md 平均 **100/100** | 结构满分：frontmatter、触发语、流程、自检、降级、变更全齐 |
| 能力卡 | 81 张，平均 94 分 | 其中 **47 张是 knowledge（无入口）**，34 张是 skill（有入口） |
| 可执行技能 | 34 个，全部是确定性引擎 | 校验/计算/生成，**没有一个是「分析方法」** |
| 评估 | 只有格式门禁 | 没有金题集、没有答案质量分、没有人工标注、没有回归基线 |
| 业务产出 | 30 条结论里 18 条是 fact | 60% 是「把观测换个说法」，13% 是测算，0 条带基线/匹配/区间 |

**一句话：团队把「结构合规」做到了 100 分，但没有任何一个机制在量「答案对不对、深不深」。**
这和上次报告的问题是同一个病根：**指标量什么，团队就优化什么。**

---

## 二、GitHub 上别人怎么解（11 个可借鉴的点）

| # | 项目 | 关键做法 | 对蛙蛙呱呱的落地 |
|---|---|---|---|
| 1 | [MetaGPT](https://github.com/FoundationAgents/MetaGPT) | **Code = SOP(Team)**：把公司 SOP 物化成角色的可执行阶段，不是角色描述 | 20 角色每个补一条「方法 SOP」：输入→问题树→假设→分析→结论→证伪，作为可执行阶段而不是散文 |
| 2 | [Open Deep Research](https://github.com/langchain-ai/open_deep_research) | Plan-and-Execute + 并行 researcher + 压缩阶段；**Deep Research Bench / RACE 评测** | 给 R05 加「计划先审后跑」；建自己的 20 题金题集，用 RACE 式评分（覆盖度/洞察/引用） |
| 3 | [STORM](https://github.com/stanford-oval/storm) | **Perspective-Guided Question Asking** + 模拟专家对话 + 大纲 | 咨询开场用「CFO/CMO/竞争对手/投资人/一线店长」五视角生成问题，再收敛成问题树 |
| 4 | [AlphaAnalyst](https://github.com/kbhujbal/AlphaAnalyst-open-source-autonomous-equity-research-agent) | 不可变观测库（带 provenance）、确定性 modeler 与 LLM 合成分离、**报告状态 complete/partial + 覆盖告警**、devil's advocate | 证据台账升级为 observation store（每条带来源/时间/单位/口径哈希）；结论缺输入就标 partial，不硬给 |
| 5 | [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | 多方法 persona（基本面/估值/情绪）+ **风险经理** + 回测/纸面交易 + 哈希链账本 + 执行前人工批准 | 加「风险经理」角色位（对建议做反方压力测试）；每个建议带「回测/情景」，决策留链 |
| 6 | [superpowers](https://github.com/obra/superpowers) | brainstorming → design → plan → subagent 执行 → TDD → review；**skill behavior evals（drill harness）** | 把「咨询方法」写成会自动触发的 skill；用行为评测（不是结构评测）验证 skill 真的改变输出 |
| 7 | [wshobson/agents](https://github.com/wshobson/agents) | 7 维静态评分（结构/前置/渐进披露/编排/令牌效率/可移植/一致性）+ **trace-based eval + 人工标注的 judge** | 把现有 100 分拆成 7 维（现在只有结构维度）；加 trace 评测：读真实会话找错，再写检查 |
| 8 | [agency-agents](https://github.com/contains-studio/agents)（本地调研库） | 角色文件含 Identity & Memory、Critical Rules、Deliverables；财务分析员规则「假设先于结论、永远三情景、敏感性检验」 | 给每个业务角色加 5—8 条**硬规则**（可被门禁检查），而不是只写职责 |

> 本地 `research/repos/` 里已有 6 个仓库（agency-agents / superpowers / wshobson / voltagent / contains-studio / buildwithclaude），说明方向早就看到了，缺的是**落地成方法与评测**。

---

## 三、目标架构：在现有 20 角色上加 6 层，不推倒重来

```
L0 角色层（已有 20 个，保留）
  └─ L1 方法层（新）  每个角色一份 method pack：决策问题 / 问题树 / 假设 / 证据分级 / 分析方法 / 证伪条件
       └─ L2 咨询工作流（新）8 阶段：定义 → MECE → 80/20 聚焦 → 分析计划 → 执行 → 整合 → 建议 → 打包
            └─ L3 知识层（升级）框架库 / 行业 playbook / 基准比率库 / 案例库（渐进披露）
                 └─ L4 数据与工具层（新）行情/财报/统计/海关等 MCP 连接器 + 确定性 modeler
                      └─ L5 评估层（新）金题集 + rubric + 人工校准 judge + 回归快照 + trace 错误分析
                           └─ L6 记忆层（新）客户上下文 / 假设与决策日志 / 复盘 → 回写方法与技能
```

### 咨询闭环（业务触达）

```
澄清（六问） → 问题树（MECE） → 假设（可证伪） → 分析计划（每条分支：数据+方法）
  → 证据（A/B/C 分级 + 口径 + 冲突） → 综合（So what） → 建议（选项/取舍/风险）
  → 实施（90 天） → 价值追踪（基线/KPI） → 复盘（哪里错了 → 回写方法）
```

**每个箭头都要有产物和门禁**，否则又会退回「报告工厂」。

---

## 四、20 角色深度地图（只列最缺的，按优先级）

| 角色 | 现状 | 最缺的方法 | 最缺的数据/工具 | 优先级 |
|---|---|---|---|---|
| R01 CEO | 会拆卡、会决策卡 | 问题树、假设排序、情景树 | 公司经营基线 | P0 |
| R02 COO | 排期/容量/复盘 | 约束理论、瓶颈分析、SOP 设计 | 流程时长/产能 | P0 |
| R03 CFO | 三表勾稽 | 三情景模型、单位经济、敏感性、现金跑道 | 真实流水/成本科目 | P0 |
| R05 研究 | 证据台账 | 竞争解释、三角验证、样本代表性 | 行业数据库/海关/统计 | P0 |
| R06 分析 | 描述/回归/贡献 | 匹配、DID、断点、基线、不确定性 | 微观数据/POS | P0 |
| R14 电商 | 选品打分 | 价格弹性、动销预测、品类角色 | 平台数据/竞品价 | P1 |
| R15 供应链 | TCO 框架 | 库存优化、履约仿真、损耗模型 | 运价/库容/时效 | P1 |
| R12 增长 | 渠道/实验 | 增量归因、MMM、LTV/CAC | 投放/归因数据 | P1 |
| R07 产品 | PRD/优先级 | JTBD、机会 solution tree | 用户访谈/行为数据 | P1 |
| R04 评审 | 事实核查 | 方法评审（对照/识别/推断） | 无 | P0（改门禁） |
| 其余 10 个 | 交付型 | 按职能补 1—2 个方法 | 按需 | P2 |

---

## 五、90 天路线（v2 以 docs/智能体团升级SOP_v2.md 为准）

| 阶段 | 周期 | 做什么 | 验收（硬） |
|---|---|---|---|
| **P0 方法层** | 2 周 | 6 个 P0 角色方法包 + R04 方法门禁 | 方法包 ≥80（已完成 100/95/90/86/84/83） |
| **P1 评估层** | 2 周 | 20 题金题 + 五维 rubric + 人工校准 judge | judge 一致率 ≥0.7；有基线分 |
| **P2 咨询工作流** | 3 周 | 8 阶段工作流：模板、双门禁、RACI、7 件套交付 | 真实议题走完 8 阶段，交付 7 件套 |
| **P3 知识层** | 3 周 | 3 个行业 playbook + 基准比率库 + 案例库 + 框架库 | 每本 ≥10 条可引用基准 |
| **P4 数据/MCP 层** | 3 周 | 8 个槽位，按需接 1—3 个；降级与审计 | mcp_doctor doctor 全绿 |
| **P5 业务试点** | 3 周 | 1 个真实客户跑完咨询闭环 | 客户评分 ≥4/5；复盘 ≥3 条方法修订 |

---

## 六、评估体系怎么建（这是「专业度」的唯一硬证据）

1. **金题集**：20 题，覆盖市场进入、定价、单位经济、渠道、供应链、竞争回应；每题给「必答要点 + 常见错误 + 金标准答案」。
2. **五维 rubric**（0—5 分）：问题定义、证据质量、分析深度、洞察力、行动性。
3. **judge 校准**：先用人工标 10 题，再让 LLM judge 打分，一致率 <0.7 就改 rubric，不信任 judge。
4. **回归快照**：每次改 method/skill 都跑 20 题，分数下降即回滚（wshobson 的 static snapshot 思路）。
5. **trace 错误分析**：读真实咨询会话，记录「哪一步想错了」，把错误写成检查项（superpowers 的 drill harness 思路）。

> 现有 `scripts/consult_audit.py` 是 v0 探针（关键词启发式），只能做横向对比与回归，**不能当质量结论**；正式评分必须用金题集 + 人工校准。

---

## 七、明确不做什么

- **不加角色**：20 个已经够，问题是深度不是数量。
- **不换框架**：不需要 LangGraph/CrewAI；现有零依赖引擎是资产，缺的是方法与数据。
- **不重写引擎**：34 个确定性技能保留，新增方法层与评测层即可。
- **不靠加长 prompt**：prompt 已经 3—4k 字，再加只会稀释；要加的是**可检查的规则**与**可执行的分析步骤**。

---

## 八、第一批可执行（已经开工的部分）

- `templates/METHOD-PACK.template.md`：方法包模板（6 段）。
- `r05-washenyuan-research/references/method-pack.md`：研究角色的填好的样例。
- `scripts/consult_audit.py`：五维探针 v0（横向对比/回归用）。
- `evals/consulting/tasks.json`：12 题种子金题（后续扩到 20）。
- `evals/consulting/rubric.md`：五维 rubric 与评分锚点。

---

## 九、本轮已落地（不是 PPT；截至 2026-11-12）

| 产物 | 路径 | 状态 |
|---|---|---|
| 方法包模板 | 	emplates/METHOD-PACK.template.md | ✅ 6 段固定结构 + 自检 10 问 |
| 6 个 P0 角色方法包 | 
01/r02/r03/r04/r05/r06/references/method-pack.md | ✅ 得分 100 / 95 / 90 / 86 / 84 / 83（udit_method.py） |
| 方法包审计 | scripts/audit_method.py | ✅ 100 分制，--all 可做 CI |
| 咨询深度探针 | scripts/consult_audit.py | ✅ 五维启发式 v0（只做横向对比/回归） |
| 金题种子 | evals/consulting/tasks.json | ✅ 12 题（目标 20 题） |
| 评分卡 | evals/consulting/rubric.md | ✅ 五维锚点 + 一票否决 + 校准流程 |
| 咨询项目工作簿 | 	emplates/CONSULTING-ENGAGEMENT.template.md | ✅ 8 阶段 + 双门禁 + 7 件套 |
| MCP 预留层 | shared/mcp/（8 槽位 + 客户端 + doctor + 测试） | ✅ 0 启用，doctor 全过 |
| 回归 | python guagua.py check | ✅ 20/20 PASS |

**下一步只差两件事**：把 20 题补齐并用人工标 10 题校准 judge；把 R04 的「方法门禁」接进 
un_gates。

## 十、需要你拍板的三件事

1. **先做哪条线**：我建议 P0（6 个角色方法包 + R04 方法门禁）→ P1（20 题评测），两周内能看到「同一问题，答案深度变化」的对比。
2. **数据预算**：3 个连接器要选源（行情/统计/财报），是否允许采买（如 Wind/企查查/海关）？
3. **咨询业务形态**：是「诊断+路线图」为主，还是「驻场+陪跑」为主？形态决定方法包与交付模板的侧重。

> 一句话：**先把「方法」和「评测」补上，20 个角色才会从「会写报告」变成「会做咨询」。**\n
---

## 十一、状态更新（2026-11-12 晚）

| 项 | 状态 |
|---|---|
| 方法包 | 20/20，均分 90.4（`audit_method.py --all`） |
| 咨询 8 阶段引擎 | shared/consulting/ + scripts/consult.py + 3 个测试通过 |
| 评测 | 20 题金题 + 基线 18.5/25（2 题已答）+ `run_consult_eval.py` |
| 知识层 | 9 框架 / 18 基准 / 3 playbook |
| MCP | 8 槽位预留，8/8 doctor 通过，0 启用 |
| 改动地图 | docs/升级改动地图.md（团队仓库 + 水果项目逐文件） |
