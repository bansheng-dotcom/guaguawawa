# [R19] 任务 2b81635f · 回归与发布候选：regression/candidate

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

## candidate_id

```json
"cand-2041-3"
```

## narrative

```json
"发布候选 cand-2041-3：裁决 PASS，3 条证据"
```

## task_id

```json
"2b81635f"
```

## skill

```json
"release"
```

## action

```json
"candidate"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "候选 ID 非空",
    "dim": "candidate.id",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "发布裁决='PASS' 在白名单 ['PASS', 'BLOCK', 'NEEDS_REVIEW']",
    "dim": "candidate.verdict",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "证据 ≥1（实际 3）",
    "dim": "candidate.evidence",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "PASS 裁决须挂回归报告",
    "dim": "candidate.regression_required",
    "sev": "OK"
  }
]
```