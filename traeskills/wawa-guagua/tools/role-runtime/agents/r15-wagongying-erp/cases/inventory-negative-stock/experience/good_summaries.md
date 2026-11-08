# 好结论范例 · 库存负库存（超卖）

## 判例 1：负库存、有盘点授权 → 产出调整请求
```json
{
  "ok": false,
  "verdict": "FAIL",
  "bin_count": 1,
  "stock_value": -27.5,
  "handoff": "盘点授权已签发，待仓管实物点数后生成调整凭证",
  "next": "出 Stock Entry 调整请求（Material Issue 冲正），点数后经授权入账"
}
```
要点：负库存本身必须 FAIL（门禁拦截），但处置路径给出「调整请求 + 授权」，不直接改台账。

## 判例 2：负库存、无授权 → 双 BLOCKER
```json
{
  "ok": false,
  "verdict": "FAIL",
  "checks": [
    {"ok": false, "msg": "负库存 RM-001@华东原料库（actual=-5）", "dim": "bin.negative_stock"},
    {"ok": false, "msg": "越界：采购/付款/改库存/冲销属人工授权，未声明 handoff", "dim": "review:execution_gate"}
  ],
  "next": "先补盘点授权，再出调整请求"
}
```
要点：`allow_negative_stock=false` 下负库存必拦；无授权改库存是第二重红线。

## 判例 3：守恒式被破坏 → 直接拦截
`actual=-5 / ordered=0 / reserved=0 / planned=0` 但 `projected=-5` 时守恒式成立；
若 `projected=0` 则守恒被破坏，先报「预计量守恒」BLOCKER，再报负库存。
先守恒后负库存，门禁顺序决定根因定位。

---

# 经验沉淀
- **负库存是结果，不是原因**：先定位根因（出库未校验 / 入账错误），再谈处置。
- **改台账是授权动作**：R15 只产出调整请求，绝不直接改 `actual_qty`。
- **守恒式是地基**：`projected = actual + ordered + planned − reserved` 必须可复算。
