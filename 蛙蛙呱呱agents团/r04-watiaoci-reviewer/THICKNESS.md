# R04 蛙挑刺 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 11 篇 / 约 36.0KB（新增 `11-adversarial-review-evidence-ladder.md`） |
| 来源 | IEEE 1012 V&V、NASA IV&V 独立性、CMMI 同行评审、ad/dar 对抗评审、Daubert 可证伪性 |
| 适用边界 | 每篇单列「适用边界」；新篇明确只评已存在成品 |
| 误用说明 | 新篇单列 8 条误用反例并对应本仓门禁 |

## 2. 生产层

`skills/` 7 个能力域、15 个动作：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `artifact` | 物料清单/工件 manifest | 存在性、stub 扫描、三级接线结论 |
| 2 | `gate` | 门禁命令/证据 | 真实退出码、STRENGTH 0–100 评分 |
| 3 | `criteria` | 外置判据 | pass/warn/fail 三态、delta 对照 |
| 4 | `quality` | claims/findings | 禁词、证据链、绝对词三查 |
| 5 | `facts` | facts + source | 五维核查、数字回溯三态 |
| 6 | `strengths` | keep_list / 两轮批评 | 保留理由校验、只评本轮修改 |
| 7 | `human` | 评审包/批次/ack | 身份红线、逐字回填计划、staged 确认 |

黄金链：`gate.audit → facts.check → criteria.review → quality.critique`；
`human.package → ingest → ack → strengths.mark`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净夹具 | `examples/*.json`（37 个） | 每个动作配干净件与脏件 |
| 案例包 | `cases/`（26 个文件） | Gherkin 步骤 + 期望值 |
| 黄金成品 | `golden/review-gate-report.html`、`golden/human-review-report.html` | 含夹具 sha256 截断与 16 条门禁结果 |
| 审查留痕 | `artifacts/` | SARIF 等评审产物 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| L1/L2/L3 串行证据链 | `artifact.verify` → `artifact:L1/L2/L3` | CRITICAL，INCOMPLETE |
| STRENGTH-001..007 | `gate.audit` → `gate:STRENGTH-*` | error 存活即 FAIL |
| 判据必须可定位 | `criteria.review` → `no_evidence` | CRITICAL |
| 完成声明须有新鲜证据 | `quality.critique` → `not_verified` | error 阻断签发 |
| 五维事实核查 | `facts.check` → `facts:*` | critical/high 阻断 |
| 数字逐字可回溯 | `facts.trace` → `verified/drift/hallucinated` | drift/hallucinated 阻断 |
| reviewer≠producer | `human.package` → `self_review` | CRITICAL |
| staged 全 copied 才 ack | `human.ack` → `human:ack` | CRITICAL |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 15 动作 |
| 门禁/引擎 | `tests/test_sop_engines.py`、`tests/test_engines_l01_l10.py` | 门禁强度与十维 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（缺来源、自评） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r04-watiaoci-reviewer/golden/build_golden.py`
- 产物：`review-gate-report.html`（9 条门禁，0 未过）、
  `human-review-report.html`（7 条门禁，0 未过）
- 命令：`python r04-watiaoci-reviewer/run_tests.py`
- 结果：全部通过（含厚度样本 T16）

## 7. 已知边界

- 只评已存在成品，不评设计意图，不代改；
- L1–L3 是结构证据，业务正确由判据与事实链分别承担；
- STRENGTH 审计评门禁配置与证据，不评估业务阈值合理性；
- 评审通过 ≠ 发布许可，发布由 R01 签发。
