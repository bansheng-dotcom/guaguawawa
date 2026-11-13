# 出图编排层（capability: image-gen-pipeline）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（**knowledge 卡**，`entry: null`；**编排层，不含 API 调用**）
- 核心资产：`references/pipeline-runbook.md`（manifest 模板 + 命名规范 + 版数档位 + 成本止损 + 失败分类 + 6 组 BAD/GOOD）
- 判定：§5 七条硬门 + 失败分类归因 + 规格闸
- 负向用例：`tests/misuse.md`
- 在能力链中的位置：`image-prompt-structure`（描述）→ **本卡（批次编排）** → `image-candidate-selection`（筛选）→ `image-ops`（后处理）
- **为什么不含调用代码**：保持团队 55 个包零依赖离线可跑；真实调用交外部工具
