# Experience RAG Model

> 用途：定义产品管理 person 的经验卡字段、索引维度和召回粒度。

## 1. 经验卡最小模型

每条经验建议使用 YAML frontmatter + 正文结构：

```md
---
experience_id: exp-YYYYMMDD-short-slug
title: 简短标题
scope: global | project | user | workflow
project: 项目名或 none
workflow_ids:
  - project-briefing
  - prd-report
artifact_types:
  - 汇报
  - PRD
experience_type: user_preference | correction | decision_pattern | anti_pattern | workflow_rule | file_governance | collaboration_rule | evidence_rule
trigger_signals:
  - 听不懂
  - 如何决策
problem_pattern: 什么情况下会遇到这个问题
applicability:
  applies_when:
    - 适用条件
  does_not_apply_when:
    - 不适用条件
source:
  kind: user_feedback | task_result | review | project_file
  path: 来源文件或对话摘要路径
validation:
  status: candidate | observed | validated | superseded
  confidence: low | medium | high
  last_verified: YYYY-MM-DD
keywords:
  - 检索词
---

## 经验结论

## 为什么成立

## 下次怎么用

## 不适用边界

## 关联文件
```

## 2. 核心维度

### 2.1 任务维度

| 字段 | 解释 |
| --- | --- |
| `workflow_ids` | 经验影响哪些 workflow，例如 `project-briefing`、`demand-management` |
| `artifact_types` | 经验影响哪些输出，例如报告、需求卡、PRD、验收场景 |
| `product_area` | 可选，影响哪个产品区域，例如首页、学习、AI 数据分析、后台 |
| `decision_dimension` | 可选，影响哪类决策，例如范围、优先级、架构、数据、体验 |

### 2.2 场景维度

| 字段 | 解释 |
| --- | --- |
| `trigger_signals` | 用户或任务中出现什么信号时召回 |
| `problem_pattern` | 抽象问题模式，不写成单次事件 |
| `stakeholders` | 用户、运营者、作者、开发、测试等受影响角色 |
| `product_stage` | idea、MVP、PRD、development、release、operation |

### 2.3 可信度维度

| 状态 | 含义 | 使用方式 |
| --- | --- | --- |
| `candidate` | 候选经验，尚未验证 | 只能提示可能风险 |
| `observed` | 单次观察成立 | 可作为提醒，不作为硬规则 |
| `validated` | 用户确认或多次复现 | 可作为默认规则 |
| `superseded` | 已被新规则替代 | 不能作为当前规则，只保留追溯 |

## 3. RAG 文本块

未来接向量库时，优先 embedding 下面这些字段：

```text
title
trigger_signals
problem_pattern
经验结论
下次怎么用
不适用边界
keywords
```

不要把长项目报告全文直接当经验 embedding。先提炼成经验卡，再入索引。

## 3.1 RAG Gate 输出模型

RAG Gate 的运行结果不是每次都生成经验卡。每轮至少产生轻量判断：

```yaml
rag_gate_decision:
  rag_level: L0 | L1 | L2
  mode: pre-question | heavy-task | normal
  query_terms:
    - keyword
  matched_index_items:
    - path: experience/EXPERIENCE_INDEX.md
      reason: 命中原因
  upgrade_to_l2: true | false
  upgrade_reason: 为什么需要或不需要打开经验卡
```

重任务进入 L2 时，再生成可复用的 `experience_brief`：

```yaml
experience_brief:
  source_cards:
    - path: experience/<项目名>/xxx.md
      status: validated
  applicable_rules:
    - 本轮适用规则
  non_applicable_rules:
    - 本轮不适用规则
  constraints_for_this_task:
    - 写报告或提问时必须遵守的约束
  reuse_key:
    project: 项目名
    workflow_id: prd-report
    artifact_type: PRD
    decision_point: 本轮决策点
```

同一重任务内部，只要 `reuse_key` 没变，继续复用 `experience_brief`，不重新检索。

## 4. 索引粒度

一条经验只解决一个可复用判断。

如果一份复盘里同时包含“汇报听不懂”“文件归档混乱”“技术选项没讲差异”，要拆成三条经验卡，而不是写成一个长总结。
