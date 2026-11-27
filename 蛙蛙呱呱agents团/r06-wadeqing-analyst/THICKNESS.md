# R06 蛙得清 · 厚度自述（T8a）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 24 篇 / 约 150KB；本轮新增 6 篇（16–21，约 26KB） |
| 来源 | 每篇列出公开论文/标准（Popper、Minto、Nosek 2018、Holm 1979、Rahm & Do 2000、Kaufman 2012 leakage、Welch 1947、Cohen 1988、Efron & Tibshirani 1993 等） |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列「误用反例」表，并写明本仓哪个门禁拦截 |

## 2. 生产层

`chain run` 一条命令串起 6 个生产模块：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `analysis_chain/frame.py` | 业务问题 + 决策用途 + 维度 | `frame.json`（3–5 个可证伪假设 + MECE + 决策映射） |
| 2 | `analysis_chain/plan.py` | frame + 窗口/切分点 | `analysis_plan.json`（预注册指标/粒度/窗口/维度/检验/停止条件） |
| 3 | `analysis_chain/profile.py` | CSV + plan | `data_profile.json`（六维质量 + 覆盖 + 偏差） |
| 4 | `analysis_chain/explore.py` | CSV + plan | `findings.json`（分母一致的分段发现） |
| 5 | `analysis_chain/explain.py` | CSV + plan + findings | `explanation.json`（驱动树 + 量价 + 替代解释 + 反事实） |
| 6 | `analysis_chain/stats_test.py` | CSV + plan + findings | `stats.json`（效应量 + CI + Welch + Holm + 敏感性） |

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 真实数据集 1 | `cases/analysis-retail/data.csv`（18,000 行） | 预埋真因：抖音×女装折扣 10%→35%（价格效应） |
| 真实数据集 2 | `cases/analysis-saas/data.csv`（9,600 行） | 预埋真因：basic 套餐 onboarding=pending 占比上升 |
| 真实数据集 3 | `cases/analysis-selfmedia/data.csv`（1,350 行） | 预埋真因：抖音推荐流量翻倍 |
| 生成器 | `tests/make_analysis_datasets.py` | 确定性 LCG，可复算 |
| 运行账本 | `chain_manifest.json` | 每段 sha256 + gate + 跨段一致 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 假设可证伪 / MECE / 决策绑定 | `frame.check` | CRITICAL（不出计划） |
| 计划先于看数 / 六要素齐全 | `plan.check` + `experience/plan_schema.json` | CRITICAL |
| 六维质量 / 泄漏 / 选择偏差 | `profile.check` | CRITICAL |
| 分母一致 / 分段来自计划 / 除零 | `explore.check` | CRITICAL |
| 驱动拆解 / 加总 ≤5% / 替代解释 ≥2 / 因果边界 | `explain.check` | CRITICAL（缺拆解为 WARN） |
| 效应量 / CI / n≥30 / Holm / 敏感性 | `stats_test.check` | CRITICAL（n 不足） |
| 全链复核 | `scripts/check_analysis_chain.py` | 退出码 1，CI 失败 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 单段门禁 + 误用拦截 | `tests/test_analysis_chain.py` | 23 条 |
| 端到端 | 同上 `TestEndToEnd` | 3 条（三数据集） |
| 误用样本 | `misuse/*.json` + 测试 | 3 个 |
| 角色验收 | `run_tests.py` §6.5 | 三数据集 run/audit/contract/真因命中 |
| CI | `scripts/ci_upgrade_checks.py` → `check_analysis_chain --selftest` | 每次升级检查都跑 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r06-wadeqing-analyst/run_tests.py`
- 结果：PASS 173 / 173
- 分项：retail → `channel:抖音`（贡献 68.7%）；saas → `onboarding:pending`；selfmedia → `platform:抖音`
- 门禁：`python scripts/check_analysis_chain.py --selftest` → PASS

## 7. 已知边界

- T8a 只到 `test`（统计结论）；`verify/chart/write/deliver`（T8b）未上线，报告仍由 R01 出具；
- `explain` 的量价拆解依赖数量列；缺列时只给贡献，门禁记 WARN 并要求写明原因；
- 比率型指标不能直接对分段求和，需在计划里单独定义分子/分母；
- 单窗口数据无法验证季节性，替代解释只能标 `unverifiable`。

## 8. T8b 报告链（2026-11-27 追加）

| 层 | 现状 |
|---|---|
| 知识层 | 新增 4 篇（22–25，约 16KB）：CoV、图表契约、文字包、运行账本，均含来源与误用 |
| 生产层 | `material_pack → verify → chart_pack → text_pack → deliver` 五个模块，一条 `chain report` 串起 |
| 证据层 | 三份数据集产出 `report.html` + `manifest.json` + `run_events.jsonl`；manifest 记录每个工件 sha256 |
| 门禁层 | CoV 六问、回流码、required_series/completeness/annotation/fail_if_missing、数字可追、Q1–Q10、呈现自检 |
| 回归层 | `tests/test_report_chain.py` 12 条；`check_claim_trace.py` / `check_chart_fail_if_missing.py` 自测进 CI |
| 角色边界 | R06 只产草稿：`author_role=r01`、`publishable=false`、`requires_signoff=true` |

最近真实运行：retail / saas / selfmedia 三份报告全部 PASS；
retail 质检 100 分（research），saas 90.9 分（baseline），selfmedia 100 分（baseline）；
结论可追率均为 100%。
