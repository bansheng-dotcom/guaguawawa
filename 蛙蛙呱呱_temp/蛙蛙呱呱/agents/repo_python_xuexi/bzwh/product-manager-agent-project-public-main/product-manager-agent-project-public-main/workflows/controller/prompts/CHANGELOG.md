# PM 总控与轻量反应 Prompt Changelog

## 0.3 - 2026-07-01

- 将经验调用改为 RAG Gate：轻任务只做 L1 判断，重任务才进入 L2。
- 重任务入口生成 `experience_brief`，内部追问默认复用；只有项目、workflow、产物或决策点变化才重新 Gate。
- 输出中的经验字段改为报告 Gate 层级和 brief 复用状态，而不是默认要求检索。

## 0.2 - 2026-07-01

- 将提问顺序改为先 `experience-rag: pre-question`，再决定是否追问。
- 增加重任务判断：报告/文档/需求包先走 `HEAVY_TASK_RAG_RULES.md` 和 `experience-rag: heavy-task`。
- 保留非重任务的 `experience-rag: normal` 分支，用于产品判断、纠错、用户偏好和持续项目。

## 0.1 - 2026-07-01

- 合并原 `PM轻量反应与工作流选择.md` 和 `PM总控路由流程.md`。
- 明确先理解、少追问、再路由、选最小产物。
