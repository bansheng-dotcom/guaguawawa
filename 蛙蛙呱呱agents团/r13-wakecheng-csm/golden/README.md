# R13 黄金样本：客户健康包 + VOC 报告

> 由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `customer-health-pack.html` | health.health → support.inbox | `health.json` / `inbox.json` | 四维加权健康分、at_risk 归因、续约窗口；渠道/状态/SLA/CSAT |
| `voc-report.html` | voc.voc → health.risk | `voc.json` / `risk.json` | NPS 三桶实算、样本量门槛、主题 ≥3 次提及；单客分带一致 |

## 怎么重新生成

```bash
python r13-wakecheng-csm/golden/build_golden.py
```

## 验收

```bash
python r13-wakecheng-csm/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`health_anonymous.json` 触发 `health.name`；
  `risk_single_dim_collapse.json` 触发 `risk.band_consistency`。

## 说明

- 健康分权重与分带外置在 `experience/thresholds.json`（30/25/25/20；
  healthy≥75 / watch≥50 / at_risk<50）；
- R13 不擅自承诺退款/赔偿，商务承诺须 R03/创始人审批。
