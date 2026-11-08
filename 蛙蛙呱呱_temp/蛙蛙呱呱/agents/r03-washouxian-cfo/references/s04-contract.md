# S04 合同与政策
> 蒸馏自: 补充技能/01-当前能力域/alirezarezvani__claude-skills/general-counsel-advisor/SKILL.md
>


## 方法论（来源 general-counsel-advisor contract_risk_scanner + term_sheet 要点清单）

### 12 条红线规则（contract.scan）

| # | 规则 | severity | 要点 |
|---|---|---|---|
| 1 | AUTO_RENEWAL | HIGH | 无上限自动续约锁定长期承诺 |
| 2 | AUTO_RENEWAL_NOTICE | CRITICAL | 60/90/180 天解约通知期实质剥夺退出权 |
| 3 | UNILATERAL_PRICE_CHANGE | CRITICAL | 单方任意调价 → 成本不可预算 |
| 4 | UNLIMITED_LIABILITY | CRITICAL | 无上限责任是生存性风险 |
| 5 | NO_TERMINATION_FOR_CONVENIENCE | MEDIUM | 剥夺便利终止权 |
| 6 | VAGUE_IP_OWNERSHIP | CRITICAL | 宽泛 IP 转让吞掉背景 IP 与复用资产 |
| 7 | UNCAPPED_CUSTOMER_INDEMNITY | CRITICAL | 无限补偿范围 = 无上限责任 |
| 8 | ONE_SIDED_INDEMNITY | HIGH | 单向补偿打破风险对价 |
| 9 | NON_COMPETE | HIGH | 过宽竞业不可执行 |
| 10 | EXCLUSIVE_DEALING | HIGH | 排他切断替代供应 |
| 11 | ASSIGNMENT_RESTRICTION | MEDIUM | 绝对禁转让阻碍并购重组 |
| 12 | NET_PAYMENT_TERMS | MEDIUM | net60+ 形成对供应商隐性融资 |

每条命中输出 matched 原文 + why + redline 建议。
**待签合同零 CRITICAL/HIGH 才可送签。**

### 政策门禁（contract.policy）

必填：purpose / scope / owner / review_cycle_days（≤365）/ enforcement。
enforcement 必须含可执行动作（阻止/拦截/拒绝/驳回），只写原则不合格。

### 整改跟踪（contract.redline）

- CRITICAL/HIGH 每条必须有状态：negotiated / accepted_risk / removed /
  rejected
- CRITICAL 接受风险须有 approver
- 全闭合或经审批接受后方可签署

### GC 关键问题清单（term_sheet 审查入口）

IP 归属、责任上限、DPA、终止/自动续约、监管触发条款。
**边界：本技能不出具正式法律意见，重大交易须外部律师。**

## 已验证算例（run_tests.py T09，已对拍）

- **scan**：`examples/contract_scan.json` → `critical_count=3`
  （命中 CRITICAL 红线 3 条），每条带 matched 原文 + why + redline。
- **sign gate**：待签合同存在 CRITICAL → `ok=false`（零 CRITICAL/HIGH
  才可送签）。
- **policy**：`examples/contract_policy.json` 字段齐全 → `ok=true`；
  缺 enforcement 可执行动作 → `ok=false`。
- **redline**：`examples/contract_redline.json` →
  `open_items=[{rule: NET_PAYMENT_TERMS}]`（未闭合的 MEDIUM 项），
  `ok=false`——未闭合项须 negotiated/accepted_risk/removed/rejected 之一。

## 实战踩坑

- 红线判定看**实质**不是关键词：合同写了「可终止」但附 180 天通知期，
  实质仍是 AUTO_RENEWAL_NOTICE（CRITICAL）——只按关键词匹配会漏判。
- policy 的 enforcement 若只写「严格遵守」，不合格：必须是可执行动作
  （阻止/拦截/拒绝/驳回），否则门禁形同虚设。
- CRITICAL 条款「接受风险」必须有 approver，否则 redline 不闭合，
  不能送签。
