---
name: qiuqiu-content
description: "知识科普长文生产线（内置 Article Director 完整多 Agent 方法包）：选题架构、大纲与细纲、分节写作、五路对抗审查、去 AI 味、风格统一、终稿收口与配图。当用户要写一篇知识科普/工具解析/方法拆解长文、要审阅改写一篇稿子、要补证据或查 AI 味时使用。Director-style multi-agent workflow for Chinese knowledge articles: topic architecture, section writing, adversarial review, de-AI-tone polishing, final integration."
---

# 知识科普文生产线（高雅人士天团 · 内容生产总监）

本技能内置 **Article Director 完整工作流包**（`upstream/`）：22 个 Agent 定义、`lean-v1` 拓扑、提示词注册表、策略契约、三层确定性校验器、去 AI 味规则、作者风格档案与批注经验库，全部原样保留。

**核心认知：这不是「一次写一篇」，而是一条可复现的生产线。** 先骨架（选题→大纲→细纲），再分节写，再对抗审查，最后整稿收口；每一层都有确定性门禁和人工闸门。

---

## 一、什么时候启用

- 「写一篇文章」「知识科普」「工具解析」「方法拆解」「教程」——正式长文
- 「审一下这篇稿子」「有没有 AI 味」「逻辑有没有断」——审查与修订
- 「帮我补证据」「找资料支撑这个论点」——单点研究
- 需要配图方案、附录、术语注释
- 需要把已有长文按风格重写、顺句、去模板化

**不启用**：短文/朋友圈/标题党快稿（直接写更快）、产品需求判断（qiuqiu-product）、数据分析报告（qiuqiu-data-analysis）。

---

## 二、启动必读（按顺序）

| 顺序 | 文件 | 读到什么 |
|---|---|---|
| 1 | `upstream/skills/article-director/SKILL.md` | 管理文件索引、核心角色、策略、两阶段生命周期、入口命令（**全文**） |
| 2 | `upstream/skills/article-director/workflows/topology.yaml` | 节点拓扑、`lean-v1` 展开、人工闸门位置、guard 阈值 |
| 3 | `upstream/skills/article-director/agents/_index.yaml` | 22 个 Agent 的注册与状态（谁是主链、谁是支撑、谁是 legacy） |

写之前再看 `upstream/skills/article-director/prompts.yaml` 的对应 `task_prefixes` 与 `strategies`（34KB，按需分段读，不要整份塞进上下文）。

---

## 三、主链路（lean-v1，默认）

```
article-architect（选题/大纲/细纲/范围控制）
  → section-writer ↔ section-editor（逐节写 + 五路审查 + 改写）
  → draft-assembler → final-integrator → appendix-agent
  → finalize-draft → 确定性门禁 → human-approval
```

| 角色 | 目录 | 只负责 |
|---|---|---|
| article-architect | `upstream/skills/article-director/agents/article-architect/` | 选题理解、大纲、细纲、范围控制 |
| section-writer | `.../agents/section-writer/` | 单节上下文写作 + reader-use-contract |
| section-editor | `.../agents/section-editor/` | 单节 AI 味/逻辑/结构/术语/文风合并审查修订 |
| section-reviewer | `.../agents/section-reviewer/` | 五路并行审查，**只提意见不改稿** |
| paragraph-rewrite-designer | `.../agents/paragraph-rewrite-designer/` | 改写单元、候选评分、选中草稿与微调指令，**不直接改正文** |
| section-rewriter | `.../agents/section-rewriter/` | 按选中方案合稿、顺句、微调 |
| final-integrator | `.../agents/final-integrator/` | 整稿连贯性、风格统一、终稿收口 |
| appendix-agent | `.../agents/appendix-agent/` | 附录、术语表、延伸阅读 |
| deep-dive-researcher（可选） | `.../agents/deep-dive-researcher/` | 论文/机制/开源实现的深度研究 |
| image-ui（可选） | `.../agents/image-ui/` | 配图方案与图片链 |
| topic-architect / term-annotator / style-harmonizer / structure-editor / narrative-smoother / concept-bridge-rewriter / primer-writer / final-package-editor / adversarial-reviewer / article-review / writer-research / sentence-pattern-detemplatizer | 同上 `agents/` | 各专项节点，按 topology 触发，不默认全开 |

---

## 四、两种策略（先选策略再动笔）

| 策略 | 目标读者收益 | 概念处理 | 默认结构 |
|---|---|---|---|
| `knowledge-explainer` | 帮读者**理解**概念 | inline-minimal（就地最小解释） | 问题 → 概念 → 机制 → 证据 → 边界 |
| `teaching-playbook` | 帮读者**复现**任务 | execution-gated（先过执行前置） | 目标 → 基础 → 路径 → 步骤 → 代码 → 验证 → 排错 → 附录 |

策略契约：`upstream/skills/article-director/references/strategies/*.json`，说明见 `references/strategy-profiles.md`。

---

## 五、三道闸门（不许绕过）

| 闸门 | 位置 | 通过条件 |
|---|---|---|
| outline-confirmation | bootstrap/outline-confirmation-01 | 大纲 + 细纲生成并通过 `harness/outline_validator.py`，人工确认 |
| article-requirements-confirmation | 进入 section 写作前 | 字数、重点段落、新需求、个人文风、认知风格、逻辑偏好已确认 |
| final-article-approval | expanded/human-approval-01 | 全文终审 + `harness/article_validator.py` 通过，人工确认后才入库 |

---

## 六、确定性校验与执行脚本

| 工具 | 作用 |
|---|---|
| `upstream/skills/article-director/harness/outline_validator.py` | Layer 1：大纲结构校验 |
| `upstream/skills/article-director/harness/package_validator.py` | Layer 2：写作/审查分包校验 |
| `upstream/skills/article-director/harness/article_validator.py` | Layer 3：终稿确定性检查 |
| `upstream/skills/article-director/supervisor.py` | 分包覆盖度 + 策略关键 section 存在性 |
| `upstream/skills/article-director/scripts/init_workflow.py` | 初始化 `--title --topic-id --strategy --workflow-mode` |
| `upstream/skills/article-director/scripts/workflow_runner.py` | 节点执行与状态推进 |
| `upstream/skills/article-director/scripts/compile_expanded_workflow.py` | 生成 expanded 脚本 |
| `upstream/scripts/check_article.py`、`upstream/scripts/workflow_writer.py` | 单篇检查与工作流写入 |

脚本面向 Python 3.10+；不能执行时降级为人工按拓扑逐节点走，并明确说明降级原因。

---

## 七、去 AI 味（硬要求）

- 规则正文：`upstream/skills/article-director/references/ai-fluff-rules.md`
- 判定量表：`upstream/skills/article-director/references/ai-tone-judge-rubric.md`（deprecated 兼容入口，规则正文以 ai-fluff-rules 为准）
- 风格档案：`upstream/skills/article-director/style-profiles/style-guide.md`（句长/段落/过渡）、`cognitive-style-guide.md`（理解路径与解释顺序）、`author-soul.md`（站位与人格，避免老师讲课式）、`anti-patterns.json`（反例）
- 批注经验：`upstream/skills/article-director/memory/review-comment-experience.md`

**验收口径**：删掉「首先/其次/最后」「值得注意的是」「在当今时代」「综上所述」这类填充；每段有具体信息增量；例子先于定义；不写「赋能/抓手/闭环」式空词；同一句式家族不连续出现三次以上。

---

## 八、输出规范

- 交付物固定：`大纲` → `细纲` → `分节草稿` → `审查记录（JSON）` → `终稿`（+ 可选 `配图方案`、`附录`）
- 审查记录落结构，不落散文评论；每条修订可回溯到审查意见。
- 终稿必须通过三道门禁再交付；未过门禁时交付「当前稿 + 未解决问题清单」，不谎称完成。
- 产物输出到用户指定目录（默认按天团交付规范建 `YYYY-MM-DD_HHMM_<标题>` 文件夹），不写进技能包目录。
- 不出现占位符、不虚构引用与数据；证据不足处标注待补。
