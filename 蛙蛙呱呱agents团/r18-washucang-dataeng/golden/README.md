# R18 黄金样本：ELT 与质量报告 + 增量与重跑报告

> 由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `elt-quality-report.html` | elt.connection → elt.sync → quality.check → quality.fresh | `connection.json` / `sync.json` / `quality_check.json` / `quality_fresh.json` | 连接器命名/凭据隔离；sync mode/stream/频率；行数/空值/重复/无效值；新鲜度 |
| `incremental-report.html` | incremental.strategy → quality.check → quality.fresh | `incremental_strategy.json` / `quality_check.json` / `quality_fresh.json` | 分区白名单、watermark、幂等键、迟到容忍；质量与新鲜度复核 |

## 怎么重新生成

```bash
python r18-washucang-dataeng/golden/build_golden.py
```

## 验收

```bash
python r18-washucang-dataeng/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`strategy_missing_partition.json` 触发 `strategy.partition`；
  `strategy_duplicate_keys.json` 触发 `strategy.conservation`（运行时引擎实算）。

## 说明

- 质量门禁是阻断器不是报告器：`ok=false` 即阻断下游；
- 回填属高风险运维，必须人工审批；本角色不擅自执行回填。
