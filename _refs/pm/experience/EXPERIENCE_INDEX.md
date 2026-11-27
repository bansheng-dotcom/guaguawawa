# Experience Index

> 用途：产品管理 person 的全局经验检索入口。项目目录可以有自己的 `经验索引.md`，但跨项目检索先看这里。

## 1. 全局索引

| 关键词 | 经验文件 | 适用场景 | 可信度 |
| --- | --- | --- | --- |
| `经验RAG` `经验检索` `经验沉淀` | `RAG_MODEL.md`、`RAG_RULES.md` | 需要判断如何读取、写入、提炼经验 | validated |
| `RAG Gate` `L1` `L2` `experience_brief` | `RAG_MODEL.md`、`RAG_RULES.md` | 需要判断是否打开经验卡、如何复用重任务经验摘要 | validated |
| `提问前` `pre-question` `质问` `grill` | `RAG_RULES.md`、`../workflows/experience-rag/workflow.yaml` | 准备追问前，先做 L1 Gate，不默认打开经验卡 | validated |
| `重任务` `heavy-task` `报告` `PRD` `竞品分析` | `RAG_RULES.md`、`../workflows/HEAVY_TASK_RAG_RULES.md` | 进入报告/文档类 workflow 前做 L2 和重思考，生成 `experience_brief` | validated |
| `纠错` `下次规则` `偏好记录` | `templates/correction-retrospective-template.md`、`templates/experience-card-template.md` | 用户指出不对、不理解、下次要这样 | validated |

## 2. 项目索引

| 项目 | 索引文件 | 重点经验 |
| --- | --- | --- |
| 暂无公开项目经验 | - | 真实项目经验应在安装后写入本地 `experience/projects/` |

## 3. 检索提示

如果当前任务没有明确项目，先搜：

```powershell
rg -n "关键词1|关键词2|workflow-id|产物名" experience user
```

如果当前任务有项目，先搜：

```powershell
rg -n "关键词1|关键词2|workflow-id|产物名" "experience/<项目名>" user
```

## 4. 更新规则

- 新增项目经验时，更新项目内 `经验索引.md`。
- 新增跨项目经验时，更新本文件。
- 新增模板或 RAG 规则时，更新 `templates/TEMPLATE_REGISTRY.md` 或 `workflows/WORKFLOW_REGISTRY.md`。
- 对外仓库不得提交未脱敏的用户档案、项目原话、账号、内部路径或业务数据。
