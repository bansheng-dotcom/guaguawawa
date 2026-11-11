# Web 应用构建（capability: web-app-development）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py spec spec`）
- 知识层：`references/web-app-delivery.md`（契约表 / 端到端切片四段 / 鉴权三规则 / 依赖方向 / 材料四件）
- 门禁自检：`scripts/gate_selftest.py`（正例 3 + 反例 3，实测 6/6）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py spec|fullstack` 与 `harness.py materials|testreport`，本包不重复实现
