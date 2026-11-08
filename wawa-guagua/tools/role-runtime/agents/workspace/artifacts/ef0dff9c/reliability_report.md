# [R20] 任务 ef0dff9c · 灾难恢复与回滚接口：rpo_rto/rollback

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

## rollback_plan

```json
"切回主站并回滚配置"
```

## step_count

```json
2
```

## narrative

```json
"回滚计划：2 步骤"
```

## task_id

```json
"ef0dff9c"
```

## skill

```json
"dr"
```

## action

```json
"rollback"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "回滚计划非空",
    "dim": "rollback.plan",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "回滚步骤 ≥1（实际 2）",
    "dim": "rollback.steps",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "回滚含人工决策点（不擅自执行灾难切换）",
    "dim": "rollback.human_decision",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "回滚步骤无环（Kahn 拓扑）",
    "dim": "rollback.acyclic",
    "sev": "OK"
  }
]
```