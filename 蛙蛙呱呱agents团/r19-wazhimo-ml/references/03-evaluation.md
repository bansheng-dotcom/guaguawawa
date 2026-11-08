# 03 · 评估数据集与评分器口径（evaluation）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-evaluation/SKILL.md
>


> 技能：`evaluation` ｜ 动作：`dataset`（评估数据集）、`scorer`（评分器）
> 来源：mlflow__mlflow（`mlflow-evaluation` 的数据集准备、scorer 设计、judge 对齐；`mlflow-agent-improvement` 的评分器断言）

## 第一层：方法论

评估是**「效果看起来不错」进不了上线关卡的唯一钥匙**。数据集、评分器、判据、
反馈来源——这四样构成「这个模型到底好不好」的可比较地基。把这段做成确定性校验的
价值，不在于「评得更花哨」，而在于**让评不出来的评估在准备层就发不出来**。

三条方法论：

1. **数据集必须带 ground truth**。每条记录要有 `inputs`（预测入参）与
   `expectations`（期望事实/正确答案）。只有 inputs 没有 expectations 的数据集，
   正确性 scorer 无标可对——评出来的分是无根之木。
2. **评分器必须有类型 + 判据**。`scorer_type`（deterministic / llm_judge / code）
   决定"怎么评"，`criteria`（判据）决定"按什么评"，`target`（评分目标）决定
   "评什么维度"。三者缺一，评分器就是一个空壳。
3. **反馈来源必须可枚举**。`feedback_source`（HUMAN / LLM_JUDGE / CODE /
   WEBHOOK）说明评分结果是谁给的。来源不明 → 无法判断这个分是人工标注、LLM 判官
   还是程序算出来的，可解释性归零。

**本角色绝对不做的事**：**绝不产出「这个模型好不好」的结论**。R19 只产出评估集、
评分器、评分规则这些**工件**；好不好的结论来自**评估运行的结果**（评估运行 +
回归，见 s05 release）。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| dataset.dataset_id | 非空 | mlflow-evaluation |
| dataset.records | ≥ 1 条 | mlflow-evaluation |
| dataset.inputs | 每条记录含非空 inputs 字典 | mlflow-evaluation |
| dataset.expectations | 每条记录含非空 expectations 字典（ground truth） | mlflow-evaluation |
| scorer.scorer_name | 非空 | mlflow-evaluation |
| scorer.scorer_type | ∈ `evaluation.scorer_types` = `[deterministic, llm_judge, code]` | mlflow-evaluation |
| scorer.target | 非空（评分目标/维度） | mlflow-evaluation |
| scorer.criteria | 非空（判据） | mlflow-evaluation |
| scorer.feedback_source | ∈ `evaluation.feedback_sources` = `[HUMAN, LLM_JUDGE, CODE, WEBHOOK]` | mlflow-evaluation |

**阈值单一真源**：`evaluation.scorer_types` / `evaluation.feedback_sources` /
`evaluation.eval_modes` 以 `experience/thresholds.json` 的 `evaluation` 段为准。

## 第三层：已验证的算例

**算例 A（干净数据集）**：`examples/evaluation_dataset.json`
```
eval-support-qa-v1 / 3 条记录 / 每条 inputs + expectations
```
每条记录都带 ground truth → `ok=true`，`verdict=PASS`。

**算例 B（脏数据集）**：`examples/evaluation_dataset_dirty.json`
```
记录 1：有 inputs、expectations={}
记录 2：inputs={}、有 expectations
```
BLOCKER ×2：记录缺 expectations（无标可对）、记录缺 inputs（无预测入参）。

**算例 C（干净评分器）**：`examples/evaluation_scorer.json`
```
answer_correctness / llm_judge / target=response / source=LLM_JUDGE
```
类型与来源都在白名单、判据非空 → `ok=true`。

**算例 D（脏评分器）**：`examples/evaluation_scorer_dirty.json`
```
vibes_check / scorer_type=gut_feeling / target="" / criteria="" / source=VIBES
```
BLOCKER ×5：类型越界、target 空、criteria 空、来源越界。

## 第四层：实战踩坑

1. **expectations 必须是字典不是字符串**。有人把 `expectations` 写成一句
   `"回答要准确"`——这不是 ground truth，是没法对齐的模糊描述。口径：expectations
   是结构化字典（如 `{"expected_facts": [...]}`），scorer 能按键取值比对。

2. **inputs 空字典 ≠ 有输入**。`inputs={}` 是"没给入参"，`inputs={"q": ""}` 是
   "给了空问题"。前者 BLOCKER（无法产生预测），后者语义上仍偏空，属边界情况。

3. **`gut_feeling` 类评分器是红线**。评分器类型必须是可复现的
   （deterministic / llm_judge / code）。任何"凭感觉""凭经验"的评分方式都不在
   白名单内——这正是 R19 要拦的"效果看起来不错"。

4. **feedback_source 大小写敏感**。白名单是大写 `LLM_JUDGE` / `HUMAN`，写
   `llm_judge` 或 `human` 都会被拦。枚举值是精确匹配。

5. **llm_judge 的评分器要声明对齐方式**。用 LLM 当判官时，判据（criteria）应
   写清评分维度与档位，否则同一个 LLM 两次评分可能不一致——判官本身也需要被
   评估。

6. **不要在结论里写"这个模型比 v2 好"**。这是评估结论不是工件。正确写法：
   "产出评估集 eval-support-qa-v1 与评分器 answer_correctness，好坏结论待评估
   运行（s05）产出。"

7. **数据集与评分器是解耦的**。同一个评估集可以配多个评分器（正确性、相关性、
   延迟），校验时各自独立，不要假设"一个数据集配一个评分器"。
