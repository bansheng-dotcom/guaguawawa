---
name: r07-wademing-pm
description: 产品经理角色技能。把模糊需求转成可评审、可执行、可验收的产品决策：产品发现与 JTBD、机会树用户研究、用户故事与 PRD、优先级与 Backlog、路线图与发布、愿景与指标、技术翻译与代码反推需求、经验检索与决策汇报。当需要写 PRD、排优先级、做用户故事、定北极星指标、翻译技术需求到产品语言时使用。
---

# R07 蛙得明 · 产品经理
> 蒸馏自: 补充技能/product-manager/SKILL.md
>


把能力全景里的 **8 个能力域各自做成一个独立技能模块**（`skills/s01..s08`），
由一个薄调度器 `agent.py` 统一分发。每个技能都是纯标准库、独立可测的单元，
把「产品经理的提示词/工作流」转成**确定性校验 + 打分**，返回可 JSON 化的结果。

## Quick Start

```bash
python agent.py manifest                      # 协作契约 + 8 技能清单
python agent.py demo                          # 生成示例工件(PRD/Job story/Backlog/指标)

python agent.py discover jobstory --input jobstory.json    # S01 JTBD job story
python agent.py discover discover  --input plan.json        # S01 发现计划
python agent.py ost ost --input ost.json                    # S02 机会解树四层
python agent.py ost poc --input solutions.json              # S02 POC 打分推荐
python agent.py ost assumption --input assumptions.json     # S02 假设优先级(Impact×Risk)
python agent.py prd prd --input examples/prd.json           # S03 PRD 八门禁
python agent.py prd story --input s.json --kind user        # S03 用户故事 4-6 AC
python agent.py prd acceptance --input ac.json              # S03 Given/When/Then
python agent.py priority rice --input backlog.json          # S04 RICE 排序
python agent.py priority opportunity --input opp.json       # S04 Opportunity Score
python agent.py roadmap premortem --input pre.json            # S05 事前尸检
python agent.py metrics northstar --input ns.json           # S06 北极星
python agent.py metrics okr --input okr.json                # S06 OKR 3×3
python agent.py techbrief techbrief --input brief.json      # S07 技术翻译五模块
python agent.py techbrief codetoprd --input code.json       # S07 代码反推需求
python agent.py decision decision --input d.json            # S08 决策汇报三层
python agent.py decision demand --input demand.json         # S08 需求卡提交规范
python agent.py decision experience --input card.json       # S08 经验卡五要素

python agent.py contract list                               # T6 8 技能机器可读契约
python agent.py contract validate --skill prd --action prd --output r.json
python agent.py contract validate-input --skill prd --action prd --input examples/prd.json
python agent.py review --result r.json --skill prd --action prd   # T7 对抗评审
python agent.py case list                                    # T8 案例库
python agent.py case validate --case saas-activation
python agent.py harness prd --input prd.json                # 确定性验证器(硬门禁)
python agent.py harness verify --prd prd.json --decision d.json
python verify_loop.py                                       # 29 动作闭环矩阵(契约×评审×ok语义)
python run_tests.py                                         # 一键端到端验收(55 项断言)
python agent.py run --task <task_id>                        # 协作入口
```

## 能力域 → 技能模块

| # | 能力域 | 子命令 | 真实执行的动作 | 整合自 |
|---|---|---|---|---|
| S01 | 产品发现与JTBD | `discover jobstory/discover/interview` | Job story 三段校验 + 发现计划(问题/分群/假设/验证) + Mom Test 四段访谈 | discover / problem-framing / jobs-to-be-done / interview-script |
| S02 | 机会树用户研究 | `ost ost/poc/assumption/research` | OST 四层结构 + POC 打分(Feasibility/Impact/MarketFit) + 假设 Impact×Risk 四象限 + 访谈笔记 | opportunity-solution-tree / prioritize-assumptions / summarize-interview |
| S03 | 用户故事与PRD | `prd prd/story/acceptance` | PRD 八门禁 + 用户故事/Job story 4-8 AC + Given/When/Then | create-prd / user-stories / job-stories / prd-report / acceptance-test |
| S04 | 优先级Backlog | `priority opportunity/ice/rice/backlog` | Opportunity Score/ICE/RICE 实算排序 + Backlog 结构校验 | prioritization-frameworks / prioritize |
| S05 | 路线图发布 | `roadmap roadmap/releasenotes/premortem` | 成果路线图句式 + 发布说明五分类 + 事前尸检 | outcome-roadmap / release-notes / pre-mortem / plan-roadmap |
| S06 | 愿景指标 | `metrics northstar/metrics/okr/vision/canvas` | 北极星 7 标准 + 指标分层 + OKR 3×3 + 愿景 3 标准 + 画布九段 | north-star-metric / product-vision / brainstorm-okrs / lean-canvas / metrics-framework |
| S07 | 技术翻译代码反推 | `techbrief techbrief/uibrief/codetoprd/releasegate` | 技术翻译五模块 + UI Brief 五模块 + 代码反推(页面/字段/接口) + 发布门禁 | technical-brief / ui-brief / code-to-prd / release-gate |
| S08 | 经验检索决策汇报 | `decision decision/demand/experience` | 决策汇报三层 + 需求卡提交规范 + 经验卡五要素 | experience-rag / demand-management / prd-report 决策门禁 |

## 协作契约

- **inputs**：`research_report`（研究/调研结论）、`voc`（客户声音/反馈）。
- **outputs**：`prd`（产品需求文档）、`backlog`（优先级排序后的待办）。
- 结果以一行 `__AGENT_RESULT__ {json}` 输出，供编排器以子进程方式消费。
- 协作入口 `run --task` 按**意图关键词 → 技能+动作**确定性路由（见 `_INTENT_ROUTES`），
  产物 `{skill}.json` 与 `prd_report.md` 写回 `workspace/artifacts/{task_id}/`。

## 关键纪律（保留自 reference，校验环不丢）

1. 八门禁硬校验：PRD 缺「不在范围」「承重假设≥3」「验收标准」任一即 FAIL。
2. 优先级可复算：RICE/ICE/Opportunity Score 是确定性算术，排序可复现。
3. 句式即契约：user story / job story / outcome roadmap 句式不符即 FAIL。
4. 吐多少由契约锁死：`contract validate` 用 JSON Schema 校验每次产出，不符即 FAIL。
5. 空泛措辞拦截：`review` 点名「提升体验/优化功能」无口径、未授权建议 → FAIL。
6. 技术翻译降级不越界：brief 只做产品语言翻译，工程/视觉实现交 R09/R10。
7. 经验卡有边界：候选经验≠已验证规则；声明 verified 必须有来源可信度。
8. 业务知识进案例库：`case` 的 artifact_type/terms/gates/boundary 是跨请求资产，不硬编码进技能。
9. smoke ≠ 闭环：`verify_loop.py` 对 29 动作逐个做「子进程真实运行 → 契约双向校验 →
   对抗评审 → ok/exit 对拍」，干净 29 PASS + 脏 29 FAIL 才算闭环全绿；只跑 `run_tests.py`
   的 smoke 会掩盖「能跑但产出坏」。

## 边界

产品取舍本角色定；客户反馈持续收集交 R13；工程实现交 R09；视觉交 R10；
财务/合规结论交 R03；统计显著性交 R06。

## 详细参考（8 个模块）

- [模块A 产品发现与 JTBD](references/01-discovery-jtbd.md)
- [模块B 机会树与用户研究](references/02-opportunity-tree-research.md)
- [模块C 用户故事与 PRD](references/03-prd-stories.md)
- [模块D 优先级与 Backlog](references/04-prioritization-backlog.md)
- [模块E 路线图与发布](references/05-roadmap-release.md)
- [模块F 产品愿景与指标](references/06-vision-metrics.md)
- [模块G 技术翻译与代码反推需求](references/07-techbrief-code-to-prd.md)
- [模块H 经验检索与决策汇报](references/08-experience-decision.md)