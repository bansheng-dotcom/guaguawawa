# 蛙人事 · attendance/leave
> 员工申请年假三天，帮我看天数对不对、额度够不够 

**结论**：next=工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 8/8 项 |
| next | **工件通过全部门禁，可进入授权与交接** | 输出字段 |
| leave_count | **1** | 输出字段 |
| status | **Approved** | 输出字段 |

## 1. leave_count
> leave_count 的判定与证据是什么？

- **leave_count：**1

## 2. status
> status 的判定与证据是什么？

- **status：**Approved

## 3. overlap_count
> overlap_count 的判定与证据是什么？

- **overlap_count：**0

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**请假 EMP-0001（Approved）2026-11-20 → 2026-11-22

## 口径与边界

- **来源：**技能 attendance/leave 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
