# R14 蛙交易 · 厚度自述（T12 Tier C：补机制）

> 按升级方案 §16「厚度包」与 §17.1 T12 逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 11 篇 / 65.9KB（商品目录、订单、计费、支付、签署、预约、工作流、收入等） |
| 来源 | 每篇列公开方法来源（订单状态机、幂等键、Saga/补偿、对账口径）与适用边界 |
| 误用说明 | 每篇有「误用反例」；对应门禁在 `harness.py`（17 项）与 `commerce_fsm.py` |
| 能力卡 | `references/capabilities/`：order-lifecycle、pricing-strategy、smart-product-selector |

## 2. 生产层

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1–10 | `skills/s01..s10` | 目录/订单/计费/支付/签署/预约/工作流/收入/选品/弹性 | 交易工件与门禁结论 |
| 11 | `local_exec.py` | 本地购物车 | 金额/数量/幂等键核验（不扣款） |
| 12 | `verify_loop.py` | 34 行闭环矩阵 | 契约 + 评审 |
| 13 | **`commerce_fsm.py`（T12 新增）** | ops 链 / 订单+支付流水 | 状态机链结果、对账分类、2 份 HTML |

`commerce_fsm.py` 实现：6 态迁移、幂等键去重、防重复扣款、五类对账差异分类。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 三条交易链 | `golden/commerce-run.json` | 正常/退款/超时重放，终态均 `closed` |
| 对账夹具 | `commerce_fsm.RECON_ORDERS/PAYMENTS` | 5 单 × 6 流水，预埋 5 类差异 |
| 黄金报告 | `golden/*.html` | 状态机报告、对账报告 |

## 4. 门禁层

| 错误码 | 判据 | 失败后果 |
|---|---|---|
| `T01_ILLEGAL_TRANSITION` | 迁移必须在 `TRANSITIONS` 表内 | 拒绝并保持原状态 |
| `T02_MISSING_IDEMPOTENCY_KEY` | 资金/状态动作必须有幂等键 | 拒绝 |
| `T03_DUPLICATE_CHARGE` | 同键必须同单同额，否则视为重复扣款 | 拒绝第二笔 |
| `T04_AMOUNT_MISMATCH` | 支付=订单金额；退款≤可退 | 拒绝 |
| `R01..R05` | 对账五类差异 | 差异 >0 即 `ok=false`，逐条派单 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 机制单测（pytest） | `tests/test_mechanism.py` | 9 条（三链/非法迁移/幂等/T03/T02/金额/对账/误用/HTML） |
| 角色端到端 | `run_tests.py` §T12 | 7 条 |
| 黄金成品 | `golden/*.html` | 2 份 |
| 误用反例 | `misuse/*.json` | 2 份（非法迁移 / 重复扣款） |
| 全量 | `python run_tests.py` | 173 / 173 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r14-wajiaoyi-commerce/run_tests.py`
- 结果：通过 173 / 173，全绿
- 机制：`python commerce_fsm.py goldens` → 三链 `ok=true`，对账 `diff_total=5`
- 呈现：`python scripts/check_report_presentation.py r14-wajiaoyi-commerce/golden/*.html` → 2/2 PASS

## 7. 已知边界

- 不接真实支付渠道，`charge` 只写本地账本，`capability_status` 仍为「不扣款」；
- 幂等键只在单进程账本内去重，跨进程需外部存储；
- 对账不含退款流水、手续费与跨时区时间窗；
- 部分退款后订单停在 `paid`，只有退满才转 `refunded`（业务口径可再细化）。
