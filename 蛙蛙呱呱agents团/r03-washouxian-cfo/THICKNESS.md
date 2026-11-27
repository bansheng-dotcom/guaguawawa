# R03 蛙守线 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 11 篇 / 约 36.2KB（`python scripts/check_role_thickness.py --report` 可复核） |
| 来源 | 每篇正文标注会计准则/合同审查/隐私法规等公开来源 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应到本仓门禁 |

## 2. 生产层

`skills/` 8 个能力域、24 个动作，输入 JSON → 结构化结论：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `financial` | 账户滚动/GL+子账/差异清单 | 平衡明细、六桶对账、差异注解缺口 |
| 2 | `cfo` | 现金与经营数据 | runway/burn、单位经济、三表恒等 |
| 3 | `tax` | ISO/AMT/RMD/safe harbor 参数 | 税务计算与缺口 |
| 4 | `contract` | 合同文本/整改状态/政策 | 红线清单、整改闭环、政策字段 |
| 5 | `privacy` | 数据流/DSR/字段清单 | 合法性基础、时限、最小化 |
| 6 | `aigov` | AI 系统画像 | 风险分级、框架映射、披露项 |
| 7 | `audit` | 留存记录/审计发现/证据 | 留存违规、严重度分布、证据缺口 |
| 8 | `risk` | KYC/AML/广告 | 风险评分、申报到期、广告合规 |

黄金链：`financial.rollforward → recon → variance`；`contract.scan → redline → policy`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 真实夹具 | `examples/*.json`（25 个） | 含干净与脏数据，脏数据由 `tests/test_skills.py` 断言被拦 |
| 案例包 | `cases/month-end-close` / `kyc-onboarding` / `runway-crisis` | case.json + semantic_layer + experience |
| 黄金成品 | `golden/month-end-close.html`、`golden/contract-review.html` | 由真实技能输出渲染，含 sha256 截断 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| roll-forward 恒等式（容差 0.01） | `financial.rollforward` → `balance` | CRITICAL，不出关账结论 |
| 六桶对账 + 匹配率 ≥95% | `financial.recon` → `matched_pct` | CRITICAL |
| 重大差异 driver 解释 why | `financial.variance` → `variance_note` | HIGH |
| 12 条合同规则 + sign_gate | `contract.scan` → `critical_findings/sign_gate` | CRITICAL，拦截送签 |
| 政策五字段 + 可执行 enforcement | `contract.policy` → `policy_field` | HIGH |
| 整改状态合法/CRITICAL 风险接受须 approver | `contract.redline` → `redline_status/risk_acceptance` | CRITICAL |
| 持牌措辞 | `review.py` → `licensed_gate` | CRITICAL |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 覆盖 24 动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（roll-forward 不平、政策缺 owner） |
| 端到端 | `run_tests.py` T01–T15 | `run_tests.py` 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r03-washouxian-cfo/golden/build_golden.py`
- 产物：`golden/month-end-close.html`（6 条门禁）、`golden/contract-review.html`（11 条门禁）
- 命令：`python r03-washouxian-cfo/run_tests.py`
- 结果：全部通过（含厚度样本 T15）

## 7. 已知边界

- 只做确定性校验与归因，不做会计估计、不代签、不出具审计/法律/税务意见；
- 合同规则为 12 条高频红线，非全量法律审查；
- 阈值外置在 `experience/thresholds.json`，改口径不改代码。
