# R05 蛙深远 · 厚度自述（T8a）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 9 篇 / 37.2KB；本轮新增 4 篇（09–12，约 17.5KB） |
| 覆盖主题 | 源分级（一手/二手/三手/数据库）、证据分级（GRADE/CEBM）与三角验证、市场测算（TAM/SAM/SOM + 自下而上 + 蒙特卡洛）、波特五力/竞品情报/Mom Test |
| 来源 | 每篇列出公开标准/论文/方法书：OECD 质量框架、ISO 20252、GRADE（BMJ 2008）、OCEBM 2011、Denzin 1978、Patton 1999、Metropolis & Ulam 1949、Saltelli 2008、Porter 1979/2008、Fuld 1995、SCIP 伦理、Fitzpatrick 2013 等 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列「误用反例」表，并写明本仓哪个门禁拦截 |

## 2. 生产层

`chain run` 一条命令串起 8 个生产模块：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `research_chain/scope.py` | 决策问题 + 决策用途 + 子问题种子 | `scope.json`（5–8 子问题 + 证据需求 + MECE 互斥/覆盖） |
| 2 | `research_chain/source.py` | scope + 候选源 | `source.json`（一手/二手/三手/数据库 × 载体 × 可访问性，逐子问题覆盖） |
| 3 | `research_chain/collect.py` | source + 证据清单 | `collect.json`（claim/value/unit/period/url/date/quote + series/metric） |
| 4 | `research_chain/verify.py` | 台账 + 源地图 + as_of | `verify.json`（回抓/复算/偏见/时效四维，未验证显式披露） |
| 5 | `research_chain/triangulate.py` | 台账 + 验证结果 | `triangulate.json`（结论 + 高/中/低置信度 + 矛盾记录） |
| 6 | `research_chain/size.py` | top-down + bottom-up + 假设 | `size.json`（双口径 + p10/p50/p90 + 假设清单） |
| 7 | `research_chain/compete.py` | 5 家 × 8 维 + 五力 + 份额 | `compete.json`（逐格有源矩阵 + battlecard + 份额） |
| 8 | `research_chain/report.py` | 前 7 段 + 边界 | `report.json` / `research_report.md` / `.html`（结论先行 + 证据附录 + 边界） |

编排：`research_chain/runner.py`（8 个 JSON + `research_manifest.json`：逐工件 sha256、阶段门禁、7 项跨段一致、`audit` 重算）。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 真实夹具 | `fixtures/pet_smart_hardware.json` | 23 个源（一手 14 / 二手 7 / 三手 1 / 数据库 1）、34 条证据、6 个子问题 |
| 矛盾样本 | 同上（市场规模 2025 两口径） | 480 亿元 vs 560 亿元，极差 15.38%，记录为 `open` 并保留区间 |
| 运行账本 | `artifacts/chain/research_manifest.json`（每次 `chain run` 生成） | 每段 sha256 + gate + 跨段一致；`chain audit` 可发现手改 |
| 黄金成品 | `golden/industry-research.html`、`competitor-matrix.html`、`market-sizing.html` | 全部由链真实跑夹具后导出；报告引用 23 个独立来源 |
| 误用样本 | `misuse/no_sources.json`、`secondary_only.json`、`overclaim.json` | 分别被 `report:traceability`、`source:type_diversity`、`tri:two_sources_or_single` 拦下 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 5–8 子问题 / 证据需求 / MECE 互斥与覆盖 | `scope:decision_question` … `scope:mece_coverage` | CRITICAL（不出源地图） |
| ≥10 候选 / ≥3 类源 / 一手+二手+三手 / 逐子问题覆盖 / 字段与可访问性 | `source:*` 7 条 | CRITICAL |
| 十字段齐全 / url+date+quote 三要素 / 来源与子问题可追 | `collect:*` 7 条 | CRITICAL |
| 100% 覆盖 / 四维验证 / 未验证披露 / 复算与时效 | `verify:*` 6 条 | CRITICAL（未验证必须披露） |
| ≥2 源或 single_source / 单源降 low / 矛盾不静默 | `tri:*` 7 条 | CRITICAL |
| 双口径 / ≥3 假设且挂证据 / 区间 / 方差 ≤50% / p10≤p50≤p90 | `size:*` 9 条 | CRITICAL |
| 5 家 × 8 维 / 逐格有源 / battlecard / 五力 / 份额 | `compete:*` 9 条 | CRITICAL |
| 结论可追 / 附录完整 / 边界 / 未验证披露 / 结论先行 | `report:*` 7 条 | CRITICAL |
| 结论源存在 / 矩阵源存在 / 份额与 size 口径一致 / 假设挂证据 | `cross:*` 7 条 | CRITICAL（链内自相矛盾） |
| 全链复核 | `chain audit` / `research_manifest.json` | 退出码 1，CI 失败 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 单段门禁 + 负例 | `tests/test_research_chain.py` | 15 条（8 段门禁 + 7 条负例/端到端/误用） |
| 端到端 | 同上 `TestEndToEnd` | 3 条（全链 + 审计篡改 + 确定性） |
| 误用拦截 | 同上 `TestMisuse` + `misuse/*.json` | 3 个 |
| 角色验收 | `run_tests.py` T16 | 3 条（链跑通 + CLI + 误用具名门禁） |
| 契约 | `contracts.py` `chain.*` | 10 个动作输出契约 |
| Profile | `scripts/validate_profiles.py --role r05` | 10 个 chain 动作 semantic_fields，PASS |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r05-washenyuan-research/run_tests.py`
- 研究链：fixture `pet_smart_hardware.json` → 8 段全 PASS，grade=A，跨段 7/7 PASS
- 规模：top-down 87.00 亿元；bottom-up 87.05 亿元；p10 70.08 / p50 88.17 / p90 110.55 亿元
- 竞争：5 家线上份额合计 68%；40 个矩阵格全部有 source id
- 报告：34 条证据 / 23 个来源；矛盾 1 组（市场规模 2025 两种口径，极差 15.38%，状态 open）
- 已知边界：本链只到 `report`，不替代 R01 正式报告；访谈不能外推总体比例；份额为线上口径；蒙特卡洛只做一阶独立抽样（未覆盖假设相关性）；`verify` 为确定性回抓/复算检查，不做真实联网抓取。
