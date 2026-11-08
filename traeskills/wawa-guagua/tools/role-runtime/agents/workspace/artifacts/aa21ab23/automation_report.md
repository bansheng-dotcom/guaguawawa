# [R17] 任务 aa21ab23 · SaaS/API 集成：workflow/credential

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
"自动化工件通过全部门禁，可进入发布与交接"
```

## node_count

```json
3
```

## trigger_count

```json
1
```

## dangling_edges

```json
0
```

## narrative

```json
"工作流 acme-lead-sync：3 节点 / 1 触发器 / 悬空边 0"
```

## task_id

```json
"aa21ab23"
```

## skill

```json
"integration"
```

## action

```json
"workflow"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "节点数 3 ≤ 上限 200",
    "dim": "workflow.size",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "节点 name/type 齐备（异常 无）",
    "dim": "workflow.node_required",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "节点名唯一（重复 无）",
    "dim": "workflow.node_unique",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "至少 1 个触发器（找到 1）",
    "dim": "workflow.trigger",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "连接引用完整（悬空 无）",
    "dim": "workflow.connections",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "无明文密钥（命中 无）",
    "dim": "workflow.no_secret",
    "sev": "OK"
  }
]
```