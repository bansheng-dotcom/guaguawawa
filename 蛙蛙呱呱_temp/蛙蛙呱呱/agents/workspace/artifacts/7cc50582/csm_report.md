# [R13] 任务 7cc50582 · 销售管道：pipeline/opp

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
"客户运营工件通过全部门禁，可交付"
```

## opp_count

```json
4
```

## stage_count

```json
4
```

## open_count

```json
4
```

## weighted_value

```json
890000.0
```

## stale_count

```json
0
```

## concentration_hhi

```json
0.4199
```

## stage_distribution

```json
{
  "NEW": 0,
  "SCREENING": 1,
  "MEETING": 1,
  "PROPOSAL": 1,
  "NEGOTIATION": 1,
  "WON": 0,
  "LOST": 0
}
```

## top_accounts

```json
[
  {
    "company": "云启科技",
    "amount": 900000.0
  },
  {
    "company": "晨星零售",
    "amount": 450000.0
  },
  {
    "company": "山海物流",
    "amount": 250000.0
  }
]
```

## narrative

```json
"开放商机 4 条、加权管道值 890000.0、停滞 0 条、客户集中度 HHI=0.4199"
```

## task_id

```json
"7cc50582"
```

## skill

```json
"pipeline"
```

## action

```json
"pipeline"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "阶段全部在白名单（越界 无）",
    "dim": "pipeline.stage_enum",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "金额均为正数（异常 无）",
    "dim": "pipeline.amount",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "加权管道值=890000.0（开放阶段 4 条）",
    "dim": "pipeline.weighted",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "停滞商机占比=0.0 ≤ 0.3（停滞 无）",
    "dim": "pipeline.stall",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "停滞商机均写原因（缺 无）",
    "dim": "pipeline.stall_reason",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "开放商机均有下一步（缺 无）",
    "dim": "pipeline.next_step",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "开放商机均有负责人（缺 无）",
    "dim": "pipeline.owner",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "客户集中度 HHI=0.4199 ≤ 0.5（3 个客户）",
    "dim": "pipeline.concentration",
    "sev": "OK"
  }
]
```