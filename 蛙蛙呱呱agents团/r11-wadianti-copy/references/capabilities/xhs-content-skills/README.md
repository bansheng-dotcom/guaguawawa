# 小红书笔记发布包（capability: xhs-content-skills）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py xhs note`）
- 夹具：`tests/xhs-pass.json`（正文 596 字）/ `tests/xhs-fail.json`（多项违规）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py xhs`（note / score / compliance），本包不重复实现
