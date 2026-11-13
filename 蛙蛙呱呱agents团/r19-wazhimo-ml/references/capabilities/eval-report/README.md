# 模型评测与发布门禁（capability: eval-report）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/eval-discipline.md`（评测集四纪律 / 评分器设计 / 报告四块 / 回归判定 / 模型卡）
- 门禁自检：`scripts/gate_selftest.py`（正例 3 + 反例 3，实测 6/6）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py` 三道（evaluation_dataset / evaluation_scorer / release_regression），本包不重复实现
