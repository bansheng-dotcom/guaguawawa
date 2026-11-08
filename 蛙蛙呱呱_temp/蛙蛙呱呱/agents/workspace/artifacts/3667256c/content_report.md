# [R11] 任务 3667256c · 文案与长文：article/script

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

## char_count

```json
662
```

## profile

```json
"article"
```

## forbidden_count

```json
0
```

## task_id

```json
"3667256c"
```

## skill

```json
"copy"
```

## action

```json
"article"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "以 # 标题开头",
    "dim": "copy.title",
    "sev": "OK"
  },
  {
    "ok": false,
    "msg": "字数 662 ≥ 800",
    "dim": "copy.length",
    "sev": "BLOCKER"
  },
  {
    "ok": true,
    "msg": "无 AI 味禁词（命中 无）",
    "dim": "copy.forbidden",
    "sev": "OK",
    "hits": []
  },
  {
    "ok": true,
    "msg": "摘要/结论段含具体数字",
    "dim": "copy.summary",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "含延伸阅读/后续阅读",
    "dim": "copy.structure",
    "sev": "OK"
  }
]
```