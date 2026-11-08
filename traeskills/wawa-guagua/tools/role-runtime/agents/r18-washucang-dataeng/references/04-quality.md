# 04 · 数据质量门禁口径（quality）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/data/validate-data/SKILL.md
>


> 技能：`quality` ｜ 动作：`check`（质量检查）、`fresh`（新鲜度口径）
> 来源：dbt-labs__dbt（generic test 语义 + source freshness 的 warn/error 分级）+ apache__airflow（数据质量检查点）

## 第一层：方法论

质量门禁是**数据进入分析环境前的最后一道关**。它在关键节点检查四类：
完整性（not_null）、唯一性（unique）、有效性（accepted_values/range）、
新鲜度（freshness）。把这段做成确定性校验的价值，不在于"报告数据多脏"，而在于
**让不达标的数据根本进不了下游**——`ok=false` 即阻断。

三条方法论：

1. **质量门禁是「阻断器」不是「报告器」**。一条检查不通过，下游所有消费方都不该
   拿到这批数据。`ok=false` 直接阻断，不是"打个警告继续"。
2. **空值率/重复率/越界数是可实算的**。不靠主观判断"数据看起来还行"，而是算
   `null_ratio ≤ 阈值`、`dup_ratio ≤ 阈值`、`invalid_count == 0`。数字说话。
3. **新鲜度决定"数据是不是过期的"**。数据年龄超过上限（dbt freshness 的
   error_after），下游拿到的是陈旧数据，结论必然滞后。

**本角色只判「数据能不能进分析环境」**，**不判「数字说明什么」**——那是 R06
的活（红线 3 的边界）。质量门禁说"这批数据合格"，不说"这个指标增长了"。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| check.table | 非空 | 被检表名 |
| check.row_count | > 0 | 空表无质量可言 |
| check.null_ratio | ≤ `quality.default_max_null_ratio`（0.1） | dbt not_null |
| check.dup_ratio | ≤ `quality.default_max_dup_ratio`（0.05） | dbt unique |
| check.invalid | `invalid_count == 0` | dbt accepted_values/range |
| check.items | 每条检查条目 `passed==true` 且带 `value` | 实测值可追溯 |
| fresh.table | 非空 | 被检表名 |
| fresh.age | `0 ≤ age_hours ≤ quality.default_max_age_hours`（24） | dbt source freshness error_after |
| fresh.loaded_at | 非空 | 新鲜度口径字段 |
| fresh.snapshotted_at | 非空 | 快照时点 |

**阈值单一真源**：`quality.default_max_null_ratio` / `default_max_dup_ratio` /
`default_max_age_hours` 以 `experience/thresholds.json` 的 `quality` 段为准。

## 第三层：已验证的算例

**算例 A（干净质量检查）**：`examples/quality_check.json`
```
orders / row_count=1000 / null_ratio=0.02 / dup_ratio=0.01 / invalid_count=0
checks=[{order_id_not_null, passed=true, value=1000}]
```
空值率/重复率均低于阈值、越界数为 0、条目带实测值 → `ok=true`，`verdict=PASS`。

**算例 B（脏质量检查）**：`examples/quality_check_dirty.json`
```
orders / row_count=1000 / null_ratio=0.5 / ...
```
BLOCKER ×1：`null_ratio=0.5 > 0.1`，`quality.null_ratio` 拦。对照 `quality_check.json`
（0.02）→ `ok=true`。

**算例 C（脏新鲜度）**：`examples/quality_fresh_dirty.json`
```
orders / age_hours=30 / loaded_at=updated_at / snapshotted_at=...
```
BLOCKER ×1：`age_hours=30 > max_age_hours=24`，`fresh.age` 拦。对照
`quality_fresh.json`（age_hours=6）→ `ok=true`。

## 第四层：实战踩坑

1. **阈值是"上限"含边界**。`age_hours == 24` 时 `0 ≤ 24 ≤ 24` 成立 → 通过。
   dbt 的 freshness 口径是 `age > error_after` 才算过期，所以等号边界放行。
   若实现写成 `<` 会与 dbt 口径错位（R18 用 `<=`，与真源一致）。

2. **空值率是比值不是计数**。`null_ratio=0.5` 与 `null_count=500` 是两种口径。
   R18 收的是 `null_ratio`（比值），若夹具给的是计数会算错——夹具必须给比值。
   计数请放在 `checks[].value` 里做可追溯。

3. **`checks` 是条目数组不是顶层 checks**。注意区分：技能输出的顶层 `checks` 是
   门禁结果（`{ok,msg,dim,sev}`），而**输入**的 `checks` 是被检数据的检查条目
   （`{name, passed, value}`）。同名不同物，读代码时极易混。R18 用
   `quality.items` 维度名做区分。

4. **`invalid_count==0` 是"零容忍"**。有效性检查（accepted_values）不允许任何
   越界值——一个 `status='bogus'` 就阻断。与空值率（有容忍上限）不同，越界是
   离散错误，必须归零。

5. **新鲜度必须有回溯口径**。`loaded_at`（加载字段名）与 `snapshotted_at`（快照
   时点）都要声明——出事时能回溯"这批数据是什么时候的"。缺任一个 → BLOCKER。

6. **不要在结论里写"数据质量良好，可放心使用"**。这是模糊措辞 + 越界暗示。正确
   写法："表 orders 质量门禁通过（null_ratio=0.02, dup_ratio=0.01, age=6h），
   数据可进入分析环境。"

7. **row_count=0 是脏数据**。空表通过所有比值检查（0/0 都"合格"）但毫无意义。
   口径：`row_count > 0` 是前置门禁，在比值检查之前拦。

8. **质量失败 ≠ 数据要删**。门禁只是"不让进下游"，不是"删掉脏数据"。删除是
   不可逆动作（红线 2），须走 s07 审批。措辞上不要把"阻断"写成"清理"。
