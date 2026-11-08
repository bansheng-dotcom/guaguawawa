# 产品经理 Agent 项目（Public）

这个仓库沉淀一个“产品管理”角色 Agent / Codex Skill。它不是通用聊天助手，也不是模板仓库，而是一个产品经理总控：先理解用户真正要解决的问题，再选择合适的产品能力、工作流、模板和经验库，产出能被用户确认、也能被后续设计、开发、测试或 Agent 执行的文档。

这是对外公开分发版。Skill 名称仍为 `product-manager`；仓库名使用 `product-manager-agent-project-public`。公开版保留完整能力、workflow、模板和经验 RAG 机制，但不包含固定用户档案、真实项目经验、内部报告或私有 Git 历史。公开边界见 `PUBLIC_RELEASE.md`。

当前版本重点解决四件事：

1. 把用户自然语言翻译成需求、范围、验收标准和决策点。
2. 把产品经理常用工作拆成目录化 workflow，而不是堆在一个长提示词里。
3. 把写作、UI、数据分析等能力内化成 PM 可轻量调用的方法，而不是硬编码依赖外部 agent。
4. 用 RAG Gate 和经验库沉淀偏好、纠错和项目判断，减少同类问题反复发生。

## 快速开始

如果把它作为 Codex Skill 使用，推荐目录名为 `product-manager`，并确保根目录包含：

```text
product-manager/
├── SKILL.md
├── AGENTS.md
├── library/
├── workflows/
├── experience/
├── templates/
├── user/
└── reports/
```

使用时可以直接说：

```text
Use $product-manager to clarify this product request and choose the right PM workflow.
```

如果不使用 Codex Skill，也可以把它当成产品管理工作手册阅读：

1. 先读 `README.md` 了解结构。
2. 再读 `SKILL.md` 了解触发入口。
3. 再读 `AGENTS.md` 了解总控判断规则。
4. 遇到具体任务时，进入 `workflows/WORKFLOW_REGISTRY.md` 找对应 workflow。

## 核心文件

| 文件/目录 | 作用 |
| --- | --- |
| `SKILL.md` | Codex Skill 标准触发入口，说明何时使用这个产品经理能力 |
| `AGENTS.md` | 产品管理总控规则，负责角色认知、任务轻重、路由、RAG Gate 和输出边界 |
| `library/` | PM 角色认知、腾讯产品法、PM Skills 融合、轻量写作/UI/数据分析能力 |
| `workflows/` | PRD、需求分析、指标、验收、MVP、竞品、项目汇报、技术翻译等目录化流程 |
| `experience/` | RAG Gate 规则、经验卡模型、项目经验、偏好和纠错沉淀 |
| `templates/` | 模板注册表；具体模板归属到对应 workflow、user 或 experience |
| `user/` | 可选的本地用户偏好入口、示例档案和记录模板 |
| `reports/` | 备用汇报归档入口；正式项目产出优先放项目根目录 |
| `agents/openai.yaml` | 可选 UI/平台元数据 |

## 适合处理的任务

| 用户意图 | 默认入口 | 主要产物 |
| --- | --- | --- |
| 想法还不清楚，需要被轻量质问 | `workflows/pm-thinking/workflow.yaml` | 已确认事实、默认假设、关键问题、下一步 workflow |
| 分析需求或反馈是否成立 | `workflows/requirement-report/workflow.yaml` | 需求成立判断、数据缺口、优先级、最低成本验证 |
| 写 PRD 或优化 PRD | `workflows/prd-report/workflow.yaml` | PRD 报告、范围、不在范围、验收标准、风险 |
| 准备进入开发 | `workflows/demand-management/workflow.yaml` | 需求卡、下游文件、协作复核状态 |
| 定义指标或验证方案 | `workflows/metrics-framework/workflow.yaml` | 指标树、口径、数据源、Go/No-Go |
| 做页面或 UI brief | `workflows/ui-brief/workflow.yaml` | 页面目标、信息架构、状态清单、交互 brief |
| 把技术方案讲成人话 | `workflows/technical-brief/workflow.yaml` | 用户影响、系统影响、权限、失败兜底 |
| 做决策汇报或项目理解 | `workflows/project-briefing/workflow.yaml` | 人话汇报、选项利弊、推荐、归档位置 |

## 工作流结构

每个正式 workflow 尽量保持同一套结构：

```text
workflows/<workflow-id>/
├── workflow.yaml       # 机器可读的触发、输入、输出、门禁和版本
├── topology.md         # 人能看懂的流程图、节点备注和门禁解释
├── runner.md           # 执行顺序、回退方式和完成标准
├── review_hints.yaml   # 可选协作审查提醒，不自动触发外部 agent
├── prompts/
│   ├── current.md      # 当前稳定提示词
│   └── CHANGELOG.md    # 提示词版本变更
├── references/         # 方法论、质量门禁、参考材料
└── templates/          # 该 workflow 专属模板
```

读 workflow 时先问 6 个问题：

1. 它解决什么问题？看 `purpose`。
2. 什么时候触发？看 `trigger_signals`。
3. 什么时候不能进入？看 `entry_policy.must_not_start_when`。
4. 需要什么输入？看 `required_inputs`。
5. 产出什么？看 `outputs`。
6. 怎么判断完成质量？看 `validation_gates`。

## RAG Gate 与经验库

这个 Agent 不把“必须读大量经验”作为默认规则，而是先经过 RAG Gate：

- `pre-question`：准备提问前，只做 L1 轻量检索，避免抽象发问。
- `normal`：非重任务但需要经验时，做轻量经验判断。
- `heavy-task`：PRD、竞品分析、正式报告等重任务，允许读取 3-5 条经验卡，并生成 `experience_brief`。

重任务内部追问默认复用入口生成的 `experience_brief`。只有项目、workflow、产物或关键决策点发生变化，才重新检索。

## 目录结构

```text
.
├── SKILL.md
├── AGENTS.md
├── README.md
├── agents/
│   └── openai.yaml
├── library/
│   ├── PM角色认知.md
│   ├── PM工作切分与能力地图.md
│   ├── PM内化能力与协作边界.md
│   ├── PM轻量写作能力.md
│   ├── PM轻量UI设计能力.md
│   ├── PM轻量数据分析能力.md
│   ├── 腾讯产品法产品纲领.md
│   └── PM Skills融合参考.md
├── workflows/
│   ├── WORKFLOW_REGISTRY.md
│   ├── WORKFLOW_TRIAGE.md
│   ├── HEAVY_TASK_RAG_RULES.md
│   ├── controller/
│   ├── experience-rag/
│   ├── pm-thinking/
│   ├── requirement-report/
│   ├── prd-report/
│   ├── demand-management/
│   ├── metrics-framework/
│   ├── acceptance-test/
│   ├── mvp-validation/
│   ├── competitive-analysis/
│   ├── product-strategy/
│   ├── ui-brief/
│   ├── technical-brief/
│   ├── report-production/
│   └── project-briefing/
├── templates/
│   └── TEMPLATE_REGISTRY.md
├── user/
│   ├── README.md
│   ├── profile.example.md
│   └── templates/
├── reports/
│   └── README.md
└── experience/
    ├── README.md
    ├── EXPERIENCE_INDEX.md
    ├── RAG_MODEL.md
    ├── RAG_RULES.md
    ├── global/
    ├── inbox/
    └── templates/
```

## 发布包边界

建议提交到 GitHub 的内容：

- `SKILL.md`
- `AGENTS.md`
- `library/`
- `workflows/`
- `templates/TEMPLATE_REGISTRY.md`
- `experience/README.md`、`EXPERIENCE_INDEX.md`、`RAG_MODEL.md`、`RAG_RULES.md`、`templates/`
- `user/README.md` 和用户偏好模板
- `reports/README.md`

不建议提交的内容：

- API Key、cookie、token、登录态。
- 一次性测试报告、临时审查报告、截图、导出物。
- 未脱敏的个人或项目材料。
- 外部开源仓库的原始全文拷贝。

本公共仓库不包含固定服务对象档案或真实项目经验。安装后如需使用个性化能力，可从 `user/profile.example.md` 复制出本地 `user/profile.md`；该文件已默认忽略。项目经验建议放入本地 `experience/projects/`，该目录也默认忽略。

## 协作方式

建议使用 GitHub 的 Issue 或 Pull Request 协作：

- 只提意见：开 Issue。
- 直接改文档：新建分支后提交 Pull Request。
- 分支命名建议：`review/pm-feedback-YYYYMMDD`。
- 不建议直接改 `main` 分支。

审阅时优先看：

1. `SKILL.md`
2. `AGENTS.md`
3. `workflows/WORKFLOW_REGISTRY.md`
4. `workflows/controller/workflow.yaml`
5. `workflows/experience-rag/workflow.yaml`
6. `workflows/prd-report/workflow.yaml`
7. `library/PM角色认知.md`
8. `library/PM工作切分与能力地图.md`
9. `library/PM内化能力与协作边界.md`

## 注意事项

- 不要提交 API Key、密码、cookie、token、登录状态文件或个人隐私数据。
- 如果需要新增真实项目经验，请写清适用项目、触发场景和下次规则。
- 如果发现模板看不懂，优先指出“哪里看不懂”和“真实产品经理会怎么写”。
- PRD、竞品分析、正式报告等重任务不要跳过 `HEAVY_TASK_RAG_RULES.md`。
- 外部协作角色只能作为提醒，不要写成本地硬编码触发契约。

## 当前状态

- 已有标准 skill 入口：`SKILL.md`
- 已有产品管理总控：`AGENTS.md`
- 已有 UI 元数据：`agents/openai.yaml`
- 已有方法论和轻量内置能力：`library/`
- 已有目录化 workflow：`workflows/`
- 已有模板注册表：`templates/TEMPLATE_REGISTRY.md`
- 已有 RAG Gate 与经验沉淀：`experience/`
- 已有用户理解入口：`user/`
- 已有备用汇报归档入口：`reports/`

下一步重点：邀请产品经理审阅，并把反馈转化为可执行的 workflow、模板和规则修改。
