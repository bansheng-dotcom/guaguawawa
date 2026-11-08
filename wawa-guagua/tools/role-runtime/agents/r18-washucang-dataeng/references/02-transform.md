# 02 · 数仓转换口径（transform）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/data/validate-data/SKILL.md
>


> 技能：`transform` ｜ 动作：`model`（模型配置）、`test`（通用测试）
> 来源：dbt-labs__dbt（`materialized` 枚举见 crates/dbt-schemas 的 Materialized、generic tests 的 unique/not_null/accepted_values/relationships、`ref()` 依赖图见 crates/dbt-dag）

## 第一层：方法论

数仓转换（dbt 层）是**一个把原始表加工成分析表的有向无环图（DAG）**，不是一堆
孤立的 SQL。每个 model 是一张表/视图/incremental/ephemeral，`ref()` 声明它依赖
哪些上游模型。把这段做成确定性校验的价值，不在于"写 SQL 更快"，而在于
**让编译期就会炸的悬空依赖进不了生产**。

三条方法论：

1. **物化方式必须落在白名单**。`table`（每次重建整表）/ `view`（视图）/
   `incremental`（增量追加/合并）/ `ephemeral`（不落库的 CTE）。写错物化方式
   （如 `view_plus`）不被 dbt 识别——枚举越界即 BLOCKER。
2. **ref 引用完整性是编译期红线**。`depends_on` 里出现一个不在模型全集
   （`all_models`）里的模型，等于 `ref()` 指向空气——编译直接失败。必须拦住。
3. **模型不自引用**。模型 ref 自己构成自环，dbt 会报循环依赖。自引用是最短
   的环，必须显式拦。

**本角色只校验转换结构与引用完整性**，**不产出业务口径结论**——"这个指标同比
涨了多少"是 R06 蛙得清的活（红线 3 边界）。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| model.model_name | 非空 | dbt model 必填 |
| model.materialized | ∈ `transform.materializations` = `[table, view, incremental, ephemeral]` | dbt-schemas Materialized |
| model.depends_on | 数组（可为空） | dbt ref() |
| model.ref_integrity | 提供 `all_models` 时，每个 ref ∈ all_models | dbt-dag 编译期 |
| model.self_ref | 模型名 ∉ 自己的 depends_on | 自环 = 循环依赖 |
| model.unique_key | `materialized==incremental` → 声明 `unique_key` | dbt incremental 去重 |
| test.tests | ≥ 1 条测试 | 无测试的模型无门禁 |
| test.test_type | ∈ `transform.test_types` = `[unique, not_null, accepted_values, relationships]` | dbt generic test |
| test.column | 每条测试绑定具体列 | dbt 列级测试 |
| test.accepted_values | test_type==accepted_values → 带 `values` 集合 | dbt accepted_values |

**阈值单一真源**：`transform.materializations` / `transform.test_types` 以
`experience/thresholds.json` 的 `transform` 段为准。

## 第三层：已验证的算例

**算例 A（干净模型）**：`examples/model.json`
```
dim_customer / table / depends_on=[stg_customer] / all_models=[stg_customer, dim_customer]
```
物化白名单、ref 完整、无自引用 → `ok=true`，`verdict=PASS`。

**算例 B（脏模型）**：`examples/model_dirty.json`
```
dim_customer / view_plus / depends_on=[stg_customer]
```
BLOCKER ×1：`materialized='view_plus'` 不在白名单（合法值含 `view`，不是
`view_plus`）。

**算例 C（脏测试）**：`examples/test_dirty.json`
```
tests=[{unique,id}, {accepted_values,status}]（第二条无 values）
```
BLOCKER ×1：`accepted_values` 未带 `values` 集合。对照 `test.json`（第二条带
`values=[active,churned]`）→ `ok=true`。

## 第四层：实战踩坑

1. **`all_models` 缺失时跳过引用完整性是刻意的**。单测一个模型工件时，未必能
   提供全图。技能口径：没有 `all_models` → 跳过 ref 完整性检查（记为 OK，不误拦）；
   提供了 → 严格校验。**不要用"没提供=通过"来逃检**，但也别把单模型工件当脏数据。

2. **self_ref 与 ref_integrity 是两回事**。`depends_on=[dim_customer]` 且模型名就是
   `dim_customer` → self_ref 拦；`depends_on=[ghost]` 而 `ghost` 不在 all_models →
   ref_integrity 拦。两条判据独立，两头都要设。

3. **incremental 的 unique_key 是去重依据**。`materialized=incremental` 却不声明
   `unique_key`，增量合并时无法判断"这行是不是已存在"，会导致重复入账或错误覆盖。
   这是 dbt incremental 的必需伴随项（同 s01 的 incremental cursor）。

4. **测试类型是 dbt 的"四大金刚"不是任意字符串**。dbt 内置 generic tests 是
   unique / not_null / accepted_values / relationships。自定义 test 也存在，但
   R18 只校验这四类内置类型的口径（见 thresholds）。

5. **不要在结论里写"该模型口径为 XXX"**。这是越界（`scope_boundary`）。正确
   写法："产出模型工件 model.json（dim_customer, table, 依赖 stg_customer），
   引用完整、无自环。"业务口径归 R06。

6. **ephemeral 也是合法物化**。它在 dbt 里是"不落库的临时 CTE"，常被误当成
   "非法"或"临时表"而误拦。口径：ephemeral 在白名单内。

7. **列级测试必须绑定列**。`{test_type: unique}` 没有 `column` 是无效测试——测试
   总得测某列。口径：每条测试 `column` 非空。

8. **模型名重复不在本技能层拦**。同名模型是图级问题（两个节点同名），R18 在
   catalog 的 lineage 层用「表名唯一」拦，transform 层只判单模型结构。职责分离。
