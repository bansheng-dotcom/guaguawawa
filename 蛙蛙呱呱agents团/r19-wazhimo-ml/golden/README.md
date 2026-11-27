# R19 黄金样本：实验与模型卡包 + 评测与发布包

> 由 `golden/build_golden.py` 调用本角色真实 MLOps 技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `experiment-and-modelcard.html` | tracking.run → evaluation.dataset → registry.register → modelcard.card | `tracking_run.json` / `evaluation_dataset.json` / `registry_register.json` / `modelcard_card.json` | 指标/参数/环境可复现；inputs+expectations；run_id 绑定；用途/限制/风险/许可/偏差 |
| `release-and-eval.html` | evaluation.scorer → release.regression → release.candidate → monitor.drift | `evaluation_scorer.json` / `release_regression.json` / `release_candidate.json` / `monitor_drift.json` | 评分器四要素；fail-before/pass-after；三裁决+证据；漂移阈值与 owner |

## 怎么重新生成

```bash
python r19-wazhimo-ml/golden/build_golden.py
```

## 验收

```bash
python r19-wazhimo-ml/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`dataset_without_expectations.json` 触发 `dataset.expectations`；
  `version_two_production.json` 触发 `version.single_prod`（不可回滚）。

## 说明

- 注册 ≠ 部署；发布候选 ≠ 生产部署；上线/回滚由 R09/R20 执行；
- R19 不产出「模型好不好」的结论，结论来自评测运行。
