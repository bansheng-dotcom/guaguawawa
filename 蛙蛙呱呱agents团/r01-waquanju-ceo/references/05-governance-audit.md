# 模块E · 治理与审计（AI 治理）
> 蒸馏自: 补充技能/alirezarezvani__claude-skills/ceo-advisor.md
>


> 整合自 microsoft/agent-governance-toolkit 的治理成熟度模型、意向授权、漂移检测。
> 核心主张：**策略即代码、default-deny、意向授权四步闭环、越界即被发现并截停**。

## E1. 治理成熟度分级

| 等级 | 关键能力 | 护栏落地 |
|---|---|---|
| L0 无治理 | 仅 prompt | `max_tool_calls` 上限、默认 deny |
| L1 基础护栏 | 限流+过滤+kill switch | 硬编码上限 |
| L2 策略即代码 | YAML 策略版本化、CI 测试、审计日志 | `default action: deny` |
| L3 信任感知 | 身份+能力委派+信任分 | 最小权限、HITL 超时 |
| L4 自治 | 自监控+自动修复+事件报告 | 违规→收权/升级/停机 |

**硬边界（不可弱化）**：永不弱化安全默认/信任阈值/评审要求；永不提交密钥凭证；信任阈值只上调。

## E2. 决策留痕与可追溯

- 两层模型（见模块 D4）：所有辩论(原始层) vs 只批准决策(已批准层)，防「未决之争」被当决策回灌。

## E3. 意向授权（Intent-Based Auth）

`declare(声明将做) → approve(人/策略批准) → check(每动作对照计划) → verify(计划 vs 实际对账)`。
verify 输出 planned/executed/unplanned/missed/drift + 信任扣分。
**漂移三档**：`SOFT_BLOCK`(放行但扣分)、`HARD_BLOCK`(拒)、`RE_DECLARE`(拒并要求重声明)。
**子任务范围收窄**：子代理意图必须为父意图子集，越界在 declare 时抛 `ScopeError`。

## E4. 权限边界与最小权限

- 每角色只授完成工作所需工具权限（只读角色无 Bash/全状态）。
- 代理身份零信任：密码学身份(Ed25519/DID)，公钥「持有证明」校验；DID 由密钥派生，不信任客户端自供公钥。
- **信任分五维**：competence / integrity / availability / predictability / transparency。

## E5. 不可逆动作授权与失败预案

- **冷却锁 freeze**（防冲动再决策）：募资 30d / 定价 60d / 市场进出 & 战略 pivot 90d / 裁员 30d。
  锁定期间拒绝重议，除非杀死标准触发或创始人显式 `freeze release`（强制解锁**永久留痕**）。
- **失败预案 = 预承诺杀死标准**：指标+阈值+触发动作；触发即停，不合「再优化一下」。
- 护栏兜底：kill switch / freeze / DO_NOT_RESURFACE / default-deny / 审计日志。

---

> 本角色的运行时护栏由 `decide`（可逆性分级）+ `freeze` 冷却语义 + 事件流 `decision_log` 承载；
> 正式的代理身份与漂移检测由 R17 蛙织网 / R19 蛙智模在运行时落地。
## 已验证算例（run_tests.py S05/T7，已对拍）

- 冷却锁的治理语义全部可确定性复现：期内重议拒绝、超期放行、杀死标准触发放行、强制解锁未留痕 CRITICAL（四分支各有断言）。
- default-deny + audit_log 缺失 → OS 门禁 fail（护栏组件化，不靠自觉）。
- 对抗评审的不可逆门禁：出现「签约/扣款/裁员」等词但结果无 `human_signoff_required` → FAIL 并路由回 writer——CEO 边界（不替创始人做不可逆决定）落成机器判据。

## 实战踩坑

- freeze 的「创始人显式解锁」必须双字段（`founder_release` + `release_logged`）：只解锁不留痕等于绕过治理，判 CRITICAL。
- 治理成熟度分级（L0-L4）本轮作为参考口径保留，未做成硬门禁——等 R17/R19 运行时接入后有真实漂移数据再落码，避免预先堆不可验证的检查。
- 冷却锁天数以 `experience/thresholds.json → companyos.freeze_days` 为准，本文表格仅示意。

## 决策留痕与复盘 (Decision Log & Audit)
- **决策日志要求**：
  - 背景与时间 (Context & Date)
  - 最终决定 (Decision)
  - 放弃的备选项及原因 (Rejected alternatives & Why)
  - 期望的短期与长期结果 (Expected outcomes)
- **董事会与融资 (Boardroom Memo)**：
  - 数据要冷酷真实 (Know your numbers cold)。
  - 融资时机 (Timing) 大于估值博弈 (Valuation)。必须在跑道充足时启动。
