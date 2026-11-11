# 增长 Campaign 设计（capability: campaign-plan）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/campaign-matrix.md`（渠道矩阵 / 20-60-20 预算 / 预注册实验 / 停止条件）
- 骨架：`tests/plan-pass.json`（campaign 计划骨架）、`tests/media-pass.json`（单渠道四要素骨架）
- 门禁自检：`scripts/gate_selftest.py`（正例 4 + 反例 3，实测 7/7）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py` 三道（plan / media / cro），本包不重复实现
