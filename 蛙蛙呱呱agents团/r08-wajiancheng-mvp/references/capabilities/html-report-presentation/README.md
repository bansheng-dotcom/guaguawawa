单文件 HTML 报告（capability: html-report-presentation）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py htmlreport plan`）
- 夹具：`tests/report-pass.json`（六项全过）/ `tests/report-fail.json`（多项缺失）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py htmlreport`（plan / html），本包不重复实现
