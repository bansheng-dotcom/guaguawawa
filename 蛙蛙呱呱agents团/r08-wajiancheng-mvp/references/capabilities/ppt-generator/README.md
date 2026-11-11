单文件 HTML 幻灯片（capability: ppt-generator）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py deck plan`）
- 夹具：`tests/deck-pass.json`（6 页正例）/ `tests/deck-fail.json`（2 页反例）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py deck`（plan / html），本包不重复实现
