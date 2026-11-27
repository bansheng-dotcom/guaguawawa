# R15 蛙供应 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 10 篇 / 约 42.6KB（`check_role_thickness --report` 可复核） |
| 来源 | frappe ERPNext（采购/库存/履约/BOM）、EOQ/安全库存/ROP 公开模型 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 12 个模块（8 个能力域 + `safety-stock`、`fulfill-sim` 两个确定性算子）：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `procurement` | 供应商/RFQ/报价/PO/到货 | 采购主数据、比价、金额与时序、到货约束 |
| 2 | `inventory` | 物料/仓库/Bin/库存交易 | 单位/计价/负库存/守恒 |
| 3 | `fulfillment` | 销售订单/发货单 | 状态双轴、金额恒等、超发门禁 |
| 4 | `production` | BOM/工单 | 配方展开与物料需求 |
| 5 | `finance` | 发票/付款 | 应付应收与状态 |
| 6 | `masterdata` | 主数据 | 字段与权限 |
| 7 | `report` | 指标 | 供应链报表 |
| 8 | `safety-stock` | σ/LT/z | 安全库存 SS |
| 9 | `fulfill-sim` | 需求/提前期/产能 | 履约率与缺货仿真 |

黄金链：`safety-stock → inventory.bin → procurement.purchase_order`；
`fulfillment.sales_order → delivery → procurement.receipt`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（36 个） | 每动作配对，脏件断言被拦 |
| 案例包 | `cases/`（18 个文件，含 `stockout-risk.md`） | 安全库存 SOP |
| 黄金成品 | `golden/replenishment-advice.html`、`golden/fulfillment-report.html` | 含夹具 sha256 与 28 条门禁 |
| 方法与阈值 | `experience/`、`ERP_SPEC.md` | SS/ROP 口径外置 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 负库存禁止 | `inventory.bin` → `bin.negative_stock` | BLOCKER |
| 预计量守恒 | `inventory.bin` → `bin.projected` | BLOCKER |
| 物料单位/计价/交期白名单 | `inventory.item` → `item.*` | BLOCKER |
| 采购金额恒等与时序 | `procurement.purchase_order` → `po.*` | FAIL |
| 到货不得超过订单 | `procurement.receipt` → `receipt.*` | FAIL |
| 发货不得超订单量 | `fulfillment.delivery` → `delivery.over_delivery` | BLOCKER |
| 订单状态双轴一致 | `fulfillment.sales_order` → `so.axis_consistency` | FAIL |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 覆盖全部动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（负库存、超发） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r15-wagongying-erp/golden/build_golden.py`
- 产物：`replenishment-advice.html`（12 条门禁，0 未过）、
  `fulfillment-report.html`（16 条门禁，0 未过）
- 命令：`python r15-wagongying-erp/run_tests.py`
- 结果：全绿（含厚度样本 T16）

## 7. 已知边界

- 安全库存是统计量，需结合供应商准时率与资金占用复核；
- 履约仿真为确定性模型，不替代现场实盘；
- 只出建议与校验，不擅自下单/付款；超发/超收须人工审批。
