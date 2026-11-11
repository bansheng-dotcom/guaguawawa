# 通用 Prompt 工程（capability: prompt-engineering）

> 本能力已升级为技能包，**入口在 [`SKILL.md`](SKILL.md)**。

- 载体：`SKILL.md`（knowledge 卡，`entry: null，无命令门禁`）
- 核心资产：`references/prompt-spec.md`（六段模板 + 输出契约样例 + 注入防护 + 回归集模板 + 8 组 BAD/GOOD）
- 判定：§5 质量门（6 条）+ §6 人工清单 + 双评一致率 ≥80%
- 负向用例：`tests/misuse.md`
- 补的是什么缺口：补的是**AI 链中段**：此前只有 `image-prompt-structure`（图片 prompt），**文本类系统提示词没有规范**——而这些恰恰是全团队每天都在写的东西。
