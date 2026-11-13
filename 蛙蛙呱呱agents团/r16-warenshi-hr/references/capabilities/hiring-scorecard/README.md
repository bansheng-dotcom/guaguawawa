# 招聘评分卡（capability: hiring-scorecard）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/scorecard-design.md`（必选项写法 / 权重设计 / 打分规则 / 反歧视红线 / Offer 前置链）
- 门禁自检：`scripts/gate_selftest.py`（正例 3 + 反例 3，实测 6/6）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py` 三道（opening / applicant / offer），本包不重复实现
