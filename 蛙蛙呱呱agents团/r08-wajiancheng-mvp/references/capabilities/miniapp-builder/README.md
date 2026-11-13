小程序工程脚手架（capability: miniapp-builder）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py miniapp plan`）
- 夹具：`tests/miniapp-pass.json` / `tests/miniapp-fail.json`（中文名 + tabbar 悬空）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py miniapp`（plan / scaffold），本包不重复实现
