# 好结论范例 · 采购超收争议

## 判例 1：超收 2% 内、有让步接收授权 → 可入账
```json
{
  "ok": true,
  "verdict": "PASS",
  "receipt_count": 1,
  "total_qty": 102,
  "handoff": "让步接收已由采购负责人签字授权，超收 2 件按损耗补发入账",
  "next": "按 102 件入库并生成 Stock Entry(Material Receipt)，To Bill 前挂对账待办"
}
```
要点：`received_qty=102 / ordered_qty=100`，容差 0.02 内且声明 handoff，账实可复算。

## 判例 2：超收 20%、无授权 → 拒绝直接入库
```json
{
  "ok": false,
  "verdict": "FAIL",
  "checks": [
    {"ok": false, "msg": "超收 item RM-001（收 120/订 100），容差 0.0", "dim": "receipt.over_receipt"},
    {"ok": false, "msg": "越界：采购/付款/改库存/冲销属人工授权，未声明 handoff", "dim": "review:execution_gate"}
  ],
  "next": "退回让步接收审批，声明授权后重验"
}
```
要点：只报门禁事实 + 处置路径，不下「要不要收」的商业结论。

## 判例 3：状态越界 → 结构即拦截
`status="Received"`（不在 Purchase Receipt 状态白名单）→ 直接 FAIL，不进入超收讨论。
先结构后语义，门禁顺序不可倒置。

---

# 经验沉淀
- **超收 ≠ 白送**：账实一致性的源头在「收 ≤ 订」，容差必须外置（thresholds.json）。
- **让步接收是授权动作**：R15 只产出请求工件，绝不替采购负责人拍板。
- **先白名单后算术**：状态越界时不要算比例，避免「越界数据算出看似合理结论」。
