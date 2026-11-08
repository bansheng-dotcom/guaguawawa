# 蛙引流 · diagnose/diagnose
> 帮我做一次增长诊断，看漏斗和 PMF 信号 

**结论**：next=增长方案通过全部门禁，可进入执行与授权

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 5/5 项 |
| next | **增长方案通过全部门禁，可进入执行与授权** | 输出字段 |
| funnel_count | **5** | 输出字段 |
| signal_count | **4** | 输出字段 |

## 1. funnel_count
> funnel_count 的判定与证据是什么？

- **funnel_count：**5

## 2. signal_count
> signal_count 的判定与证据是什么？

- **signal_count：**4

## 口径与边界

- **来源：**技能 diagnose/diagnose 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
