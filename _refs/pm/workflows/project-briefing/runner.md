# 项目理解与汇报 Runner

## 1. Runner 定位

这是项目汇报 runner。它不追求标准模板，而是让用户更快看懂项目和决策点。

## 1.1 重任务门禁

如果本轮要产出汇报或决策报告，先读 `workflows/HEAVY_TASK_RAG_RULES.md`，执行 `workflows/experience-rag/workflow.yaml` 的 `heavy-task` 模式；如果需要请用户拍板或补关键事实，先复用入口 `experience_brief`，关键维度变化才执行 `pre-question` L1。

## 2. 执行步骤

| 步骤 | 动作 | 输出 |
| --- | --- | --- |
| 1 | 读取 `user/` 和项目偏好 | 对话对象理解 |
| 2 | 读取本次相关项目事实 | 事实清单 |
| 3 | 区分事实、推断、建议 | 判断基础 |
| 4 | 若需要决策，生成多个选项和利弊 | 决策表 |
| 5 | 给推荐但不替用户拍板 | 推荐 |
| 6 | 写清归档位置 | 存档路径 |

## 3. 文件管理

| 文件 | 用途 |
| --- | --- |
| `references/project-briefing-guide.md` | 项目理解、人感汇报、归档规则 |
| `templates/human-readable-briefing-template.md` | 轻量汇报模板 |
| `user/profile.md` | 可选本地用户偏好摘要；不存在时跳过 |
| `reports/README.md` | 备用归档规则 |

## 4. 回退方式

- 如果事实不足，标注假设和补证路径。
- 如果只有一个选项，说明其他选项为什么不成立。
- 如果用户不想看长报告，压缩成结论、选项、下一步。

## 5. 完成标准

- 汇报有判断，不像模板。
- 决策点有选项、利弊、风险和兜底。
- 重要内容有归档位置。
