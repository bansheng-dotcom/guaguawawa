# R16 蛙人师 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 10 篇 / 约 45.8KB（`check_role_thickness --report` 可复核） |
| 来源 | frappe HRMS（招聘/绩效/薪酬/考勤/报销）公开口径 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 8 个能力域、18 个动作：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `recruit` | 职位/候选人/录用 | 状态前置、必填、邮箱格式 |
| 2 | `people` | 员工/合同 | 主数据与合同到期 |
| 3 | `attendance` | 考勤/请假 | 状态与日期 |
| 4 | `performance` | 评估/KRA/目标 | 评分区间、打分完整、进度 |
| 5 | `payroll` | 薪酬输入/核算 | 毛净恒等、来源溯源 |
| 6 | `expense` | 报销单 | 状态与审批 |
| 7 | `report` | 人力指标 | headcount/turnover 等 |
| 8 | `funnel` | 招聘漏斗 | 逐级转化与瓶颈 |

黄金链：`recruit.opening → applicant → offer → performance.appraisal`；
`payroll.input → payroll.calc`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（33 个） | 每动作配对，脏件断言被拦 |
| 案例包 | `cases/`（18 个文件） | SOP 与阈值 |
| 黄金成品 | `golden/hiring-performance-pack.html`、`golden/payroll-compliance-pack.html` | 含夹具 sha256 与 24 条门禁 |
| 阈值 | `experience/thresholds.json` | 状态白名单、评分区间、薪酬容差 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 招聘状态白名单/必填 | `recruit.*` → `opening/applicant/offer.*` | BLOCKER |
| Accepted 须来自 Shortlisted | `recruit.offer` → `offer.prior` | BLOCKER |
| 评分区间 0–5 | `performance.appraisal` → `appraisal.total_score/kra_scores` | BLOCKER |
| KRA 打分完整 | `performance.appraisal` → `appraisal.kra_complete` | BLOCKER |
| 薪酬组成项类型与来源 | `payroll.input` → `payroll.component_*` | BLOCKER |
| 毛额/净额恒等 | `payroll.calc` → `payroll.gross/net` | BLOCKER |
| 制度性字段可溯源 | `payroll.calc` → `payroll.system_source` | BLOCKER |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 18 动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（无评分表、净额不平） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r16-warenshi-hr/golden/build_golden.py`
- 产物：`hiring-performance-pack.html`（15 条门禁，0 未过）、
  `payroll-compliance-pack.html`（9 条门禁，0 未过）
- 命令：`python r16-warenshi-hr/run_tests.py`
- 结果：全绿（含厚度样本 T16）

## 7. 已知边界

- 只产招聘/绩效/薪酬工件，不擅自发 Offer、入职、定档、发薪；
- 薪酬合规与劳动关系结论须 R03/外部专业复核；
- 评分是管理动作，不是数学结论。
