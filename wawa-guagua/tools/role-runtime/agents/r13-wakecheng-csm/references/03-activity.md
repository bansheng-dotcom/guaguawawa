# s03 销售活动与跟进（activity / log）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/log-activity/SKILL.md
>


来源沉淀：`twentyhq__twenty` —— `task.workspace-entity.ts`（任务截止/负责人/状态）/
`note` / `timeline-activity`（活动记录与互动时间线）。只取「承诺—截止—负责人」的
三件套语义与活动类型枚举，不取任务通知实现。

## 一、方法论（什么时候用、核心口径）

跟进的价值不在于「记了流水账」，而在于**说过的每一句话都有 what/owner/due 三件套**。
只有 what 没有 owner，就是没人做；只有 owner 没有 due，就是无限期；只有 due 没有
what，就是交差。所以本能力域做两件事：

- `activity`：校验一批跟进活动——类型白名单、承诺三件套、逾期识别、开放商机覆盖。
- `log`：校验单条活动记录——类型、承诺、日期可解析、摘要非空。

立场：**逾期用确定性日期差实算**（`datetime.date.today()` 与 due 的日差，宽限 1 天），
不靠人判断「算不算逾期」。另一个关键判据是**开放商机活动覆盖**：一条开放商机一条活动
都没有，就是失联商机——这比逾期更致命。

边界：本角色只校验跟进事实，不评价销售个人能力；不替 R02 排期。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `activity` 节：

- `activity_types`：`meeting / email / call / task / note / demo`
- `commitment_required`：`what / owner / due`
- `followup_window_days`：7；`overdue_grace_days`：1；`min_activities_per_open_opp`：1

**activity 校验规则**：
- 任一 `type` 越界 → BLOCKER。
- 任一活动三件套有空项 → BLOCKER。
- `(today − due).days − grace > 0` → 逾期 → BLOCKER（不可解析的日期不计入逾期）。
- 提供 `open_opportunities` 时，任一商机未被任何活动的 `opportunity` 字段覆盖 → BLOCKER。

**log 校验规则**：类型在白名单、三件套齐备、`due` 可被 `date.fromisoformat` 解析、
`summary` 非空。

**输出键**：activity → `activity_count / overdue_count / next_due`；log → `activity_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

- `examples/activity.json`：3 条活动（meeting/email/call），承诺齐备，覆盖「CRM 平台迁移」
  与「客服系统升级」两条开放商机 → `activity_count=3`、`overdue_count=0`、ok=true。
- `examples/log.json`：meeting + due=2026-11-10 + 摘要非空 → ok=true。
- `examples/activity_dirty.json`：due=2020-01-01 已逾期 + 「未覆盖商机」无活动 →
  命中 `activity.overdue` 与 `activity.coverage`，ok=false / exit 1。
- `examples/log_dirty.json`：类型 `nope`、what/owner/summary 全空、due=`not-a-date` →
  四条 BLOCKER 全中。

## 四、实战踩坑（真拦下来的教训）

- **日期可解析 ≠ 未逾期**：这是两个检查。日志里 due 写成「下周三」这种自然语言，
  先判不可解析；只有合法 ISO 日期才进入逾期计算。
- **逾期宽限 1 天是真的必要**：当天到期的活动在当天晚上跑批，会全部误报逾期。
- **覆盖检查比逾期检查更早发现问题**：一条开放商机一条活动都没有，通常意味着
  商机已死但阶段没改——这是管道失真的根源之一。
- **log 的 due 是「跟进日期」不是「创建日期」**：混用会让逾期统计整体失真。

## 五、给下游的交接

- 逾期清单 + 失联商机清单 → R13 自己的 `pipeline` 与 `health` 复核。
- 连续两次逾期的商机 → 升级单交 R07（产品侧阻塞）或 R02（资源排期）。
