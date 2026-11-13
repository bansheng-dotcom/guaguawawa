# 预算与差异分析（capability: budget-variance）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（knowledge 卡，`entry: null，无命令门禁`）
- 核心资产：`references/variance-bridge.md`（三段差异桥算法 + 科目归并规则 + 8 组 BAD/GOOD）
- 判定：§5 质量门（6 条）+ §6 人工清单 + 双评一致率 ≥80%
- 负向用例：`tests/misuse.md`
- 补的是什么缺口：补的是**财务链中段**：此前 r03 只有 `cash-runway`（看未来）与 `model-audit`（查过去），缺「预算 vs 实际」这一环——有跑道无预算，等于管不住花钱。
