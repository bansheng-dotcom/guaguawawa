# R19 三维发布方案决策看板

- 推荐：**SCN_B_STEADY** 稳健基准发布版 (Steady Release)
- 权重：速度 0.2 / 证据 0.35 / 风险 0.3 / 成本 0.15
- 敏感性（±20% 权重）：排名稳定

| 方案 | 工期(天) | 样本量 | 门禁数 | ROI | 推荐 |
| :--- | ---: | ---: | ---: | ---: | :---: |
| SCN_A_QUICK<br>极速轻量实验版 (Quick Experiment) | 0.5 | 100 | 3/8 | 6.85 | — |
| SCN_B_STEADY<br>稳健基准发布版 (Steady Release) | 1.5 | 500 | 8/8 | 8.4 | ⭐ 推荐 |
| SCN_C_STRICT<br>严苛高保障版 (Strict Assurance) | 3.0 | 1000 | 8/8 | 7.65 | — |

## 方案要点

### SCN_A_QUICK · 极速轻量实验版 (Quick Experiment)

- 定位：小样本快速试跑，只过 3 维门禁，适合探索期与内部实验
- 交付物：experiment_log, evaluation(小样本), exploratory_report
- 风险/成本：medium / low

### SCN_B_STEADY · 稳健基准发布版 (Steady Release)

- 定位：全量评估 + fail-before/pass-after 回归 + 8 维门禁，适合正式发布
- 交付物：evaluation, regression_report, release_candidate, ml_bundle + SARIF, modelcard
- 风险/成本：low / medium

### SCN_C_STRICT · 严苛高保障版 (Strict Assurance)

- 定位：双倍样本 + 红队复核 + 人工签核，适合高风险/金融医疗场景
- 交付物：evaluation(双倍样本), regression_report, redteam_review, release_candidate, human_signoff, modelcard
- 风险/成本：low / high
