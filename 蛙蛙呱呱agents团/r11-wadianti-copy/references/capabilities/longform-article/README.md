# 长文与稿件（capability: longform-article）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py copy article`）
- 门禁自检：`scripts/gate_selftest.py`（2 正例 + 2 反例，实测 4/4）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py copy`（article / voice），本包不重复实现
