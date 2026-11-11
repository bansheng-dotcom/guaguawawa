# 交接与验收（capability: handoff-acceptance）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/handoff-contract.md`（交接包字段 / 验收契约 / 结论三选一 / 审计轨迹）
- 骨架：`tests/handoff-pass.json`（交接包骨架）、`tests/accept-pass.json`（验收记录骨架）
- 门禁自检：`scripts/gate_selftest.py`（正例 5 + 反例 2，实测 7/7）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py harness` 三道（package / accept / trace）；**注意 harness.py 无 __main__，必须走 agent.py**，本包不重复实现
