# 事件契约与命名（event-schema）

> 命名 · 属性最小集 · 漏斗 · 字典 · 10 组 BAD/GOOD。版本：v1

---

## 一、命名三层

```
<对象>_<动作>[ _<限定> ]
order_paid
cart_item_added
page_viewed
checkout_step_completed
```

| 规则 | 说明 |
|---|---|
| 全小写下划线 | 不用驼峰、不用连字符 |
| 对象在前，动作在后 | `order_paid` 不是 `paid_order` |
| 动作用过去式 | `paid` / `added` / `viewed`（事件已发生） |
| 禁数字与缩写 | ❌ `click1` `btn2` `e1` `trk_a` `orderOK` |
| 限定放最后 | `checkout_step_completed`（第几阶用属性表达） |

---

## 二、属性最小集（每事件必填）

| 属性 | 类型 | 说明 |
|---|---|---|
| `user_id` | string | 登录用户；匿名用 `anon_id` |
| `occurred_at` | timestamp | 事件发生时刻（非上报时刻） |
| `<对象>_id` | string | 事件主体 id（order_id / sku_id / page_path） |
| `channel` | string | 来源渠道（枚举，禁自由文本） |
| `app_version` / `platform` | string | 端与版本（排查异常用） |

**必填阈值**：**≥3 个**，且必须含 `user_id` 与 `occurred_at`。

---

## 三、触发时机：发起 vs 成功（必须两个事件）

```
❌ 只埋一个：checkout_submitted（点击）
   → 数据里看不出「点了但失败」的比例

✅ 两个事件：
   checkout_submitted   （用户点击提交）
   checkout_succeeded   （服务端确认成功）
   checkout_failed      （服务端返回失败，带 reason 属性）
```

**判据**：任何有「成功/失败」之分的动作，都必须拆成 ≥2 个事件。

---

## 四、漏斗模板

```markdown
## 漏斗：加购 → 下单 → 支付
| 步 | 事件 | 时间窗（距上一步） |
|---|---|---|
| 1 | cart_item_added | — |
| 2 | order_created | ≤24h |
| 3 | order_paid | ≤2h |

窗口上限：整条漏斗 ≤7 天
```

**铁律**：漏斗必须**逐步声明**；禁止用「装过 A 且后来有 B」这类查询倒推——
那是相关，不是路径，且无法界定时间归属。

---

## 五、数据字典模板

| 事件 | 中文名 | 必填属性 | 触发时机 | 负责人 | 上线日 | 版本 |
|---|---|---|---|---|---|---|
| order_paid | 订单支付成功 | user_id, occurred_at, order_id, amount, pay_method | 支付回调成功 | r14 | 2026-11-01 | v1 |
| order_pay_failed | 订单支付失败 | user_id, occurred_at, order_id, reason | 支付回调失败 | r14 | 2026-11-01 | v1 |

**版本规则**：改属性名/删属性/改触发时机 → **升版本**，旧事件保留一个版本周期。
原地改会让「上个月的数据」和「这个月的数据」不可比，而没人会记得改过。

---

## 六、上线 7 天回看三件事

| 检查 | 异常信号 | 可能原因 |
|---|---|---|
| 量级 | 为 0，或等于全站 UV | 没埋上 / 埋错位置 / 触发太宽 |
| 属性缺失率 | `user_id` 缺失 >20% | 未登录态没回填 |
| 漏斗异常 | 某一步 100% 流失 | 事件没埋或时机错 |

---

## 七、10 组 BAD/GOOD

| # | 场景 | ❌ | ✅ |
|---|---|---|---|
| 1 | 命名 | `click1` | `cart_item_added` |
| 2 | 命名顺序 | `paid_order` | `order_paid` |
| 3 | 粒度 | 一个 `button_click` 覆盖全站按钮 | 按对象拆：`cart_item_added` / `order_submitted` |
| 4 | 触发 | 点击即埋「已支付」 | `order_paid` 在支付回调成功后埋 |
| 5 | 失败 | 不埋失败 | `order_pay_failed` + `reason` |
| 6 | 漏斗 | 「装过A后来有B」 | 逐步声明 + 时间窗 |
| 7 | 属性 | 只有事件名 | user_id + occurred_at + order_id |
| 8 | 字典 | 无 | 字典含负责人/上线日/版本 |
| 9 | 改属性 | 原地改 | 升 v2，旧版保留一个周期 |
| 10 | 回看 | 上线不管 | 7 天内看量级/缺失/漏斗 |

---

## 八、来源

- 「对象_动作」命名与过去式动作：事件追踪命名通行实践
- 发起/成功拆分：避免「假成功」的常见教训
- 漏斗显式声明与版本化：数据契约（data contract）思路
- 回看三项：本团队 `data-validation` 六维质量在埋点场景的裁剪
