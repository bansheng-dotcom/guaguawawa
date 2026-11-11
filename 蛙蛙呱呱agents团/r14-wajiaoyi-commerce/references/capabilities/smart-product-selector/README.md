# 选品评分（capability: smart-product-selector）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py selection score`）
- 夹具：`tests/selection-pass.json` / `tests/selection-fail.json`
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py selection`（score / profit），本包不重复实现
