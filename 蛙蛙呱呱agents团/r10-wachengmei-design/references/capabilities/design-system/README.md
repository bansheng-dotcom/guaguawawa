# 设计系统与令牌（capability: design-system）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py brand token`）
- 门禁自检：`scripts/gate_selftest.py`（正例 2 + 反例 1，实测 3/3）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py brand token` 与 `designsys`，本包不重复实现
