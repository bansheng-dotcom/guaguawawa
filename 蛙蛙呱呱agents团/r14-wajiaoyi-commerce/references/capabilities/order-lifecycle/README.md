# 订单生命周期（capability: order-lifecycle）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（frontmatter 含触发语、`metadata.verify` 门禁命令）
- 知识层：`references/order-state-machine.md`（三态模型 / 迁移白名单 / 终态保护 / 退款与幂等）
- 订单骨架：`tests/order-pass.json`
- 门禁自检：`scripts/gate_selftest.py`（正例 6 + 反例 5，实测 11/11）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `harness.py` 七道门禁（order / cart / refund / state / transition / events / webhook），本包不重复实现
