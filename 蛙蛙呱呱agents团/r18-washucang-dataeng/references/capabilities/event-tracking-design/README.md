# 埋点与事件设计（capability: event-tracking-design）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（knowledge 卡，`entry: null，无命令门禁`）
- 核心资产：`references/event-schema.md`（事件命名规范 + 属性最小集 + 漏斗模板 + 数据字典模板 + 10 组 BAD/GOOD）
- 判定：§5 质量门（7 条）+ §6 人工清单 + 双评一致率 ≥80%
- 负向用例：`tests/misuse.md`
- 补的是什么缺口：补的是**数据链起点**：此前 r18 只有 `dbt-unit-test`（建模与测试），但**埋点从没设计过**——建模建得再好，没埋到的数据永远出不来。
