# R19 八维发布硬门禁矩阵

- 账本：ML_SPEC.md | SHA256：`ea0523c4dcd46b4f…` | 门禁数：8

| 门禁 | 名称 | 刚性标准 | 破坏处置 |
| :--- | :--- | :--- | :--- |
| **GATE-01** | 评估指标可复算门禁 | 记录含 expected/predicted 且混淆计数守恒 | 评估报告作废 |
| **GATE-02** | 证据链完整门禁 | verdict=PASS ⇒ evidence ≥ 1 | 降级 NEEDS_REVIEW |
| **GATE-03** | 回归门禁 | PASS ⇒ regression_id + fail_before/pass_after/existing_green | 退回补回归 |
| **GATE-04** | 资产可溯源门禁 | path 非空 + run_id 绑定 + sha256 可校验 | 禁止入库 |
| **GATE-05** | 凭据零泄露门禁 | 凭据词命中数 = 0 | 退回密钥管理 |
| **GATE-06** | 阶段唯一性门禁 | production 版本数 ≤ 1 | 回滚多余版本 |
| **GATE-07** | 枚举合规门禁 | verdict/stage/risk_tier/license 白名单 | 按白名单归一 |
| **GATE-08** | 越权移交门禁 | 发布动作声明 handoff / authorized_by | [REDLINE BLOCKED] |

## 北极星 KPI

| 代号 | 名称 | 目标 | 口径 |
| :--- | :--- | ---: | :--- |
| **ERA** | 评估可复算率 | 100.0% | confusion(tp+fp+tn+fn)=n 且 accuracy=(tp+tn)/n，容差 0.00 |
| **GGR** | 回归门禁通过率 | 100.0% | PASS ⇒ regression_id ∧ fail_before ∧ pass_after ∧ existing_green |
| **ATR** | 资产可溯源率 | 100.0% | assets[].path ∧ run_id ∧ sha256 |
| **CLR** | 凭据零泄露率 | 100.0% | credential_hits = 0 |
| **BTA** | 勾稽容差绝对值 | 0.00 | |delta| <= 1e-9 |
