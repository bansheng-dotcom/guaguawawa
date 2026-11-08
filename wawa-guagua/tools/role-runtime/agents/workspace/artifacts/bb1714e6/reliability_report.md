# [R20] 任务 bb1714e6 · 加密增量备份：backup/snapshot

## ok

```json
false
```

## verdict

```json
"FAIL"
```

## next

```json
"存在未通过门禁，按 checks 修复后重验"
```

## repo

```json
"/backups/repo"
```

## snapshot_count

```json
0
```

## snapshot_id

```json
""
```

## narrative

```json
"备份仓 /backups/repo：0 快照"
```

## task_id

```json
"bb1714e6"
```

## skill

```json
"backup"
```

## action

```json
"snapshot"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "备份仓路径非空",
    "dim": "snapshot.repo",
    "sev": "OK"
  },
  {
    "ok": false,
    "msg": "快照 ≥1（实际 0）",
    "dim": "snapshot.count",
    "sev": "BLOCKER"
  },
  {
    "ok": true,
    "msg": "快照含 snapshot_id/ts（缺 无）",
    "dim": "snapshot.required",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "快照 ID 唯一",
    "dim": "snapshot.unique",
    "sev": "OK"
  }
]
```