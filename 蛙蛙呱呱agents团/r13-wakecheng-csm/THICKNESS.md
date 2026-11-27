# R13 蛙客成 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 11 篇 / 约 42.4KB（`python scripts/check_role_thickness.py --report` 可复核） |
| 来源 | twenty（CRM/管道）、chatwoot（会话/SLA/CSAT）、formbricks（问卷/NPS）等公开仓口径 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 8 个能力域、16 个动作：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `crm` | person/company | 联系人/公司主数据 |
| 2 | `pipeline` | 商机清单 | 阶段/停滞/加权预测/HHI |
| 3 | `activity` | 活动与承诺 | 跟进窗口、逾期承诺 |
| 4 | `support` | 会话/工单 | 渠道/状态/SLA/CSAT/重开 |
| 5 | `voc` | 问卷与响应 | NPS 三桶、响应率、主题 |
| 6 | `health` | 四维客户分 | 加权健康分、分带、续约候选 |
| 7 | `knowledge` | FAQ/升级 | 答案质量、升级路由、证据 |
| 8 | `automation` | 规则 | 触发/审批点/审计字段 |

黄金链：`health.health → support.inbox`；`voc.voc → health.risk`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（30 个） | 每个动作配对，脏件断言被拦 |
| 案例包 | `cases/`（18 个文件） | SOP 与经验包 |
| 黄金成品 | `golden/customer-health-pack.html`、`golden/voc-report.html` | 含夹具 sha256 截断与 21 条门禁 |
| 阈值 | `experience/thresholds.json` | 健康分权重、分带、SLA、NPS 口径 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 健康表无匿名行 | `health.health` → `health.name` | BLOCKER |
| 四维权重和 = 100 | `health.health` → `health.weights` | BLOCKER |
| at_risk 必须写归因 | `health.health` → `health.risk_reason` | BLOCKER |
| 单维崩坏不得判 healthy | `health.risk` → `risk.band_consistency` | FAIL |
| NPS 0–10 且响应率门槛 | `voc.voc` → `voc.nps_range` / `voc.response_rate` | FAIL |
| 渠道/状态白名单 | `support.inbox` → `support.channel_enum` / `status_enum` | BLOCKER |
| 首响/解决/重开/CSAT | `support.inbox` → `support.*` | BLOCKER |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 16 动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（匿名行、单维崩坏） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r13-wakecheng-csm/golden/build_golden.py`
- 产物：`customer-health-pack.html`（11 条门禁，0 未过）、
  `voc-report.html`（10 条门禁，0 未过）
- 命令：`python r13-wakecheng-csm/run_tests.py`
- 结果：全绿（含厚度样本 T16）

## 7. 已知边界

- 健康分是确定性加权，不替代客户访谈；
- 样本 <10 时 NPS 仅报告不作结论；主题为确定性词频近似；
- 续约候选只是输入，商务承诺与折扣须 R03/创始人审批；
- 不擅自承诺退款/赔偿。
