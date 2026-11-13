# 2026-06-24 Writer Agent v3

## 版本目标

把 writer 从“按细纲直接扩写正文”升级为“先建立局部上下文契约，再写正文”。

本版本只处理 writer 链路：

- 生成上一节、本节、下一节的结构化上下文窗口。
- writer-controller 先产出 `reader_use_contract` 和 2-3 轮可审计决策日志。
- writer-section 再基于契约写本节正文。

## 明确不改

- 不新增独立审查 agent。
- 不改变既有 review、revision、final review 的职责边界。
- 不让上一节或下一节正文成为运行时依赖，避免破坏 section 并行。

## 新节点

```text
build-argument-spine-{section_id}
-> build-writer-context-window-{section_id}
-> plan-writer-controller-{section_id}
-> writer-section-{section_id}
```

`previous_block` 和 `next_block` 只来自结构化 manifest，不来自其他 writer 已生成正文。

## 影响矩阵

| 文件 | 目的 | 上下游影响 | 验证 | 回退 |
| --- | --- | --- | --- | --- |
| `scripts/build_writer_context_window.py` | 生成 previous/current/next 上下文窗口 | 供 writer-controller 消费 | 生成指定 section 的 `writer-context-window.json` | 从 compile 中移除调用并删除脚本 |
| `agents/writer-research/SKILL.md` | 定义 controller mode 与 section drafting mode | 只影响 writer-research 行为 | writer-controller 输出 JSON，writer-section 输出 Markdown | 删除新增章节 |
| `prompts.yaml` | 注册 writer-research 新职责和约束 | 只影响 writer-research prompt | YAML 可解析，writer prompt 含 controller 约束 | 回退 writer-research 条目 |
| `compile_expanded_workflow.py` | 在 writer 前插入 context-window 与 controller 节点 | writer 前置多两步；下游 review 链保持原样 | dry-run 出现新 writer 节点且 review 链不变 | 回退新增 writer 节点和边 |
| `workflows/topology.yaml` | 同步人类可读拓扑说明 | 便于维护者理解 writer v3 | YAML 可解析 | 删除 writer v3 拓扑说明 |

## 验收标准

- `python -m py_compile` 通过。
- `prompts.yaml` 和 `workflows/topology.yaml` 可解析。
- `build_writer_context_window.py` 能为 7-03 任一 section 生成上下文窗口。
- expanded workflow 中，每个 section 的 writer 前存在 context-window 与 controller 节点。
- downstream review、revision、final review 不因为本版本新增职责。
