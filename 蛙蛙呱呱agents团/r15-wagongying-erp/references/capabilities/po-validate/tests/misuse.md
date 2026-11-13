# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/po-validate/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 采购单总额 ≠ 行项目之和 | `po.grand_total` | ✅ exit=1（`examples/purchase_order_dirty.json`） |
| MU-02 | 采购单日期非法 | `po.date_order` | ✅ exit=1（同上） |
| MU-03 | 收货数量超过订单数量 | `receipt.over_receipt` | ✅ exit=1（`examples/receipt_dirty.json`） |
| MU-04 | 库存分录用途自创 | `stock_entry.purpose` | ✅ exit=1（`examples/stock_entry_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-05 | 收货单不填关联采购单号 | 无法判超收 | §6 关联检查 |
| MU-06 | 单价变更无变更单 | 无法审计 | §6 + 三单匹配 |
| MU-07 | 三单不匹配就改发票凑平 | 抹平差异 | §6 + `r03` |
| MU-08 | 盘盈盘亏直接调数量 | 无原因留痕 | §6 |
| MU-09 | 修改历史单据 | 账永久失真 | §7 EX-09 |
| MU-10 | 单据校验靠肉眼 | 漏检 | §6 跑门禁 |
| MU-11 | 供应商未准入就下单 | 合规风险 | §8 + `r03` |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 每次改 `harness.py purchase_order/receipt/stock_entry` 后重跑 `--self-test`
- [ ] 三单（订单/收货/发票）数量与单价差异都解释过
- [ ] 历史错误一律走冲正，没有直接改单据

> **纪律**：库存账对不平，99% 不是算术问题，是**某张单据当初就该被拦下**。
