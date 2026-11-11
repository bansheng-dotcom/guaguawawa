# R14 蛙交易 · 交易与收入履约官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/close-plan/SKILL.md
>


把「从商品上架到收入事件登记的交易履约链」做成**本地可运行、可确定性校验**的角色 Agent。
不真开支付账户 / 不真扣款 / 不真退款 / 不代签，而是把「该定什么口径、什么约束、什么证据」
落成白名单 + 确定性算术 + 门禁。

来源仓库：`medusajs__medusa`（ProductStatus / OrderStatus / PaymentStatus / FulfillmentStatus）、
`getlago__lago`（AGGREGATION_TYPES / CHARGE_MODELS / INTERVALS / Invoice STATUS）、
`stripe__stripe-node`（PaymentIntent.status / Refund / Webhook 幂等）、
`documenso__documenso`（DocumentStatus / RecipientRole / SigningStatus）、
`alextselegidis__easyappointments`（预约状态与 customer/provider/service 三元组）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 商品电商后端 | `catalog` | `product` / `price` | 商品三必填 + ProductStatus 白名单 + 类型白名单 + 价格非负；单品价格复查 |
| 订单与购物车 | `order` | `cart` / `order` | 行项目三必填 + 行数 ≤50 + 小计恒等式 Σ(单价×数量)；订单三态（Order/Payment/Fulfillment）分轴枚举 + 跨轴矛盾识别 |
| 订阅计量计费 | `billing` | `plan` / `usage` / `invoice` | 聚合类型 7 枚举 + 计费模型 6 枚举 + 周期 4 枚举 + `custom_agg` 必须声明表达式；用量必填；账单恒等式 total == Σ行项目 |
| 支付集成 | `payment` | `payment_intent` / `refund` | PI 状态 7 枚举 + 金额下限 50（最小单位，防元分混淆）+ 成功态幂等键；退款比例 ≤1.0 + 前置状态可退集合 |
| 电子签审计 | `signature` | `document` / `signing` | DocumentStatus 3 枚举 + RecipientRole 5 枚举 + 邮箱非空；COMPLETED 须全员（SIGNER/APPROVER）签署 + DRAFT 不得含已签（防伪造） |
| 服务预约 | `appointment` | `appointment` / `calendar` | 五元组必填 + 时长 ≤240min + 时序正确 + 状态 6 枚举；日历重叠检测（含 5min 缓冲） |
| 交易状态编排 | `workflow` | `state` / `transition` | 四实体状态白名单 + 声明式迁移表（`_VALID_TRANSITIONS`）+ 终态不可逆 + 回滚边禁止 |
| 收入数据接口 | `revenue` | `events` / `webhook` | 事件类型 9 枚举 + 三要素 + 时间戳单调非递减 + 金额汇总；回调重试 0–5 + 对账声明 + 高风险事件审批声明 |
| 选品评分 | `selection` | `score` / `profit` | 五维 1–5 分 + 上游权重 30/20/25/30/15 合计 120% 已归一化 + 综合分四档；推荐品必须有假设卡（SP-09）；毛利率 <30% 警告、<15% 建议放弃 |

共 **9 技能 / 19 动作**（19 个门禁）。

## 协作契约

- **inputs**：`package` + `quotation`
- **outputs**：`order` + `payment_status`
- 意图路由（`agent.py run --task`）：签署/电子签/审计包 → signature；预约/日历/时段 → appointment；
  订阅/计量/计费/账单/用量 → billing；状态机/迁移/退款状态/履约 → workflow；
  退款/退钱/退单 → payment/refund；支付/支付意图/回调 → payment/payment_intent；
  事件表/收入数据/对账/webhook → revenue；商品/价格/购物车/订单 → order；兜底 → `order/order`。

## 运行

```bash
python agent.py manifest                                   # 契约 + 8 技能清单
python agent.py demo                                       # 生成示例交易工件
python agent.py catalog product --input examples/product.json
python agent.py order cart      --input examples/cart.json
python agent.py billing invoice --input examples/invoice.json
python agent.py payment refund  --input examples/refund.json
python agent.py signature signing --input examples/signing.json
python agent.py appointment calendar --input examples/calendar.json
python agent.py workflow transition  --input examples/transition.json
python agent.py revenue events   --input examples/events.json
python agent.py harness refund --input examples/refund.json   # 确定性门禁
python agent.py contract list
python agent.py case list
python verify_loop.py                                       # 34 行闭环矩阵
python run_tests.py                                         # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **汇率 / 税务 / 合同效力 / 法律意见**归 R03；**财务报表口径**归 R03。
- **库存与采购**归 R15；**自动化实现（n8n / Webhook / 重试机制）**归 R17。
- 本角色只产出**交易工件**（订单、账单、支付意图、退款请求、签署审计、预约、事件需求），
  不产出财务结论、不做法律判断、不实现自动化。
- **红线（不可越）**：
  1. 不擅自开通支付账户、配置真实密钥、发起扣款、发起退款、代签合同。
  2. 凭据（`api_key` / `secret` / `token` / `password` / 私钥 / 密钥）绝不出现在任何输出中。
  3. 涉及资金真实流动的动作一律产出**请求工件 + handoff 声明**，由人工授权后执行。

## Honest capability status and safe local execution

`manifest` reports `capability_status`: local transition/idempotency/money validation is `real`; external payment is `blocked`. `python agent.py local --input <order.json>` validates local data only; it never charges. Result and bridged report carry capability status. Missing external credentials or unreachable systems are blocked, not success.


- 干净数据 → `ok=true` / exit 0；脏数据（枚举越界 / 恒等式不闭合 / 超额退款 / 时序倒退 /
  双重预订 / 非法迁移 / 伪造签署）→ `ok=false` / exit 1。
- 对抗评审五检查：`contract` / `credential_gate` / `execution_gate` / `scope_boundary` /
  `concrete_artifact`；失败按类别 route 回 writer（凭据泄露 / 越权执行 / 越界）或
  controller（无工件 / 无价值），类别为 `credential_leak` / `unauthorized_exec` /
  `scope_overlap` / `artifact_not_concrete` / `no_report_value`。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `order-refund-dispute` 补充争议履约状态集与授权比例门槛）。
- Windows GBK 控制台：所有输出经 UTF-8 重配置，verify_loop 使用 `[OK]` / `[XX]` ASCII 标记。

---

## 外部能力（可选，见 references/external/）

以下外部能力（Trae 插件 / WorkBuddy 技能）的入口文档已拷入 `references/external/`，深层 references 与脚本仍以登记源目录为准：

- `omnichannel-commerce-assistant` · 全渠道电商经营诊断（技能；消费方：r12, r02）
- `smart-product-selector` · 智能选品分析（技能；消费方：r01, r06, r12）

就绪状态：`python guagua.py capabilities --role r14 --probe`；
MCP 类需要 MCP 客户端接入，本团队 CLI 不直连。
