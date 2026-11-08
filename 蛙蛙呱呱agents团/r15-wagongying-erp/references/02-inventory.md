# 02 · 库存与仓库口径（inventory）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/inventory-planner/SKILL.md
>


> 技能：`inventory` ｜ 动作：`item` / `warehouse` / `bin` / `stock_entry`
> 来源：frappe__erpnext（Item / Warehouse / Bin / Stock Entry）

## 第一层：方法论

库存台账以 **Bin（物料 + 仓库）为最小事实单元**，不是以「物料」为单位。同一物料在两个仓库
是两个 Bin，两条独立账。把库存按物料聚合而忽略仓库维度，是账实不一致的第一大来源。

本技能坚持三条原则：
1. **账实一致性由「实际数量 ≥ 0」保证**——负库存默认禁止（`allow_negative_stock=false`），
   出现即账实不一致，先拦后查根因。
2. **预计量必须守恒**——`projected = actual + ordered + planned − reserved`，这是 MRP 的地基，
   守恒式被破坏意味着「未来某时点可承诺量」是错的。
3. **库存交易是「记录已发生」，不是「直接改库存」**——任何盘盈盘亏必须声明 handoff，
   走 Stock Entry（用途白名单）留痕，禁止直接改 `actual_qty`。

物料主数据（item_code/item_name/stock_uom/valuation_method）是库存的事实源。UOM 白名单
（Nos/kg/g/m/cm/Pcs/Set/hr/day/Box/Pallet）挡住「箱 vs kg」这类单位污染；计价方法
（FIFO/Moving Average/LIFO/Standard Cost）决定成本结转口径，必须在物料层定死。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| item_required | `item_code` + `item_name` 非空 | erpnext Item |
| stock_uom | ∈ 白名单（≥9 个单位） | thresholds.inventory |
| valuation_method | ∈ `{FIFO, Moving Average, LIFO, Standard Cost}` | erpnext Item |
| lead_time_days | ≤ 3650 天 | thresholds.inventory |
| warehouse 必填 | `warehouse_name` 非空 | erpnext Warehouse |
| 组仓库 | is_group=true 时不得为退次库 | 结构公理 |
| 非根仓库 | 必须声明 `parent_warehouse` | erpnext Warehouse |
| bin_required | `warehouse` + `item_code` | erpnext Bin |
| 负库存 | actual_qty ≥ 0（默认禁止） | thresholds.inventory |
| 守恒式 | projected == actual + ordered + planned − reserved | erpnext Bin |
| stock_entry 用途 | ∈ `{Material Receipt, Material Issue, Material Transfer, Manufacture, Repack, Send to Subcontractor}` | erpnext Stock Entry |
| 调拨 | Material Transfer 须源仓 + 目标仓 | 结构公理 |

**关键区分**：`actual_qty`（实际库存）与 `projected_qty`（预计量）是两回事。
actual 是「现在有多少」，projected 是「未来某时点会有多少」。把 projected 当 actual
用来发货，是超卖的根源。`ordered_qty`（已订购在途）与 `reserved_qty`（已预留）的
符号方向相反，守恒式里 ordered/planned 加、reserved 减，写反就全错。

## 第三层：已验证的算例

**算例 A（干净）**：`examples/bin.json`
```
华东原料库 / RM-001：actual=20, ordered=100, reserved=10, planned=0
projected = 20+100+0−10 = 110 == 声明 110 → 守恒成立；actual≥0 → PASS
```

**算例 B（脏·负库存）**：`examples/bin_dirty.json`
```
actual=-5 → 负库存（allow_negative_stock=false）→ FAIL
```
负库存是「超卖或入账错误」的结果，不是原因；先拦，再定位根因。

**算例 C（脏·用途越界）**：`examples/stock_entry_dirty.json`
```
purpose="Unknown" → 不在 6 用途白名单 → FAIL
```
自造用途 = 绕过库存交易管控，必须拦。

**算例 D（脏·单位越界）**：`examples/item_dirty.json`
```
stock_uom="箱" → 不在 UOM 白名单 → FAIL
```
单位污染会让「1 箱 = 多少 kg」变成无解，必须回到主数据层定死单位。

## 第四层：实战踩坑

- **负库存是结果不是原因**：直接「改库存到 0」掩盖了超卖/入账错误，R15 红线禁止直接改
  `actual_qty`，只能产出盘点调整请求。
- **守恒式写反**：`projected = actual + ordered + planned − reserved`，reserved 是减号。
  写反后预计量偏大，MRP 会承诺出并不存在的库存。
- **组仓库 vs 实体库**：is_group=true 的仓库不能存实物，很多导入数据把它当实体库用，
  层级门禁必须在源头挡住。
- **计价方法不能中途乱改**：FIFO vs Moving Average 的成本结转差异巨大，一旦有历史凭证，
  改动会触发重算，必须人工授权。
