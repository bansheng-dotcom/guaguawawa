# R20 发布硬门禁矩阵

- 账本版本：1.0.0
- 账本指纹：`ee375aede90fe6a1…`
- 北极星：可用率 0.999 / MTTR 30min / RTO 4h / RPO 1h

| 门禁 | 名称 | 维度 | 阈值 |
| --- | --- | --- | --- |
| G1 | 结构完整性 | structure | 工件为对象且 checks 非空 |
| G2 | SLO 口径一致 | slo | reliability metric ∈ [0,1] 且 >= 0.999 |
| G3 | 证据链完整 | evidence | 至少 1 条通过判据且带 dim/msg |
| G4 | 授权与交接 | authorization | 破坏性动作必须带 authorization/handoff |
| G5 | 回滚可执行 | rollback | 恢复类动作必须有 rollback_plan 且步骤 >= 1 |
| G6 | 可观测性 | observability | 须有 monitor/alert/telemetry 证据 |
| G7 | 值班与升级 | oncall | 须有 owner 与升级链（<= 3 级） |
| G8 | 卫生与凭据 | hygiene | 无凭据明文、无 TODO/待定 占位 |
