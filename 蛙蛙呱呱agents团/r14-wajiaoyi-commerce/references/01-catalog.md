# 01 · 商品目录与价格口径（catalog）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/product-management/write-spec/SKILL.md
>


> 技能：`catalog` ｜ 动作：`product`（商品目录校验）、`price`（单品价格校验）
> 来源：medusajs__medusa（ProductStatus、ProductType、ProductVariant price）

## 第一层：方法论

商品目录是整条交易链的**唯一事实源**。下游的购物车、订单、账单、事件全部引用商品 ID 与价格，
一旦目录层口径错，错误会以乘数方式向下游扩散（一个商品错价 × 1000 单 = 1000 张错账单）。

因此目录层只做两件事，且必须做死：
1. **状态合法性**——商品只能处于 medusa 定义的状态枚举内，不允许自造状态。
2. **价格非负**——price < 0 在交易语义里永远无意义（无"负价商品"），出现即数据错误，
   不允许用"这是折扣字段"之类的解释蒙混过去；折扣属于定价策略，不属于商品基准价。

目录层的**不做什么**同样重要：不做促销、不做库存扣减、不做税务计算。这些分别属于
定价策略层、R15 库存、R03 财务。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| product_required | `title`、`status`、`price` 三字段必须存在 | thresholds.catalog.product_required |
| product_status | ∈ `{draft, proposed, published, rejected}` | medusa ProductStatus |
| product_types | ∈ `{physical, digital, service}` | medusa ProductType |
| price > 0 | 数值且严格大于 0（0 与负值均拦截） | 交易语义公理 |
| title 非空 | 去空格后长度 > 0 | 标识可读性要求 |

**关键区分**：`draft` 与 `published` 是**可售性**的分界。`draft` 商品不得出现在购物车/订单校验的
可售集合里；`rejected` 表示曾被审核否决，需人工处理后才可恢复。把 `draft` 当 `published` 使用，
是目录层最常见的静默错误——校验通过，但下游卖了一个不该卖的东西。

价格区分 `price`（基准价）与 `unit_price`（订单行实际单价）。基准价只能有一个来源，
行单价允许因促销而偏离基准价，但**偏离本身必须在订单层有据可查**。

## 第三层：已验证的算例

**算例 A（干净）**：`examples/product.json`
```
CRM 3 席位订阅 / published / 299.0 / digital   → PASS
数据看板加装   / published / 149.0 / service   → PASS
品牌吉祥物公仔 / draft     / 59.0  / physical  → PASS（draft 合法，仅不可售）
```
校验输出：3 个商品全部字段齐备、状态合法、价格非负 → `ok=true`，`product_count=3`。

**算例 B（脏数据）**：`examples/product_dirty.json`
```
""         / published / 299.0 / digital → BLOCKER: title 为空
"越界状态" / 上架中    / -5.0  / digital → BLOCKER: status 不在枚举 + price ≤ 0
```
实际触发 3 条失败判据：`商品必填齐备（缺 ['']）`、`商品状态在白名单（越界 ['越界状态']）`、
`价格均为正数（异常 ['越界状态']）` → `ok=false`，`grade=FAIL`。

**算例 C（价格）**：`examples/price.json` → `299.0 > 0`、`status=published` → PASS。
`examples/price_dirty.json` → `商品名非空` + `状态='上架中' 在白名单` + `价格=0.0 为正` 三条失败。

**重要口径**：`price = 0` 会被拦截（判据是 `> 0` 而非 `≥ 0`）。本仓库把"免费"表达为
**不创建价格条目**或走独立的免费通道，而不是 `price=0`——因为 `price=0` 与
"价格字段未填/被误清空"在数据上无法区分。这是刻意的保守选择，避免把"漏填"静默当成"免费"。

## 第四层：实战踩坑

1. **状态词中英混用**：业务方习惯说"上架中"，数据库存 `published`。校验层只认枚举值，
   中文状态一律 BLOCKER。不要把"上架中"映射成 `published` 蒙过去——映射规则不透明时，
   错映射比报错更危险。

2. **把 draft 商品放进演示数据**：演示时为了好看混入 draft 商品，结果 demo 通过了、
   真实下单流程却拒绝了。约定：demo 数据集里可以有 draft，但必须在演示脚本里显式说明
   "此项不可售"。`sellable_count` 就是为此准备的独立证据字段（可售数 ≠ 总数）。

3. **价格精度**：299.0 与 299 在 JSON 里是同一个数，但序列化后字符串不同。
   比对价格时用数值比对，禁止字符串比对。

4. **多币种缺失**：medusa 的价格天然带 currency_code。本角色的示例工件省略了币种字段，
   若接入真实数据，币种缺失必须视为 WARN 而非静默通过——币种口径归 R03 财务确认。

5. **product_count 是证据不是装饰**：评审（review.py）会检查产出是否含具体工件键。
   只写"我检查了商品目录"而不带 `products` / `product_count`，会被判 `artifact_not_concrete`。
