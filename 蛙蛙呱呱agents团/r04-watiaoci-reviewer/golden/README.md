# R04 黄金样本：门禁强度评审 + 人工评审工作流

> 由 `golden/build_golden.py` 调用本角色真实评审技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `review-gate-report.html` | gate.audit → facts.check → criteria.review → quality.critique | `gate_audit.json` / `facts_check.json` / `criteria_review.json` / `quality_critique.json` | 7 模式 0 命中（100/solid）、五维事实 0 违例、判据 0 fail、完成声明证据新鲜 |
| `human-review-report.html` | human.package → human.ingest → human.ack → strengths.mark | `human_package.json` / `human_ingest.json` / `human_ack.json` / `strengths_mark.json` | reviewer≠producer、批次契约与逐字回填计划、staged 全 copied 才 ACKED |

## 怎么重新生成

```bash
python r04-watiaoci-reviewer/golden/build_golden.py
```

## 验收

```bash
python r04-watiaoci-reviewer/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`facts_missing_source.json` 触发 `citation_missing`；
  `human_self_review.json` 触发 `self_review`。

## 说明

- 两份报告均为 PASS；评审过程只记录不代改；
- 新增 `references/11-adversarial-review-evidence-ladder.md` 补齐对抗评审与
  三级证据链的方法底座（含来源、边界、误用反例）。
