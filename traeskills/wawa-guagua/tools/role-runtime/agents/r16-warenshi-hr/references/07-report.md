# 07 · 组织运营报表口径（report）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/people-report/SKILL.md
>


> 技能：`report` ｜ 动作：`headcount`（花名册汇总）、`report`（运营指标）
> 来源：frappe__hrms 报表层 + frappe-ui（前端子模块，UI 来源登记）

## 第一层：方法论

报表是**「经营事实的投影」，不是「经营判断」**。R16 只保证计数与比例的口径正确、
字段合法；**趋势解读、归因与「该不该裁/该不该招」的结论交 R01 决策 + R06 分析**
（红线 3 的延伸：不做组织决策结论）。

三条方法论：

1. **分组恒等是报表的信任基础**。`Σ分组计数 == total`。分组计数与总数对不上，
   报表就没有可信度。
2. **指标白名单防字段漂移**。运营指标字段必须来自白名单（headcount/turnover_rate/
   attendance_rate/leave_balance/payroll_input_count）。未知字段一律拦下。
3. **流动率实算**。`turnover_rate == period_exits / period_starts`（若有口径）。

**本角色绝对不做的事**：不做趋势解读、不做组织决策结论、不做裁员/扩编建议。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| headcount.groups | `≥ 1` | 分组非空 |
| headcount 恒等 | `Σ分组计数 == total` | 分组恒等 |
| headcount.dim | 每个分组的 `dim`/`name` 非空 | 分组维度非空 |
| report.metrics | 对象非空 | 指标对象 |
| report.field_whitelist | 字段 ∈ `{headcount, turnover_rate, attendance_rate, leave_balance, payroll_input_count}` | thresholds.report |
| report.nonneg | 所有数值 `≥ 0` | 指标非负 |
| report.turnover | `turnover_rate == period_exits / period_starts`（若有口径） | 流动率恒等 |

**指标白名单速查**：
- `headcount`：在编人数。
- `turnover_rate`：流动率 = 期内离职 / 期初人数。
- `attendance_rate`：出勤率。
- `leave_balance`：休假余额（总量）。
- `payroll_input_count`：薪酬输入条数（与 s05 勾稽）。

## 第三层：已验证的算例

**算例 A（干净花名册）**：`examples/headcount.json`
```
total=5 / [Active=4, Left=1]
```
分组和 4+1=5 == total=5 → `ok=true`。

**算例 B（脏花名册）**：`examples/headcount_dirty.json`
```
total=5 / [Active=3, Left=1]
```
BLOCKER：分组和 3+1=4 ≠ total=5（分组恒等失败）。

**算例 C（干净指标）**：`examples/report.json`
```
headcount=5, turnover_rate=0.2, attendance_rate=0.96
period_starts=5, period_exits=1
```
字段白名单、非负、流动率 1/5=0.2 == 声明 0.2 → `ok=true`。

**算例 D（脏指标）**：`examples/report_dirty.json`
```
headcount=-5, turnover_rate=0.9, unknown_metric=3
period_starts=5, period_exits=1
```
BLOCKER ×3：headcount 为负、`unknown_metric` 越界白名单、流动率 0.9 ≠ 1/5=0.2。

## 第四层：实战踩坑

1. **分组恒等的"漏算"**。如果某个分组（如 `Suspended`）未被计入分组列表，但计入了
   total，就会分组和 < total。必须显式列出所有分组。

2. **指标字段漂移**。LLM 容易"发明"指标（如 `satisfaction_score`）。白名单拦下是为了
   防止报表口径无法对账。

3. **负值指标**。headcount 为负、比率 > 1 都是可能的用 bug 暴露点。口径：非负。

4. **流动率的分子分母**。`turnover_rate = period_exits / period_starts`。用期末人数
   作分母会低估流动率。口径须明确。

5. **per-capita 类指标**。人均产值等需要财务数据，不在 R16 范围（交 R03/R06）。

6. **不要在结论里写"人员流失严重，建议加薪留人"**。这是组织决策，交 R01。
   正确写法："花名册 total=5（Active=4, Left=1），流动率 0.2 = 1/5，指标口径一致；
   趋势解读与决策建议交 R01 + R06。"

7. **Left 员工的剔除口径**。`Left` 应从在编花名册剔除，但历史报表可能保留。
   调用方须明确"在编口径"还是"历史口径"。

8. **headcount 与 roster 的区别**。`headcount` 是计数结果，`roster` 是明细列表。
   本技能只校验计数汇总的恒等，明细交 s02 人员档案。
