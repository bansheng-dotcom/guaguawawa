# AUTOMATION_SPEC.md - R17 自动化与集成单一信任源 (SSOT)

## 版本：v13.0
## 责任人 (DRI): R17 蛙织网 · 自动化与集成工程师

---

## 1. 北极星指标 (KPIs)
| 指标 | 名称 | 目标值 | 容差 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **WSR** | 工作流成功率 | >= 99.9% | 0.001 | 端到端成功运行实例 / 总触发数 |
| **CIR** | 凭据零泄露率 | = 100.0% | 0.00 | 明文 API Key 零泄露，强制凭据引用 |
| **IDE** | 写操作幂等覆盖率 | = 100.0% | 0.00 | 所有写动作强制幂等键 |
| **ZND** | 零悬空连接边比率 | = 100.0% | 0.00 | 工作流拓扑无悬空引用、无环 |
| **APR** | 高危操作审批阻断率 | = 100.0% | 0.00 | 生产发布/资金操作强制 HITL 审批 |

---

## 2. 8 维硬门禁刚性审查矩阵 (The 8-Dimension Gate Matrix)
| Gate ID | 名称 | 刚性阈值条件 |
| :--- | :--- | :--- |
| **GATE-01** | 悬空边与拓扑无环 | `dangling_edges == 0 and is_dag == True` |
| **GATE-02** | 明文凭据零容忍 | `plaintext_credentials_count == 0` |
| **GATE-03** | 写操作幂等保障 | `has_idempotency_key == True` |
| **GATE-04** | 未经审批擅自发布拦截 | `unapproved_publish == False` |
| **GATE-05** | 失败重试与死信兜底 | `0 <= max_retries <= 10 and has_dlq == True` |
| **GATE-06** | 字段映射合法性 | `target_fields in snake_case and no reserved_cols` |
| **GATE-07** | AI 节点护栏权限 | `has model, purpose, guardrail, and permission` |
| **GATE-08** | 全链路可观测审计 | `has trigger, input, execution, output, operator` |
