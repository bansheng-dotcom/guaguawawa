# 产品管理经验库

这个目录存放产品管理 person 自己的经验，不替代项目正式文档。

经验库的目标不是保存聊天记录，而是让产品经理在下次判断前能检索到“类似场景下应该怎么判断、怎么汇报、怎么避免犯错”。

## 1. 目录结构

```text
experience/
├── README.md
├── EXPERIENCE_INDEX.md
├── RAG_MODEL.md
├── RAG_RULES.md
├── global/
│   └── README.md
├── inbox/
│   └── README.md
├── templates/
│   ├── experience-card-template.md
│   └── correction-retrospective-template.md
└── <项目名>/
    ├── README.md
    ├── 经验索引.md
    ├── 用户偏好与要求-<项目名>.md
    ├── 纠错经验库.md
    └── YYYY-MM-DD-主题.md
```

## 2. 经验沉淀维度

经验至少按 8 个维度沉淀：

| 维度 | 用途 | 示例 |
| --- | --- | --- |
| `scope` | 适用范围 | `global`、`project`、`user`、`workflow` |
| `project` | 所属项目 | `示例项目` |
| `workflow_ids` | 影响哪些工作流 | `project-briefing`、`prd-report` |
| `artifact_types` | 影响哪些产物 | 汇报、PRD、需求卡、UI brief、测试场景 |
| `experience_type` | 经验类型 | 用户偏好、纠错、决策模式、反模式、文件治理、协作规则 |
| `trigger_signals` | 什么时候召回 | “听不懂”“如何决策”“需求进开发” |
| `applicability` | 适用边界 | 适用、不适用、需要补证据 |
| `validation` | 可信度 | 用户明确确认、重复出现、单次观察、已废弃 |

详细字段见 `RAG_MODEL.md`。

## 3. 读取顺序

执行产品判断、准备提问、项目汇报、PRD、需求管理、纠错复盘前，先经过 RAG Gate：

1. `EXPERIENCE_INDEX.md`
2. 当前项目目录的 `经验索引.md`
3. 当前项目目录的 `用户偏好与要求-<项目名>.md`
4. 当前项目目录的 `纠错经验库.md`
5. 只有 Gate 判断需要升级 L2 时，才打开与当前任务关键词匹配的经验卡

如果是跨项目或没有项目目录，优先读 `global/` 和 `user/`。

提问前默认只做 L1：看索引、用户偏好和项目纠错摘要，不打开大量经验卡，目的是把追问压缩到 0-1 个关键问题。汇报、需求文档、PRD、竞品分析等报告/文档类重任务，先按 `workflows/HEAVY_TASK_RAG_RULES.md` 做 L2 和重思考，生成可复用 `experience_brief`，再进入具体 workflow。

## 4. 写入规则

只有高复用经验才写入：

- 用户明确表达偏好、纠错或长期规则。
- 同类问题第二次出现。
- 某个产品判断模式能复用到后续需求。
- 某个失败模式下次很可能复发。
- 文件归档、协作审核、汇报方式影响后续工作。

不要写入：

- 未验证事实。
- 一次性聊天摘要。
- 项目正式结论的副本。
- 没有触发条件的空泛方法论。

## 5. 经验使用红线

- 经验只提供判断参考，不替代当前项目事实。
- 经验必须说明适用范围；范围不匹配时不能套用。
- 新用户原话优先于旧经验。
- 已废弃或低置信经验只能提示风险，不能作为结论。
