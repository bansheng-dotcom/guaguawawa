# R11 蛙点题 · 厚度自述（内容生产线）

> 按升级方案 §5「五层可验收」、§16「厚度包」与 §17.2 r11 表逐项自述。
> 只写能被命令复核的事实；同一输入复算结果一致。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 16 篇；本轮新增 7 篇（`references/09`–`15`），覆盖选题、证据、细纲、草稿、审稿、改写、终稿 |
| 来源 | 每篇单列「来源」，含公开方法（需求三角、搜索意图、图尔敏模型、BLUF、plain language、Minto 金字塔）与本仓实现路径 |
| 适用边界 | 每篇单列「适用边界」，写明不覆盖的场景（如强监管主题、纯新闻通稿） |
| 误用反例 | 每篇单列「误用反例」，并写明由哪个门禁拦截（`topic.top3`、`research.claim_sources`、`rewrite.facts` 等） |

## 2. 生产层

`content_chain/runner.py` 一条命令串起 7 段，每段一个 JSON 工件：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `content_chain/topic.py` | brief（行业/受众/目标/约束/关键词） | `topic_candidates.json`（10 候选 + 三维分数 + Top3 理由） |
| 2 | `content_chain/research.py` | topic + brief.sources/facts | `research_pack.json`（sources/claims/quotes/gaps + 三档来源） |
| 3 | `content_chain/outline.py` | research | `outline.json`（3–5 节 × 6 字段） |
| 4 | `content_chain/draft.py` | outline + research + brief | `drafts.json`（每节 3 候选 + 多样性 + 选稿理由） |
| 5 | `content_chain/review.py` | drafts | `review.json`（五维 findings：原文 + 改法） |
| 6 | `content_chain/rewrite.py` | drafts + review + brief | `rewrite.json`（200–400 字单元 × 2–4 候选，覆盖率 100%） |
| 7 | `content_chain/final.py` | outline + rewrite + research + brief | `final.md`、`final.html`、`final_audit.json` |

CLI：`skills/s09_content_chain.py` 暴露 `topic/research/outline/draft/review/rewrite/final/run/audit`，
已注册进 `skills/__init__.py`；现有 `s01`–`s08`、`s11` 渠道动作全部保留。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 黄金输入 1 | `fixtures/knowledge.json` | 知识科普长文：内容复利，8 条来源、5 条 claim |
| 黄金输入 2 | `fixtures/tutorial.json` | 工具教程：R11 内容链七道工序，8 条来源、5 条 claim |
| 黄金输入 3 | `fixtures/opinion.json` | 观点文：一人公司内容中台，8 条来源、5 条 claim |
| 黄金成品 | `golden/*.html` | 三份均由链真实跑 fixtures 后落盘，`golden/README.md` 写明输入/命令/逐项验收 |
| 误用样本 | `misuse/*.json` | 全篇套话、结论无证据、改写新增事实，各对应一个具名门禁 |
| 运行账本 | `chain_manifest.json` | 每段 sha256 + 门禁 + 跨段一致性 |
| 证据台账 | `research_pack.json` | 每条来源含 URL、日期、≥12 字原文；每条 claim 挂来源 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 10 候选 / 三维齐 / Top3 有理由 | `topic.check` | CRITICAL（`topic.count`、`topic.scores`、`topic.top3`） |
| ≥8 来源 / URL+日期+≥12 字原文 / claim 挂来源 | `research.check` | CRITICAL（`research.sources`、`research.source_fields`、`research.claim_sources`） |
| 每节 6 字段齐 | `outline.check` | CRITICAL（`outline.fields`） |
| 3 候选 / 多样性 ≥0.6 / 分数 ≥85 / 有理由 / 删公共轨道 | `draft.check` | CRITICAL（`draft.diversity`、`draft.score`、`draft.common_track`） |
| 五维齐 / 每条有原文与改法 | `review.check` + `verify_quotes` | CRITICAL（`review.dims`、`review.quote`、`review.traceable`） |
| 单元 200–400 / 2–4 候选 / 覆盖率 100% / 数字专名一致 | `rewrite.check` + `recheck_facts` | CRITICAL（`rewrite.units`、`rewrite.coverage`、`rewrite.facts`） |
| 结构完整 / 论证流 / AI 套话密度 / 数字可追 / 平台长度 | `final.audit` | CRITICAL（`final.structure`、`final.argument_flow`、`final.ai_fluff`、`final.fact_check`、`final.platform_length`） |
| 跨段一致：章节 id、claims 数字覆盖 final 数字 | `runner.cross_checks` | CRITICAL（`manifest.chapters`、`manifest.numbers`） |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 各段门禁 + 端到端 + 误用拦截 | `tests/test_content_chain.py` | 21 条（7 段门禁、3 端到端、3 误用，其余为独立复核） |
| 端到端数据集 | `fixtures/knowledge|tutorial|opinion` | 3 条，全部 PASS |
| 误用样本 | `misuse/all-fluff.json`、`conclusion-without-evidence.json`、`rewrite-adds-fact.json` | 3 个 |
| 角色验收 | `run_tests.py` §「内容链七段」 | 调用 unittest 加载 21 条并计入总分 |
| 黄金快照 | `golden/*.html` | 3 份 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r11-wadianti-copy/run_tests.py`
- 结果：PASS 93 / 93（含 content_chain 21 条）
- 命令：`python -m pytest r11-wadianti-copy/tests -q -p no:cacheprovider`
- 结果：全绿
- 三份 fixtures 的链结果：7 段门禁全部 PASS；`audit_dir` 独立复核 PASS；
  正文字数 1349 / 1351 / 1336，套话密度均为 0.00。

## 7. 已知边界

- `evolve` 子命令与 `engines/` 十维演练仍保留，供既有 `run_tests.py` 使用；它们与七段链是两套口径，
  待渠道动作收敛后再统一，当前不删。
- 草稿段是确定性模板拼接，不是语言模型生成；语句偏工程化，发布前仍需人工润色。
- 来源 URL/日期/原文由输入提供，链内不联网核验真伪；三手来源不能单独支撑数字结论。
- 事实核对只保证“正文数字可追到 claims”，不保证来源本身可靠；强监管主题需人工审签。
- 终检长度取 brief.constraints；缺省 800–6000 字，短稿场景需显式放宽。
