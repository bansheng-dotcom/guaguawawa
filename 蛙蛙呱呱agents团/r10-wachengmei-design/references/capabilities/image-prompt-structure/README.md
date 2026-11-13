# 出图提示词结构（capability: image-prompt-structure）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（**knowledge 范式卡**，`entry: null`，无命令门禁）
- 核心资产：`references/prompt-anatomy.md`（六段详解 + 12 组 BAD/GOOD + 负向词库 + 9 平台规格表）
- 判定：§5 六条硬门 + 四版一致性抽检（≥3/4）
- 负向用例：`tests/misuse.md`
- 在能力链中的位置：**判据 → 本卡（描述）→ `image-gen-pipeline`（出图）→ `image-ops`（后处理）**
