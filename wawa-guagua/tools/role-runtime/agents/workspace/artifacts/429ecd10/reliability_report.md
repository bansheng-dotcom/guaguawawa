# [R20] 任务 429ecd10 · 恢复演练：restore/drill

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
"可靠性工件通过全部门禁，可进入授权与交接"
```

## drill_id

```json
"drill-001"
```

## restored_count

```json
150.0
```

## result

```json
"success"
```

## narrative

```json
"恢复演练 drill-001：恢复 150 文件，结果 success"
```

## task_id

```json
"429ecd10"
```

## skill

```json
"restore"
```

## action

```json
"drill"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "演练 ID 非空",
    "dim": "drill.id",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "恢复文件数 > 0（实际 150）",
    "dim": "drill.restored",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "演练结果='success' ∈ {success,failure}",
    "dim": "drill.result",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "成功演练带校验和一致性证据",
    "dim": "drill.checksum",
    "sev": "OK"
  }
]
```