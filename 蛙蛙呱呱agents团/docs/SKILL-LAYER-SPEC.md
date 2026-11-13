# 蛙蛙呱呱 · 技能层规格（SKILL-LAYER-SPEC v1.0）

> **文档编号**：DSH-SPEC-SKILL-001
> **适用对象**：R01~R20 全角色技能卡、29 个能力技能包、以及后续新增技能
> **解决的问题**：当前 20 份角色 `SKILL.md` 平均得分 **12/100**、29 张能力卡平均 **15/100**（`python scripts/audit_skill_layer.py` 实测）。
> 卡片是写给人看的"说明"，而接入大模型需要的是**写给模型看的、可按需加载、可被确定性门禁兜底的技能包**。
> **上位标准**：[Agent Skills 开放标准](https://agentskills.io)（`SKILL.md` + `references/` + `scripts/`），
> Claude Code 官方文档称其"跨多个 AI 工具通用"（[code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills.md)）。

---

## 一、为什么是三层，而不是"把文档写长一点"

旧方案只有一个层次：把知识塞进 system prompt。实测 `python chat.py --role r06` 单次注入 **6,439 字符 / 约 3,200 token**，
且是**扁平全文拼接**——模型要么全看，要么全不看，没有"用到再展开"的能力。

新方案是三层职责分离：

| 层 | 载体 | 谁读 | 加载时机 | 职责 | 失败后果 |
|---|---|---|---|---|---|
| **L1 引导层** | `SKILL.md`（frontmatter + 正文） | 大模型 | 常驻：只有 frontmatter 进上下文 | 判断"这是不是我的活、该怎么干" | 技能不被触发 / 触发后跑偏 |
| **L2 知识层** | `references/*.md` | 大模型 | **按需**：正文里点名才读 | 领域口径、词表、模板、案例 | 结论不可溯源 / 口径漂移 |
| **L3 校验层** | `scripts/*.py`、`harness.py`、`cases/` | 程序 | 交付前必跑 | 确定性门禁：数值实算、合规扫描、结构校验 | 模型自说自话，无兜底 |

**铁律**：L1 不重复 L2/L3 的内容，只写"什么时候去读哪个"。
L3 必须能在**没有 LLM** 的情况下独立复算——这是本项目已有的最大资产，规格要求把它**声明在技能包里**，而不是藏在 `agent.py` 里。

> 依据：官方文档明确指出「skill 的 body 只在被使用时加载，所以长参考资料在用到之前几乎不产生成本」
> （[code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills.md)）；
> 反之 body 一旦加载会跨轮次留在上下文，**每一行都是持续成本**，所以正文必须短。

---

## 二、目录布局（技能包 = 一个目录）

```
<role-dir>/references/capabilities/<skill-id>/
├── SKILL.md              # 必需。L1 引导层，唯一入口
├── README.md             # 必需（兼容层）。≤10 行，只做指针，供 guagua.py 旧路径探测
├── references/           # 可选。L2 知识层，按需加载，单文件 ≤ 6,000 token
│   ├── <topic>.md
│   └── <topic>.md
├── templates/            # 可选。交付物骨架，模型直接填
│   └── <deliverable>.md
├── scripts/              # 可选。L3 校验层，零第三方依赖优先
│   └── <verifier>.py
├── tests/                # 强推荐。负向测试集，证明门禁真的会拦住错误
│   └── misuse.md
└── assets/               # 可选。图片/样例，非文本大文件
```

**四件套判据**（有 `scripts/` 的技能包必须有 `tests/`）：
`SKILL.md` + `templates/` + `scripts/` + `tests/misuse.md`。
没有负向测试的门禁，等于没有门禁——它只是一段"据说会检查"的代码。
对标依据：[`osamabinjannat/remote-hiring-skills`](https://github.com/osamabinjannat/remote-hiring-skills)
把"Skill + 模板 + 测试（含至少一份 `misuse-*.md`）"作为**强制单元**，
并用 CI（`.github/scripts/validate-skills.mjs`）校验结构。

**硬约束**

| 约束 | 口径 | 理由 |
|---|---|---|
| 目录名 = `<skill-id>` | 全小写 kebab-case，`^[a-z][a-z0-9-]{1,63}$` | 与 `metadata`/catalog 主键一致 |
| `SKILL.md` 与目录同层 | 不放 `<id>/skills/<id>/SKILL.md` 双层嵌套 | 扁平路径对 20 个角色 × N 技能可维护 |
| `README.md` 保留 | 首行指向 `SKILL.md` | `shared/capabilities.py::card_path()` 与 `guagua.py capabilities --probe` 仍可用 |
| 单文件 ≤ **6,000 token** | 超了必须拆分到 `references/` 子文件 | 单次工具读取的可控上限 |
| 一个技能包只做一个技能 | 出现"顺便也能做 X"就拆包 | 模型靠 description 选技能，混杂会让触发漂移 |
| 路径只用相对路径 | 正文写 `references/x.md`，不写绝对路径、不写 `~` | 换机器/换平台即可用；`compatibility` 字段里也不放绝对路径 |

---

## 三、Frontmatter：只用 6 个可移植字段

**关键决策：只使用 Agent Skills 规范内的 6 个字段**，其余全部塞进 `metadata`。

原因：官方文档明确——超出规范的字段在打包/上传时会**硬报错**而非忽略：
`Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name`
（[code.claude.com/docs/en/skills#using-skill-frontmatter-outside-claude-code](https://code.claude.com/docs/en/skills.md)）

我们要接的不止一家模型，所以**规范内的 6 字段是唯一安全子集**。

> **外部交叉验证**：社区仓库 `osamabinjannat/remote-hiring-skills` 的 CI 校验器
> [`.github/scripts/validate-skills.mjs`](https://github.com/osamabinjannat/remote-hiring-skills/blob/main/.github/scripts/validate-skills.mjs)
> 允许的字段恰好就是这 6 个：`name, description, license, compatibility, metadata, allowed-tools`，
> 其余一律拒绝。两处独立来源给出同一结论 → 本规格按此执行。

```yaml
---
name: ecommerce-designer
description: 电商视觉设计技能包。把商品卖点翻译成可转化的视觉主张，产出主图矩阵、详情页分屏脚本、版式色彩字体令牌、AI 出图提示词、像素级平台规格清单与合规校验报告。当需要做电商主图、详情页、店铺视觉、白底图、场景图、卖点图、活动图，或诊断现有视觉稿并排改版优先级时使用。不负责品牌 VI 从零设计、印刷包装与 UI 界面。
license: MIT
compatibility: 通用。需要 Python 3.10+ 才能跑 scripts/ 下的校验脚本；无脚本时可纯文本交付，能力不降级。
metadata:
  owner: r10
  version: "2.0.0"
  kind: knowledge          # knowledge=规范型 / skill=带确定性入口
  triggers: "电商主图,详情页,白底图,卖点图,设计稿诊断"
  verify: python scripts/verify_delivery.py --file <交付物.md> --strict
  entry: "null"            # kind=skill 时填 "python agent.py ecom plan"
  consumers: "r14,r12"
  supersedes: README.md
---
```

### 3.1 字段规则

| 字段 | 规则 |
|---|---|
| `name` | **必填**。≤ **64** 字符；只允许 `a-z0-9-`；**不得以连字符开头/结尾**；**不得出现连续连字符**（`--`）；**必须与父目录名逐字一致**。不一致会导致宿主把它登记成另一个名字，或直接拒绝加载 |
| `description` | **必填**。规范长度 1–**1024** 字符；它同时要回答"做什么"和"何时用"。宿主技能清单里 `description` + `when_to_use` 合计按 **1,536 字符截断**，所以关键用途**必须写在最前面**；中文实作建议 ≤ 500 字符 |
| `license` | 可选。固定 `MIT`（自有资产）；若内化了第三方原文，必须写明来源与许可 |
| `compatibility` | 可选。≤ **500** 字符。写清运行前提与**无脚本时如何降级**；不放绝对路径 |
| `allowed-tools` | 可选，**规范中标注为实验性**。空格分隔的字符串（不是 YAML 列表）。只读技能可省略；写文件的技能写 `Read Write Edit Bash`。**不要**为了"方便"给全量工具——它会扩大被不可信内容劫持的面 |
| `metadata` | 可选。**规范定义为 `string → string` 映射**，见 §3.2 |

> **没有顶层 `version` 字段。** 规范只有上述 6 个字段，版本号必须放进 `metadata.version`。
> 实测参照仓库 `wshobson/agents` 的 185 份 `SKILL.md` 里有 14 份把 `version:` 写在了顶层——这是最常见的隐性不合规。

### 3.2 `metadata` 子键（本项目内部契约）

> **硬性格式**：`metadata` 的所有值**必须是字符串**，不能是 YAML 列表或嵌套 map。
> 列表类字段一律用**英文逗号分隔的单字符串**表示（`"r14,r12"`），由读取方 `split(",")`。
> 违反会导致严格校验器直接拒绝（`shared/skill_index.py` 做兜底解析，但不代表合规）。

| 键 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `owner` | `"r01"`..`"r20"` | ✓ | 唯一负责角色（对齐 `ORG.md`"一个职能一个 owner"） |
| `version` | `"x.y.z"` | ✓ | semver 字符串；与 `shared/capabilities/catalog.json` 同步 |
| `kind` | `"skill"` \| `"knowledge"` | ✓ | 沿用现有口径：`skill` 有确定性命令，`knowledge` 只有规范 |
| `triggers` | `"词1,词2,词3"` | ✓ | 3–8 个中文触发词，逗号分隔，不写英文缩写（中文场景召回更高） |
| `verify` | 命令字符串 \| `"null"` | ✓ | **交付前必跑**的校验命令；`"null"` 表示无脚本，须在正文 §8 写明人工替代动作 |
| `entry` | 命令字符串 \| `"null"` | ✓ | 存在时的主入口，如 `"python agent.py ecom plan"` |
| `consumers` | `"r14,r12"` | ✓ | 可消费该能力的其它角色（可为空字符串） |
| `supersedes` | 字符串 | | 被本文件取代的旧载体 |
| `distilled_from` | 字符串 | | 知识来源与版本，用于溯源与重蒸馏 |

> **注意**：`metadata` 里的 `verify` 必须**真的能跑**。规格禁止写"建议执行验证"这类无法执行的描述。
> 若脚本尚不存在，`verify` 必须写 `"null"`，并在正文 §8 给出人工核对清单。

---

## 四、Description 写作法（决定技能死活的部分）

`description` 是模型在**不读正文**时唯一能看到的内容，它同时承担三件事：
**选型（是不是我）→ 排他（不是别人）→ 交付预期（能拿到什么）**。

### 4.1 四段式

```
<名词短语，做什么>。<2–4 个能力要点，动宾结构>。当<触发场景1>、<触发场景2>、<触发场景3>时使用。不负责<明确不做的边界>。
```

### 4.2 必守规则

| # | 规则 | 反例 → 正例 |
|---|---|---|
| D1 | **第三人称，不用"你/我"** | ~~"我帮你做电商图"~~ → "电商视觉设计技能包。" |
| D2 | **触发语显式化**，用"当…时使用"，而不是让模型猜 | ~~"用于电商设计"~~ → "当需要做电商主图、详情页、白底图时使用。" |
| D3 | **首句就给核心用途**，不要铺垫背景 | ~~"随着电商行业的发展…"~~ → "电商选品分析技能包。" |
| D4 | **写清不做什么**，这是防越权最便宜的手段 | 缺 → "不负责品牌 VI 从零设计、印刷包装与 UI 界面。" |
| D5 | **不写实现细节**（脚本名、目录结构），那是正文的事 | ~~"调用 adlaw_scan.py 扫描"~~ → 删除 |
| D6 | 中文优先；需要英文可另写 `description_en` 到 `metadata` | — |
| D7 | 长度 150–500 字符（中文） | 太短触发不足；太长被截断 |
| **D8** | **绝不在 description 里概括执行流程** | 反例：~~"先做竞品扫描，再出主张表，最后生成主图"~~。实测教训：当 description 概括了流程，模型会**认为已经知道怎么做而跳过正文**，正文里的门禁与分支全部失效（[obra/superpowers · writing-skills/references/discovery.md](https://github.com/obra/superpowers/blob/main/skills/writing-skills/references/discovery.md)） |
| **D9** | **宁可"用力过猛"（pushy），也不要过于保守** | 官方 `skill-creator` 指出模型天然倾向"触发不足（undertrigger）"：任务明明相关却不加载技能。对策是让 description 更明确地覆盖场景，而不是更含蓄 |

**为什么 D8 最容易被违反**：写 description 时人本能地想"让人一眼看懂这个技能分几步"。
但那是**正文的职责**。description 只回答两个问题：**做什么 / 什么时候找我**。多写一句流程，就多一分被跳过正文的风险。

### 4.3 自检三问（写完必答，答不上就重写）

1. 一个不懂本项目的人，只读这一句，**知不知道什么时候该找它**？
2. 同时有两个相邻技能（如 `ecommerce-designer` vs `design-system`），**模型能不能靠 description 区分**？
3. 触发词是否**覆盖了用户真实会说的中文**（"主图""详情页""白底图"），而不是内部术语（"视觉资产矩阵"）？

---

## 五、正文结构：10 节固定骨架

顺序固定、编号保留，便于模型定位、便于脚本检查。
**双重上限：≤ 500 行 且 ≤ 5,000 token（约 3,500 中文字）**；
超了就搬去 `references/`，正文只留指针。
（≤500 行 / ≤5k token 是 Agent Skills 官方给出的正文预算，社区 CI 里的 `MAX_SKILL_LINES = 500` 就是它的机器化版本。）

### 5.0 五种被反复验证有效的结构（本骨架已内置）

| 结构 | 作用 | 落在本规格的哪一节 |
|---|---|---|
| **Gotchas 段（踩坑清单）** | 单位篇幅收益最高的内容：模型不知道、只有踩过才知道的事 | §7 易犯错误对照表 |
| **输出模板** | 让模型填空而不是自由创作，格式稳定性立刻提升 | §4 → `templates/` |
| **`- [ ]` 勾选清单** | 把"确保质量"变成可逐条打勾的动作 | §6 交付前自检 |
| **验证循环（do → validate → fix → repeat）** | 不让模型自己判断对错，而是跑脚本读结论 | §5 质量门 + `scripts/` |
| **计划-校验-执行** | 先产出中间产物并对照事实源校验，再执行昂贵动作 | §3 的"每步产出 + 过关条件" |

> **一句话原则**：**补充模型缺的，删掉模型已经会的。**
> 反例（官方文档点名的坏样板）：在技能里解释"PDF 是什么格式"。
> 模型不需要这段，但它每轮都在为这段付 token。

| 节 | 标题 | 字数预算 | 必须包含 | 禁止包含 |
|---|---|---|---|---|
| §1 | **何时用 / 何时不用** | ≤ 200 | 三条以上"该用"的正例问法；三条以上"不该用/转给谁" | 模糊表述"视情况而定" |
| §2 | **前置输入与最省追问** | ≤ 250 | 一句话即可开工的最小输入；≤ 4 问一次性问清，每问带 2–3 个候选 | 连环追问 |
| §3 | **执行流水线** | ≤ 900 | 编号步骤；每步写"产出 + 过关条件" | 只写"要专业" |
| §4 | **交付物清单** | ≤ 300 | 逐项列出，能指向 `templates/` 就指 | 交付物描述不可验收 |
| §5 | **质量门（一票否决项）** | ≤ 300 | 3–7 条**可判定**的必过项 | "尽量""争取" |
| §6 | **交付前自检清单** | ≤ 250 | `- [ ]` 且 ≥ 5 条 | 清单与 §5 重复 |
| §7 | **易犯错误对照表** | ≤ 400 | ≥ 6 行，编号 `EX-01..`，左"错法"右"改法" | 无编号的散文 |
| §8 | **降级与边界** | ≤ 350 | 表：触发情况 → 处置。至少覆盖"脚本跑不了/无联网/输入只给一句/涉违规" | "无法处理" |
| §9 | **资源地图** | ≤ 250 | 三列表：什么时候读 → 读哪个文件。按需加载，不写"全部阅读" | 罗列全部文件却不给场景 |
| §10 | **变更记录** | ≤ 150 | 版本 + 日期 + 一句话改了什么 | 无 |

### 5.1 §3 执行流水线的写法（最容易写废的一节）

每一步必须是**可判定的动作**，不是形容词。

```markdown
### Step 3 · 视觉主张锻造（灵魂步骤，禁止跳过）
按三步翻译，禁止从参数直接跳画面：事实 → 利益 → 画面。
产出「视觉主张表」，每条锁定：主张句 / 证据 / 画面载体 / 人群 / 版位。
**过关条件**：3 秒可读（1 词 + 1 数字 + 1 动作）且证据可被审核。
```

反例（不可判定，必须改写）：
```markdown
### Step 3 · 提炼卖点
深入理解商品，提炼出打动人的核心卖点。
```

### 5.2 §6 自检清单 vs §5 质量门的分工

- **§5 质量门**：交给**别人**（R04 评审官 / harness）执行的硬门禁，通常有脚本。
- **§6 自检清单**：交给**模型自己**在交付前逐条打勾的自查，是"防自己偷懒"，条目比 §5 更细。

---

## 六、与现有工程的接线（不改坏任何东西）

### 6.1 三类加载路径

| 场景 | 入口 | 读什么 |
|---|---|---|
| 原生 Agent Skills 宿主（Claude Code / WorkBuddy / CodeBuddy / DSH） | 宿主自动发现 `SKILL.md` | 只读 frontmatter，按需读正文 |
| 本项目 `python chat.py --role rXX` | `shared/knowledge_base.py` | 注入角色卡 + **技能包的 §1/§3/§5 摘要**（不是全文） |
| 本项目 `python guagua.py skills` | 新增子命令 | 列出技能包的 `name/description/kind/verify`，供上层编排器做选型索引 |

### 6.2 需要同步的三处（少一处就漂移）

1. `shared/capabilities/catalog.json` — 增 `skill_md` 字段，`kind/version/owner/consumers` 必须与 frontmatter 一致。
2. `shared/capabilities.py::card_path()` — 优先返回 `SKILL.md`，回落 `README.md`。
3. `docs/CAPABILITY_MAP.md` — 由脚本重新生成，不再手写。

> 这与 `ORG.md` §五 已有的教训一致：**注册表与路由矩阵两处必须同步**，否则就是"文档说能跑、实际跑不了"。

### 6.3 技能包的三条"不破坏"约束

1. **不删旧文件**：`README.md` 保留为指针，历史链接不断。
2. **不改 `agent.py` 契约**：技能包不新增 CLI 子命令，只把已有的 `entry` 写进 frontmatter。
3. **不动 `harness.py`**：技能包的 `verify` 命令可以被 harness 调用，但技能包自身不实现门禁。

---

## 七、多模型可移植性矩阵

| 宿主 | 读什么 | 本项目要做的适配 | 降级后仍可用的部分 |
|---|---|---|---|
| **Claude Code / claude.ai** | `SKILL.md` frontmatter + 正文 + `references/` | 无（规范 6 字段即为它的子集） | 全部 |
| **WorkBuddy / CodeBuddy 专家团** | `plugin.json` + `agents/*.md`（含 `name/description/displayName/profession/maxTurns`） | 由技能包**生成** `agents/<id>.md`，description 直接复用 `description` 字段 | 全部（技能包作为 references 挂载） |
| **DSH** | 会话技能目录 / `SKILL.md` | 无 | 全部 |
| **OpenAI / Gemini / Qwen / DeepSeek 纯对话** | 单条 system prompt | 拼装器把 `frontmatter.description` + 正文 §1/§3/§5/§6 拼成一段 | L3 校验仍可跑（Python 无关模型） |
| **无文件的 API 调用** | 只有字符串 | 提供 `scripts/build_prompt.py --skill <id>` 输出自包含 prompt | L3 校验仍可跑 |

**结论**：L1+L2 是"给模型看的文本"，天然可移植；L3 是"给机器看的代码"，与模型无关。
真正需要按宿主编译的只有**加载机制**，不是内容。所以**规格只约束内容，不约束加载**。

---

## 八、验收：`audit_skill_layer.py` 的评分口径

脚本对每份 `SKILL.md` 打分（满分 100），权重按"对可选性与可执行性的影响"排序：

| 维度 | 分值 | 判定方式 |
|---|---|---|
| `frontmatter` | 15 | 首行 `---` 围栏 + `name` + `description` 齐备 |
| `trigger_phrases` | 15 | `description` ≥ 40 字且含"当…时使用 / Use when / 用于" |
| `workflow` | 10 | 有"流程/步骤/Step"小标题 **且** 有编号条目 |
| `resource_map` | 10 | 有"资源/参考文件/索引/Reference"小标题 |
| `scripts_table` | 10 | 正文出现 `scripts/` 且出现 `.py/.sh/.js` |
| `selfcheck` | 10 | 有自检类小标题 且 `- [ ]` ≥ 3 条 |
| `pitfalls` | 15 | 有错误对照小标题 且命中 `XX-01` 形态编号 ≥ 1 |
| `degradation` | 10 | 有降级/异常/故障小标题 |
| `provenance` | 5 | 有变更记录/来源/版本小标题 |

**等级**：A ≥ 90（旗舰）｜B ≥ 75（可用，**上线门槛**）｜C ≥ 50（骨架）｜D ≥ 25（占位）｜E < 25（空壳）

CI 门禁用 `--min 75`：任何一份低于 75 直接退出码 1。

> 现存基线（2026-11-11 实测）：角色卡平均 **12**（最高 r06 = 45），能力卡平均 **15**（全部为 E 级）。
> 目标：P0 角色与 P0 技能包 ≥ 90，其余 ≥ 75。

### 8.1 分数之外的两条硬要求（脚本查不了，评审官查）

| # | 要求 | 判定 |
|---|---|---|
| H1 | `scripts/` 存在时，`tests/misuse.md` 必须存在，且每条负向用例**真跑过**、真被拦住 | 评审官抽 3 条现场跑 |
| H2 | `metadata.verify` 命令必须能跑通（`--self-test` 通过或对样例返回预期退出码） | 评审官实跑，不接受"已验证" |

### 8.2 门禁脚本的契约（L3 最小规格）

一个合格的门禁脚本必须同时满足 **5 条**：

1. **入参可从 argv 或 stdin 拿 JSON/文件路径**；
2. **输出 JSON 结论**（`{ok, fails[], warns[], hits[]}`）——便于上游编排器消费；
3. **不通过时返回非 0 退出码**——只 print 不 exit 的脚本无法被任何 CI 拦住；
4. **带 `--self-test`**，内置 ≥ 2 个正例 + 1 个反例 fixture；
5. **零第三方依赖**（或显式声明依赖并在 `compatibility` 写明）。

> 对标结论来自 2026-11-11 对 7 个主流仓库的门禁脚本实盘比对：
> 唯一可靠使用退出码的是
> [`remote-hiring-skills/.github/scripts/validate-skills.mjs`](https://github.com/osamabinjannat/remote-hiring-skills/blob/main/.github/scripts/validate-skills.mjs)；
> 而 [`zavora-ai/skill-erp-operations/scripts/validate_order.py`](https://github.com/zavora-ai/skill-erp-operations/blob/main/scripts/validate_order.py)
> 虽然返回了规范的 `{valid, errors[], warnings[], computed{}}`，但**永远 exit 0**，因此上游无法据其拦截。
> **7 个里没有一个是带 `--self-test` 的**——这是本项目可以立刻领先的地方。

---

## 九、反模式（写技能包时最常见的 8 个坑）

| # | 反模式 | 为什么错 | 正确做法 |
|---|---|---|---|
| A-01 | 把技能包写成项目 README（命令清单 + 目录树） | 模型要的是"怎么干活"，不是"怎么装环境" | 环境说明进 `compatibility`，正文只写执行 |
| A-02 | 正文大段复制 `references/` 内容 | 违反按需加载，白白吃掉上下文 | 正文只留"什么时候读哪个文件" |
| A-03 | `description` 写成内部术语 | 用户永远不会那么说，技能永不触发 | 用用户真实问法做触发词 |
| A-04 | 一份 SKILL.md 塞 8 个技能 | 触发漂移，交付不可控 | 一包一技能，超出就拆 |
| A-05 | 写"建议执行验证"但没有可跑命令 | 无法兜底，等于没有 L3 | `verify` 要么填真命令，要么填 `null` + 人工清单 |
| A-06 | 用绝对路径 `D:\...`、`~/.workbuddy/...` | 换机器即坏，且违反可移植 | 全相对路径 |
| A-07 | 自检清单写成"确保质量良好" | 不可判定，模型无法拒绝自己 | 每条都要能判真假 |
| A-08 | 无变更记录 | 无法判断该包是否过期，旧口径会持续污染 | §10 每次改动追加一行 |

---

## 十、版本

- **v1.0（2026-11-11）**：首版。确立三层模型、6 字段可移植 frontmatter、10 节正文骨架、description 四段式、100 分验收口径。
  依据：Agent Skills 开放标准（[agentskills.io](https://agentskills.io)）、Claude Code 官方 skills 文档（[code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills.md)）、
  以及项目内 4 份标杆技能包（`ecommerce-designer`、`smart-product-selector`、`nano-banana-pro`、`h3-prompt-writing`）的结构反推。
