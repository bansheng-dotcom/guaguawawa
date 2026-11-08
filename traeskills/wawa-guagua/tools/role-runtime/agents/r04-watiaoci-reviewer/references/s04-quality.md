# S04 工作质量批判与迭代收敛（critique / converge）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/code-review/SKILL.md
>


## 方法论（来源 harness-engineering / quality）

对生产方的「完成声明」做对抗性批判，三查：

1. **hedge 词**：should / probably / seems to / I believe 这类含糊表述
   ——评审语境里等于没说；
2. **证据链**：声明「完成」却不给本会话新鲜证据（Iron Law：
   完成声明必须有当次运行的可复现证据）；
3. **绝对词**：「全部通过」「生产级」「完美」——没有全量证据支撑就是吹牛。

批判的目标不是骂，是**收敛**：多轮 findings 数量不再下降，
说明修复停滞，该升级人工介入（human/S07）。

## 可执行口径

- critique 三查全部确定性判定：
  - hedge 命中 `quality.hedge_words` → error；
  - 完成声明无 evidence_refs → error（对照键见 `review.evidence_keys`）；
  - 绝对词命中 `quality.absolutist_words` 且无证据 → error；
  - severities 枚举外置在 `quality.severities`；
  - findings 结构照 soundness schema：
    {id, check, title, detail, severity, autoFixable, suggestedFix, evidence}——
    每条 finding 必须能定位到检查与证据。
- converge：两轮 findings 总数 t1 → t2，
  **t2 ≥ t1 即 converged**（不再下降=不再有新增修复价值的信号）；
  还在降 → ITERATING（继续修）。

## 已验证算例

- `cases/landing-acceptance/` 第 2 步：3 条完成声明 → 1 verified / 4 error，
  verdict=FAIL；第 4 步 R08 修复后复评 → 2 声明 / 2 verified / 0 error / PASS；
  第 5 步 converge：4 → 0，还在下降 → ITERATING；
- `examples/quality_critique_dirty.json`：hedge + 无证据 + 绝对词四连，
  三查各打各的 error。

## 实战踩坑

- hedge 扫描**只扫结论字段**（`review.conclusion_keys`：summary /
  conclusion / overall_note 等），不扫 msg / detail——
  检查描述里引用用户原文「should be fine」会被误伤成禁词（R06 的教训）；
- converge 的方向别写反：数字下降是好事，**持平**才是 converged；
- critique 的 finding 别只给「问题」不给「修法」：suggestedFix 必填。
