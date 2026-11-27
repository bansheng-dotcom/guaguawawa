# R14 黄金成品（golden）：状态机报告 + 对账报告

两份 HTML 由 `commerce_fsm.py` 真跑三条交易链与一次对账后导出；
`golden/commerce-run.json` 是同一轮的机器可读结果。

```bash
cd r14-wajiaoyi-commerce
python commerce_fsm.py goldens                    # 重建两份 HTML + commerce-run.json
python commerce_fsm.py run    --input <ops.json>  # 跑一条状态机链
python commerce_fsm.py recon  --input <orders+payments.json>
python commerce_fsm.py check  --case misuse/illegal-transition.json
```

| 文件 | 内容 | 验收点 |
|---|---|---|
| `commerce-state-machine.html` | 6 态迁移表 + 三条链（正常成交 / 全额退款 / 超时重放）+ 逐步明细 | 三链终态 `closed`；未支付发货被 T01、同键换额被 T03；幂等不重复扣款 |
| `commerce-reconciliation.html` | 对账：五类差异汇总 + 明细 + 处置建议 | 缺失/孤儿/重复/金额/状态 各 1 项，定位到具体订单 |
| `commerce-run.json` | 三条链逐步结果 + 对账分类 | `ok=true`，`diff_total=5` |

## 三条交易链

1. **正常成交**：create → charge → fulfill → close；
2. **全额退款**：create → charge → refund 30 → refund 169 → close；
3. **超时重放 + 非法企图**：未支付先发货（T01）、支付、同键重放（幂等）、
   同键换金额（T03）、履约、关闭。

## 对账夹具（确定性）

5 笔订单 × 6 笔支付流水，预埋五类差异：
`SO-1003` 缺流水、`SO-9999` 孤儿流水（对应 P-06）、`SO-1005` 重复支付、
`SO-1002` 金额 189≠199、`SO-1004` 未支付却有成功流水。

## 误用样本（misuse/）

| 文件 | 故意违规 | 期望错误码 |
|---|---|---|
| `illegal-transition.json` | 未支付就发货 | `T01_ILLEGAL_TRANSITION` |
| `duplicate-charge.json` | 同一幂等键换金额重放 | `T03_DUPLICATE_CHARGE` |
