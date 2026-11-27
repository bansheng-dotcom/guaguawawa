# 10 · PRD 八段与红队 premortem

> 服务 R07 W2 `pm_workflows/prd.py`。八门禁与存量 `skills/s03_prd.py` 同一出处。

## 1. 来源

- 升级方案 §10.3：`pm/workflows/prd-report/`（含 3 个模板）→ `workflows/prd/`；
  红队模板 `prd-red-team-premortem-template.md` → 本仓 `templates/PRD-PREMORTEM.template.md` 方向。
- 公开方法：Marty Cagan《Inspired》四风险（价值/可用/可行/商业）；
  Gary Klein 的 premortem（事前验尸）；Given/When/Then（Gherkin）。
- 本仓 SSOT：`PM_SPEC.md §4` 定义 problem / user / value / scope / metric /
  acceptance / risk / read 八门禁。

## 2. 八段 PRD

| 门禁 | 最低要求 | 常见缺失 |
|---|---|---|
| problem | 问题 + 场景，≥10 字，无「待定/TBD」 | 只写「优化体验」 |
| user | segment + scenario | 只有人群没有场景 |
| value | before / how / after | 只写「更好用」 |
| scope | P0 非空 + non_goals 非空 | **没有不在范围** |
| metric | 北极星 + baseline + target + guardrail | 只有目标没有基线 |
| acceptance | Given/When/Then 结构化 | 验收不可判定 |
| risk | ≥3 条承重假设 + 验证方式 | 假设无验证 |
| read | 结论摘要 ≥10 字 | 无摘要 |

## 3. 用户故事与验收

- 每条故事按 `as_a / i_want / so_that` 三段写；
- 验收条目 4~6 条（Job story 6~8 条）；
- 验收必须「有对象、有阈值、有判定人」。

## 4. 红队 premortem（新增硬门禁）

假设项目已经失败，倒推原因：

- ≥5 条失败原因；
- 每条必须有 `mitigation`（缓解措施）与 `owner`（责任人）；
- 只写「风险：可能失败」不算，必须能落到行动。

## 5. 适用边界

- 适用：0→1 新品、存量功能改造、跨团队交付前的需求冻结。
- 不适用：一句话 bug 修复、纯文案替换、已有明确验收的合规改造。
- premortem 不替代 R04 独立评审；它只暴露项目内部失败路径。

## 6. 误用反例

| 误用 | 表现 | 本仓拦截 |
|---|---|---|
| PRD 无不在范围 | `scope.non_goals = []` | `eight.scope` + `scope.non_goals`（BLOCKER） |
| 红队走过场 | 只有 3 条原因 | `premortem.count`（<5） |
| 原因无责任人 | mitigation 有、owner 空 | `premortem.owner`（BLOCKER） |
| 验收不可判定 | 「体验流畅」 | `eight.acceptance` |

误用样本见 `misuse/prd_no_non_goals.json`。
