> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 角色能力决策（REPORT-CAPABILITY-DECISIONS.md）

> 版本：v0.1 · 2026-11-17
> 依据：`python guagua.py report capabilities`（20 角色 / 195 技能 / 94 可进报告）
> 结论：**不强行把 20 个角色塞进报告；用 coverage 说真话。**

---

## 1. 四个“不进报告”角色

| 角色 | 可进报告技能 | 现状 | 决定 | 后果 |
|---|---|---|---|---|
| **r08 蛙建成**（MVP） | 1/10 | `enters=false` | **执行角色，不进报告** | `mvp.*` 四个能力 blocked；MVP/上线类报告写 gap |
| **r09 蛙稳码**（工程） | 0/8 | `enters=false` | **执行角色，不进报告** | `tech.spec` / `tech.test` blocked；技术类报告写 gap |
| **r10 蛙成美**（设计） | 1/14 | `enters=false` | **执行角色，不进报告** | `brand.tokens` blocked；品牌硬证据写 gap |
| **r17 蛙织网**（自动化） | 1/9 | `enters=false` | **执行角色，不进报告** | `integration.contract` / `integration.webhook` blocked；集成类报告写 gap |

---

## 2. 为什么不“补人”

把 r09 硬标成“进报告”，只会得到两种结果：

1. 报告里出现没有证据的技术结论（假 depth）；
2. 门禁把“角色出现”当“能力覆盖”（假 coverage）。

两者都比“写 gap”更糟。**缺能力就写缺能力，缺证据就写缺证据。**

---

## 3. 什么条件下可以恢复

| 角色 | 恢复条件（可验收） | 对应能力 |
|---|---|---|
| r08 | 交付 `kill_criteria.json` + `learning.json`，且能被 claim card 引用 | `mvp.slice` / `mvp.learning` |
| r09 | 交付 `test_report.json` + `diff_summary.json`，且有可复跑命令 | `tech.spec` / `tech.test` |
| r10 | 交付 `brand_token_audit.json`（令牌/对比度/尺寸阶梯） | `brand.tokens` / `brand.consistency` |
| r17 | 交付 `webhook_retry_log.json`（幂等/重试/死信） | `integration.webhook` |

恢复不是改 `enters=true`，而是**先有可进报告的证据契约**，再把 `enters` 打开。

---

## 4. 两个“只做草案/定性”角色

| 角色 | 状态 | 能进报告的部分 | 不能进的部分 |
|---|---|---|---|
| r11 蛙点题（内容） | `simulated` | 受众/选题/结构建议（观察节） | 品牌合规、效果承诺（标题/动作） |
| r14 蛙交易（交易） | `simulated` | 订单三态、退款/对账的本地校验 | 真实支付/履约结果（无外部系统） |

---

## 5. 一个“薄”角色

| 角色 | 可进报告技能 | 处理 |
|---|---|---|
| r03 蛙守线（CFO/合规） | 1/8 | 财务类结论必须与 r06 的口径/数据共同出具；单独用 r03 时标 `thin`，不单独支撑头条 |

---

## 6. 决策

1. **P2/P3 期间保持现状**：4 个 blocked、2 个 simulated、1 个 thin；
2. **报告遇到 blocked 能力时写 gap**，coverage 判 `INCOMPLETE`；
3. **P4 扩维度时再评估**：是否给 r09/r10/r17 补“证据契约”，而不是补“角色标签”；
4. **任何恢复都必须过 claim card**：没有 `refs` + `falsifier` 的证据，不算恢复。
