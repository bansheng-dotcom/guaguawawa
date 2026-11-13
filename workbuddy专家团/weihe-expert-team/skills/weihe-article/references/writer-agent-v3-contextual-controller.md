# Writer Agent v3：上下文总控写作设计

## 背景

7-03 写作暴露出一个系统性问题：大纲和细纲能约束“写什么”，但不能稳定约束“具体段落怎样让读者先用起来”。即使 writer 已经收到前置提示词，正文仍可能走向抽象概念、分类和机制解释，把简单经验复杂化。

本设计把 writer 从“细纲扩写器”升级为“局部上下文写作总控”。

## 设计目标

- writer 写正文前，先判断上一节、本节、下一节之间的关系。
- writer 必须生成可审计的 `reader_use_contract`，再写正文。
- writer 必须记录 2-3 轮简短决策日志，说明按当前契约写还缺什么、如何调整。
- 保持现有 section 并行能力，不把文章写作强行改成串行。
- 不影响后续 AI-tone、logic、structure、revision、final review 链。

## 为什么不传上一节/下一节已生成正文

现有 article-director 的 section job 支持并行执行。如果 writer 必须读取上一节已生成正文，所有 section writer 会被迫串行，影响运行速度，也增加失败恢复复杂度。

因此本版本传递的是结构上下文，不是已生成正文：

- `previous_block`：上一节在 section-manifest 中的结构内容。
- `current_block`：本节结构内容 + 当前 argument-spine。
- `next_block`：下一节在 section-manifest 中的结构内容。

这些输入足够判断承接、重复、提前解释和下一节依赖，同时不引入运行时串行依赖。

## 新增节点

```text
build-argument-spine-{section_id}
→ build-writer-context-window-{section_id}
→ plan-writer-controller-{section_id}
→ writer-section-{section_id}
```

### build-writer-context-window

脚本节点。输出：

`sections/{section_id}/writer-context-window.json`

内容包括：

- `previous_block`
- `current_block`
- `next_block`
- `base_prompt`
- `context_policy`
- `writer_controller_required_output`

### plan-writer-controller

agent 节点。输出：

`sections/{section_id}/writer-control-log.json`

必须输出 JSON：

- `context_map`
- `reader_use_contract`
- `deliberation_log`
- `write_readiness`
- `upstream_issue`
- `downstream_issue`
- `self_check`

该节点不写正文。

### writer-section

agent 节点。新增输入：

- `writer-context-window.json`
- `writer-control-log.json`

正文必须从 `reader_use_contract` 开始写，不允许直接从细纲概念起笔。

## 影响范围

| 文件 | 目的 | 上下游影响 | 回退方式 |
| --- | --- | --- | --- |
| `scripts/build_writer_context_window.py` | 生成上一节/本节/下一节上下文窗口 | 供 writer-controller 消费 | 删除脚本并从 compile 中移除节点 |
| `scripts/compile_expanded_workflow.py` | 插入 context-window 和 writer-controller 节点 | expanded workflow 每节增加 2 个节点 | 回退 writer 节点输入和边 |
| `agents/writer-research/SKILL.md` | 定义 writer v3 两阶段职责 | 影响 writer-controller 与 writer-section 行为 | 回退新增章节 |
| `prompts.yaml` | 注册 writer-research 新职责和约束 | 影响任务包角色说明 | 回退 writer-research 条目新增约束 |
| `workflows/topology.yaml` | 人类可读拓扑同步 | 不影响 runner，但影响维护认知 | 回退新增节点说明 |

## 当前验证

- Python 语法检查通过。
- `build_writer_context_window.py` 已能为 7-03 section-03 生成上下文窗口。
- `prompts.yaml` 与 `workflows/topology.yaml` YAML 解析通过。
- `compile_expanded_workflow.py` 重新编译后，每个 section 新增 2 个节点。
- `workflow_runner.py --dry-run` 能读取新 expanded workflow。

## 暂不做的事

- 暂不强制 JSON schema 校验 `writer-control-log.json`。原因是先验证机制收益，避免一次改动过重。
- 暂不把 previous/next 改成已生成正文。原因是会破坏 section 并行。
- 暂不改 review/revision 链。现有 AI-tone、logic、structure 和 revision 仍保持原有职责。

## 下一步

如果下一篇文章验证有效，再补：

- `schemas/writer-control-log.schema.json`
- `validate-writer-control-log-{section_id}` gate
- `reader-access-check-{section_id}`，专门检查正文是否真的按 reader_use_contract 写作
