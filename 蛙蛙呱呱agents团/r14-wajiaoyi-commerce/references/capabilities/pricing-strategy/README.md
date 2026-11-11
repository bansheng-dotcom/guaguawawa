# 定价与促销策略（capability: pricing-strategy）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（knowledge 卡，`entry: null，无命令门禁`）
- 核心资产：`references/pricing-models.md`（成本五项拆解 + 三种定价方法 + 折扣阶梯算例 + 10 组 BAD/GOOD）
- 判定：§5 质量门（6 条）+ §6 人工清单 + 双评一致率 ≥80%
- 负向用例：`tests/misuse.md`
- 补的是什么缺口：补的是**交易链起点**：此前 `smart-product-selector` 会算「毛利空间」维度，`order-lifecycle` 会校验订单，但**定价策略本身没有卡**——导致选品、投放、毛利都建立在一个没人算过的价格上。
