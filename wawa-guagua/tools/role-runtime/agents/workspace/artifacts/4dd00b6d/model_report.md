# [R19] 任务 4dd00b6d · 评估数据集与评分器：dataset/scorer

## ok

```json
true
```

## verdict

```json
"PASS"
```

## next

```json
"模型工程工件通过全部门禁，可进入授权与交接"
```

## scorer_name

```json
"answer_correctness"
```

## scorer_type

```json
"llm_judge"
```

## feedback_source

```json
"LLM_JUDGE"
```

## narrative

```json
"评分器 answer_correctness：llm_judge / 来源 LLM_JUDGE"
```

## task_id

```json
"4dd00b6d"
```

## skill

```json
"evaluation"
```

## action

```json
"scorer"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "评分器名非空",
    "dim": "scorer.name",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "评分器类型='llm_judge' 在白名单 ['deterministic', 'llm_judge', 'code']",
    "dim": "scorer.type",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "声明评分目标（评什么维度）",
    "dim": "scorer.target",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "评分标准非空（判据）",
    "dim": "scorer.criteria",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "反馈来源='LLM_JUDGE' 在白名单 ['HUMAN', 'LLM_JUDGE', 'CODE', 'WEBHOOK']",
    "dim": "scorer.feedback_source",
    "sev": "OK"
  }
]
```