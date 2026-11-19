# 任务卡：r19 蛙智模（模型工程与 AI 评估官）

- 总任务：内蒙古奶食品（奶豆腐/奶皮子/奶酪）能不能做成一人公司的线上生意
- 数据通道：**web** —— 用户未给数据：联网找公开可核来源，每条留原文引文与链接
- 你负责：实验追踪, 模型注册与版本, 评估数据集与评分器, Agent Trace 与调试
- 可用技能：tracking, registry, evaluation, trace, release, monitor, modelcard, eval_ci
- 可用动作：评估集准备, 评分与评估, 模型注册入库, 发布候选裁决, 发布回归, 漂移监控, 模型卡, Trace 分析

## 你要判断什么（自己定，不要等我给）

从你的专业出发，回答这个问题里**只有你能回答**的部分。答不了就写进 missing，不要编。

## 交什么

写到 `../内蒙古奶食品调研_2026-11-18/cards/r19/claims.json`，格式见 `brief.md` 的「一条结论必须长这样」，
最少包含：numbers / sources / sections（每节 title 带数字、≥2 条解读、带 refs、带 falsifier）。

## 边界

- 只用公开可核来源；查不到写 missing
- 同一指标两个数，必须在 conflicts 里写清口径差