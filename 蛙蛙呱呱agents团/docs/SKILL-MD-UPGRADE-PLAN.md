# 蛙蛙呱呱 · 技能层升级方案（SKILL.md 引领版 v1.0）

> **文档编号**：DSH-PLAN-SKILL-001
> **触发背景**：提示词工程（`prompt_profile.json` + `core/prompt_kernel`）与工程化（`harness` / `contract` / `review` / `tickets`）已成型，
> 但**技能层仍是代码优先**——20 角色的 `SKILL.md` 平均 **12/100**，29 张能力卡平均 **17/100**，28 张是空壳级。
> 接入大模型时，模型看不到"什么时候该用哪个技能、按什么步骤做、做到什么算合格"，只能靠 `agent.py --help` 猜。
> **本方案补齐这一层，且不推翻任何已跑通的东西。**

**配套文档**

| 文档 | 作用 |
|---|---|
| [`SKILL-LAYER-SPEC.md`](SKILL-LAYER-SPEC.md) | 技能层规格：写出一份合格 SKILL.md 的硬标准 |
| [`templates/SKILL.template.md`](../templates/SKILL.template.md) | 可复制骨架（十节固定结构） |
| [`scripts/audit_skill_layer.py`](../scripts/audit_skill_layer.py) | 体检脚本，100 分制，可作 CI 门禁 |
| [`research/`](research/) | 三份外部调研原文（技术角色 / 商业角色 / 生态标准） |

---

## 0. 一页结论

| 问题 | 答案 |
|---|---|
| **要不要重写？** | **不重写。** 已有的 `harness/contract/review/cases` 是项目最大资产，规格要求把它**声明进技能包**，而不是替代它 |
| **缺的到底是什么？** | 缺**一层**：L1 引导层（`SKILL.md`）。现在只有 L2 知识层（`references/`）和 L3 校验层（`scripts/`），中间没有"路由 + 步骤 + 过关条件" |
| **最小可行改造** | 每个能力目录加一份 `SKILL.md`（frontmatter 6 字段 + 十节正文），旧 `README.md` 降为指针 |
| **要不要改代码？** | 只需 3 处小改：`card_path()` 优先 `SKILL.md`、新增 `shared/skill_index.py`、新增 `guagua.py skills`。**三处均已落地并跑通**；`agent.py` 与 `harness.py` 一行未动 |
| **多久见效？** | P0 的 6 个角色/技能包是"当天可完成、当天可验证"的量级（每包 1.5–2 小时，有模板与脚本兜底） |
| **怎么防止又退化？** | `audit_skill_layer.py --min 75` 进 CI + `metadata.verify` 必须真能跑 + `tests/misuse.md` 负向用例 |
| **能接哪些模型？** | frontmatter 只用规范内 6 字段 → Claude Code / claude.ai / WorkBuddy / CodeBuddy / DSH 均可直接加载；纯对话模型由拼装器降级为单段 prompt |

---

## 1. 现状：真实体检数据（不是感觉，是跑出来的）

### 1.1 角色技能卡：20 份，平均 12 分，无一份达到"可用"

实测命令：`python scripts/audit_skill_layer.py`

| 角色 | 行数 | 得分 | 等级 | 主要失分项 |
|---|---|---|---|---|
| r06 蛙得清（数据分析） | 158 | **45** | D 占位 | 流程 / 脚本表 / 自检 / 错误表 / 降级 |
| r07 蛙得明（产品） | 113 | 40 | D 占位 | 脚本表 / 自检 / 错误表 / 降级 / 变更 |
| r01 蛙全局（CEO） | 102 | 30 | D 占位 | 流程 / 资源地图 / 脚本表 / 自检 / 错误表 / 降级 / 变更 |
| r02 蛙排布（COO） | 116 | 30 | D 占位 | 同上 |
| r08 蛙建成（MVP） | 111 | 25 | D 占位 | 触发语 + 上述七项 |
| r10 蛙成美（设计） | 155 | 25 | D 占位 | 触发语 + 上述七项 |
| r11 蛙点题（内容） | 33 | 15 | E 空壳 | 仅 33 行，无资源地图 |
| r18 蛙数仓（数仓） | 128 | 10 | E 空壳 | 仅 frontmatter |
| r03 / r04 / r05 / r09 | 89–145 | 5 | E 空壳 | **无 frontmatter**，全靠正文 |
| r12–r17 / r19 / r20 | 71–143 | **0** | E 空壳 | **无 frontmatter、无触发语、无任何可检查结构** |

> **13 份 SKILL.md 连 YAML frontmatter 都没有**（r03 / r04 / r05 / r09 / r12–r20，共 13 个）。
> 没有 frontmatter 意味着：**任何按 Agent Skills 标准工作的宿主都发现不了它**——它只是一份 README。
> 只有 7 份有 frontmatter（r01 / r02 / r06 / r07 / r08 / r10 / r11），而这 7 份里仍有 2 份（r08 / r10）描述不含触发语。

### 1.2 能力卡：29 张，平均 17 分，28 张空壳

> **口径说明**：本节数字是 **2026-11-11 升级前基线**（29 张卡）。
> 升级后已增至 33 张、均分 30，其中 6 张 A 级——对比见 §9「实测对比」。

| 事实 | 数据 |
|---|---|
| 卡片总量 | 29 张（`shared/capabilities/catalog.json` v3） |
| 形态分布 | 代码 10 / 规范 19 |
| 文件体积 | **0.79–0.94 KB**（全部） |
| 含 YAML frontmatter | **0 张** |
| 通过 "产物可复算：数字/口径可被他人重算" 这句模板化验收文案 | **29/29**（即：全部是同一套样板） |
| 有 `SKILL.md` | **0 张**（升级后 1 张） |
| 达 A/B 级 | **0 张** |

典型样本 —— `ecommerce-designer` 升级前的全部内容（887 字节）：

```markdown
# 电商视觉设计
> 归属：R10　消费：r14, r12　版本：v1
## 定位
电商主图/详情页的视觉结构：卖点优先级、平台规格、A/B 素材。
## 执行步骤
1. 首图只放一个主卖点 + 一个信任元素
2. 详情页按「痛点→方案→证据→参数→服务」排
...
## 产出与验收
- 依据可追溯：结论能指回证据或标注为判断
- 产物可复算：数字/口径可被他人重算
- 边界写清：空/错/取消/重试至少覆盖一项
```

**问题不在文笔，在于这四行"验收"对任何技能都成立——所以对任何技能都不构成约束。**
模型读完这 887 字节，仍然不知道"五张主图分别负责什么""极限词怎么替换""平台规格从哪查"。

### 1.3 提示词注入：一次 5,055 字符的"扁平全文"

实测 `python chat.py --role rXX`（10 个角色取样）：

| 角色 | 注入字符数 | 行数 |
|---|---|---|
| r20 值守 | 7,764 | 288 |
| r01 CEO | 6,557 | 248 |
| r06 分析 | 6,439 | 213 |
| r03 财务 | 5,075 | 181 |
| r10 设计 | 4,170 | 184 |
| r11 内容 | 3,680 | 161 |
| 平均 | **5,055** | ≈200 |

> `shared/knowledge_base.py::build_system_prompt()` 把 `references/` 全文拼进 prompt。
> 结果是**全有或全无**：模型要么吞下 5k 字符，要么一点看不到；没有"用到再展开"的中间态。
> 这与 Agent Skills 的渐进披露口径正好相反——官方明确指出：**正文只在被使用时加载，所以长参考资料在用到之前几乎不产生成本**
> （[code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills.md)）。

### 1.4 已经很强、必须保住的部分

| 资产 | 现状 | 本方案对它的态度 |
|---|---|---|
| `harness.py` 确定性门禁 | r01 有 21 个门禁，`ok=false` 非 0 退出 | **保留**，只要求写进 `metadata.verify` 与 §5 |
| `contract.py` 技能契约 | 7 技能全登记，缺字段即 FAIL | **保留**，不再重复实现 |
| `review.py` 对抗评审 | 6 项确定性挑战，BLOCKER 即 FAIL | **保留**，作为 §8 的逻辑类兜底 |
| `cases/` 案例库 | 含阈值、优先级规则、优质范例 | **保留**，在 §9 资源地图里给入口 |
| `prompt_profile.json` | 结构化的路由 + 澄清 + L2 提示词块 | **保留**，它是 L1 的机器可读孪生 |
| `agent.py` 15 个技能子命令（r10） | 真实可跑，含 `--self-test` 惯例 | **保留**，写进 `metadata.entry` |

**结论：不是推倒重建，是在既有两层之间插入一层，并把已有能力"声明出来"。**

---

## 2. 差距诊断：不是"文档不够长"，是缺一个层次

```
现状                              目标
────                              ────
references/（知识）               L1  SKILL.md       ← 缺这一层
scripts/（校验）                  L2  references/    ← 已有
                                  L3  scripts/       ← 已有（且强于多数开源项目）
```

| # | 缺失 | 具体表现 | 后果 |
|---|---|---|---|
| G1 | **无可发现入口** | **13 份**角色卡无 frontmatter；29 张能力卡无 `SKILL.md` | 宿主扫不到 → 技能等于不存在，只能靠人记命令 |
| G2 | **无触发语** | **16 份**（占 20 份的 80%）的描述不含"当…时使用" | 模型无法判断"这个活该找谁"，只能靠关键词映射表（脆弱） |
| G3 | **无步骤与过关条件** | 能力卡只有 4 条没有验收口径的"执行步骤" | 模型自由发挥，每次交付形态都不一样 |
| G4 | **无降级设计** | 无一说明"脚本跑不了/无联网/只给一句话"怎么办 | 环境一缺就卡死或编造 |
| G5 | **校验层不可见** | `harness` 强，但技能卡里一句没提 | 模型不知道有门禁，也不会去跑 |
| G6 | **无负向测试** | 全项目无 `tests/misuse.md` | 门禁是否真能拦住错误，无人验证过 |

---

## 3. 目标架构

### 3.1 三层职责

| 层 | 载体 | 常驻成本 | 谁读 | 回答什么问题 |
|---|---|---|---|---|
| **L1 引导** | `SKILL.md`（frontmatter + 十节正文） | 只常驻 frontmatter（约 100 token） | 大模型 | 这是我的活吗？按什么步骤做？做到什么算过？ |
| **L2 知识** | `references/*.md` | 0（按需加载） | 大模型 | 具体口径、词表、模板、案例在哪 |
| **L3 校验** | `scripts/*.py` + `tests/misuse.md` | 0 | 程序 | 做完了吗？能不能交付？ |

### 3.2 接入路径（三种宿主，一套内容）

```text
                    ┌──────────────────────────────────────┐
                    │  同一份 SKILL.md（规范 6 字段 + 十节）  │
                    └───────────────┬──────────────────────┘
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
  Agent Skills 宿主            本项目 runtime              纯对话模型
 (Claude Code / claude.ai /   guagua.py skills /           scripts/build_prompt.py
  WorkBuddy / CodeBuddy /       chat.py 按需注入 §1/§3/§5      拼成单段 system prompt
  DSH) 自动发现                  摘要
         └──────────────────────────┴──────────────────────────┘
                                    ▼
                        L3 脚本始终可跑（与模型无关）
```

### 3.3 已落地的三处代码改动（向后兼容）

| 改动 | 文件 | 兼容策略 |
|---|---|---|
| 能力卡路径优先 `SKILL.md` | `shared/capabilities.py::card_path()` | 存在则用，否则回落 `README.md`；`guagua.py capabilities --probe` 不受影响（实测 29 张全部可解析） |
| 新增技能包索引 | `shared/skill_index.py`（新文件，192 行） | 只读扫描；手写 frontmatter 子集解析，无第三方依赖；解析失败标 `parse_error` 不静默 |
| 新增选型索引命令 | `guagua.py skills [--role|--id|--json|--broken]` | 新子命令，不改任何旧命令行为；实测 `guagua.py check` 仍 20/20 通过 |

> `shared/capabilities/catalog.json` 本轮**未改**——它仍是 29 张能力卡的注册表，
> 与 `SKILL.md` frontmatter 的 `metadata` 字段一一对应。等 P0 批量落地后再一次性回写同步，避免中途双写漂移。

---

## 4. GitHub 对标：按角色找"该抄哪一个"

> 全部条目于 2026-11-11 通过 GitHub API / 仓库实盘核对；三项调研原文见 [`research/`](research/)。
> 星数为当日快照。**标注"未验证"的路径不写进方案**——宁可少写，不要写错。

### 4.1 权威基线（三份必须读）

| 来源 | 星 | 为什么是基线 |
|---|---|---|
| [agentskills.io/specification](https://agentskills.io/specification) | — | SKILL.md 开放标准的**唯一权威**：6 字段、`name` 必须与目录同名、description 1–1024 字符、三级渐进披露 |
| [anthropics/skills](https://github.com/anthropics/skills) | 192.5k | 官方 19 个技能实盘。**docx/xlsx/pptx 三件套是质量标杆**：任务路由表开头 + 只写"坑"不写"API 常识" + 强制验证门（soffice→pdf→读图） |
| [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 35.4k | **官方按业务职能分插件**，与我们的 20 角色最贴近 |

> **重要事实**：`anthropics/skills` **不含任何 CFO / COO / HR / 供应链 / ERP 技能**。
> 业务角色的可参考样例只能来自社区仓库——这直接解释了为什么我们 20 个角色里
> **有 8 个连一张能力卡都没有**（r03 / r04 / r13 / r16 / r17 / r18 / r19 / r20），
> 且这 8 个里有 5 个（r17 / r18 / r19 / r20 及部分 r16 子项）在全网**找不到合格样板**，必须自建。

### 4.2 20 角色 × 最缺的那一个技能 × 对标出处

| 角色 | 现有技能层 | 最缺的一件事 | 对标（repo → file） | 我方差异 |
|---|---|---|---|---|
| **R01 CEO** | 1 卡（战略罗盘，规范） | **硬闸门**：什么算"已获批准可动手" | `obra/superpowers` → `skills/brainstorming/SKILL.md`（`<HARD-GATE>` + 动作枚举 + "approval covers what you showed them"） | 把闸门接到 `decide/reversibility`，而不只写在散文里 |
| **R02 COO** | 2 卡（经营分析、飞书） | **状态报告输出契约** | `anthropics/knowledge-work-plugins` → `operations/skills/status-report/SKILL.md`（输出模板 + `Decisions Needed` 四列表） | 加 RAG 量化阈值（RED > 15% 预算超支），消灭"感觉黄了" |
| **R03 CFO** | **0 卡**（8 个 references 模块） | **模型审计七步（只读、不许改）** | `w95/awesome-claude-corporate-skills` → `02-finance-accounting/check-model/SKILL.md`（问题日志 `#|Tab|Cell|Severity|Description|Fix` + 分模型类型 bug 分类 + "别擅自改模型"） | 优先抄 `anthropics` 原件（w95 大量逐字复制且已停更 2026-02） |
| **R04 评审** | **0 卡** | **反合谋五条 + 验证铁律** | `obra/superpowers` → `skills/requesting-code-review/code-reviewer.md`（只读、`Declined to judge` 清单、不收子代理意见）+ `skills/verification-before-completion/SKILL.md`（Iron Law + claim vs 不足证据表） | 与已有 `review.py` 6 项挑战合并，不另起炉灶 |
| **R05 研究** | 4 卡（全规范） | **每张图强制标来源 + 禁止泛化来源** | w95 → `competitive-analysis/references/schemas.md`（"Source: [Citation] ([Date])" 预留位）+ `initiating-coverage/assets/quality-checklist.md`（"CRITICAL DO NOT DELIVER IF"） | 已有 `evidence_ledger` 端口，把它变成硬门禁 |
| **R06 分析** | 2 卡 | **陷阱目录 + 检测 SQL** | w95 → `10-data-analytics/data-validation/SKILL.md`（Join Explosion / Survivorship Bias / Average of Averages 各配检测查询）+ `anthropics` → `data/skills/sql-queries/SKILL.md`（五方言分区） | 中文口径 + 接 `metric_store` |
| **R07 产品** | 2 卡（其中 1 张代码） | **每条故事带验收 + DoD，加 RICE 算例** | w95 → `09-product-management/prd-writer/SKILL.md`（AC + DoD 双层 + RICE 算式 8000×2×0.75/4=3000 + 12 项审批清单） | 接到已有 `prdguard` 门禁 |
| **R08 MVP** | 5 卡 | **"故意偷懒账本"** | `contains-studio/agents` → `engineering/rapid-prototyper.md`（TODO 标记 + 6 周时间盒 + 按"为什么做原型"决策框架） | ⚠ 该仓库无 license 且停更 2025-07，只借思想不借文本 |
| **R09 工程** | 2 卡 | **TDD + 请求/接收评审分两侧** | `obra/superpowers` → `skills/test-driven-development/`、`requesting-code-review/`、`receiving-code-review/` | 已有 pytest 与 CI，补"流程"这一层 |
| **R10 设计** | 5 卡（**已升级 1**） | **品牌即代码（令牌 + 禁用清单）** | `contains-studio` → `design/brand-guardian.md`（CSS 变量/JS token/WCAG 4.5:1）+ `anthropics` → `design/skills/design-critique/SKILL.md`（五维、2 秒第一印象、🔴🟡🟢 分级、最多 3 条建议） | ✅ 本方案已用 `ecommerce-designer` 打样到 100 分 |
| **R11 内容** | 2 卡 | **来源优先级阶梯 + 常量/变调模型** | w95 → `04-marketing/brand-voice-enforcement/SKILL.md`（guideline 来源解析阶梯 + strictness 三档 + 冲突协议 + "等用户，别自创"） | 修它的缺陷：它引用的 `agents/*.md` 是悬空指针 |
| **R12 增长** | 1 卡 | **渠道矩阵 + 预注册 A/B** | w95 → `04-marketing/campaign-planner/SKILL.md`（Reach/Cost/Engagement/Relevance 矩阵 + 20/60/20 预算 + 预注册单一主指标） | 补功效分析（原文缺） |
| **R13 CSM** | **0 卡** | **加权健康分 + 分级升级** | w95 → `11-customer-success/qbr-builder/SKILL.md`（25/20/20/20/15 加权 → 1–100，绿 80+/黄 60–79/红 <60，delta 红标）+ `anthropics` → `customer-support/skills/customer-escalation/SKILL.md`（分级表 + 每级必含内容 + investigate/fix/decide/approve） | 接 `crm_record` / `voc` 端口 |
| **R14 交易** | 2 卡 | **订单生命周期 + 部分退款模式识别** | `40RTY-ai/shopify-admin-skills` → `skills/order-intelligence/shopify-admin-partial-refund-pattern-detector/SKILL.md`、`skills/returns/*` | 多平台而非 Shopify 单平台 |
| **R15 供应** | 1 卡 | **采购单校验器（带退出码）** | `zavora-ai/skill-erp-operations` → `scripts/validate_order.py`（`{valid,errors,warnings,computed}` 返回体） | **修它的致命缺陷**：它永远 `exit 0`，上游拦不住 |
| **R16 人事** | **0 卡** | **评分卡 + 负向测试（结构最佳）** | `osamabinjannat/remote-hiring-skills` → `skills/scorecard-builder/SKILL.md` + `tests/misuse-score-candidates.md`（**每技能强制 2–3 个 test + ≥1 个 misuse**） | 加 `expect.json`，让负向测试可机器判分 |
| **R17 自动化** | **0 卡** | **无可抄样板 → 自建** | `studiomeyer-io/n8n-workflows` → `PRODUCTION_CHECKLIST.md`（清单与模板分开，各自独立演进） | **调研结论：全网无高质量 n8n 技能包**，这是空白区 |
| **R18 数仓** | **0 卡** | **技能目录本身即 dbt 项目 + 双宿主清单** | `dbt-labs/dbt-agent-skills` → `skills/dbt/skills/{adding-dbt-unit-test,using-dbt-state,working-with-dbt-mesh}/` + `.claude-plugin/` + `.cursor-plugin/` | 单源多适配器（见 §4.3 第 5 条） |
| **R19 智模** | **0 卡** | **评测报告即 schema，不是感觉** | `anthropics/skills` → `skills/claude-api/shared/evals/report/SCHEMA.md`（16KB）+ `evals/{build-eval,eval-audit}`；`promptfoo/promptfoo` → `.claude/skills/promptfoo-evals/SKILL.md` | 接 MLflow；用例放数据文件不放 prompt |
| **R20 值守** | **0 卡** | **事件响应角色种子** | `OneWave-AI/claude-skills` → `incident-responder/SKILL.md`；`anthropics/skills` → `managed-agents-quickstarts/incident-commander.md` | **调研结论：全网无 SLO/burn-rate、无备份恢复演练技能包**，自建 |

### 4.3 跨角色机理：10 条必须抄的做法（按价值排序）

| # | 做法 | 出处（已验证） | 我们的落地位置 |
|---|---|---|---|
| 1 | **每个技能配负向测试** `tests/misuse-*.md`：把"必须拒绝"写成断言 | `remote-hiring-skills`（全调查中结构最佳仓库） | 规格 §2「四件套判据」+ 已落 `ecommerce-designer/tests/misuse.md`（18 条） |
| 2 | **门禁脚本四件套**：JSON 入 → JSON 结论出 → 非 0 退出 → `--self-test` | 七种变体逐一验证；**7 个里没有一个带 `--self-test`** | 规格 §8.2（已实现于 `verify_delivery.py`，3 组内置 fixture） |
| 3 | **黄金快照回归**：把分数存成基线，改技能导致降分即 CI 失败 | `wshobson/agents` → `evals/static-score-snapshot.json`（96KB） | 把 `audit_skill_layer.py --json` 输出入库做快照 |
| 4 | **编号失败码 + SARIF 诊断层** | **全调查未发现任何仓库实现** | 我们的差异化：`EX-NN` + 门禁 ID（`G01`…）+ `--json` 便于映射 SARIF |
| 5 | **单源多适配器**：一份正文，生成多个宿主清单，CI 校验同步 | `dbt-labs` 双 plugin 目录；`promptfoo` 双 marketplace；`wshobson` 的 `CLAUDE.md` 只有 9 字节（纯指针） | 由 `SKILL.md` 生成 `agents/<id>.md`（WorkBuddy 格式），不双写 |
| 6 | **description 只写触发，不写流程** | `superpowers` → `writing-skills/references/discovery.md`（**有实测失败案例**：description 概括流程后模型跳过正文，本该两次评审只做了一次） | 规格 §4 D8 |
| 7 | **`<HARD-GATE>` 批准闸门 + 动作枚举** | `superpowers` → `brainstorming/SKILL.md` | R01 / R13 / R14 的不可逆动作 |
| 8 | **每技能 ≤ 500 行**（`MAX_SKILL_LINES = 500`） | `remote-hiring-skills/.github/scripts/validate-skills.mjs` | 规格 §5 双重上限 |
| 9 | **"CRITICAL — DO NOT DELIVER IF"** 式交付闸门 + 带空格的计数下限 | w95 → `initiating-coverage/assets/quality-checklist.md` | §5 质量门写法 |
| 10 | **禁用清单式负向约束**（比正面要求有效） | `anthropics` → `frontend-design`；`marketing/skills/brand-review` 的绝对化用语标记 | R10 / R11 的 §7 错误表 |

### 4.4 三条"别抄"的教训（别人踩过的坑）

| 缺陷 | 出处 | 我们要避免的写法 |
|---|---|---|
| `description` 写在 frontmatter 之外 → 发现机制直接失效 | w95 的 `unit-economics`、`check-model` | 规格强制 `---` 必须第 1 行；`skill_index.py` 解析失败标 `parse_error` 而非静默 |
| 引用 `agents/*.md` 但文件不存在（悬空指针） | w95 `brand-voice-enforcement` | 资源地图只许指向**已存在**文件；`audit_skill_layer.py` 可扩展做存在性校验 |
| 无 frontmatter 的 md 混在同目录 → 无法加载 | `contains-studio` `design/` 中 `growth-hacker.md` 缺 frontmatter | 同目录所有技能文件必须同规格 |

---

## 5. 20 角色 × 技能清单（要建什么，谁先建）

> 编号 `S-xx` 为建议技能 ID。`现状` 列：✅ 已有可用 / ⚠ 有骨架 / ✗ 无。

### P0（决定经营决策质量，先做；6 个包）

| 优先级 | 角色 | 技能 ID | 现状 | 核心内容 | 门禁 |
|---|---|---|---|---|---|
| P0-1 | R10 | `ecommerce-designer` | ✅ **100 分 / A 级** | 主图五岗位 / 12 屏情绪曲线 / 极限词三档替换 | `verify_delivery.py`（自检 3/3） |
| P0-2 | R01 | `decision-gate` | ✅ **100 分 / A 级** | 可逆性三级 + 五问 + 十字段决策卡 + 升级判定 + 批准闸门枚举 | `harness.py card/escalate`（自检 4/4） |
| P0-3 | R03 | `model-audit` | ✅ **100 分 / A 级** | 三表勾稽 / 总账子账对账 / 证据链 / 六列问题日志 / 只读 | `audit_gate.py`（自检 6/6，**修掉 harness 恒 exit 0**） |
| P0-4 | R04 | `review-anti-collusion` | ✅ **100 分 / A 级** | 反合谋五条 + 拒绝评判清单 + 严重度校准 + 结论契约 | `harness verdict` + `review.py`（自检 6/6） |
| P0-5 | R07 | `prd-authoring` | ✅ **100 分 / A 级** | 两层 PRD + P0 四段 + source 枚举 + AC vs DoD + RICE | `prdguard check` + `harness prd`（自检 5/5） |
| P0-6 | R14 | `order-lifecycle` | ✅ **100 分 / A 级** | 三态分离 + 一致性 + 迁移白名单 + 终态保护 + 退款四项 + 幂等 | `harness.py` 七道（自检 11/11） |

> **P0 六个旗舰包全部完成（6/6，均 100 分 A 级）**，覆盖决策、财务、质量、产品、设计、交易六个职能，
> 共 **35 项自检断言、17 个反例**实测被拦。
>
> 两类形态都已验证：
> - `kind: knowledge`（`ecommerce-designer`）：门禁脚本在**包内**；
> - `kind: skill`（其余五个）：门禁**复用角色根目录的 `harness.py` / `review.py` / `prdguard`**，包内只放自检器。
> 后者是主形态——**判定逻辑只许有一份实现，否则必然漂移**。

### P1（运营与增长主链路；5 个包）

| 优先级 | 角色 | 技能 ID | 现状 | 核心内容 |
|---|---|---|---|---|
| P1-1 | R02 | `handoff-acceptance` | ✅ **100 分 / A 级** | 交接包必填 + 复现命令 + 逐条验收带证据 + 审计轨迹 | `agent.py harness package/accept/trace`（自检 7/7） |
| P1-2 | R06 | `data-validation` | ✅ **100 分 / A 级** | 六维质量审计 + 口径枚举 + 来源分级 + 幸存者偏差三问 + 交叉核对 | `harness semantic` + `gate_wrap.py` 包装 `quality audit`（自检 5/5） |
| P1-3 | R12 | `campaign-plan` | ✅ **100 分 / A 级** | 阶段 + 唯一北极星 + 20/60/20 + 预注册实验 + 停止条件三件套 | `harness plan/media/cro`（自检 7/7） |
| P1-4 | R13 | `qbr-health` | ✅ **100 分 / A 级** | 四维加权 30/25/25/20 + 三色区间 + delta/临期 + 归因 + 升级分级 | `harness health/risk/escalation`（自检 7/7） |
| P1-5 | R11 | `brand-voice` | ✅ **100 分 / A 级** | 口吻基线 + 禁词阶梯 + 术语 from→to + 绝对化用语 + 两遍法 | `harness edit/audit/term`（自检 6/6） |

> **P1 五包全部完成，均 100 分**。其中两处偏离已在上文「批次总览」注明：
> `status-report` → `handoff-acceptance`（r02 无可用的状态报告门禁）；
> `data-validation` 增补 `quality audit` + 共享包装器（`semantic` 不校验非空）。

### P2（质量与稳定性；5 个包）

| 优先级 | 角色 | 技能 ID | 现状 | 核心内容 |
|---|---|---|---|---|
| P2-1 | R05 | `evidence-ledger` | ⚠ 4 卡 | 每图强制来源 + 禁止泛化来源 + 链接抽测 |
| P2-2 | R16 | `hiring-scorecard` | ✗ | 评分卡 + `tests/misuse` 强制 + `expect.json` |
| P2-3 | R18 | `dbt-unit-test` | ✗ | 单测 / state / mesh 三层 + 双宿主清单 |
| P2-4 | R19 | `eval-report` | ✗ | 评测报告 schema + judge + 红队 |
| P2-5 | R20 | `incident-response` | ✗ | 分级 + 每级必含 + 恢复演练（SLO 部分自建） |

### P3（支撑型，按需；4 个包）

| 优先级 | 角色 | 技能 ID | 现状 | 说明 |
|---|---|---|---|---|
| P3-1 | R08 | `rapid-prototype` | ⚠ 5 卡 | 捷径账本 + 时间盒 + 禁用清单 |
| P3-2 | R09 | `tdd-review-pair` | ⚠ 2 卡 | TDD + 请求/接收评审两侧 |
| P3-3 | R15 | `po-validate` | ⚠ 1 卡 | 采购单校验器（**必须带非 0 退出码**） |
| P3-4 | R17 | `webhook-retry` | ✗ | **全网无样板，纯自建**：幂等键 / 重试退避 / DLQ / 审计 |

### 批次总览（当前进度）

| 批次 | 角色 | 技能包 | 状态 |
|---|---|---|---|
| P0 | r01/r03/r04/r07/r10/r14 | `decision-gate` / `model-audit` / `review-anti-collusion` / `prd-authoring` / `ecommerce-designer` / `order-lifecycle` | ✅ **6/6 完成，均 100 分** |
| **P1** | r02/r06/r11/r12/r13 | `handoff-acceptance` / `data-validation` / `brand-voice` / `campaign-plan` / `qbr-health` | ✅ **5/5 完成，均 100 分** |
| **P2** | r05/r16/r18/r19/r20 | `evidence-ledger` / `hiring-scorecard` / `dbt-unit-test` / `eval-report` / `incident-response` | ✅ **5/5 完成，均 100 分** |
| **P3** | r08/r09/r15/r17 | `rapid-prototype` / `tdd-review-pair` / `po-validate` / `webhook-retry` | ✅ **4/4 完成，均 100 分** |
| **收口** | 全 20 角色 | 20 份角色技能卡（frontmatter + 十节 + 端口表） | ✅ **20/20 完成，均 100 分** |

> **全部收官**：20 个技能包 + 20 份角色卡，**40/40 份 A 级 100 分**；
> 技能包合计 **118 项自检断言、56 个反例**实测被拦。
>
> **角色卡的处理方式（重要）**：原 `SKILL.md` 的工程细节（Quick Start / 子命令映射 / 质量闭环）
> **没有丢弃**，而是原样迁到各角色 `references/engineering-notes.md`，
> 新 `SKILL.md` 重写为「角色技能卡」（我是谁 / 何时找我 / 端口 / 任务入口 / 流程 / 门禁 / 自检 / 降级 / 资源地图）。
> 这是刻意分层：**卡给模型看，engineering-notes 给人看**。
>
> **诚实说明**：20 份角色卡是**同一模板按角色填充**（职责、能力、端口、边界、升级路径、参考文献均来自
> registry / configs / prompt_profile）。它们的价值在**端口与能力索引的一致性**，不在于文本独创性。
> 真正的角色差异化在 20 个技能包里。

> **P0+P1 共 11 包收官**：63 项自检断言、30 个反例实测被拦。
>
> **两处与原计划的偏离（已记录在对应包的 §10）**：
> 1. r02 原计划做 `status-report`，但 r02 的 `status`/`graph` 动作无可用输出，
>    改为做有真实门禁的 `handoff-acceptance`（对应其能力域"交接与验收追踪"）。
> 2. r06 实测 `harness semantic` 只校验枚举不校验非空，因此补了 `quality audit` + 共享包装器，
>    并把该局限写进 §9 与 misuse，而不是假装已覆盖。

> **两批收官后可复制的三条经验**（写下一批之前先读）：
> 1. **先看角色根目录有没有现成门禁**：11 个包里 9 个直接复用了既有 `harness.py` / `review.py` / `prdguard`，
>    只有 `ecommerce-designer` 需要新写脚本。**不要一上来就写校验器。**
> 2. **每个包都会暴露既有门禁的一个真问题**：r03 `harness.py` 恒 exit 0、r02 `harness.py` 无 `__main__`、
>    r06 `quality audit` 恒 exit 0 且 `semantic` 不校验非空、R07 两层 schema 不通、R04 `review.py` 对空 packet 假绿。
>    写自检器时才看得见——**这就是负向测试的价值**。
> 3. **反例比正例重要**：30 条反例里有 8 条一开始是"通过"的，全部是 fixture 喂错形状或字段名猜错。

**合计**：P0 6 + P1 5 + P2 5 + P3 4 = **20 个技能包**，覆盖全部 20 角色（每角色至少 1 个旗舰包）。
其余 27 张旧卡保留为兼容层，按同一规格在后续迭代中逐张升级。

---

## 6. 路线图与工作量

| 批次 | 内容 | 单位工时 | 小计 | 完成标志 |
|---|---|---|---|---|
| **第 0 批（已完成）** | 规格 + 模板 + 体检脚本 + 索引命令 + 1 个打样包 + 负向测试 | — | — | `audit_skill_layer.py --min 75` 对打样包通过 |
| **第 1 批 P0** | 6 个旗舰包 | 1.5–2 h/包 | 9–12 h | 6 包均 ≥ 90 分；每包 `verify` 真跑通 |
| **第 2 批 P1** | 5 个包 | 1.5 h/包 | 7.5 h | 均 ≥ 85 分 |
| **第 3 批 P2** | 5 个包 | 1.5 h/包 | 7.5 h | 均 ≥ 85 分 |
| **第 4 批 P3** | 4 个包 | 1.5–3 h/包（R17 自建最重） | 8–12 h | 均 ≥ 75 分 |
| **收口** | 20 份角色 SKILL.md 升级为"角色技能卡" | 0.5 h/份 | 10 h | 角色卡 ≥ 75 分 |
| **收口** | CI 接 `--min 75` + 黄金快照入库 | 2 h | 2 h | 提交即校验 |

> **关键判断**：真正的瓶颈不是写文档，而是**为每个技能补一个能跑的 `verify`**。
> 没有脚本的技能包可以合法地用 `verify: "null"` + §8 人工清单，但**一个角色至少要有 1 个可跑门禁**，否则等于没有 L3。

---

## 7. 验收：Definition of Done

一个技能包算"升级完成"，必须同时满足 **6 条**：

| # | 条件 | 验证方式 |
|---|---|---|
| 1 | `audit_skill_layer.py` 得分 **≥ 75**（旗舰 ≥ 90） | `python scripts/audit_skill_layer.py --min 75` 退出码 0 |
| 2 | frontmatter 只用 6 个规范字段，`metadata` 值全为字符串 | 人工 + `guagua.py skills --broken` 无输出 |
| 3 | `name` 与目录名逐字一致 | `guagua.py skills --id <id>` 无 `[WARN]` |
| 4 | `metadata.verify` 真能跑（或为 `null` 且 §8 有人工清单） | 现场执行命令 |
| 5 | 有 `scripts/` 则必须有 `tests/misuse.md`，且抽 3 条真被拦住 | 现场跑 3 条负向用例 |
| 6 | 资源地图指向的文件**全部存在** | 遍历 §9 表格，逐条 `Test-Path` |

**CI 门禁（已实现并可跑）**

```bash
python scripts/check_skill_gate.py        # 升级门槛 + 黄金快照回归（推荐作为 CI 主入口）
python scripts/audit_skill_layer.py --check-refs   # 结构分 + 悬空指针
python guagua.py skills --broken          # frontmatter 合规
python guagua.py check                    # 20 角色入口不回归
```

`check_skill_gate.py` 的三条判据：

| 判据 | 含义 | 实测 |
|---|---|---|
| `BELOW_BAR` | 已升级技能包得分 < 75 → 失败 | `--bar 101` 实测报 2 条违规、exit 1 |
| `DANGLING` | 资源地图指向不存在的文件 → 失败 | 开发期真实捕获 1 处（`.json` 被正则截成 `.js`） |
| `REGRESSION` | 得分低于 `skill_score_snapshot.json` 基线 → 失败 | 篡改快照实测报 `role:r12 99→0`、exit 1 |

> 第三条是**调研中 7 个主流仓库只有 1 个做对**的那一层（`wshobson/agents` 的 `evals/static-score-snapshot.json`）。
> 没有它，改一次技能就悄悄降一次质量，且没人发现。

---

## 8. 风险、反模式与"明确不做"

### 8.1 风险

| 风险 | 表现 | 对策 |
|---|---|---|
| **文档通胀** | 每包写到 600 行，正文超 5k token | 硬上限：≤500 行 / ≤5k token；超出必须搬 `references/` |
| **门禁造假** | `verify` 写了命令但从没人跑 | DoD 第 4 条要求现场执行；CI 里跑一遍 |
| **重复造轮子** | 每个角色自己实现一套校验 | 优先复用 `harness.py` / `review.py`，技能包只声明不实现 |
| **改坏旧路径** | 删 `README.md` 导致 `--probe` 崩 | 已定：README 保留为指针；`card_path()` 存在性判断 |
| **过度工程** | 为 29 张旧卡一次性全改 | 分批：每角色先建 1 个旗舰包，旧卡逐步替换 |
| **中英混杂** | 触发词用英文，中文用户不触发 | 规格 §3.2：`triggers` 必须中文 |

### 8.2 明确不做

- ❌ **不引入 YAML 解析依赖**：`skill_index.py` 手写子集解析，保持零依赖。
- ❌ **不改 `agent.py` 的 CLI 契约**：技能包只声明 `entry`，不新增子命令。
- ❌ **不实现 SARIF 输出**（本轮）：先有编号 + JSON，SARIF 是下一轮。
- ❌ **不把 `references/` 内容复制进正文**：违反渐进披露，白吃上下文。
- ❌ **不追求 20 个角色一次性满分**：先旗舰后长尾。

---

## 9. 本方案已落地的产物（全部可验证）

| 产物 | 路径 | 状态 |
|---|---|---|
| 技能层规格 | [`docs/SKILL-LAYER-SPEC.md`](SKILL-LAYER-SPEC.md) | ✅ 完成（10 节 + 6 字段 + 100 分口径） |
| 骨架模板 | [`templates/SKILL.template.md`](../templates/SKILL.template.md) | ✅ 完成 |
| 体检脚本 | [`scripts/audit_skill_layer.py`](../scripts/audit_skill_layer.py) | ✅ 可跑，`--json` / `--min` / `--check-refs` |
| **CI 门禁 + 黄金快照** | [`scripts/check_skill_gate.py`](../scripts/check_skill_gate.py) + `skill_score_snapshot.json` | ✅ 3 条判据实测生效（门槛/悬空/回归） |
| 技能包索引 | [`shared/skill_index.py`](../shared/skill_index.py) + `guagua.py skills` | ✅ 可跑，`--id/--role/--json/--broken` |
| **旗舰包 ①（知识型）** | [`r10-.../ecommerce-designer/SKILL.md`](../r10-wachengmei-design/references/capabilities/ecommerce-designer/SKILL.md) | ✅ **100 分 / A 级**；254 行 |
| **旗舰包 ②（门禁型）** | [`r01-.../decision-gate/SKILL.md`](../r01-waquanju-ceo/references/capabilities/decision-gate/SKILL.md) | ✅ **100 分 / A 级**；241 行 |
| **旗舰包 ③** | [`r03-.../model-audit/SKILL.md`](../r03-washouxian-cfo/references/capabilities/model-audit/SKILL.md) | ✅ **100 分 / A 级**；297 行；自检 6/6 |
| **旗舰包 ④** | [`r04-.../review-anti-collusion/SKILL.md`](../r04-watiaoci-reviewer/references/capabilities/review-anti-collusion/SKILL.md) | ✅ **100 分 / A 级**；254 行；自检 6/6 |
| **旗舰包 ⑤** | [`r07-.../prd-authoring/SKILL.md`](../r07-wademing-pm/references/capabilities/prd-authoring/SKILL.md) | ✅ **100 分 / A 级**；255 行；自检 5/5 |
| **旗舰包 ⑥** | [`r14-.../order-lifecycle/SKILL.md`](../r14-wajiaoyi-commerce/references/capabilities/order-lifecycle/SKILL.md) | ✅ **100 分 / A 级**；263 行；自检 11/11 |
| 知识层（包①） | 4 份 `references/` | ✅ 规格矩阵 / 合规 / 详情页模块 / 交付契约 |
| 知识层（包②） | `references/hard-gate.md` | ✅ 批准闸门六种"可以了"判定 + 五类绕闸手法 |
| 交付骨架 | 两包各 `templates/` | ✅ 七件套 / 决策卡示例（已过 15 项门禁） |
| 门禁脚本 | 包① `verify_delivery.py`；包② `gate_selftest.py` | ✅ self-test 分别 PASS 3/3、4/4 |
| 负向测试 | 两包各 `tests/misuse.md` | ✅ 18 条 / 16 条；13 条实测被拦（exit 1） |
| 调研原文 | [`docs/research/`](research/) | ✅ 3 份（技术 / 商业 / 生态），共约 160KB |
| **角色层专家团包** | [`agent-packs/`](../agent-packs/)（20 份 `agents/*.md` + `plugin.json`） | ✅ 生成器 + `--check` 漂移检测实测生效 |
| **生成器** | [`scripts/gen_agent_packs.py`](../scripts/gen_agent_packs.py) | ✅ 单向渲染 4 处事实来源；改一次源，重跑即同步 20 份 |
| **跨宿主入口** | [`AGENTS.md`](../AGENTS.md) | ✅ 根目录，符合 agents.md 标准 |

### 实测对比（同一脚本，同一口径）

| 指标 | 升级前 | 升级后（P0+P1） |
|---|---|---|
| 达 A 级（≥90 分）的技能包 | 0 | **11** |
| `ecommerce-designer` | 15（E 空壳） | **100（A 旗舰）** |
| `decision-gate` | 15（E 空壳） | **100（A 旗舰）** |
| P0 其余 4 包 | 无此能力（或 15 分空壳） | **各 100（A 旗舰）** |
| P1 五包 | 无此能力（或规范卡） | **各 100（A 旗舰）** |
| 文件体积 | 0.8–1.0 KB/张 | 12–56 KB/包（正文 235–297 行 + 知识层 + 门禁） |
| 可机读门禁 | 0 个技能包有 | **11 个包全部有**，63 项自检断言 |
| 反例实测被拦 | 0 | **30 条** |
| 全局能力卡数量 | 29 | **38**（新增 9 个能力包） |
| 全局能力卡均分 | 15（仅 README 口径） | **39**（`SKILL.md` 优先口径；11 张 A 级拉高，27 张待升级） |
| 共享门禁包装器 | 无 | **`scripts/gate_wrap.py`**（9 条判定规则 + 3 条解析用例自检） |

---

## 10. 下一步建议（基于已完成部分修正）

### 10.1 一个必须修正的判断：角色 ≠ 技能

原方案把"20 份角色 `SKILL.md` 升级"当成第一优先级。做完两个旗舰包后要修正这一点：

| 层 | 该用什么载体 | 理由 |
|---|---|---|
| **角色**（谁负责什么、向谁汇报、怎么派活） | **Agent 定义** `agents/<id>.md`（frontmatter：`name` / `description` / `displayName` / `profession` / `maxTurns`） | 角色是"常驻身份"，不是"按需技能"。放进技能列表会让宿主每次都为一个永不触发的角色付上下文成本 |
| **任务**（主图怎么做、决策卡怎么填） | **技能包** `SKILL.md`（规范 6 字段 + 十节） | 任务是"按需加载"，只在相关时才进上下文 |

**证据**：宿主之间分工是清楚的——
WorkBuddy/CodeBuddy 用 `plugin.json` + `agents/*.md` 定义团队成员，用 `skills/` 定义技能；
Claude Code 用 `.claude/agents/*.md` 定义子代理，用 `.claude/skills/*/SKILL.md` 定义技能。
把 20 个角色塞进技能列表，等于在 30 个任务技能之上再加 20 个几乎永不命中的条目。

> 所以 `audit_skill_layer.py` 对"角色 SKILL.md"的打分，衡量的是**工程文档完整度**，
> 不是**宿主可发现性**。两件事不该混在一个指标里。当前角色卡分低（均值 12）是事实，
> 但它不应该靠"把角色改成技能"来修。

### 10.2 修正后的下一步（三件事，按顺序）

| 顺序 | 做什么 | 产出 | 估算 | 状态 |
|---|---|---|---|---|
| **①** | 写 `scripts/gen_agent_packs.py`：从 `configs/rXX.yaml` + `core/registry.py` + 现有 SKILL.md 生成 20 份 `agents/<id>.md` + 一份 `plugin.json` | 一个可被 WorkBuddy/CodeBuddy/Claude Code 直接加载的 20 人专家团 | 3–4 h | ✅ **已完成**（见 §11） |
| **②** | 补完 P0 剩余 4 个技能包：`model-audit`(R03) / `review-anti-collusion`(R04) / `prd-authoring`(R07) / `order-lifecycle`(R14) | 4 个 ≥90 分包 | 6–8 h | ✅ **已完成**（4 包均 100 分，见 §5 P0 表） |
| **③** | 角色卡批量补齐（frontmatter + 触发语 + 能力索引），完成后启用 `--role-bar 75` | 20 份 ≥75 分 | 8–10 h | ⬜ 待做（最后做，不阻塞前两项） |

**不建议现在做的**：把 29 张旧能力卡一次性全改（P1–P3 的 14 个包）。理由：先用 6 个 P0 包验证
"十节骨架 + 可跑门禁 + 负向测试"这套模式在**不同职能**上都成立，再复制。目前只验证了 2 个职能。

---

## 11. 角色层已落地：`agent-packs/`

### 11.1 做了什么

`scripts/gen_agent_packs.py` 把 4 处事实来源**单向渲染**成宿主可直接加载的专家团包：

```
输入（只读，权威）                      输出（生成，不要手改）
──────────────────────                ──────────────────────────
core/registry.py    ID/名称/职位/能力    →  agent-packs/plugin.json      专家团清单
configs/rXX.yaml    核心职责/关键原则    →  agent-packs/manifest.yaml    极简声明
*/prompt_profile.json  动作/触发词        →  agent-packs/agents/*.md    20 份角色定义
ORG.md §三 编制表   边界/升级路径         →  agent-packs/README.md       加载说明
avatars/*.png       头像                 →  agent-packs/avatars/*.png   21 张副本
                                        →  AGENTS.md（角色团根目录）
```

> **为什么 AGENTS.md 生成在根目录而不是 `agent-packs/` 里**：它引用的 `ORG.md` / `docs/` 都在根目录。
> 放进子目录会让所有相对路径差一级——这是实测踩到的坑（第一版生成错了位置，已修正）。

### 11.2 产物

| 产物 | 规模 | 说明 |
|---|---|---|
| `agents/*.md` | 20 份，91–117 行，4.2–7.3 KB | frontmatter 5 字段，与 WorkBuddy 参考实现**逐字一致**（实测 key 差集为空） |
| `plugin.json` | 20 成员 / 19 memberAgents / 1 lead | 实测：`agents` 指向的 20 个文件全部存在，21 个头像全部存在 |
| `AGENTS.md` | 根目录，含四条 CI 自检命令 | 符合 [agents.md](https://agents.md) 标准，nearest-file-wins |
| 头像副本 | 21 张 / 5.6 MB | 宿主要求路径在包内；`--no-avatars` 可跳过 |

### 11.3 三处设计决策（都有实测依据）

| 决策 | 依据 |
|---|---|
| **description 写成"做什么 + 何时调用 + 不负责什么"** | 与 SKILL.md 的 D1–D4 同源；角色委派和技能触发是同一个信息结构 |
| **主理人带 19 行成员表 + "什么时候找他"列** | 对齐 WorkBuddy `efficiency-squad` 的 team-lead 写法；派活要靠 description 而不是靠猜 |
| **`--check` 做漂移检测（CI 用）** | 调研结论：`wshobson/agents` 的 `CLAUDE.md` 只有 9 字节（纯指针），`remote-hiring-skills` 用 CI 强制 `AGENTS.md == CLAUDE.md`。我们采用"生成 + `--check`"这一支 |

### 11.4 实测结果

```bash
python scripts/gen_agent_packs.py           # 20 份角色定义 + 21 头像，exit 0
python scripts/gen_agent_packs.py --check   # 无漂移，exit 0
# 漂移自证：手改一份 agent md → --check 报 [内容与源不一致] exit 1；重新生成 → exit 0
```

四条 CI 全绿：`guagua.py check` 20/20、`check_skill_gate.py` 无违规、`audit --check-refs` 0 悬空、`gen --check` 无漂移。

### 11.5 三种宿主怎么用

| 宿主 | 用法 |
|---|---|
| **WorkBuddy / CodeBuddy** | 整个 `agent-packs/` 作为 plugin 导入，入口 `plugin.json` |
| **Claude Code** | `agents/*.md` 复制或软链到 `.claude/agents/`，文件名即子代理名 |
| **通用（AGENTS.md）** | 宿主读根目录 `AGENTS.md`，由它指向 `ORG.md` / `docs/` 等权威文档 |

### 10.3 立即可执行的验收命令

```bash
python scripts/check_skill_gate.py        # 应输出：对象 50｜已升级技能包 2｜无违规
python scripts/audit_skill_layer.py       # 应输出：能力卡均分 20，A 级 2 张
python guagua.py skills                   # 应输出：2 项，均有门禁、无异常
python guagua.py check                    # 应输出：20/20 PASS
```
