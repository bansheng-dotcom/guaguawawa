# regression-gate · 好结论范例

## 范例 1：回归证据齐全才放行

> 候选 cand-2041-3 通过发布裁决。
> - 回归报告 reg-2041-3：诊断层 instruction；旧版 v2 在「退货期限」用例上失败
>   （fail_before=true），新版 v3 同用例通过（pass_after=true），既有 28 项测试全绿
>   （existing_green=true）。
> - 证据链 3 条：评估集正确率 0.91→0.95、回归结论、既有测试结论。
> - 裁决 PASS（已挂 regression_id）。
> 移交：实际生产发布交 R09，业务取舍交 R06。

## 范例 2：证据不足退 NEEDS_REVIEW

> 候选 cand-2041-4 暂不能放行，退 NEEDS_REVIEW。
> - 缺回归报告：无 fail-before/pass-after 证据。
> - 证据链仅 1 条主观描述「试了几个问题效果不错」，不构成发布证据。
> 下一步：补齐回归测试（旧版失败、新版通过）后再裁。

## 范例 3：明确阻断

> 候选 cand-2041-5 裁决 BLOCK。
> - 回归回归失败：pass_after=false，新版在「退款金额」用例上仍失败。
> - 诊断层 knowledge：知识库缺退款规则片段。
> 移交：修复知识库后重跑回归。
