# 04 · 生产/服务资源口径（production）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/restock/SKILL.md
>


> 技能：`production` ｜ 动作：`bom` / `material_request`
> 来源：frappe__erpnext（BOM / Material Request）

## 第一层：方法论

生产链由两个事实源驱动：**BOM（配方）** 与 **物料请求（缺口怎么补）**。

- **BOM 是「生产一件成品要哪些料」的配方**：它必须逐层可展开。配方不闭合（成品无行项目、
  行项目无用量、用量为零）会让 MRP 全错——不是算出错误的量，而是**算不出量**。
- **物料请求是「缺口怎么补」**：它的 `purpose` 决定后续路径（Purchase→采购 / Material
  Transfer→调拨 / Material Issue→领料 / Manufacture→自产 / Customer Provided→客供）。

本技能坚持两条原则：
1. **配方必须闭合**——成品 + 基准批量 + 非空行项目 + 用量为正，缺一不可。
2. **用途决定路径**——purpose 是白名单枚举，自造用途 = 绕过物料计划管控。

BOM 的 `quantity`（基准批量）是「生产多少件成品」的分母，行项目的 `qty` 是「每基准批量
需要多少料」。二者混淆会让 MRP 的需求量整体错一个倍数——这是生产计划最隐蔽的错误。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| bom_required | `item` + `quantity` + `items` | erpnext BOM |
| bom_item_required | `item_code` + `qty` | erpnext BOM Item |
| 用量为正 | 每行 qty > 0 | 语义公理 |
| 基准批量 | quantity > 0 | 语义公理 |
| BOM 行数 | ≤ 500 | thresholds.production |
| mr_purpose | ∈ `{Purchase, Material Transfer, Material Issue, Manufacture, Customer Provided}` | erpnext Material Request |
| mr_status | 十一态 `{Draft, Submitted, Stopped, Cancelled, Pending, Partially Ordered, Partially Received, Ordered, Issued, Transferred, Received}` | erpnext Material Request |
| mr_required | `purpose` + `items` | erpnext Material Request |
| 请求数量 | 每行 qty > 0 | 语义公理 |

**关键区分**：`Partially Ordered`（部分已下单）与 `Partially Received`（部分已收）
是两个不同阶段；`Ordered`（已全部下单）不等于 `Received`（已全部收货）。
把「已下单」当「已到货」会让生产排期基于不存在的库存，这是生产计划最常见的隐患。

## 第三层：已验证的算例

**算例 A（干净·配方闭合）**：`examples/bom.json`
```
BOM-001 / FG-001 / quantity=1
items: RM-001 ×2 + RM-002 ×1 → 行项目非空、用量为正、基准批量为正 → PASS
```

**算例 B（脏·零用量）**：`examples/bom_dirty.json`
```
items: RM-001 ×0 → 用量为 0，配方不闭合 → FAIL
```
零用量的行项目是「假配方」：MRP 会以为不需要该料，实际生产却要，必然缺料。

**算例 C（脏·用途越界）**：`examples/material_request_dirty.json`
```
purpose="Hack" → 不在 5 用途白名单 → FAIL
```

**算例 D（应拦·成品无行项目）**：
```
bom 的 items=[] → 配方不闭合（成品没有任何料）→ FAIL
```
空配方比错配方更危险：它让 MRP 静默输出「零需求」。

## 第四层：实战踩坑

- **基准批量与行项目用量混淆**：`quantity`（每批多少成品）与行项目 `qty`（每批用多少料）
  是不同量纲；混淆会让需求量整体错倍数，且错误不报错、只算错。
- **This BOM 非默认**：一个成品可能有多个 BOM（多版本），`is_default` 决定 MRP 用哪个；
  门禁不应假设「唯一 BOM」，但要保证被选中的 BOM 自身闭合。
- **物料请求的 status 与 purpose 双白名单**：只校验一个会漏；两者交叉才不会误判路径。
- **客供料（Customer Provided）特殊**：客供料不入自有库存账户，但仍是 BOM 的行项目；
  门禁按用途区分，不因「客供」就跳过配方校验。
