# R15 蛙供应 · ERP 与供应链运营官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/inventory-planner/SKILL.md
>


把「从采购、库存、销售履约到财务业务台账的 ERP 供应链链」做成**本地可运行、可确定性校验**的角色 Agent。
不真下单采购 / 不真付款 / 不真改库存 / 不调整历史账目，而是把「该定什么口径、什么约束、什么证据」
落成白名单 + 确定性算术 + 门禁。

来源仓库：`frappe__erpnext`（Purchase Order / Supplier / Item / Warehouse / Bin /
Purchase Receipt / Sales Order / Delivery Note / BOM / Material Request /
Sales-Purchase Invoice / Payment Entry 的 doctype status Select 字段与必填字段）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 采购与供应商 | `procurement` | `supplier` / `rfq` / `quotation` / `purchase_order` / `receipt` | 供应商类型 3 枚举 + 账期 ≤180 天；询价 ≥2 家；报价/订单恒等式 Σ(qty×rate)；PO 状态 10 枚举 + 交货≥下单日期；收货状态 6 枚举 + 超收容差 0 |
| 库存与仓库 | `inventory` | `item` / `warehouse` / `bin` / `stock_entry` | 物料必填 + UOM 白名单 + 计价方法 4 枚举；仓库层级；Bin 负库存默认禁止 + 预计量守恒（actual+ordered+planned−reserved）；库存交易用途 6 枚举 |
| 销售与履约记录 | `fulfillment` | `sales_order` / `delivery` | SO 状态 9 枚举 + 发货/开票双轴 + Completed 须全交付全开票 + 恒等式；发货状态 5 枚举 + 超发容差 0 |
| 生产/服务资源 | `production` | `bom` / `material_request` | BOM 配方必填 + 用量为正；物料请求用途 5 枚举 + 状态 11 枚举 |
| ERP财务业务接口 | `finance` | `invoice` / `payment` | 发票状态 9 枚举 + 恒等式 + 行项目必填；付款单状态 3 枚举 + 金额非负 + 必须声明授权（不代付款） |
| 主数据与权限 | `masterdata` | `master_data` / `permission` | 主数据类型 6 枚举 + 编码白名单 + 同类型唯一；角色 6 枚举 + 动作 7 枚举 + SoD 冲突识别 + 高危动作须审计备注 |
| 运营报表 | `report` | `report` | 报表类型 4 枚举 + 周期口径（YYYY/YYYY-MM/YYYY-Qn）+ KPI 三要素（值/分子/分母）可复算 |

共 **7 技能 / 18 动作**（18 个门禁）。

## 协作契约

- **inputs**：`order` + `sop`
- **outputs**：`purchase_order` + `inventory_ledger`
- 意图路由（`agent.py run --task`）：报价/quotation → procurement/quotation；询价/rfq → procurement/rfq；
  收货/到货/入库单 → procurement/receipt；采购/下单/买 → procurement/purchase_order；供应商 → procurement/supplier；
  BOM/配方 → production/bom；物料请求/缺料/请购 → production/material_request；
  发票/应收应付 → finance/invoice；付款/打款 → finance/payment；权限/职责分离 → masterdata/permission；
  主数据/编码 → masterdata/master_data；报表/KPI/台账 → report/report；发货/交付 → fulfillment/delivery；
  销售订单 → fulfillment/sales_order；库存明细 → inventory/bin；出入库/调拨 → inventory/stock_entry；
  仓库 → inventory/warehouse；物料/品号 → inventory/item；兜底 → `procurement/purchase_order`。

## 运行

```bash
python agent.py manifest                                   # 契约 + 7 技能清单
python agent.py demo                                       # 生成示例 ERP 工件
python agent.py procurement purchase_order --input examples/purchase_order.json
python agent.py inventory bin --input examples/bin.json
python agent.py fulfillment sales_order --input examples/sales_order.json
python agent.py production bom --input examples/bom.json
python agent.py finance invoice --input examples/invoice.json
python agent.py masterdata permission --input examples/permission.json
python agent.py report report --input examples/report.json
python agent.py harness purchase_order --input examples/purchase_order.json   # 确定性门禁
python agent.py contract list
python agent.py case list
python verify_loop.py                                       # 36 行闭环矩阵
python run_tests.py                                         # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **财务报表口径 / 税务结论 / 合同效力 / 法律意见**归 R03；**数据分析结论**归 R06；
  **自动化实现（n8n/Webhook/重试）**归 R17；**交易履约（订单/支付）**归 R14。
- 本角色只产出**ERP 供应链工件**（采购单、询价单、收货单、库存台账、发货单、BOM、
  物料请求、发票、付款单、主数据、权限矩阵、运营报表），不做财务结论、不做法律判断、
  不实现自动化、不真下单采购/付款。
- **红线（不可越）**：
  1. 不擅自采购、不擅自下单、不代付款、不发起付款。
  2. 不擅自改库存、不调整历史账目、不冲销历史凭证、不反记账。
  3. 凭据（`api_key` / `secret` / `token` / `password` / `private_key` / 私钥 / 密钥）
     绝不出现在任何输出中。
  4. 涉及资金流动 / 库存变动 / 历史调整的动作一律产出**请求工件 + handoff 声明**，由人工授权后执行。

## Honest capability status and safe local execution

`manifest` reports local ledger validation as `real` and external ERP mutation as `blocked`. Run `python agent.py local --input <ledger.csv-or-json> --output <result.json>` for a local stock ledger conservation check. It does not mutate inventory or call ERP.


- 干净数据 → `ok=true` / exit 0；脏数据（枚举越界 / 恒等式不闭合 / 超收超发 / 负库存 /
  时序倒退 / 周期口径非法 / KPI 不可复算 / 无授权付款）→ `ok=false` / exit 1。
- 对抗评审五检查：`contract` / `credential_gate` / `execution_gate` / `scope_boundary` /
  `concrete_artifact`；失败按类别 route 回 writer（凭据泄露 / 越权执行 / 越界）或
  controller（无工件 / 无价值），类别为 `credential_leak` / `unauthorized_exec` /
  `scope_overlap` / `artifact_not_concrete` / `no_report_value`。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `purchase-over-receipt` 补充超收容差与让步接收授权、`inventory-negative-stock`
  补充负库存开关与盘点调整路径）。
- Windows GBK 控制台：所有输出经 UTF-8 重配置，verify_loop 使用 `[OK]` / `[XX]` ASCII 标记。
