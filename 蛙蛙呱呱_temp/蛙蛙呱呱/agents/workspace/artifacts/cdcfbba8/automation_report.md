# 蛙织网 · integration/workflow
> 帮我核查这个自动化工作流的结构是否合规、能不能集成 

**结论**：next=自动化工件通过全部门禁，可进入发布与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 6/6 项 |
| next | **自动化工件通过全部门禁，可进入发布与交接** | 输出字段 |
| node_count | **3** | 输出字段 |
| trigger_count | **1** | 输出字段 |

## 1. node_count
> node_count 的判定与证据是什么？

- **node_count：**3

## 2. trigger_count
> trigger_count 的判定与证据是什么？

- **trigger_count：**1

## 3. dangling_edges
> dangling_edges 的判定与证据是什么？

- **dangling_edges：**0

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**工作流 acme-lead-sync：3 节点 / 1 触发器 / 悬空边 0

## 口径与边界

- **来源：**技能 integration/workflow 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
