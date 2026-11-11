# 硬决策闸门（capability: decision-gate）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/hard-gate.md`（批准闸门枚举）
- 决策卡骨架：`templates/decision-card.example.json`（已通过 15 项门禁）
- 门禁自检：`scripts/gate_selftest.py`（正例 2 + 反例 2）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用角色根目录 `harness.py`（`card` / `escalate` / `reversibility`），本包不重复实现
