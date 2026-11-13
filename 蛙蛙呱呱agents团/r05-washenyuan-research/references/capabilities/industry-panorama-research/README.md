# 行业全景研究（capability: industry-panorama-research）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。
> 本文件仅保留旧路径指针，供 `guagua.py capabilities --probe` 与历史链接继续可用。

- 技能包：`SKILL.md`（`metadata.verify` = `agent.py industry landscape`）
- 门禁自检：`scripts/gate_selftest.py`（4 正例 + 4 反例，实测 8/8）
- 负向用例：`tests/misuse.md`
- 判定逻辑：复用 `agent.py industry`（landscape/concentration）与 `sizing`（size/sensitivity），本包不重复实现
