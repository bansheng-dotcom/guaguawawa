# 蛙人事 · recruit/offer
> 帮我看这份录用通知能不能发，候选人前置状态合不合法 

**结论**：next=人事工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 4/4 项 |
| next | **人事工件通过全部门禁，可进入授权与交接** | 输出字段 |
| offer_count | **1** | 输出字段 |
| status | **Accepted** | 输出字段 |

## 1. offer_count
> offer_count 的判定与证据是什么？

- **offer_count：**1

## 2. status
> status 的判定与证据是什么？

- **status：**Accepted

## 3. narrative
> narrative 的判定与证据是什么？

- **narrative：**录用 张三（Accepted）职位 R9 代码工程官

## 口径与边界

- **来源：**技能 recruit/offer 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
