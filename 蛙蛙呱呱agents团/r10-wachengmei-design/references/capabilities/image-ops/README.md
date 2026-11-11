本地图片处理（capability: image-ops）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py imgops info`）
- 夹具：`tests/sample.png`（64×64 RGB）/ `tests/not-a-png.png`（伪 PNG）
- 门禁自检：`scripts/gate_selftest.py`（实测 2/2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py imgops`，本包不重复实现
