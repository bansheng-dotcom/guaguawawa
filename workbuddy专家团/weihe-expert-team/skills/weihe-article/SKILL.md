---
name: weihe-article
description: "Director-style multi-agent workflow for Chinese knowledge-popularization articles. Use when Codex needs to coordinate topic architecture, research writing, article review, image generation, workflow state tracking, and approved-content ingest with formal IDs and reusable asset management."
---

# Article Director

Use this skill when the task is not just "write an article", but "run a stable article production workflow".

> 本副本由 article-director 上游仓库接入渭河-专家团，`agents/`、`references/`、`scripts/`、`style-profiles/`、`workflows/` 均已随包携带。下表中指向 `D:\知识库\...` 的外部路径来自上游环境，在本包内不可用，仅保留作版本记录。

## 管理文件索引

本 skill 的所有配置已结构化管理，便于人类观察、修改和机器理解：

| 文件 | 用途 | 说明 |
|------|------|------|
| `config.py` | 全局配置 | 温度、阈值、路径，以及从 ai-tone-director 加载的确定性证据词 |
| `prompts.yaml` | 提示词注册表 | 所有 agent 角色定义、task_prefix、策略后缀，集中管理 |
| `workflows/topology.yaml` | 工作流拓扑+路由 | 人类可读的流程图 + 路由规则 + 阈值 + guards |
| `file-conventions.yaml` | 文件生成规范 | 所有节点的输出路径、类型、生命周期、可见性规则 |
| `harness/outline_validator.py` | 大纲校验 | Layer 1：topic-architect 输出校验 |
| `harness/package_validator.py` | 分包校验 | Layer 2：writer/reviewer 包输出校验 |
| `harness/article_validator.py` | 终稿校验 | Layer 3：最终文章确定性检查（整合 check_article.py） |
| `supervisor.py` | 覆盖度检查 | 分包覆盖度 + 策略关键 section 存在性 |
| `agents/_index.yaml` | Agent 注册表 | subagent 与支撑 skill 的索引、状态、用途 |
| `agents/*/manifest.yaml` | Agent 元数据 | 每个 subagent 的版本、IO契约、依赖、温度 |
| `agents/*/SKILL.md` | Agent 详细定义 | 每个 subagent 的完整角色规范 |
| `references/strategies/*.json` | 策略契约 | knowledge-explainer / teaching-playbook 的机器可读配置 |
| `memory/review-comment-experience.md` | 批注经验库 | 沉淀用户对文章结构、案例进入方式、AI味和小白解释的复用经验 |
| `D:\知识库\skills\agent-runtime` | 统一运行账本 | 与小红书图文 workflow 共用的 run-manifest、node-events、artifact-manifest、memory-scope 管理层 |
| `D:\知识库\skills\内容生产\ai-tone-director\SKILL.md` | 去 AI 味总控支撑 skill | 去 AI 味唯一事实源：提示词、经验库、工作流、审查 schema、修订计划和版本记录；供 article-review、style-harmonizer 与人工终审引用 |
| `references/ai-tone-judge-rubric.md` | deprecated 兼容入口 | 历史路径保留，不再存放规则正文 |
| `style-profiles/style-guide.md` | 作者句式与语气风格 | 句长、段落、过渡、开头、人称与语气 |
| `style-profiles/cognitive-style-guide.md` | 作者认知与逻辑风格 | 从0到1理解路径、逻辑取舍、解释顺序 |
| `style-profiles/author-soul.md` | 作者站位与写作人格 | 经验式判断、任务复盘、取舍感，避免老师讲课式姿态 |
| `agents/sentence-pattern-detemplatizer/SKILL.md` | deprecated 兼容入口 | 历史路径保留，句式家族规则已迁移至 ai-tone-director |

## 核心角色

核心角色与支撑 skill 详见 `agents/_index.yaml`。默认新结构是 `lean-v1`，保留 4 个上层职责；其中 `section-editor` 在执行层展开为 `section-reviewer` fan-out 和 `section-rewriter` 集中修改：

| Agent | 职责 |
| --- | --- |
| `article-architect` | 选题理解、大纲、细纲、范围控制 |
| `section-writer` | 单节上下文写作，生成 reader-use-contract 并写正文 |
| `section-editor` | 单节 AI 味、逻辑、结构、术语和文风合并审查修订 |
| `final-integrator` | 整稿连贯性、风格统一和终稿收口 |

执行支撑节点：

| Agent | 职责 |
| --- | --- |
| `section-reviewer` | 五路并行审查，只提修改意见 |
| `paragraph-rewrite-designer` | 审查后输出 v2 改写单元、候选评分、选中草稿和全文微调指令，不直接改正文 |
| `section-rewriter` | 按 designer 选中方案合稿、顺句和微调，保持 section-editor 下游契约 |

`deep-dive-researcher` 和 `image-ui` 是可选支撑，不进入默认主链。旧多 agent 链路保留为 `standard-legacy` 兼容入口。

lean-v1 核心链路：

```
article-architect → section-writer / section-editor loop
  → draft-assembler → final-integrator → appendix-agent
  → finalize-draft → deterministic gates → human-approval
```

## 策略

两种内置策略，详见 `prompts.yaml#strategies`：

| 策略 | 目标 | 概念策略 | 默认结构 |
|------|------|----------|----------|
| `knowledge-explainer` | 帮读者理解概念 | inline-minimal | 问题→概念→机制→证据→边界 |
| `teaching-playbook` | 帮读者复现任务 | execution-gated | 目标→基础→路径→步骤→代码→验证→排错→附录 |

## 工作流

两阶段生命周期，详见 `workflows/topology.yaml`：

1. **Bootstrap**：选题→大纲→细纲→分包→生成 expanded 脚本
2. **Expanded**：writer 并行写作→对抗审查→收敛组装→双审→人工终审

两个人工闸门：
- `outline-confirmation`：大纲确认后才进入正文写作
- `article-requirements-confirmation`：确认字数、重点段落、新需求、个人文风、认知风格和逻辑偏好后才进入 section 写作
- `final-article-approval`：全文终审后才能入库

## 入口

```bash
python skills/article-director/scripts/init_workflow.py --title "..." --topic-id "..." --strategy knowledge-explainer --workflow-mode lean-v1
python skills/article-director/scripts/workflow_runner.py --script skills/article-director/outputs/{topic_id}/run_{topic_id}.py --dry-run
python skills/article-director/scripts/workflow_runner.py --script skills/article-director/outputs/{topic_id}/run_{topic_id}.py --autonomous
```

稳定入口：`init_workflow.py -> workflow_runner.py -> compile_expanded_workflow.py`。

`--workflow-mode lean-v1` 会生成 4 个上层职责的精简链路，并在 section-editor 内部硬编码展开 review fan-out + centralized rewrite；不传时保留标准兼容链路。

### Codex 付费模式

当前默认执行模式为 `codex`。这不是 OpenAI/DeepSeek/Anthropic API 调用，而是 Codex 桌面付费会话内的任务交接模式：

1. `workflow_runner.py --autonomous` 遇到 agent 节点时，生成 `outputs/{topic_id}/codex-tasks/{node_id}.json`。
2. 主 Codex 会话读取该任务包，按 `system_prompt`、`user_content`、`output_path` 写入节点产物。
3. 用 `workflow_runner.py --submit-codex-node {node_id} --content-file <output-file>` 提交节点，runner 负责 schema 校验、日志记录和推进后续节点。

除非明确设置 `ARTICLE_DIRECTOR_PROVIDER=openai/deepseek/anthropic` 且设置 `ARTICLE_DIRECTOR_ALLOW_API_PROVIDER=1`，否则 runner 不得直接调用 API provider。

## Deprecated / Disabled Paths

- `compile_short_article_workflow.py` 已废弃，不作为正式入口。
- 旧 short workflow、validation smoke outputs、坏运行目录只允许历史检查，不允许作为新任务入口。

## 确定性工具

- `scripts/workflow_runner.py` — 节点推进引擎
- `scripts/compile_expanded_workflow.py` — expanded 工作流编译器
- `scripts/doctor_article_director.py` — 诊断工具
- `harness/outline_validator.py` — 大纲校验（Layer 1）
- `harness/package_validator.py` — 分包校验（Layer 2）
- `harness/article_validator.py` — 终稿校验（Layer 3，整合 check_article.py）
- `supervisor.py` — 覆盖度检查
- `D:\知识库\projects\知识星球自动更新-AI社群\scripts\content_ingest.py` — 入库门控

## 强制规则

- 不自动发布
- 不跳过 `state/reviews/{topic_id}.json`
- 不把已审批内容只存在 `tmp/`
- 当前 Codex 付费模式下，不调用 OpenAI/DeepSeek/Anthropic API provider；agent 节点必须通过 Codex task packet 显式交接与提交。
- 策略不能定义节点、边、提供商或路由（只能定义内容意图和提示词后缀）
- 生成的工作流脚本必须包含 `ARTICLE_DIRECTOR_WORKFLOW_VERSION`
- 收到用户对大纲或正文的批注后，先沉淀到 topic memory；若批注可复用，再同步到 `memory/review-comment-experience.md`
- 每次 workflow 运行必须生成 `run-manifest.json`、`node-events.jsonl`、`artifact-manifest.json`、`version-lock.json`、`requirement-log.jsonl`、`memory-scope.json`。
- 执行中的 agent 默认只能读取当前 `outputs/{topic_id}/memory/` 和当前 run 的产物；全局 `memory/review-comment-experience.md` 只能作为已沉淀的可复用写作经验，不能代替当前文章的事实、结构或用户新要求。
