# [R01] 任务 5d737576 · 经营与硬决策：reversibility/card/escalate

## ok

```json
false
```

## intent

```json
"自助版定价决策卡评估 "
```

## triage

```json
{
  "level": "task",
  "domains": [],
  "boardroom": false,
  "next": "六问澄清先行"
}
```

## routing

```json
{
  "roles": [],
  "boardroom": false,
  "next": "六问澄清先行"
}
```

## task_id

```json
"5d737576"
```

## skill

```json
"decide"
```

## action

```json
"card"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "目标分层=task",
    "dim": "triage.level",
    "sev": "OK"
  },
  {
    "ok": false,
    "msg": "命中至少一个职能域（否则先六问）",
    "dim": "triage.domain",
    "sev": "BLOCKER"
  },
  {
    "ok": true,
    "msg": "单职能域 → 直接指派",
    "dim": "triage.boardroom",
    "sev": "OK"
  },
  {
    "ok": false,
    "msg": "无法命中任何角色 → 先六问澄清再路由",
    "dim": "route.match",
    "sev": "BLOCKER"
  }
]
```