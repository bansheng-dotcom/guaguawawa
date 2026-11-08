# 蛙智模 · evaluation/scorer
> 帮我看看这个客服助手评分器合不合格，评测口径对不对 

**结论**：next=模型工程工件通过全部门禁，可进入授权与交接

## 关键指标

| 指标 | 值 | 说明 |
|---|---|---|
| 门禁 | **PASS** | 5/5 项 |
| next | **模型工程工件通过全部门禁，可进入授权与交接** | 输出字段 |
| scorer_name | **answer_correctness** | 输出字段 |
| scorer_type | **llm_judge** | 输出字段 |

## 1. scorer_name
> scorer_name 的判定与证据是什么？

- **scorer_name：**answer_correctness

## 2. scorer_type
> scorer_type 的判定与证据是什么？

- **scorer_type：**llm_judge

## 3. feedback_source
> feedback_source 的判定与证据是什么？

- **feedback_source：**LLM_JUDGE

## 4. narrative
> narrative 的判定与证据是什么？

- **narrative：**评分器 answer_correctness：llm_judge / 来源 LLM_JUDGE

## 口径与边界

- **来源：**技能 evaluation/scorer 的确定性输出（无 LLM）。
- **边界：**结论仅基于本次输入的产出；未纳入的输入不参与判断。
