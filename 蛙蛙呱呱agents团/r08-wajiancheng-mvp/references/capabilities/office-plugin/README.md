Office 交付物（capability: office-plugin）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py office xlsx`）
- 夹具：`tests/xlsx-pass.json`（两表带表头）/ `tests/xlsx-fail.json`（无表头无数据）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2，写临时文件后自动清理）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py office`（probe / xlsx / docx），本包不重复实现
