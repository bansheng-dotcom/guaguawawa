# 发布与变更管理（capability: release-change-management）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（knowledge 卡，`entry: null，无命令门禁`）
- 核心资产：`references/release-runbook.md`（变更分级表 + 回滚预案模板 + 灰度节奏 + 8 组 BAD/GOOD）
- 判定：§5 质量门（6 条）+ §6 人工清单 + 双评一致率 ≥80%
- 负向用例：`tests/misuse.md`
- 补的是什么缺口：补的是**运维链起点**：此前 r20 只有 `incident-response`（出事之后），**变更管理全空**——而事故的起点几乎全在变更上。
