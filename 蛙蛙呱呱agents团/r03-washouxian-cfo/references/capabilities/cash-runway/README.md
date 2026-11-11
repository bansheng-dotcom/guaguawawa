现金流跑道（capability: cash-runway）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py cfo runway`）
- 夹具：`tests/runway-pass.json`（正例）/ `../../../examples/cfo_runway.json`（反例）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py cfo runway`，本包不重复实现
