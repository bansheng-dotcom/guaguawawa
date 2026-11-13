# PRD 撰写（capability: prd-authoring）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/two-layer-prd.md`（两层分工 / AC vs DoD / RICE 算例 / 12 项审批）
- 执行层骨架：`tests/spec-pass.json`（可直接改）
- 门禁自检：`scripts/gate_selftest.py`（正例 2 + 反例 3，实测 5/5）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py prdguard`（12 项）与 `harness.py prd`，本包不重复实现
