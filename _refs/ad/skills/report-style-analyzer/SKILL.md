---
name: report-style-analyzer
description: 将任意文章、报告、段落样本拆解成可复用的文风资产包，分析结论生成机制、论述结构、常用语、段落节奏、认知模式、段落功能标签和反模式；当需要学习某个作者文风、沉淀风格 profile、生成下游写作/审稿/修改 agent 可用的风格输入时使用。内置“渭河文风”作为用户默认报告写作风格。
---

# Report Style Analyzer

## 作用

这个 skill 是通用文风解析器。它接收用户本次提供的文章、报告、段落、文件列表或目录，拆解出“这个文风如何产生结论、如何论述、如何组织段落、如何使用语言”的机制，并输出下一个 agent 可直接复用的风格资产包。

它不固定读取某个文章目录，也不只总结某组文章的内容观点。文章样本是输入项，skill 的能力是把输入样本抽象成规则。

## 默认风格

当用户没有指定新风格名，且任务涉及用户自己的数据分析、经营分析、知识科普或报告写作时，默认调用“渭河文风”：

- `references/weihestyle-profile.md`
- `references/weihestyle-language-bank.md`
- `references/weihestyle-paragraph-rhythm.md`
- `references/weihestyle-review-rubric.md`
- `references/paragraph-tagging-review-protocol.md`

## 输入形式

支持任意一种输入：

- 用户直接粘贴的文章或段落。
- 一个或多个本地 markdown、txt、docx 转写文本。
- 一个本地文章目录。
- 已有报告草稿，需要反推其文风或判断是否符合某个文风。

如果输入是路径，先做只读审计，再读取样本。不要把某个固定目录写死进流程。

## 工作流

### 1. 建立语料边界

确认本次输入是什么、样本数量、主题范围、是否同一作者、是否同一类型内容。样本不足时仍可输出临时 profile，但必须标注置信度。

### 2. 按五大类拆解

使用 `references/analyzer-core.md` 和 `references/style-taxonomy.md`，把样本拆成五类：

1. `结论生成机制`: 结论从什么问题、判断、证据和取舍中得出。
2. `论述组织机制`: 文章如何开场、推进、转折、收束。
3. `语言表达机制`: 常用判断句、转折句、解释句、推进句、边界句。
4. `段落节奏机制`: 段落长度、段落功能、句子密度、长短句搭配。
5. `认知风格机制`: 作者如何理解问题、反对什么、优先什么、承认什么边界。

### 3. 段落标签驱动审查

当任务是审查或修改文章时，读取 `references/paragraph-tagging-review-protocol.md`。先给段落打功能标签，再按标签触发局部审查；全文链路缺口单独检查。不要让每个段落遍历所有问题。

局部审查只判断这个段落是否完成自己的功能；全文审查再判断是否缺少真实问题、常见误区、作者判断、业务场景、阶段性结论、可干预动作和边界。

### 4. 形成风格资产包

按 `references/output-contract.md` 输出下游 agent 可用的资产，至少包含：

- `style_profile`: 这个文风的总体画像。
- `reasoning_pattern`: 结论如何生成。
- `argument_pattern`: 论述如何推进。
- `language_bank`: 常用语、句式和表达功能。
- `paragraph_rhythm`: 段落长度、节奏、功能分布。
- `paragraph_tagging_protocol`: 段落功能标签和标签触发的审查项。
- `anti_patterns`: 哪些写法不像该作者。
- `reuse_prompt_contract`: 给写作 agent、审稿 agent、改写 agent 的硬约束。

### 5. 沉淀或更新具体风格

只有当用户明确要求“保存/沉淀/作为 skill 的一部分”时，才把某个作者风格写入 skill 资产。当前已内置“渭河文风”，作为用户默认风格。

新增风格时命名清晰，例如：

```text
references/<style-name>-profile.md
references/<style-name>-language-bank.md
references/<style-name>-paragraph-rhythm.md
references/<style-name>-review-rubric.md
```

## 审查输出质量

解析结果必须满足：

- 规则高于摘抄，不能只复述原文观点。
- 每个大类都要先给抽象机制，再给细分规则。
- 语言库必须说明句式功能，而不是罗列口头禅。
- 段落节奏必须描述段落长度、句间推进和段落功能。
- 结论机制必须说明结论如何得出，而不只是结论是什么。
- 审查/修改必须走段落标签，不允许每段遍历全部问题。
- 输出必须能交给下一个 agent 直接写作、审稿或改写。

## 辅助脚本

`scripts/extract_report_style.py` 可做确定性辅助抽取：文件清单、段落候选、常用连接词、段落长度、句式标记。脚本只提供证据候选，最终风格抽象由 agent 按本 skill 的分类体系完成。

