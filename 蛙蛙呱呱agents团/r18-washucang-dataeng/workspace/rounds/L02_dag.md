# 数据工程交付 DAG · 68e72e43966b

- 原始意图：把 orders 和 dwd_orders 最近30天的增量数据做成看板，2小时内要新鲜，空值率不超过0.05
- 源表：orders, dwd_orders（2 张）
- 时间窗：30 天（来源：最近30天）
- 新鲜度 SLA：2.0 小时
- 模式：incremental · 目的地：dashboard
- 总工时：35.7 h（4.46 人天）
- 关键路径：01_profile → 02_model → 03_orchestrate → 04_gate → 05_publish（35.7 h）

## 阶段

| 阶段 | 标题 | 工时(h) | 门禁 |
|---|---|---|---|
| 01_profile | 数据探查与审计 | 4.2 | 源表可达 + 字段画像 + 空值/重复基线 |
| 02_model | 建模与转换 | 12.6 | 物化方式合法 + ref 不悬空 + 不自引用 |
| 03_orchestrate | 编排与调度 | 8.4 | DAG 无环 + 任务状态无 failed + 重试≤3 |
| 04_gate | 质量门禁 | 6.3 | 空值率≤0.10 + 重复率≤0.05 + 新鲜度≤SLA |
| 05_publish | 发布与交付 | 4.2 | 伴生 bundle/SARIF 落盘 + handoff 声明 |

## 依赖边

- 01_profile → 02_model：源表画像决定建模口径
- 01_profile → 03_orchestrate：源表分区字段决定调度窗口
- 02_model → 03_orchestrate：编排依赖模型产物
- 02_model → 04_gate：门禁绑定模型输出列
- 03_orchestrate → 04_gate：门禁需在调度后按批次执行
- 04_gate → 05_publish：门禁不过不得发布
