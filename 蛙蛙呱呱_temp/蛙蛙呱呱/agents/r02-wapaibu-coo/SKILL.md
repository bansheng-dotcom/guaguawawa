---
name: r02-wapaibu-coo
description: COO 首席运营官角色技能。七个能力域各自可执行：工作拆解与排期（WBS/冲刺/关键路径）、容量与委派（负载/派工/拆分）、交接与验收追踪（交接包/验收/链路）、复盘与事故分析（事后复盘/五维打分/行动项）、流程与 SOP（SOP/浪费检测/会议）、知识运营（文档技能化/条目/检索）、项目群与 Agent 编排（状态/分波/依赖图）。当需要排期、管容量、交接验收、复盘事故、沉淀 SOP 与知识、编排项目群时使用。已引入真实执行层，不再仅仅是门禁校验。
---

# R02 蛙排布 · COO 首席运营官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/productivity/task-management/SKILL.md
>


七技能结构：`skills/s01..s07`，每技能 3 动作共 21 个确定性动作，
全部纯标准库实算（排期日历、Kahn 拓扑+关键路径正反传、BM25+RRF 检索、
置信三态评分……），配 harness/契约/对抗评审/案例库/阈值外置五重闭环。

## Quick Start

```bash
python agent.py manifest                                  # 协作契约 + 技能清单
python agent.py demo                                      # 7 份示例运营工件
python agent.py schedule wbs      --input examples/wbs.json
python agent.py schedule sprint  --input examples/sprint.json
python agent.py schedule critpath --input examples/critpath.json
python agent.py capacity check    --input examples/capacity.json
python agent.py capacity delegate --input examples/delegation.json
python agent.py capacity split    --input examples/oversized_task.json
python agent.py handoff package   --input examples/handoff.json
python agent.py handoff accept    --input examples/acceptance.json
python agent.py retro postmortem  --input examples/incident.json
python agent.py process waste     --input examples/waste.json
python agent.py knowledge search  --input examples/knowledgestore.json
python agent.py portfolio status   --input examples/portfolio.json
python agent.py portfolio plan     --input examples/orchestration.json
python agent.py run --task <task_id>                       # 协作入口：任务卡→路由→产出
python run_tests.py                                       # 一键验收（107 项）
```

## 能力域 → 子命令映射（7 域 21 动作）

| 能力域 | 技能 | 动作（确定性校验） |
|---|---|---|
| 工作拆解与排期 | `schedule` | `wbs` 八类任务白名单+估算 0.05-3.0 人日 · `sprint` 逐日容量填充+跳周末+日例会节奏 · `critpath` Kahn 拓扑+ES/EF 正传+LF/LS 反传，浮动=0 即关键路径 |
| 容量与委派 | `capacity` | `check` 加权负载（紧急×1.2）+单项目 >50% 红线 · `delegate` >8h 必拆+blocked_by≤2+关键结果≥1 · `split` ceil(h/8) 均分且 Σ子任务=原任务 |
| 交接与验收追踪 | `handoff` | `package` 工单四要素+复现命令+HP 包号（sha8） · `accept` 逐条 pass+证据，无证据不许过 · `trace` 时间线单调+created→closed 闭环 |
| 复盘与事故分析 | `retro` | `postmortem` sev 1-5+sev≥4 30 分钟升级+根因必填 · `grade` 五维打分，LOSS 未闭环即 FAIL · `action` 过期 CRITICAL+闭环率 |
| 流程与 SOP | `process` | `sop` 关键步骤必带控制点（占比≥0.3） · `waste` 返工/长等待检测+量化机会陈述 · `meeting` 时间盒 15/60/120+行动项出口 |
| 知识运营 | `knowledge` | `digest` 13 种类型白名单+chNN+token 预算+sha256 指纹防重跑 · `entry` 幂等指纹+150% 尺寸拆分+90 天过期 · `search` BM25+RRF(k=60)+过期降权 0.5 |
| 项目群与 Agent 编排 | `portfolio` | `status` RAG 映射（on_track→G/at_risk→A/behind|missed→R）+跨角色依赖 · `plan` Kahn 分波+人工审批门（p0 变更/资金/红线）+波负载≤24h · `graph` 引用完整性+置信三态+god 节点+深度上限 |

## 与 R01 的去重边界

- **R01 蛙全局管「拆给谁」**：taskcard 六段+DRI+依赖图 DFS+波次+20 角色路由。
- **R02 蛙排布管「怎么排、怎么交接验收、怎么沉淀」**：拿到 R01 的任务卡后
  做排期日历、容量红线、交接包与验收链路、复盘、SOP 与知识入库。
- 依赖检测口径共享 `\br\d{2}\b` 正则，但 R02 只读不派单。

## 质量闭环（对齐 R01/R06/R07 标杆）

- **harness**（T2）：`python agent.py harness <gate> --input x.json`，21 个验证器，
  CRITICAL/BLOCKER/HIGH 即 FAIL 退出非 0；`verify` = WBS→sprint→capacity 全链综合门禁；
  `runlog` 最近 5 次运行留痕。
- **契约**（T6）：`python agent.py contract list`，7 技能 21 动作全登记，
  `validate` 缺必填字段即 FAIL。
- **对抗评审**（T7）：`python agent.py review --result x.json --skill s --action a`，
  5 项确定性挑战（契约/无主之责/空话黑词/建议授权/量化价值），任一 FAIL 即退回。
- **案例库**（T8）：`cases/sprint-rescue`（冲刺救火）、
  `cases/incident-postmortem`（事故复盘），`case validate` 三件套结构门禁
  （case.json+semantic_layer.json+experience/）。
- **阈值外置**（T9）：`experience/thresholds.json`（紧急权重 1.2、8h 上限、
  30 分钟升级、7 天闭环窗、站会时间盒、RRF k=60、13 种类型、置信三态……），
  改口径不改代码，热加载生效。
- **闭环自测**（B25）：`python verify_loop.py`，21 动作×运行×契约×评审全绿。

## 关键原则

- **一切估算有口径**：WBS 估算 0.05-3.0 人日、>8h 必拆、Σ子任务=原任务
  （口径恒等），拆分前后的总量对得上才算排期。
- **交接必带复现命令**：没有复现命令的交接包出不了门；验收逐条对证据，
  无证据不许过。
- **发现浪费即 FAIL**：waste 是发现型语义——流程里查出返工/长等待时
  `ok=false` 退出非 0，逼出机会陈述（三段式+量化）。
- **红线必须人工**：p0 变更/资金/红线类编排未获人工审批即拦。
- **结果以 `__AGENT_RESULT__ {json}` 输出**，PASS=0 / FAIL=1。

## 协作契约

- **inputs**：`goal`、`task_cards`（来自 R01）
- **outputs**：`sprint_plan`、`handoff_pkg`

## 详细参考（按需加载，7 个能力域）

- [模块1 工作拆解与排期](references/01-schedule-wbs.md) —— WBS 白名单、冲刺日历、关键路径正反传
- [模块2 容量与委派](references/02-capacity-delegation.md) —— 加权负载、8h 上限、口径恒等拆分
- [模块3 交接与验收追踪](references/03-handoff-acceptance.md) —— 交接包四要素、验收证据链、审计链路
- [模块4 复盘与事故分析](references/04-retro-incident.md) —— severity 分级、升级时限、五维打分
- [模块5 流程与 SOP](references/05-process-sop.md) —— 控制点密度、七大浪费、会议时间盒
- [模块6 知识运营](references/06-knowledge-ops.md) —— 文档技能化、幂等入库、BM25+RRF 检索
- [模块7 项目群与 Agent 编排](references/07-portfolio-orchestration.md) —— RAG 状态、分波审批门、依赖图置信
