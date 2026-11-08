# 模块C · 硬决策与可逆性
> 蒸馏自: 补充技能/alirezarezvani__claude-skills/ceo-advisor.md
>


> 整合自 c-level-agents 的 decide / hard-call / cross-eval / freeze。
> 核心主张：**按可逆性分级、先求尽调更高 bar、反方质询先行、不可逆必须你授权**。

## C1. 决策可逆性分级

| 级 | 定义 | 例 | 门槛 |
|---|---|---|---|
| 可逆（双向门） | 试错→学习→调整，代价低 | 换供应商、改策略 | 快速决策 |
| 部分可逆 | 能撤销但很痛 | 重组、换分工 | 中度尽调 |
| 不可逆（单向门） | 无法撤销 | 裁员、关停锁定产品 | 尽调更全、bar 更高 |

**决策前必答五问**：①能撤销吗、代价多大？②是否把可逆决策当成不可逆在拖延（是＝逃避）？
③真 pivot 还是优化？④一次性重置还是衰退开端？⑤一次砍深够了吗（不够深＝两轮，毁信任）？

## C2. 反方质询（Red Team）

- **Phase 2 隔离**先行（各角色独立出立场，不限他人观点，防锚定），再交叉质询（CFO 审数、
  CISO 审风险、CPO 审 JTBD）。
- 魔鬼代言人对领先方案输出 3 条顾虑分级 `CRITICAL/HIGH/MEDIUM` + 缓解预案。
- 高风险不可逆必做**多模型交叉评估**：同 memo 送多模型独立评审，各出「3 顾虑+3 支持+投票
  APPROVE/REJECT/DEFER」。裁决：🟢≥2 APPROVE 且无 CRITICAL→GO；🟡任一 DEFER/CRITICAL→PAUSE；
  🔴≥2 REJECT→STOP。
- **Andy Grove 测试**：假设明天被换掉、新 CEO 上任会怎么做？用无沉没成本外视角找「显眼的对」。

## C3. 硬决策问句集（无好选项时）

- 10/10/10：10 分钟感受（最不可靠）/ 10 个月影响 / 10 年后回看（最可靠）。
- **预公告测试**：先写出公告信「我们做这个决定是因为……」——立不住＝没准备好。
- 利益相关方影响映射：员工/留任/客户/投资人/自己 × 各选项影响。
- 沟通计划：谁最先知道（被直接影响者优先）→ 如何告知（对人当面绝不邮件）→ 说什么 → 之后发生什么。

## C4. 何时升级给人类

不可逆、高成本可逆、拆分董事会投票、gut-feel 推翻顾问一致 → **必须人工签发**。
大额资金/裁员/受监管市场/条款书 → 人批准后走 `/decide` 留证。
快速判断：**反转成本 > 6 个月公司时间** → 升级 cross-eval + 人工。
## 已验证算例（run_tests.py S03/S04，已对拍）

- 「签约新供应商并扣款」命中不可逆关键词 → `reversibility=不可逆`，动作=「需你最终授权，禁止自动执行」。
- 决策卡负例：`reversibility=不可逆` 且 `rollback_plan=""` → CRITICAL——不可逆无回滚预案直接拦。
- 升级判定：不可逆+9 个月反转成本 → `must_escalate=true`；可逆+1 个月 → 无需升级；应升级未声明 `human_signoff_required` → CRITICAL。
- 交叉评估三分支：APPROVE×2 → GO；任一 DEFER → PAUSE；REJECT×2 → STOP（run_tests 各分支逐一验证）。

## 实战踩坑

- crosseval 初版只看「APPROVE≥2 且无 CRITICAL」，漏了「任一 DEFER → PAUSE」——评审弃权就是没尽调，不能当放行，已修。
- 对抗评审（T7）发现「建议立即裁员」类未授权不可逆建议：`failure_category=unauthorized_or_irreversible`，回 writer 补人工签发声明。
- 升级阈值（escalate_cost_months）与可逆性关键词表以 `experience/thresholds.json → decide` 为准，本文不手抄。

## 经营与硬决策 (Hard Decisions)
- **可逆性决策框架 (Reversibility Framework)**：
  - **单向门 (One-way door)**：不可逆决策（重组、大额并购）。需深度分析、多方会审。
  - **双向门 (Two-way door)**：可逆决策（产品迭代）。追求速度、敏捷试错。
- **魔鬼代言人 (Devil's Advocate)**：
  - 对完美提议进行最坏情况推演（Bear Scenario）。
  - 如果计划彻底失败，最大的导火索是什么？有什么止损方案？
- **资源分配 (Capital Allocation)**：不匹配波次规划（Wave Planning）优先级的决策一律否决 (No-Go)。
