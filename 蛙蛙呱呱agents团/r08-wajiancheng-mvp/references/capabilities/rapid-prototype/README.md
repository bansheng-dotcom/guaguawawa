# 快速原型（capability: rapid-prototype）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 门禁自检：`scripts/gate_selftest.py`（`--self-test`）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用角色根目录 `harness.py`，本包不重复实现
