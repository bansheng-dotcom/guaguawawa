# [R14] 任务 229d38ae · 电子签与签署审计：document/signing

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

## document_count

```json
1
```

## recipient_count

```json
2
```

## status

```json
"COMPLETED"
```

## narrative

```json
"文件 （COMPLETED）签署人 2 名"
```

## task_id

```json
"229d38ae"
```

## skill

```json
"signature"
```

## action

```json
"document"
```

## 门禁

```json
[
  {
    "ok": false,
    "msg": "文件标题非空",
    "dim": "document.title",
    "sev": "BLOCKER"
  },
  {
    "ok": true,
    "msg": "文件状态='COMPLETED' 在白名单",
    "dim": "document.status",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "签署人 ≥1（实际 2）",
    "dim": "document.recipients",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "签署人角色在白名单（越界 无）",
    "dim": "document.role",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "签署人均有邮箱（缺 无）",
    "dim": "document.email",
    "sev": "OK"
  }
]
```