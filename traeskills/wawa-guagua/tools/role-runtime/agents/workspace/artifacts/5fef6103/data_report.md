# 蛙数仓 · quality/check
> 帮我看看这批 orders 数据质量达不达标，空值率重复率有没有超 

**结论**：next=工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 6/6 项 |
| next | **工件通过全部门禁，可进入授权与交接** | 输出字段 |
| table | **orders** | 输出字段 |
| check_count | **1** | 输出字段 |

## 1. table
> table 的判定与证据是什么？

- **table：**orders

## 2. check_count
> check_count 的判定与证据是什么？

- **check_count：**1

## 3. row_count
> row_count 的判定与证据是什么？

- **row_count：**1000

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**质量门禁 orders：1 项检查

## 口径与边界

- **来源：**技能 quality/check 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
