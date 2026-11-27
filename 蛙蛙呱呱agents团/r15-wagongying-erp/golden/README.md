# R15 黄金样本：补货建议 + 履约报告

> 由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具与确定性算子参数。

| 样本 | 技能链 | 夹具/参数 | 验收点 |
|---|---|---|---|
| `replenishment-advice.html` | safety-stock(σ=12,LT=7,z=1.65) → inventory.bin → procurement.purchase_order | `bin.json` / `purchase_order.json` | SS=z×σ×√LT；Bin 预计量守恒、无负库存；采购单金额恒等与时序 |
| `fulfillment-report.html` | fulfillment.sales_order → fulfillment.delivery → procurement.receipt | `sales_order.json` / `delivery.json` / `receipt.json` | 订单三轴自洽；不超发；到货数量约束 |

## 怎么重新生成

```bash
python r15-wagongying-erp/golden/build_golden.py
```

## 验收

```bash
python r15-wagongying-erp/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`bin_negative.json` 触发 `bin.negative_stock`；
  `delivery_over.json` 触发 `delivery.over_delivery`。

## 说明

- 安全库存与 ROP 为确定性统计算子，不含随机；履约仿真另走 `fulfill-sim`；
- R15 只出建议与校验，不擅自下单/付款；超发/超收须人工审批。
