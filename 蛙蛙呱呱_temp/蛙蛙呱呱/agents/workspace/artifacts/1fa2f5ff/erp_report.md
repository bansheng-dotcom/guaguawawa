# 蛙供应 · procurement/purchase_order
> 这单货要补采购，帮我看这张采购订单合不合规、能不能下单 

**结论**：next=ERP 工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 8/8 项 |
| next | **ERP 工件通过全部门禁，可进入授权与交接** | 输出字段 |
| po_count | **1** | 输出字段 |
| total | **700.00** | 输出字段 |

## 1. po_count
> po_count 的判定与证据是什么？

- **po_count：**1

## 2. total
> total 的判定与证据是什么？

- **total：**700.00

## 3. line_item_count
> line_item_count 的判定与证据是什么？

- **line_item_count：**2

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**采购订单 PO-2026-001（华东原料供应商）：To Receive、2 行、合计 700.0

## 口径与边界

- **来源：**技能 procurement/purchase_order 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
