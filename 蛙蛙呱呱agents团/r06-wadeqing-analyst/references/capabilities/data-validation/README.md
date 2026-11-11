# 数据校验（capability: data-validation）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/data-provenance.md`（六维门槛 / 字段处置四类 / 来源分级 / 幸存者偏差三问 / 交叉核对）
- 骨架：`tests/semantic-pass.json`（指标语义模型骨架）、`tests/dirty.csv`（脏数据样例）
- 门禁自检：`scripts/gate_selftest.py`（正例 3 + 反例 2，实测 5/5）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py semantic` 与 `agent.py quality audit`（后者经共享 `scripts/gate_wrap.py` 包装），本包不重复实现
