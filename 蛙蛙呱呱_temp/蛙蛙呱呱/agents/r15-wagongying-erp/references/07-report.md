# 07 · 运营报表口径（report）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/report-builder/SKILL.md
>


> 技能：`report` ｜ 动作：`report`
> 来源：frappe__erpnext（采购/库存/履约/财务台账报表口径）

## 第一层：方法论

报表是**「读已经发生的业务事实」，不是「下结论」**。结论归 R06（数据分析）或
R03（财务口径）；本角色产出的是**可复算的运营台账**。

因此本技能只校验三件事，且必须做死：
1. **报表结构合法**——report_type / period / kpis 必填，类型在白名单（purchase/inventory/
   fulfillment/finance_ledger）。
2. **周期口径合规**——只接受 `YYYY` / `YYYY-MM` / `YYYY-Qn`，挡住「昨天」「上个月」这类
   不可机读、不可复算的模糊周期。
3. **KPI 可复算**——每个 KPI 必须有「值 + 分子 + 分母」三要素，且值 ≈ 分子/分母
   （容差 0.01）。纯数量指标分母=1。

**关键立场**：一个 KPI 如果只有「值」而没有「分子/分母」，它就是一个**不可审计的数字**——
别人无法验证它是怎么算出来的，也无法发现它何时变错。可复算是运营台账的生命线：
宁可少报一个 KPI，也不报一个不可复算的 KPI。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| report_type | ∈ `{purchase, inventory, fulfillment, finance_ledger}` | thresholds.report |
| report_required | `report_type` + `period` + `kpis` | thresholds.report |
| period_pattern | `^(\d{4}-(0[1-9]|1[0-2])|\d{4}-Q[1-4]|\d{4})$` | thresholds.report |
| KPI 三要素 | value > 0 且 denominator > 0（或 numerator 有效） | 可复算公理 |
| KPI 可复算 | value ≈ numerator/denominator（容差 0.01） | 可复算公理 |

**关键区分**：`report_type` 决定这份台账的**语义**（采购 vs 库存 vs 履约 vs 财务），
period 决定它的**时间范围**，两者都必须在结构层定死。KPI 的 numerator/denominator
是「口径」，value 是「结果」——口径和结果分离，才谈得上审计。

## 第三层：已验证的算例

**算例 A（干净·可复算 KPI）**：`examples/report.json`
```
report_type=inventory / period=2026-11
kpis: 库存周转率 = 1200/300 = 4.0 == value → 可复算 → PASS
```

**算例 B（脏·周期口径非法）**：`examples/report_dirty.json`
```
period="昨天" → 不匹配 YYYY/YYYY-MM/YYYY-Qn → FAIL
```
模糊周期不可机读、不可跨期对账，必须拦。

**算例 C（脏·KPI 不可复算）**：`examples/report_dirty.json`
```
库存周转率 分子=1200 分母=300 但 value=9.9 → 9.9 ≠ 4.0 → FAIL
```
「值」与「口径」脱节是报表数据污染的典型：数字报上去了，但没人能验证。

## 第四层：实战踩坑

- **KPI 只有值没有口径 = 不可审计**：只报「周转率 4.0」不报「1200/300」，下游无法复核，
  也无法发现「值被手改」。
- **周期格式必须机读**：`YYYY-Qn` 表示季度，与 `YYYY-MM` 月份不同；不规范的周期会让
  跨期对账变成人工游戏。
- **报表是读操作**：报表校验不改变任何业务数据，但「读出来的数」必须和业务台账对得上，
  否则报表层会制造一个「看起来合理的错误结论」。
- **结论移交**：看到「周转率下降」这类结论时，R15 只给可复算的台账与 KPI，不下
  「该不该补货/该不该降价」的判断——那是 R06/R01 的活。
