# [R12] 任务 15d9101c · 增长诊断与基线：diagnose/unit

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
"增长方案通过全部门禁，可进入执行与授权"
```

## funnel_count

```json
5
```

## signal_count

```json
4
```

## task_id

```json
"15d9101c"
```

## skill

```json
"diagnose"
```

## action

```json
"diagnose"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "北极星指标一主一辅齐备",
    "dim": "diagnose.northstar",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "漏斗阶段 ≥1（实际 5）",
    "dim": "diagnose.funnel",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "漏斗阶段在白名单（越界 无）",
    "dim": "diagnose.funnel_enum",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "PMF 信号 ≥1（实际 4）",
    "dim": "diagnose.pmf",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "PMF 信号在白名单（越界 无）",
    "dim": "diagnose.pmf_enum",
    "sev": "OK"
  }
]
```