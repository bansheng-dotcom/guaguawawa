# 07 · 运行复盘口径（postmortem）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/skills/incident-response/SKILL.md
>


> 技能：`postmortem` ｜ 动作：`postmortem`（复盘结构）、`improvement`（改进项闭环）
> 来源：故障复盘（blameless postmortem）语义 + R20 运行复盘纪律

## 第一层：方法论

复盘层定义**故障后学什么、改进项怎么闭环**。把这段做成确定性校验的价值，
不在于"写得更煽情"，而在于**让四要素缺失的复盘和永远 open 的改进项进不了
知识库**——一份没有根因的复盘等于"我出过事，但不知道为什么"；一条永远
open 的改进项等于"我反思了，但什么都不会改"。

三条方法论：

1. **复盘是「学习」，不是「追责」**（blameless）。本角色只校验复盘结构是否
   成立、改进项是否可追踪闭环，不替 R02/R09 定性责任、不写结论性归因
   （根因描述 ≠ 责任认定）。
2. **四要素是复盘的骨架**：timeline（时间线）、root_cause（根因）、impact
   （影响）、actions（改进项）。缺一不可。
3. **改进项必须可追踪闭环**：每条带 owner + due + status，且无 open 未闭环。
   只产出"反思"不产出"改进"的复盘没有价值。

**本角色只校验复盘结构，不追责、不写结论性归因**。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| postmortem_id | 非空字符串 | 复盘标识 |
| severity | ∈ `postmortem.severities`（sev1/sev2/sev3） | 严重度分级 |
| 四要素 | timeline/root_cause/impact/actions 全部非空 | 复盘骨架 |
| root_cause | 非空（且非复述现象） | 根因 |
| improvement.actions | ≥ 1 条 | 改进项集 |
| 每条 action | 含 action/owner/due/status | 可追踪结构 |
| status | ∈ {open, done, wontfix} | 闭环状态枚举 |
| closed_loop | 无 status=open 的改进项 | 闭环要求 |

**阈值单一真源**：`postmortem.severities` / `postmortem.required_sections` 以
`experience/thresholds.json` 的 `postmortem` 段为准。

## 第三层：已验证的算例

**算例 A（干净复盘）**：`examples/postmortem.json`
```
pm-001 / severity=sev2 / timeline=… / root_cause=数据库连接池耗尽 /
impact=API 不可用 30 分钟 / actions=加大连接池+加告警
```
四要素齐、severity 在白名单 → `ok=true`，`verdict=PASS`。

**算例 B（脏复盘）**：`examples/postmortem_dirty.json`
```
pm-001 / severity=sev9 / timeline="" / root_cause="" / impact="" / actions=""
```
BLOCKER ×2：`postmortem.severity`（sev9 越界）+ `postmortem.sections`
（四要素全空）。

**算例 C（改进项）**：`examples/improvement.json` vs `improvement_dirty.json`
```
actions=[{加大连接池,r09,2026-11-12,done},{加监控告警,r20,2026-11-12,done}] → PASS
actions=[{加大连接池,r09,2026-11-12,open}]                                  → FAIL
```
无 open 未闭环项才算闭环。`action_count` 回写 2。

## 第四层：实战踩坑

1. **status 枚举只有 open/done/wontfix，没有 "in_progress"**。R20 口径里
   "正在做"归 open（未闭环），"不做了"归 wontfix（已闭环）。加 in_progress
   会让闭环判据变模糊——只改 thresholds 不引入新枚举。

2. **四要素判据用 `required_sections` 循环，不硬编码字段名**。`timeline`/
   `root_cause`/`impact`/`actions` 四个键名从 thresholds 的
   `postmortem.required_sections` 读，判据写 `for s in th["required_sections"]`。
   未来若加第五要素（如 "cost"），只改 thresholds，判据自动跟随。

3. **root_cause 判据是"非空"，不是"非现象"**。"数据库连接池耗尽"和
   "API 挂了"都能过非空判据——区分"根因 vs 现象"是语义判断，R20 不做
   （那是 blameless 复盘里人工/R02 的活）。判据只保证"有人写了根因"。

4. **`improvement_dirty` 只 open 一条也拦**。闭环判据 `not open_items` 要求
   零 open。这是硬闭环——但真实团队总有 open 项，所以 R20 口径是：改进项
   工件里不允许 open，open 项应留在 Backlog（R07），不留在复盘工件里。

5. **actions 是字符串（postmortem 里）也是数组（improvement 里）**。两个动作
   的 `actions` 字段类型不同：postmortem 的 actions 是四要素之一（自由文本
   摘要），improvement 的 actions 是结构化改进项数组。评审的 conclusion_keys
   不扫 actions（非文本键），concrete_keys 含 `action_count`（improvement 的
   可交付键）——R15 教训：concrete_keys 不含 ok/checks。
