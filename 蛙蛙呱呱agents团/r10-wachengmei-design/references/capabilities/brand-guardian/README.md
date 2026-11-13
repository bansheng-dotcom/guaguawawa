品牌一致性守卫（capability: brand-guardian）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py brandcheck check`）
- 夹具：`tests/brand-pass.json` / `tests/brand-fail.json`（以 `../../../DESIGN.md` 令牌为基准）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py brandcheck check`，本包不重复实现
