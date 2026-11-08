# [R16] 任务 2bcc16c2 · 考勤与休假：attendance/leave

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
"人事工件通过全部门禁，可进入授权与交接"
```

## leave_count

```json
1
```

## status

```json
"Approved"
```

## overlap_count

```json
0
```

## narrative

```json
"请假 EMP-0001（Approved）2026-11-20 → 2026-11-22"
```

## task_id

```json
"2bcc16c2"
```

## skill

```json
"attendance"
```

## action

```json
"leave"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "请假必填齐备（缺 无）",
    "dim": "leave.required",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "请假状态='Approved' 在白名单",
    "dim": "leave.status",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "起始日期可解析",
    "dim": "leave.from",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "结束日期可解析",
    "dim": "leave.to",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "起始不晚于结束",
    "dim": "leave.order",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "请假天数恒等：声明 3 = 实算 3",
    "dim": "leave.identity",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "请假 3 天 ≤ 余额 10 天",
    "dim": "leave.balance",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "请假区间无重叠（重叠 无）",
    "dim": "leave.overlap",
    "sev": "OK"
  }
]
```