# [R14] 任务 0393413f · 支付服务端集成：payment_intent/refund

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
"交易工件通过全部门禁，可进入授权与交接"
```

## refund_count

```json
1
```

## amount

```json
29900.0
```

## refund_ratio

```json
0.2859
```

## narrative

```json
"退款 29900.0（比例 0.2859）前置 succeeded"
```

## task_id

```json
"0393413f"
```

## skill

```json
"payment"
```

## action

```json
"refund"
```

## 门禁

```json
[
  {
    "ok": true,
    "msg": "退款必填齐备（缺 无）",
    "dim": "refund.required",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "退款金额=29900.0 为正",
    "dim": "refund.amount",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "退款比例=0.2859 ≤ 1.0",
    "dim": "refund.ratio",
    "sev": "OK"
  },
  {
    "ok": true,
    "msg": "前置状态=succeeded 可退款",
    "dim": "refund.prior",
    "sev": "OK"
  }
]
```