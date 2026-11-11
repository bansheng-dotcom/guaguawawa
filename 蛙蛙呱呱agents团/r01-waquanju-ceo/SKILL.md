---
name: r01-waquanju-ceo
description: CEO 主理人/编排器角色技能。七个能力域各自可执行：意图识别与任务分级（简报/六问/分级）、跨部门拆解（任务卡/波次/路由）、经营与硬决策（可逆性/决策卡/升级）、反方质询（魔鬼代言人/交叉评估/Grove 测试）、公司 OS 与治理（六大组件/记分卡/IDS/冷却锁）、决策留痕与复盘（日志/冲突检查/复盘）、高层汇报与创始人陪练（董事会材料/陪练）。当需要拆分意图、指派角色、评估决策风险、治理公司 OS 时使用。
---

# R01 蛙全局 · CEO 主理人 / 编排器
> 蒸馏自: 补充技能/alirezarezvani__claude-skills/ceo-advisor.md
>


两层结构：**七个能力域技能**（skills/s01..s07，各自确定性校验）+ **编排器本体**
（plan/status/run，Orchestrator + Shared-State 模式）。

## Quick Start

```bash
python agent.py manifest                                  # 协作契约 + 技能清单
python agent.py demo                                      # 7 份示例决策工件
python agent.py intent brief    --input examples/brief.json
python agent.py intent clarify  --input clarify.json
python agent.py decompose taskcard --input examples/taskcard.json
python agent.py decompose wave   --input wave.json
python agent.py decide card      --input examples/decision_card.json
python agent.py decide escalate  --input escalate.json
python agent.py redteam devil    --input examples/redteam.json
python agent.py redteam crosseval --input crosseval.json
python agent.py companyos freeze --input freeze.json
python agent.py decisionlog entry --input examples/decisionlog.json
python agent.py boardroom memo   --input examples/board.json
python agent.py plan --intent "分析订单数据趋势"            # 拆成公司级任务卡
python agent.py status                                    # 任务依赖与状态
python agent.py run --all                                 # 按依赖调度执行并验收
```

## 能力域 → 子命令映射（7 域 21 动作）

| 能力域 | 技能 | 动作（确定性校验） |
|---|---|---|
| 意图识别与任务分级 | `intent` | `brief` 简报七字段+成功/杀死标准先于决策 · `clarify` 六问+判定灯 · `triage` 六分层+职能域+boardroom |
| 跨部门拆解 | `decompose` | `taskcard` 六段门禁+单一主责 · `wave` 循环检测+波次编排 · `route` 意图→角色路由 |
| 经营与硬决策 | `decide` | `reversibility` 可逆性三级+五问 · `card` 决策卡+回滚计划+预公告 · `escalate` 人工签发判定 |
| 反方质询 | `redteam` | `devil` ≥3 顾虑分级+CRITICAL 必带缓解 · `crosseval` GO/PAUSE/STOP 裁决 · `grove` 换人测试 |
| 公司 OS 与治理 | `companyos` | `os` 六大组件+Rocks 二元 · `scorecard` 5-15 指标数值目标+只看红 · `ids` 一 owner 一动作一到期 · `freeze` 冷却锁 |
| 决策留痕与复盘 | `decisionlog` | `entry` 日志条目门禁 · `conflict` DO_NOT_RESURFACE/矛盾/歧义 · `retro` 预承诺标准打分 |
| 高层汇报与创始人陪练 | `boardroom` | `memo` 成绩/问题/计划/求助+miss 必归因 · `coach` ≥2 视角+行动项 |

## 质量闭环（对齐 R06/R07 标杆）

- **harness**（T2）：`python harness.py <gate> --input x.json`，21 个门禁，
  `ok=false` 退出码非 0；`verify` = brief+card 综合门禁。
- **契约**（T6）：`python agent.py contract list`，7 技能全登记，
  `validate` 缺必填字段即 FAIL。
- **对抗评审**（T7）：`python agent.py review --result x.json --skill s --action a`，
  6 项确定性挑战（契约/空泛战略措辞/建议授权/不可逆须人工签发/结论须带
  成功杀死标准/产出价值），任一 BLOCKER 即 FAIL。
- **案例库**（T8）：`cases/pricing-freeze`（定价决策+冷却锁）、
  `cases/quarterly-boardroom`（季度董事会+复盘），`case validate` 结构门禁。
- **阈值外置**（T9）：`experience/thresholds.json`（六问清单、冷却锁天数、
  记分卡 5-15、Rocks 3-7、升级成本 6 个月…），改口径不改代码。
- **可观测性**（T4）：每次运行记 `workspace/runlog.jsonl`，
  `harness runlog` 可追溯。

## 关键原则

- **不可逆动作必须你授权**：decide 判「不可逆」一律禁止自动执行；
  评审发现不可逆词但无 `human_signoff_required` 即 FAIL（CEO 边界）。
- **先锁标准再谈实现**：成功/杀死标准先于决策写，禁止事后补。
- **上下文隔离**：子进程边界调用其它 Agent，不共享内存。
- **端口契约**：跨角色交接只认 `inputs`/`outputs`。

## 协作契约

- **inputs**：`intent`、`decision_memo`
- **outputs**：`task_cards`、`decision_log`、`board_report`
- 结果以 `__AGENT_RESULT__ {json}` 输出。

## 详细参考（按需加载，7 个能力域）

- [模块A 意图分级](references/01-vision-intent.md) —— 六问澄清、目标分层、战略简报
- [模块B 跨角色拆解](references/02-orchestration-decomposition.md) —— 五相环、WBS、DRI、路由
- [模块C 硬决策](references/03-hard-decisions.md) —— 可逆性分级、反方质询、10/10/10
- [模块D 公司 OS](references/04-company-os.md) —— 六大组件、决策日志、复盘
- [模块E 治理审计](references/05-governance-audit.md) —— 成熟度、意向授权、漂移、冷却锁

---

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `strategic-growth-compass` · 战略与增长罗盘（规范；消费方：r07, r12）

查看：`python guagua.py capabilities --role r01`

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `strategic-growth-compass` · 战略与增长罗盘（规范；消费方：r07, r12）

查看：`python guagua.py capabilities --role r01`
