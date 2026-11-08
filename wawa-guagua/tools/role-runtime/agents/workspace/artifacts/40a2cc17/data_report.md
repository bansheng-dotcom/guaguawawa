# [R18] 任务 40a2cc17 · 数据质量门禁：check/fresh

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
"数据管道工件通过全部门禁，可进入授权与交接"
```

## table

```json
"orders"
```

## check_count

```json
1
```

## row_count

```json
1000
```

## narrative

```json
"质量门禁 orders：1 项检查"
```

## task_id

```json
"40a2cc17"
```

## skill

```json
"quality"
```

## action

```json
"check"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "表名非空",
    "dim": "quality.table",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "行数 1000 > 0",
    "dim": "quality.row_count",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "空值率 0.02 ≤ 0.1",
    "dim": "quality.null_ratio",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "重复率 0.01 ≤ 0.05",
    "dim": "quality.dup_ratio",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "无效值 0 = 0",
    "dim": "quality.invalid",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "检查条目全通过且带实测值（未过 无）",
    "dim": "quality.items",
    "sev": "OK"
  }
]
```