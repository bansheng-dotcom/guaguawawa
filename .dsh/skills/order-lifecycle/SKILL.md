---
name: order-lifecycle
description: 订单生命周期技能包。把"下单→支付→履约→退款"做成可校验的三态状态机：订单状态、支付状态、履约状态必须互不矛盾，迁移必须合法且终态不可再动，退款必须满足必填项、金额比例与前置状态约束。当需要校验订单三态一致性、设计退款与部分退款、排查状态卡死、或定义状态迁移白名单时使用。不负责出财务意见、不执行真实支付、不做税务与合规判断。
license: MIT
compatibility: 通用。门禁在角色根目录 harness.py（order / cart / refund / state / transition / events / webhook 七道，Python 3.10+、零第三方依赖）；无 Python 环境时按 §8 转人工七项核对，此时不得标记订单可结算。
metadata:
  owner: r14
  version: "2.0.0"
  kind: skill
  triggers: "订单状态,三态一致性,退款,部分退款,状态机,状态迁移,幂等"
  verify: python harness.py order --input <订单.json>
  entry: "python agent.py order order --input <订单.json>"
  consumers: "r03,r13,r15"
  supersedes: README.md
---

<!-- 本文件由 scripts/sync_dsh_skills.py 生成，请勿手改；改源包后重跑同步 -->

# 订单生命周期（Order Lifecycle）

> 一句话定位：**这个技能存在的意义，是防止"订单四个状态各自都能看，合起来是错的"**。
> 电商事故里最难查的一类不是"少了一笔钱"，而是**状态自相矛盾**：
> 已全额退款却显示"已完成"、退款金额超过订单总额、终态订单还在被迁移、退款前状态本该是"已取消"却是"处理中"。
> 这些都不会报错，但会让对账永远对不平。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「这笔订单状态对不对」「为什么这单退不了款」
- 「退款金额怎么算」「部分退款要改哪些状态」
- 「订单卡在 processing 不动了」「能不能从 refunded 再改回去」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 这笔退款要不要批 / 财务影响 | `r03` 财务合规官 | 本技能只判状态合法，不出财务意见 |
| 客户投诉怎么安抚 / 补偿话术 | `r13` 客户成功 | 那是客户运营，不是状态机 |
| 库存怎么扣减 / 补货 | `r15` 供应链 | 库存账在 ERP 侧 |
| 支付渠道对账差异 | `r03` + 渠道对账单 | 本技能不接真实支付接口 |

**最小可开工输入**：**一笔订单的三态**（order / payment / fulfillment）+ 金额，或**一次状态迁移**（from → to）。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 订单号 | 必需 | 无法推断；缺失即 `order.id` BLOCKER |
| `status` / `payment_status` / `fulfillment_status` | 必需 | 缺任一则无法判三态一致性，必须问 |
| 订单总额 `total` | 必需 | 缺失则无法判退款比例 |
| 退款金额与前置状态 | 退款场景必需 | 缺则 `refund.required` BLOCKER |
| 迁移 `kind` / `from_status` / `to_status` | 迁移场景必需 | 缺则无法判合法性 |

**追问纪律**：最多一轮，只问**缺哪个状态字段**与**金额**。其余按白名单默认执行。

---

## §3 执行流水线（Workflow）

### Step 1 · 三态分离（先认清有三个独立状态）
订单不是"一个状态"，是**三个正交状态**：

| 维度 | 取值（白名单） | 谁推进 |
|---|---|---|
| `status`（订单） | `pending` / `paid` / `completed` / `canceled` | 订单编排 |
| `payment_status`（支付） | `pending` / `authorized` / `captured` / `refunded` / `failed` | 支付集成 |
| `fulfillment_status`（履约） | `unfulfilled` / `partial` / `fulfilled` / `delivered` | 仓储物流 |

**任何字段不在白名单 → BLOCKER**。白名单外不可能是"新状态"，只能是笔误或越权写入。

- **产出**：三态字段各自校验结果
- **过关条件**：三个字段全部在白名单内

### Step 2 · 三态一致性（本技能的核心价值）
逐条比对，找**互斥组合**：

| 矛盾组合 | 为什么错 |
|---|---|
| `payment_status=refunded` 且 `status=completed` | 已全额退款却算完成，收入虚增 |
| `fulfillment_status=delivered` 且 `status=pending` | 货已到但订单未支付，履约先于支付 |
| `payment_status=failed` 且 `status=paid` | 支付失败却标记已付 |
| `status=canceled` 且 `payment_status=captured` | 取消了却仍持仓，钱没退 |

- **产出**：`order.consistency` 结论
- **过关条件**：无矛盾组合；`total > 0`

### Step 3 · 迁移合法性（只走白名单路径）
每次状态变更都作为一条 `transition` 单独校验：
- `kind` 在实体白名单内（`order` / `payment` / `fulfillment` / `refund`）；
- `from_status` 是合法起点；
- `to_status` 在**允许迁移列表**内；
- **终态不可再迁移**（见 Step 4）。

**迁移必须显式设计，不能靠代码里 if/else 临时补**。没写进白名单的路径一律视为非法。

- **产出**：`transition.*` 结论
- **过关条件**：四条全过

### Step 4 · 终态保护（进去就出不来）
`completed` / `canceled` / `refunded` / `delivered` 属**终态**：不得再有后续动作。
若要"重开"，正确的做法不是改状态——而是**新建一笔关联订单**（换货单/补偿单），保留原单不动。

> 直接改终态会让历史对账永久失真。这是审计上不可接受的。

- **产出**：`workflow.terminal` 结论
- **过关条件**：终态实体无后续动作

### Step 5 · 退款约束（四条一起看）
| 检查 | 规则 |
|---|---|
| `refund.required` | 必填项齐备（金额、原因、`payment_intent` 等） |
| `refund.amount` | 金额 > 0 |
| `refund.ratio` | **退款比例 ≤ 1.0**（累计退款不得超订单总额） |
| `refund.prior` | **前置状态可退款**（`canceled` 等状态不可退款） |

**部分退款的正确做法**：拆分退款单，每笔独立记录，累计比例由系统汇总校验——
不要在同一个 `refund` 记录里反复改金额。

- **产出**：`refund.*` 结论
- **过关条件**：四项全过

### Step 6 · 幂等与事件（防重复扣款/重复发货）
- 每个变更动作带**幂等键**（订单号 + 动作 + 序号）；
- `events` 逐条校验事件结构与顺序；
- `webhook` 校验签名与重放窗口。

重试是常态，**幂等不是优化项，是正确性要求**：同一次重试不能产生第二笔扣款或第二次发货。

- **产出**：`events` / `webhook` 结论
- **过关条件**：两者退出码 0

### Step 7 · 跑门禁
```bash
python harness.py order       --input <订单.json>
python harness.py state       --input <状态快照.json>
python harness.py transition  --input <迁移.json>
python harness.py refund      --input <退款.json>
python harness.py cart        --input <购物车.json>
python harness.py events      --input <事件流.json>
python harness.py webhook     --input <回调.json>
```
七道门禁各自独立；哪一道跑不了，就在交付物里标注"该项未验"。

- **过关条件**：本次涉及的每一道退出码 0

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 订单三态校验结果 | 终端 JSON | `harness.py order` 输出 |
| 2 | 状态机定义（实体 × 合法迁移白名单） | `.md` | `references/order-state-machine.md` §二 |
| 3 | 退款规则说明（含部分退款） | `.md` | `references/order-state-machine.md` §四 |
| 4 | 迁移与终态保护结论 | 终端 JSON | `harness.py transition` / `state` |
| 5 | 幂等与事件校验结论 | 终端 JSON | `harness.py events` / `webhook` |

- 命名：`order_<订单号>_<YYYYMMDD>.json`
- **状态机定义必须落盘**；口头约定"这样改可以"在下次接口改动时必然失效。

---

## §5 质量门（一票否决，不过不给交付）

1. **订单号非空**（`order.id`）；
2. **三个状态字段都在白名单内**（`order.status` / `payment_status` / `fulfillment_status`）；
3. **三态无矛盾组合**（`order.consistency`）；
4. **订单总额 > 0**（`order.total`）；
5. **每次迁移走白名单路径**（`transition.to`）；
6. **终态不再迁移、终态实体无后续动作**（`transition.terminal` / `workflow.terminal`）；
7. **退款四项全过**：必填 / 金额 > 0 / 比例 ≤ 1.0 / 前置状态可退。

> 验收命令：`python harness.py order --input <订单.json>`（及本次涉及的其它门禁）
> 命中任一项不过 → 回 §3 对应 Step 重做，**不允许直接改状态字段让门禁变绿**。

---

## §6 交付前自检清单

- [ ] 三个状态字段都填了，没有一个靠"默认值"糊过去
- [ ] 三个状态值都在白名单内，没有自创状态名
- [ ] 逐条比对过矛盾组合表，没有"已退款却完成"这类组合
- [ ] 订单总额 > 0，且与行项目汇总一致
- [ ] 这次涉及的每次迁移都在合法路径列表内
- [ ] 没有尝试从终态往回改（要重开就新建关联单）
- [ ] 退款金额 > 0，且**累计**退款比例 ≤ 1.0
- [ ] 退款前置状态是可退款状态
- [ ] 每个变更动作都有幂等键，重试不会产生第二笔扣款/发货
- [ ] `events` / `webhook` 校验通过（涉及则必做）
- [ ] 七道门禁中本次涉及的都已跑并退出码 0
- [ ] 状态机定义已落盘为文档，不是只在聊天里说过

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 已全额退款却把订单状态留成 `completed` | 退款后订单状态必须同步为 `canceled` 或专用退款完成态；门禁会判矛盾 |
| EX-02 | 货已 `delivered` 但订单还是 `pending` | 履约不得早于支付；先修支付状态再修履约 |
| EX-03 | 直接在代码里加一条 `if status == 'x': status='y'` | 迁移必须写进白名单，否则下次改动必然踩空 |
| EX-04 | 从 `refunded` 改回 `captured`（想"撤销退款"） | 终态不可逆；正确做法是新建一笔补偿/重购单 |
| EX-05 | 部分退款在一笔记录里反复改金额 | 每笔退款独立记录，累计比例由系统汇总校验 |
| EX-06 | 退款前置状态是 `canceled` 仍发起退款 | `refund.prior` 会拦；先确认钱是否真的收过 |
| EX-07 | 退款金额按"用户要求"填，不校总额 | 比例 ≤ 1.0 是硬约束；超额部分走补偿而非退款 |
| EX-08 | 重试不设幂等键，重复扣款/重复发货 | 幂等键 = 订单号 + 动作 + 序号；重试必须命中同一键 |
| EX-09 | 用 `status` 一个字段承担全部语义 | 三态分离：订单/支付/履约各自独立维护 |
| EX-10 | 门禁报错就改状态字段让它变绿 | 先修**事实**（钱是否真退、货是否真发），再改状态 |
| EX-11 | webhook 不做签名与重放校验 | 回调必须验签 + 重放窗口；否则可被伪造"已支付" |
| EX-12 | 状态机只存在于某人的记忆里 | 白名单落盘成文档，接口改动时同步更新 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `harness.py` 跑不了（无 Python） | 按 §6 人工逐项核对，标注「未跑门禁」；**不得标记订单可结算**，最多标"待复核" |
| 只给订单号没有状态 | 无法判一致性，要求补三态字段（这是最小必需） |
| 支付/物流系统不可达 | 状态按调用方提供值校验，标注"未与源头核对"，并在交付物写明核对于何时做 |
| 退款金额与订单总额口径不同（含运费/税） | 明确口径后计算比例；口径不一致时先统一口径再判 |
| 历史脏数据（终态订单已有后续动作） | 不改历史；新增修正记录 + 关联说明，标注为历史遗留 |
| 用户要求"先让它过，回头补" | 拒绝：状态门禁不接受"先绿后补"，因为绿了就会被结算 |
| 涉及真实资金操作 | 本技能只做规则校验，真实退款/扣款由 `r14` 集成层执行并需人工授权 |

**明确不做**
- 不出财务意见、不做收入确认判断（归 `r03`）；
- 不动真实资金、不调用真实支付接口；
- 不做税务、发票、合规判断（归 `r03`）；
- 不做库存账与补货（归 `r15`）。

---

## §9 资源地图（按需读取，禁止全量加载）

> 本技能包**不自建门禁**：七道判定全部复用角色根目录 `harness.py`。
> 本包只声明契约、给状态机与退款规则、做自检。

| 什么时候需要 | 读哪个文件 |
|---|---|
| 三态模型、合法迁移白名单、终态清单、退款与幂等规则 | `references/order-state-machine.md` |
| 订单骨架（可直接改） | `tests/order-pass.json` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py` |
| 负向用例（哪些错法必须被拦） | `tests/misuse.md` |
| 官方夹具全集（clean / dirty 各一套） | `D:/蛙蛙呱呱/蛙蛙呱呱agents团/r14-wajiaoyi-commerce/examples/` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 7 道门禁对正/反例的退出码 | `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 重构为十节技能包。
  新增：§1 转交表、§2 最小可开工输入、§3 七步流水线（三态分离→一致性→迁移→终态→退款→幂等→门禁）、
  §7 十二条错误表、§8 七种降级、`references/order-state-machine.md`、
  `scripts/gate_selftest.py`、`tests/order-pass.json`、`tests/misuse.md`。
  门禁复用 `harness.py` 七道，未新增判定实现。
- v1.0（此前）：无独立能力卡（仅角色级 `SKILL.md` 提到"商品电商后端/订阅计量/支付集成"等能力域）。
