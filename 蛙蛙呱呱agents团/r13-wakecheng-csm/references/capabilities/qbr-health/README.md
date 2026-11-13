# 客户健康与 QBR（capability: qbr-health）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/qbr-playbook.md`（四维加权 / 三色区间 / delta 与临期 / 升级分级 / QBR 结构）
- 骨架：`tests/health-pass.json`（健康分骨架）
- 门禁自检：`scripts/gate_selftest.py`（正例 4 + 反例 3，实测 7/7）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py` 三道（health / risk / escalation），本包不重复实现
