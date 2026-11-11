# 20 智能体「品味层」升级报告

> 结论先说：**我们已经有 45 个能"照着做"的技能包，但没有一个能回答"做成什么样才算好"。**
> 门禁能判「结构齐不齐」，判不了「这东西好不好看、专不专业、能不能直接给客户」。
> 这份报告从 GitHub 上的开源质量标尺出发，给 20 个角色各补上「好」的判据。
>
> 生成日期：2026-11-11 ｜ 调研方式：本地已克隆的开源仓库 + GitHub/公开标准线上核对

---

## 一、我们缺的到底是什么

先看一张对照表。左边是我们的卡现在会说的，右边是开源项目里真正的"好标准"会说的：

| 我们的卡说 | 开源标尺说（真实原文） |
|---|---|
| 「标题要清晰、层级要分明」 | 「层级之间**字号差 ≥1.5 倍**；标题 bold、正文 regular；用颜色区分 primary vs muted」 |
| 「图表要清晰」 | 「**禁用饼图切 >5 份**；双 Y 轴只在量纲不同且相关时用；截断坐标轴必须显式标注」 |
| 「评审要有证据」 | 「对每条声称 done/fixed/passing 的文本，**回看同一轮的工具输出**；无输出支撑的即报为无证据」 |
| 「客户健康要关注」 | 「**≥60% 已购席位活跃**；首次价值实现 **≤30 天**；参会率 %、工单响应时长」 |
| 「复盘要写根因」 | 「根因不得写"人为失误"；时间线必须单调；必备章节缺失即不合规」 |

**差别不在措辞，在两点**：

1. **BAD/GOOD 对照**：好的标尺一定给出「错的例子 + 对的例子」，并且是**同一场景的两种写法**，不是抽象原则。
2. **可量化阈值**：好的标尺一定落到数字（1.5 倍、≥60%、≤30 天、≤5 类），不是「适当」「合理」「清晰」。

这两点合起来，才是"知道怎么做"升级成"知道什么是好"。

### 一个真实样本（`design-principles.md`，298 行，13 条原则）

```html
<!-- ❌ BAD: Everything same weight -->
<p class="text-lg">Welcome</p>
<p class="text-lg">Build amazing products with our platform</p>
<p class="text-lg">Get Started</p>

<!-- ✅ GOOD: Clear hierarchy -->
<p class="text-sm uppercase tracking-widest text-gray-500">Welcome</p>
<h1 class="text-5xl font-bold mt-2">Build amazing products</h1>
<p class="text-xl text-gray-600 mt-4">with our platform</p>
<button class="mt-8 bg-black text-white px-8 py-3">Get Started</button>
```

**Key techniques:** Size difference between levels (**1.5x+ ratio**) · Weight contrast · Color contrast · Spatial grouping

这就是我们要的形态：**同一段内容的两种写法 + 四条技术判据（其中一条带倍数）**。
来源：`buildwithclaude` 的 `frontend-design-pro/skills/design-wizard/references/`（本地已克隆）。

---

## 二、调研到的四类「质量标尺」范式

| 范式 | 代表 | 它解决什么 | 我们怎么用 |
|---|---|---|---|
| **A. 原则 + BAD/GOOD 对照** | `frontend-design-pro` 13 条设计原则（298 行） | 「视觉好不好」 | 每条原则配 1 组 BAD/GOOD，落成 `references/` |
| **B. 分层评审判据** | `ralph-review-trio` 的 `opus-checklist`（Tier A 逐项/ Tier B 收口） | 「评审有没有漏」 | 给 `r04` 一张「评审分级」卡，避免把收口项当逐项项 |
| **C. 同轮证据链** | `superpowers` 的 `quality-evidence` | 「声称完成但没做」 | 给 `r04/r02/r20` 一张「主张-证据同轮核对」卡 |
| **D. 量化评分表** | `customer-success-manager`（采用 30% / 成果 25% / 关系 20% / 支持 15% / 商业 10%，含 ≥60%、30 天） | 「客户健康好不好」 | 给 `r13` 补「QBR 叙事 + 阈值表」 |

补充参考（线上核对过存在）：
[Microsoft `skills` 的 frontend-design-review](https://github.com/microsoft/skills)、
[`caylent/tufte-data-viz`（Tufte 数据可视化原则）](https://github.com/caylent/tufte-data-viz)、
[`pbakaus/impeccable`（polish / 质量门槛）](https://github.com/pbakaus/impeccable)、
[GitHub 数据可视化风格指南](https://www.datavizstyleguide.com/highlights/keep-the-scope-explicit)、
[`Aiken7881/manxueai-agentic-struct` 的 style-guide.md](https://github.com/Aiken7881/manxueai-agentic-struct)。

---

## 三、20 个角色的逐个体检

> 读法：**「现在能执行」= 已有可跑门禁；「缺的品味」= 门禁判不了的那一层；
> 「学谁」= 具体锚点；「要建的卡」= 新增 knowledge 卡（不是改现有包）。**

| # | 角色 | 现在能执行 | 缺的品味（门禁判不了） | 学谁 | 要建的卡 |
|---|---|---|---|---|---|
| r01 | CEO 决策 | 可逆性分级、决策卡十字段 | **坏战略识别**：目标当战略、动作无连贯性 | Rumelt 坏战略四要素 | `strategy-quality` |
| r02 | COO 运营 | 交接包、验收逐条证据 | **SOP 可执行性**：步骤有无动词、有无可验收物 | `superpowers` 证据链 | `sop-readability` |
| r03 | CFO 财务 | 三表勾稽、对账 | **数字呈现**：口径表、差异桥（bridge）、单位经济叙事 | 三表 + bridge 惯例 | `financial-narrative` |
| r04 | 评审官 | pass/fail + 证据链 | **评审分级**：哪些该逐项、哪些只能收口判 | `ralph-review-trio` Tier A/B | `review-tiering` |
| r05 | 研究员 | 来源分级、反幻觉 | **结论强度措辞**：证据弱时说"迹象"不说"证明" | 学术 hedge 语阶 | `claim-strength` |
| r06 | 分析师 | 六维质量、指标语义 | **图表诚实与数据墨水比**：饼图上限、双轴禁令 | Tufte + GitHub dataviz | `chart-honesty` |
| r07 | PM | PRD 两层、四段结构 | **叙事**：PR/FAQ 六页、金字塔结构、用户故事 INVEST | Amazon PR/FAQ | `prd-narrative` |
| r08 | 原型官 | MVP 切片、QA 三件 | **"能见人"的标准**：可点击路径、截图取景、时间盒演示脚本 | 原型评审惯例 | `prototype-demoable` |
| r09 | 工程师 | TDD、材料、端到端 | **代码可读性**：命名、错误处理、注释密度；前端 13 原则 | 13 principles + 命名规范 | `code-readability` |
| r10 | 设计官 | 六件套、令牌、logo | **视觉"好看"**：13 原则 + 比例阶梯 + 留白与对齐 | `design-principles.md` | `visual-hierarchy` + `composition` |
| r11 | 文案 | 语调、禁词、埋词 | **具体化**：形容词→数字；中文标点与行文节奏 | 编辑规范 + 具体化练习 | `copy-concreteness` |
| r12 | 增长 | campaign 预注册 | **素材疲劳与创意判断**：CTR 衰减、素材迭代节奏 | 增长惯例 | `creative-fatigue` |
| r13 | CSM | 健康分四维、QBR | **量化客户标准 + QBR 叙事** | `customer-success-manager` | `cs-quant-benchmark` |
| r14 | 商业 | 订单三态、退款 | **对客话术**：退款/纠纷的表达与预期管理 | 客服写作规范 | `customer-facing-tone` |
| r15 | ERP | 单据链、三单匹配 | **差异桥呈现**：数量/单价差异怎么讲清楚 | 采购差异分析惯例 | `variance-bridge` |
| r16 | HR | 评分卡、Offer 校验 | **行为证据锚定**（BEI）：每分对应一段行为事实 | 结构化面试 BEI | `behavioral-anchors` |
| r17 | 自动化 | webhook、幂等、死信 | **可观测性命名**：事件名、日志字段、告警文案 | 可观测性规范 | `observability-naming` |
| r18 | 数据工程 | dbt 分层、测试 | **建模命名与文档**：staging/intermediate/mart 命名法、列级说明 | dbt 最佳实践 | `dbt-naming-doc` |
| r19 | ML | 评测集、评分器、回归 | **失败案例集与错误分类**：错在哪、错多少、错给谁 | 模型评估惯例 | `error-taxonomy` |
| r20 | SRE | 时间线、复盘、演练 | **复盘写作质量**：无责表述、根因层级、行动项可验收 | 无责复盘模板 | `postmortem-writing` |

**共 20 张新卡**，其中 8 张是跨角色高杠杆（下一节）。

---

## 四、8 张高杠杆卡（先做这 8 张，覆盖 20 个角色）

这 8 张会被多个角色复用，投入产出比最高。**每张的形态都是「原则 + BAD/GOOD 对照 + 阈值」。**

| # | 卡 | 服务角色 | 核心内容（一屏可查） | 阈值示例 |
|---|---|---|---|---|
| 1 | `bad-good-contrast` | 全部 20 | **怎么写对照**：同一场景两种写法、差异点标注、禁写抽象原则 | 每组 ≥1 组对照，抽象句 ≤20% |
| 2 | `quantified-taste` | 全部 20 | **把"好"变数字**：凡形容词必须配阈值或对照 | 每卡 ≥5 个阈值 |
| 3 | `visual-hierarchy` | r08/r09/r10/r06 | 13 条视觉原则 + 比例阶梯 | 层级字号差 ≥1.5×；间距只用 4/8/12/16/24/32/48 |
| 4 | `chart-honesty` | r01/r05/r06 | Tufte 数据墨水比、图表选择矩阵、诚实红线 | 饼图 ≤5 类；禁双轴（除量纲不同）；截断轴必标 |
| 5 | `review-tiering` | r02/r04/r19/r20 | Tier A 逐项 vs Tier B 收口；同轮证据链 | 每条主张须有同轮工具输出 |
| 6 | `narrative-structure` | r01/r07/r13 | PR/FAQ 六页、金字塔、结论先行 | 首段出结论；章节 ≥3 且各带摘要 |
| 7 | `tone-axes` | r11/r13/r14 | 语调三轴（正式度/温度/能量）+ 具体化 | 形容词 ≤3 处/千字；每处配数字 |
| 8 | `rubric-calibration` | r04/r16/r19 | rubric 怎么写、双评、一致性检验 | 双评一致率 ≥80%，否则重训 rubric |

---

## 五、每张卡的落地形态（照这个骨架写）

**目录结构**（knowledge 卡也是标准 SKILL.md，才能进技能索引）：

```
<role>/references/capabilities/<card-id>/
├── SKILL.md                      # 十节，frontmatter 六字段，kind: knowledge
├── references/
│   └── <topic>-contrast.md       # BAD/GOOD 对照库（本卡真正的价值所在）
└── tests/
    └── misuse.md                 # 人工评审表（审美无法自动断言）
```

**SKILL.md §3 必须写成"判断流水线"**，不是"知识介绍"。示例（`visual-hierarchy`）：

```
Step 1 · 数层级：这一屏有几级信息？（>3 级说明没分主次）
Step 2 · 量比例：相邻层级字号差 ≥1.5×？不到就调，别靠"感觉"
Step 3 · 查权重：标题 bold / 正文 regular；主操作与取消必须不同权重
Step 4 · 验留白：同组间距 4/8，异组 16/24，区块 32/48
Step 5 · 反看：把图变灰，主次还分得出来吗？分不出→回 Step 1
```

**`references/*-contrast.md` 的写法（这是核心资产）**：

```markdown
## 层级不分（❌ BAD）
三行文字同字号同颜色，用户不知道先看哪 → 逐个读，成本高

## 层级分明（✅ GOOD）
标签 12px/灰 → 标题 28px/bold → 副标 16px → 按钮 16px/反白
判据：字号 28/12 = 2.3×（≥1.5 达标）；灰度下主次仍可辨
```

---

## 六、怎么验证"好"（审美无法机器判定）

这一层必须诚实：**没有门禁能判"好看"**。可行的三条：

| 手段 | 做法 | 判据 |
|---|---|---|
| **双评一致性** | 两个角色独立按 rubric 打分，不互相看 | 一致率 ≥80%；低于则 rubric 写得不清楚，先改 rubric |
| **对照抽检** | 随机抽 5 个产物，与 `references` 里的 GOOD 样例并列看 | 任一项明显劣于 GOOD → 该条原则没被掌握 |
| **回归集** | 攒 10 个历史产物 + 人工分（好/中/差），新版本重打 | 与人工分排序一致（Spearman ≥0.7） |

**不要做的事**：给 knowledge 卡写一个"永远 exit 0"的脚本。
那是假绿，比没有门禁更糟——它会让"没检查"看起来像"检查过了"。

---

## 七、分三批落地

| 批 | 内容 | 数量 | 预计 |
|---|---|---|---|
| **P1** | 8 张高杠杆卡（含 references 对照库） | 8 卡 | **8/8 完成** ✅ （`bad-good-contrast` / `quantified-taste` / `visual-hierarchy` / `chart-honesty` / `review-tiering` / `narrative-structure` / `tone-axes` / `rubric-calibration`） |
| **P2** | 12 张角色专属卡（r01/r03/r05/r08/r09/r12/r15/r17/r18/r19 等） | 12 卡 | P1 验收后 |
| **P3** | 把"品味判据"回灌进现有 45 个包的 §5/§6 | — | 持续 |

每批完成后：
```bash
python scripts/sync_dsh_skills.py            # 镜像到 DSH 发现根 → 模型可见
python scripts/sync_dsh_skills.py --check    # CI 校验无漂移
python scripts/audit_skill_layer.py --check-refs
python scripts/check_skill_gate.py
```

> **关键**：knowledge 卡写完必须镜像，否则模型看不见它（
> DSH 只从 `<projectRoot>/.dsh/skills` 等四个根发现技能）。

---

## 八、诚实清单

1. **"好看"没有客观标准，只有可校准的一致标准**。本报告给的是 rubric，不是真理。
2. **BAD/GOOD 对照的质量取决于取样**。抄开源样例要注明来源，且要换成我们自己的场景，不能直接搬英文 tech demo。
3. **20 张卡全做完约等于再造半层技能库**。P1 的 8 张是性价比拐点，后 12 张按真实需求触发。
4. **调研样本偏向中英双语的技术/设计类仓库**，商业类（财务/HR/法务）的高质量开源标尺明显更少，那部分更多是行业惯例而非开源资产——已在表中标注为"惯例"而非"学谁"。
5. **本地 `research/repos` 只有 6 个仓库**（`buildwithclaude`、`superpowers`、`wshobson-agents` 等），
   样本有限；线上核对补充了 5 个公开来源，但未做逐仓库深读。

---

## 九、参考来源

- [microsoft/skills · frontend-design-review](https://github.com/microsoft/skills) —— 微软的前端设计评审 skill
- [davepoon/buildwithclaude · frontend-design-pro/design-principles.md](https://github.com/davepoon/buildwithclaude) —— 13 条视觉原则 + BAD/GOOD 代码对照（本报告核心范式来源）
- [davepoon/buildwithclaude · ralph-review-trio](https://github.com/davepoon/buildwithclaude) —— 分层评审判据（Tier A/B）
- [obra/superpowers · quality-evidence](https://github.com/obra/superpowers) —— 主张必须由同轮工具输出支撑
- [caylent/tufte-data-viz](https://github.com/caylent/tufte-data-viz) —— Tufte 数据可视化原则
- [pbakaus/impeccable](https://github.com/pbakaus/impeccable) —— polish / 质量门槛
- [GitHub 数据可视化风格指南](https://www.datavizstyleguide.com/highlights/keep-the-scope-explicit) —— 图表范围与口径显式化
- [Aiken7881/manxueai-agentic-struct · style-guide.md](https://github.com/Aiken7881/manxueai-agentic-struct) —— 中文写作风格指南样例
- [ven0m0/claude-config · prd.md](https://github.com/ven0m0/claude-config) —— PRD agent 的产出规范
