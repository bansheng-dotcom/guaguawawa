# 经验卡模板

```md
---
experience_id: exp-YYYYMMDD-short-slug
title: 经验标题
scope: global | project | user | workflow
project: 项目名或 none
workflow_ids:
  - workflow-id
artifact_types:
  - 产物类型
experience_type: user_preference | correction | decision_pattern | anti_pattern | workflow_rule | file_governance | collaboration_rule | evidence_rule
trigger_signals:
  - 触发词
problem_pattern: 抽象问题模式
applicability:
  applies_when:
    - 适用条件
  does_not_apply_when:
    - 不适用条件
source:
  kind: user_feedback | task_result | review | project_file
  path: 来源路径或摘要
validation:
  status: candidate | observed | validated | superseded
  confidence: low | medium | high
  last_verified: YYYY-MM-DD
keywords:
  - 检索关键词
---

## 经验结论

一句话写清下次应该怎么做。

## 为什么成立

写来源、触发场景和判断依据。

## 下次怎么用

写成可执行规则，不写空泛原则。

## 不适用边界

写清什么时候不能套用。

## 关联文件

- `path/to/file.md`
```
