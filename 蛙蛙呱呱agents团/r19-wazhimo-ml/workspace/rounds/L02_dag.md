# R19 模型工程交付 DAG

- 诉求：紧急评估客服助手模型，准确率>=0.9，P95<200ms，明天发布，500条样本
- 模型：未指定 | 数据集：未指定 | 风险：medium | 紧急：True
- 拓扑合法：**True** | 波次 4 | 总工时 6.5h | 关键路径 4.5h | 并行增益 2.0h

## 阶段与依赖

| 阶段 | 技能 | 依赖 | 工时(h) | 交付物 |
| :--- | :--- | :--- | ---: | :--- |
| 实验登记(audit) | tracking/experiment | — | 1.2 | experiment_id + tracking_uri + 实验类型 |
| 运行追踪(track) | tracking/run | audit | 0.8 | run_id + 指标/参数/环境快照 |
| 评估评分(evaluate) | evaluation/scorer | track | 2.1 | 评估集 + 评分器 + accuracy/F1 精算 |
| 回归验证(regression) | release/regression | track | 2.0 | fail-before/pass-after/existing_green 回归证据 |
| 发布裁决(decide) | release/candidate | evaluate / regression | 0.4 | PASS/BLOCK/NEEDS_REVIEW 三裁决 + 证据链 |

## 并行波次

1. audit
2. track
3. evaluate, regression
4. decide

## 关键路径

audit → track → evaluate → decide
