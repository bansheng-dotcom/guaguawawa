# [R17] 任务 831ec68e · 人工审批节点：approval/publish

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

## publish_ready

```json
true
```

## narrative

```json
"发布门禁 acme-lead-sync：可发布"
```

## task_id

```json
"831ec68e"
```

## skill

```json
"approval"
```

## action

```json
"publish"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "workflow_name 非空",
    "dim": "publish.name",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "发布有显式请求或 live run 证据（requested=True, evidence=False）",
    "dim": "publish.gate",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "未验证节点已披露或不存在",
    "dim": "publish.disclosure",
    "sev": "OK"
  }
]
```