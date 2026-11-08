# 蛙全局 · decide/card
> 自助版定价决策卡评估 

**结论**：门禁未通过：1/2 项检查失败。

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **FAIL** | 1/2 项 |
| intent | **自助版定价决策卡评估 ** | 输出字段 |

## 1. intent
> intent 的判定与证据是什么？

- **intent：**自助版定价决策卡评估 

## 2. triage
> triage 的判定与证据是什么？

- {'level': 'strategy', 'domains': [], 'boardroom': None, 'next': None}

## 3. routing
> routing 的判定与证据是什么？

- {'roles': [], 'boardroom': False, 'next': '六问澄清先行'}

## 口径与边界

- **来源：**技能 decide/card 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
