# 06 · 数据目录与口径接口口径（catalog）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/data/data-context-extractor/SKILL.md
>


> 技能：`catalog` ｜ 动作：`entry`（目录条目）、`lineage`（血缘）
> 来源：dbt（model/source 文档 + lineage）+ airbyte catalog（stream schema）+ airflow lineage

## 第一层：方法论

数据目录是**分析层的唯一入口**——没有登记的表/字段，分析层就不该消费。目录
记录"有什么表、表里的字段是什么类型、谁负责、什么时候更新的"，血缘记录"这些表
之间谁来自谁"。把这段做成确定性校验的价值，不在于"文档写得全"，而在于
**让没有登记的表和断链的血缘暴露出来**。

三条方法论：

1. **目录是 R06 的唯一入口**。表/字段必须登记在目录里，分析层才能消费。未登记
   的表 = 来历不明 = 不该被引用。
2. **血缘引用必须完整**。血缘边 `[A, B]` 里的 A/B 必须在已声明表集合内。出现
   未声明的上游表 = 断链（无法溯源到源头）。
3. **owner 非空 = 出事有人认领**。没有负责人的表，出问题找不到人。owner 是
   数据治理的最低要求。

**本角色只交「数据目录与口径接口」**，**不交「数字结论」**——红线 3 边界，
结论归 R06。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| entry.table | 非空 | 表名 |
| entry.owner | 非空 | 数据治理责任人 |
| entry.updated_at | 非空 | 新鲜度口径声明 |
| entry.fields | ≥ 1 个字段 | 表结构 |
| entry.field_type | 每个字段 type ∈ `catalog.field_types` = `[string, integer, number, boolean, timestamp, date, json]` | catalog schema |
| entry.field_unique | 字段名非空且唯一 | 表结构完整性 |
| lineage.tables | ≥ 1 且表名唯一 | 表集合 |
| lineage.ref_integrity | 每条边两端 ∈ tables | 血缘完整性 |
| lineage.acyclic | Kahn 拓扑可剥完 ⇒ 无环 | 血缘 DAG |

**阈值单一真源**：`catalog.field_types` 以 `experience/thresholds.json` 的
`catalog` 段为准。

## 第三层：已验证的算例

**算例 A（干净目录条目）**：`examples/catalog_entry.json`
```
orders / owner=R18 / updated_at=updated_at / fields=[{order_id,integer},{created_at,timestamp}]
```
表名/owner/更新时间齐、字段类型白名单、字段名唯一 → `ok=true`，`verdict=PASS`。

**算例 B（脏目录条目）**：`examples/catalog_entry_dirty.json`
```
orders / owner="" / fields=[{order_id, uuid}]
```
BLOCKER ×2：`owner` 为空（`catalog.owner`）、字段类型 `uuid` 不在白名单
（`catalog.field_type`）。

**算例 C（脏血缘）**：`examples/lineage_dirty.json`
```
tables=[stg_orders, fct_orders] / edges=[[stg_orders,fct_orders],[ghost,fct_orders]]
```
BLOCKER ×1：边 `[ghost, fct_orders]` 里 `ghost` 不在 tables 中，
`lineage.ref_integrity` 拦。对照 `lineage.json`（无悬空边、无环）→ `ok=true`。

## 第四层：实战踩坑

1. **字段类型白名单来自 catalog schema，不是 SQL 类型全集**。`uuid` / `array` /
   `map` 等类型**不在** R18 的白名单里。理由：R18 的目录口径对齐 airbyte catalog
   的基础类型（string/integer/number/boolean/timestamp/date/json），保证跨连接器
   可比。特殊类型须先归一化到基础类型再登记。

2. **字段名唯一是硬约束**。两个同名字段（`id` 出现两次）会让下游 `SELECT id` 不知
   指向哪个。口径：字段名非空且唯一。

3. **血缘无环与引用完整是两条独立判据**。`edges=[[a,b],[b,a]]` 且 a/b 都在 tables
   里 → ref_integrity 过、acyclic 拦。`edges=[[ghost,b]]` 且 ghost 不在 tables →
   ref_integrity 拦、acyclic 因悬空边不计入而可能假过。两头都要设。

4. **血缘边方向 = 数据流向**。`[stg_orders, fct_orders]` 表示 stg_orders 是上游、
   fct_orders 是下游（数据从 stg 流到 fct）。写反会导致溯源方向错误。

5. **`updated_at` 是"字段名"不是"时间戳值"**。目录条目的 `updated_at` 声明的是
   "哪个字段记录更新时间"（如 `updated_at` 或 `etl_ts`），不是具体时间。这是与
   s04 新鲜度联动的地基——声明了才能算数据年龄。

6. **owner 是角色/人，不是系统**。`owner="prod"` 或 `owner="pipeline"` 不算有效
   owner（没人认领）。口径是非空字符串，但语义上应指向具体责任人（如 R18、R06）。

7. **不要在结论里写"该表口径为日活跃用户数"**。这是越界（`scope_boundary`）。
   正确写法："产出目录条目 catalog_entry.json（orders 表，owner=R18，2 字段），
   字段口径登记完整。"字段**业务含义**的描述属 R06。

8. **目录条目不含数据行**。目录是**schema 级**（表的元数据），不是数据级（表里的
   行）。任何尝试把数据行塞进目录条目的做法都是口径混淆。

9. **lineage 的 tables 是"已知表全集"**。它是引用完整性的比对基准。如果只登记了
   部分表（如只有 fct_orders），那么所有指向未登记表的边都会被误判悬空——
   **tables 必须包含涉及的所有表**。
