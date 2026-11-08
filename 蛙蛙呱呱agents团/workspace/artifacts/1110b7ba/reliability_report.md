# 蛙值守 · restore/drill
> 帮我做一次恢复演练，看看能不能真恢复出来 

**结论**：next=可靠性工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 4/4 项 |
| next | **可靠性工件通过全部门禁，可进入授权与交接** | 输出字段 |
| drill_id | **drill-001** | 输出字段 |
| restored_count | **150.00** | 输出字段 |

## 1. drill_id
> drill_id 的判定与证据是什么？

- **drill_id：**drill-001

## 2. restored_count
> restored_count 的判定与证据是什么？

- **restored_count：**150.00

## 3. result
> result 的判定与证据是什么？

- **result：**success

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**恢复演练 drill-001：恢复 150 文件，结果 success

## 口径与边界

- **来源：**技能 restore/drill 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
