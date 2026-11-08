# 蛙交易 · signature/document
> 帮我看看这份电子签合同签完了没，有没有人没签 

**结论**：next=存在未通过门禁，按 checks 修复后重验

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **FAIL** | 4/5 项 |
| next | **存在未通过门禁，按 checks 修复后重验** | 输出字段 |
| document_count | **1** | 输出字段 |
| recipient_count | **2** | 输出字段 |

## 1. document_count
> document_count 的判定与证据是什么？

- **document_count：**1

## 2. recipient_count
> recipient_count 的判定与证据是什么？

- **recipient_count：**2

## 3. status
> status 的判定与证据是什么？

- **status：**COMPLETED

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**文件 （COMPLETED）签署人 2 名

## 口径与边界

- **来源：**技能 signature/document 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
