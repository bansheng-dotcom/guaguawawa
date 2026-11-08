---
name: wawa-guagua
description: "蛙蛙呱呱 · 20 角色一人公司专家团。把一次跨域经营需求拆成六段任务卡与依赖波次，分派给 CEO/COO/财务合规/独立评审/战略研究/数据分析/产品/MVP/代码工程/视觉设计/内容/增长/客户成功/交易履约/供应链/人事/自动化/数仓/模型评估/可靠性 20 个岗位，每个岗位自带可执行的确定性 Python 技能包（agent.py + harness + 契约 + 案例 + 回归）。当用户要把一个想法做成「一人公司」的完整方案、要做跨部门拆解与排期、要多角色分工产出 PRD/数据结论/代码/设计/内容/增长/合规复核、要独立评审给 PASS/FAIL、或要按组织协议做经营体检与创始人汇报时使用。也用在这些说法：蛙蛙呱呱、一人公司、20 个角色、CEO 编排、任务卡、波次调度、独立评审、红线合规、经营体检。"
---

# 蛙蛙呱呱 · 20 角色一人公司专家团

## 这是什么

一套**团队型**经营专家包：20 个岗位、六层编制，外加一份可执行的运行时镜像
（`tools/role-runtime/agents/`）。

它不是一堆提示词，而是**可执行的确定性技能包**：每个岗位都有
`agent.py`（技能入口）、`harness.py`（门禁）、`contracts.py`（端口契约）、
`cases/`（案例）、`run_tests.py` / `verify_loop.py`（回归）。结论必须来自真跑脚本的
`__AGENT_RESULT__` JSON，不允许凭记忆编数字。

组织语义（谁负责什么、怎么交接、怎么汇报）的来源：
`tools/role-runtime/agents/` 下的 `ORG.md` · `PROTOCOL.md` · `REPORT-STANDARD.md` ·
`TEAM.md` · `REPORT-BRIDGE-GUIDE.md`。能力执行一律走各岗位技能包。

## 什么时候用

用：

- 需求跨 2 个以上职能域（如「从想法到上线」「做内容 + 投放 + 复盘」「经营全链路体检」）
- 需要先把模糊需求拆成可验收的任务卡、排依赖波次、指定单一 owner
- 需要多岗位各自出专业产出，再由独立评审给 PASS / FAIL
- 涉及钱、合同、隐私、红线的复核
- 需要按统一汇报规范交付 `.md` + `.html` 双格式的经营结论

不用：

- 单点技术问题（直接改代码即可，不必建团队）
- 只想要创意文案，不需要组织流程与门禁
- 需要真正并发 spawn 20 个独立子智能体的场景——本包
  `capability_status.external_delegation = blocked`，见「已知边界」

## 快速开始

必须先 `cd` 到某个岗位目录再跑，路径都相对岗位目录：

```bash
cd tools/role-runtime/agents/r01-waquanju-ceo   # 入口：运行时镜像

python agent.py manifest                                   # 查协作契约 + 技能清单
python agent.py <skill> <action> --input examples/<fixture>.json
python harness.py <gate> --input x.json                    # 确定性门禁
python run_tests.py                                        # 端到端回归
python verify_loop.py                                      # 闭环矩阵（部分岗位提供）
```

实测基线：

- `python agent.py manifest` → `__AGENT_RESULT__` 含 role/name/title/capabilities/inputs/outputs/skills
- 依赖：Python 3.12 可用即可跑核心链路；`requirements.txt` 里的 pandas / pyyaml /
  jsonschema / requests / Jinja2 仅部分岗位需要

## 包结构地图

```text
wawa-guagua/
├── SKILL.md                     本文件（技能入口，路由 + 执行步骤 + 约束）
└── tools/role-runtime/
    └── agents/                  运行时镜像（20 岗位 + 共享内核）
        ├── __init__.py          agents 包入口（把仓库根注入 sys.path）
        ├── core/                共享内核：registry · protocol · runner ·
        │                        dag_orchestrator · report_bridge · report_renderer ·
        │                        workspace · approvals · artifact_registry
        ├── shared/              共享能力：报告引擎、知识库、叙事库、角色画像
        ├── r01-… ~ r20-…/       20 个岗位技能包（agent.py + harness + contracts + cases + tests）
        ├── scripts/             批量脚本
        ├── orchestrations/      编排场景
        ├── configs/             r01-r20 配置
        ├── workspace/           共享工作区（事件流 + 历史产物）
        ├── avatars/             团队形象资源
        ├── docs/                SOP 文档
        └── ORG.md PROTOCOL.md TEAM.md REPORT-STANDARD.md REPORT-BRIDGE-GUIDE.md
```

## 执行步骤

### 第 1 步 · 判级与选模式

读 `tools/role-runtime/agents/PROTOCOL.md`，判定：

| 命中 | 模式 | 做法 |
|---|---|---|
| 只落在 1 个职能域 | A · 单角色直调 | 澄清 → 自查 → 展开 → 自评 → 汇报（五步），不建团队 |
| 输入不足 / 越界 / 推不动 | B · 移交 | 按分类表移交，带 `context_summary` + `artifacts` + `call_chain`；禁止自调用，最大深度 2，总移交 > 3 次升级 R01 |
| 2+ 职能域 | C · 多角色编排 | 走下面第 2–6 步的五相环 |

预设 Workflow（触发条件 → 编排）：

| Workflow | 触发 | 编排 |
|---|---|---|
| 链式交付 | 「从想法到上线」「做一个产品」 | 澄清 → 战略研究 → 产品经理 → MVP → 代码工程 → 独立评审 → 汇编 |
| 数据驱动 | 「营收方案」「验证某个假设」 | 产品经理出假设 → 数据分析只验证不发明 → MVP 只渲染不新增声明 → 独立评审复核；假设被推翻就回产品经理改假设，不硬凑结论 |
| 内容增长 | 「做内容/投放/涨粉」 | 内容主笔成稿 → 视觉设计配图 → 增长运营投放 → 数据分析归因复盘 → 独立评审复核 |
| 合规闭环 | 涉钱、合同、隐私、红线 | 财务合规复核 → 独立评审 → 结论直通创始人 |
| 经营体检 | 「看看这门生意」「全链路体检」 | 财务/数据/增长/客户成功/可靠性并行 → COO 汇总排期 → 独立评审裁决 → 汇编 |

### 第 2 步 · 拆任务卡 + 建依赖图

每张卡六段：**任务名 + owner（单一主责）｜目标｜拥有文件｜需求｜接口契约｜验收标准｜明确不做**。
「明确不做」为空即门禁不通过。依赖图先做环检测（DFS 三色标记）再拓扑分波，
`max_wave_depth = 6`，同波次无依赖可并行。

### 第 3 步 · 加载目标岗位技能包

先读 `tools/role-runtime/agents/<role-dir>/SKILL.md` 的能力域表，再
`python agent.py manifest` 查契约，确认 `skill` + `action` + 输入 fixture 三件套存在。
**不要预读整包**。

### 第 4 步 · 真跑确定性脚本

```bash
cd tools/role-runtime/agents/<role-dir>
python agent.py <skill> <action> --input examples/<fixture>.json
```

成员回传必须附：跑了哪个 `skill/action`、输入 fixture、门禁 PASS/FAIL、
`__AGENT_RESULT__` 关键字段。只有观点没有运行结果 → 退回重做。

### 第 5 步 · 独立评审

`r04-watiaoci-reviewer`（R04 蛙挑刺）按三级证据链 + 6 项对抗挑战出
`PASS / FAIL / BLOCKED`。三个回路：`evidence_does_not_support_conclusion` → 回重算；
`expression_title_or_line_fit` → 回改写；`no_report_value` → 丢弃。
`reviewer == producer` 直接判 FAIL。

### 第 6 步 · 汇编与交付

报告统一走 `core/report_bridge.py` → `core/report_renderer.py`。
结构：背景与目标 / 各角色结论表 / 综合判断 / 决策建议 / 风险与边界 / 附录。
交付 `.md`（快读）+ `.html`（自包含正式件）。每完成一个阶段向用户简要通报进度。

### 交付前自检

- [ ] 每个数字都能回溯到某次真实脚本输出或原始数据
- [ ] 模拟数据已在 meta/notes 显式标注 `simulated`
- [ ] 缺数据的地方写 `blocked`，没有硬编结论
- [ ] 需要创始人拍的不可逆决策已出 `escalate` 决策卡 + 回滚计划，没有代签
- [ ] 独立评审结论未被改写，且评审人 ≠ 生产者
- [ ] 事件已写入 `workspace/events.jsonl`（没有事件等于没发生）

## 角色路由表

| ID | 花名 | 职衔 | 目录 | 输入 → 输出 |
|---|---|---|---|---|
| r01 | 蛙全局 | CEO 主理人 / 编排器 | `r01-waquanju-ceo` | intent, decision_memo → task_cards, decision_log, board_report |
| r02 | 蛙排布 | COO 首席运营官 | `r02-wapaibu-coo` | goal, task_cards → sprint_plan, handoff_pkg |
| r03 | 蛙守线 | 财务合规官 / 红线负责人 | `r03-washouxian-cfo` | financials, contracts, data_flows → compliance_review, risk_register |
| r04 | 蛙挑刺 | 独立评审官 | `r04-watiaoci-reviewer` | artifact, acceptance_criteria → pass_fail, critique_report |
| r05 | 蛙深远 | 战略研究官 | `r05-washenyuan-research` | topic, scope → research_report, evidence_ledger |
| r06 | 蛙得清 | 数据分析师 | `r06-wadeqing-analyst` | dataset, metrics_spec → dataset, analysis_report |
| r07 | 蛙得明 | 产品经理 | `r07-wademing-pm` | research_report, voc → prd, backlog |
| r08 | 蛙建成 | 产品实现官 (MVP) | `r08-wajiancheng-mvp` | prd, ui_brief → mvp, page_assets |
| r09 | 蛙稳码 | 代码工程官 | `r09-wawenma-engineer` | mvp, spec → production_code, test_report |
| r10 | 蛙成美 | 视觉设计官 | `r10-wachengmei-design` | brand_brief, content → visual_assets, vi |
| r11 | 蛙点题 | 内容主笔 | `r11-wadianti-copy` | topic, audience → content_draft, publish_list |
| r12 | 蛙引流 | 增长运营官 | `r12-wayingliu-growth` | content_draft, product → growth_plan, channel_assets |
| r13 | 蛙客成 | 客户成功与销售运营官 | `r13-wakecheng-csm` | lead, order_status → crm_record, voc |
| r14 | 蛙交易 | 交易与收入履约官 | `r14-wajiaoyi-commerce` | package, quotation → order, payment_status |
| r15 | 蛙供应 | ERP 与供应链运营官 | `r15-wagongying-erp` | order, sop → purchase_order, inventory_ledger |
| r16 | 蛙人事 | 人员与组织运营官 | `r16-warenshi-hr` | org_decision, roles → roster, payroll_input |
| r17 | 蛙织网 | 自动化与集成工程师 | `r17-wazhiwang-automation` | rules, fields → workflow, audit_log |
| r18 | 蛙数仓 | 数据工程与管道官 | `r18-washucang-dataeng` | source, metrics_spec → dataset, data_catalog |
| r19 | 蛙智模 | 模型工程与 AI 评估官 | `r19-wazhimo-ml` | dataset, model → experiment_log, evaluation |
| r20 | 蛙值守 | 可靠性与恢复官 | `r20-washouzhi-sre` | topology, asset_list → monitor_config, backup_repo |

六层编制：决策与治理（r01–r04）/ 战略、数据与智能（r05、r06、r18、r19）/
产品与技术（r07–r10）/ 市场与客户（r11–r13）/ 交易与组织运营（r14–r16）/
自动化与可靠性（r17、r20）。完整职责边界与「明确不做」：
`tools/role-runtime/agents/ORG.md`。

## 关键约束

**五条组织铁律**（不可协商）

1. 一个文件 / 一个职能只有一个 owner；「共同负责」＝没人负责。
2. 编排器必须瘦：只加载上下文 → 派发正确角色 → 回收结果 → 更新状态，不写产出。
3. 生成与校验分离：谁生成谁负责；R04 独立评审，`reviewer == producer` 即 FAIL。
4. 一切带终止条件：成功标准全命中收口；杀死标准触发即强制终止转复盘。
5. 不可逆决策仅创始人：裁员/关停/锁定产品/大额资金/受监管条款，只出 `escalate`
   决策卡 + 回滚计划，不代签。两条汇报线：执行线（成员 → R01 → 创始人）与
   独立评审线（R04 旁路直通创始人，结论不被打回或改写）。

**数据诚实性**

- 每个数字标来源、时点、口径、置信等级；模拟数据必须显式标注。
- 缺数据写 `blocked`，外部能力未接入如实降级为 `simulated`，不制造确定性。
- 禁用词：`需要关注`、`有待进一步分析`、`值得注意`、`综合来看`（无数字支撑时）、`可能存在问题`。

**运行卫生**

- 报告、截图、临时依赖等运行产物放在包外；只有 `workspace/` 是包内的事件与历史产物区。
- `core/workspace.py` 用 `O_EXCL` 文件锁（5 秒超时）。中断留下
  `workspace/.events.lock` 时，删该锁文件即可恢复；**不要并发跑多个回归脚本**。
- 跑 `run_tests.py` 会写入 `workspace/` 与 runlog，属预期行为。

## 已知边界

- **不能真正并发派发**：`agent.py manifest` 报 `external_delegation: blocked`。
  在只装技能的环境里，按角色顺序**逐个执行**，把上一角色完整产出原文
  传给下一角色，不要假装同时开了 20 个成员。
- **回归非全绿是既有状态**：源项目 `run_tests.py` 本身就有失败项。门禁判定看「不新增 FAIL」。
- `avatars/` 是团队形象资源，不影响任何技能执行。
