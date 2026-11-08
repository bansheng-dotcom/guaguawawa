# [R19] 任务 c16132d4 · 模型卡与资产证据：card/asset

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

## model_name

```json
"support-qa-assistant"
```

## risk_tier

```json
"medium"
```

## license_type

```json
"proprietary"
```

## narrative

```json
"模型卡 support-qa-assistant：风险 medium / 许可 proprietary"
```

## task_id

```json
"c16132d4"
```

## skill

```json
"modelcard"
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
    "msg": "模型名非空",
    "dim": "card.model_name",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "声明用途（intended use）",
    "dim": "card.intended_use",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "声明限制（limitations）",
    "dim": "card.limitations",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "风险分层='medium' 在白名单 ['low', 'medium', 'high']",
    "dim": "card.risk_tier",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "许可='proprietary' 在白名单 ['proprietary', 'open_source', 'research_only']",
    "dim": "card.license",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "声明已知偏差（known bias）",
    "dim": "card.known_bias",
    "sev": "OK"
  }
]
```