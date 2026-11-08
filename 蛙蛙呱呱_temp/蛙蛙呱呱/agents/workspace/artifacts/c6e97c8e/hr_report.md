# [R16] 任务 c6e97c8e · 薪酬准备：input/calc

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

## payroll_input_count

```json
1
```

## gross_pay

```json
20000.0
```

## net_pay

```json
18000.0
```

## total_deduction

```json
2000.0
```

## employer_contribution

```json
0
```

## narrative

```json
"核算：毛额 20000 扣除 2000 净额 18000（待 R03/外部复核，非发放）"
```

## task_id

```json
"c6e97c8e"
```

## skill

```json
"payroll"
```

## action

```json
"calc"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "毛额恒等：声明 20000 = ΣEarning 20000",
    "dim": "payroll.gross",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "净额恒等：声明 18000 = 毛额 20000 − 扣除 2000 = 18000",
    "dim": "payroll.net",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "计薪天数 20 ≤ 计薪基数 22",
    "dim": "payroll.days",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "制度性字段均可溯源（凭空 无）",
    "dim": "payroll.system_source",
    "sev": "OK"
  }
]
```