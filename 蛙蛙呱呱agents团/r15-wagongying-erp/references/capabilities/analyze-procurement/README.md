# 采购 TCO 分析（capability: analyze-procurement）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py tco compare`）
- 夹具：`tests/tco-pass.json` / `tests/tco-fail.json`
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py tco`（compare / lifecycle），本包不重复实现
