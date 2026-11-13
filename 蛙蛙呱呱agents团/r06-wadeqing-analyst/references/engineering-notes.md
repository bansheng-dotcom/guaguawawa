---
name: r06-wadeqing-analyst
description: 数据分析师角色技能。把业务问题转成可复算、可验证的数字结论：指标语义建模、数据清洗质检、探索与漏斗/留存/RFM、根因贡献分解、统计检验与A/B实验、科学计算与NLP、生信专项、可视化与可审计报告、自媒体数据运营。当需要分析 CSV/表格数据、算指标、做漏斗留存、检验统计结论、生成经营或自媒体日报时使用。
---

# R06 蛙得清 · 数据分析师
> 蒸馏自: 
> 补充技能/01-当前能力域/nimrodfisher__data-analytics-skills (全量 31 个场景)
> 补充技能/01-当前能力域/py-why__dowhy (因果推断模块)
> 补充技能/01-当前能力域/Starlitnightly__omicverse (生信与高维分析模块)

把能力全景里的 **9 个能力域各自做成一个独立技能模块**（`skills/s01..s09`）。
本角色不再停留在“纯文本与 JSON 的规则门禁”层面。我们已经为其注入了 **Pandas、SciPy、statsmodels 等真实计算环境**以及**外置的动态业务规则字典 (`rules/`)**，让它成为一个真正能吃进数据、跑出记分卡、并生成自动化报告的执行型员工。

## 深度决策报告（厚度 + 深度，2026-11 新增）

单跑一个技能只能得到「点结论」。要出**能直接给创始人拍板的厚报告**，用深度流水线：

```bash
# 七步分析链：质量体检 → 趋势 → 时序诊断 → 结构拆解 → 帕累托 → 分布 → 显著性
python agent.py depth --input workspace/parking_profit_12m.csv \
  --decompose-input workspace/parking_profit.csv \
  --value profit --date month --dim zone --period month \
  --before 2025-09 --after 2025-10 --intent "停车场 12 个月利润结构诊断"

# 等价：直接跑流水线脚本
python pipelines/deep_report.py --input workspace/parking_profit_12m.csv ...
```

产物：`workspace/deep_report/deep_report.html`（内嵌 SVG 图表）+ `deep_report.md`（快读版）。
实测：**3 张图 / 6 个分析小节 / 1 份审计附录，HTML 32KB，MD 9.5KB**（改造前 868B、0 图）。

| 文件 | 职责 |
| :--- | :--- |
| `pipelines/deep_analysis.py` | 七步链，逐步调用本角色技能，产出 figures / sections / appendix / signals |
| `pipelines/deep_report.py` | 装配 REP-001 规格（决策指令 + KPI + 三级归因 + 护栏 + 灰度 + 附录）并渲染 |
| `tests/test_deep_report.py` | 防退化断言：图 ≥3、小节 ≥5、附录非空、无乱码 |

标准见 `agents/docs/SOP_REPORT_DEPTH.md`；共享能力见 `agents/shared/report_depth.py`。

---

## Quick Start

```bash
python agent.py manifest                                    # 协作契约 + 9 技能清单
python agent.py demo                                        # 生成示例订单数据(带脏数据)

python agent.py semantics validate --input model.json      # S01 语义层校验
python agent.py semantics tree     --input model.json      # S01 指标树
python agent.py semantics link     --input model.json --data orders.csv   # 防幻觉联动
python agent.py semantics compute  --input model.json --data orders.csv   # 度量实算
python agent.py semantics reconcile --a 100 --b 90 --label gmv          # 口径对账
python agent.py quality audit  --input examples/orders.csv           # S02 六维质量审计
python agent.py quality clean  --input examples/orders.csv           # S02 清洗去重
python agent.py explore trend  --input examples/orders.csv --date date --value amount
python agent.py explore cohort --input examples/orders.csv --user user_id --period date
python agent.py explore time_series --input examples/orders.csv --date date --value amount --window 3
python agent.py explore segment --input examples/orders.csv --features amount,sessions --k 3
python agent.py explore metrics --input subs.csv --model saas     # 或 --model ecommerce
python agent.py rootcause drilldown --input examples/orders.csv --dim channel --value amount
python agent.py statistics abtest --input examples/orders.csv --group channel \
    --control 抖音 --treatment 微信 --metric amount
# 能力域5 按来源技能粒度拆细为 9 个单功能子命令（上一行改用 abtest）：
#   describe / correlate / ttest / chi2 / anova / regression / abtest
#   power   —— A/B 设计前置：样本量 / MDE 反解（statsmodels 功效同口径）
#   causal  —— 因果四步（dowhy 口径）：混淆识别 / 后门分层调整 / 安慰剂反驳
python agent.py power --baseline 0.15 --mde 0.03            # 每组需要多少样本
python agent.py power --baseline 0.15 --n-per-group 1000    # 这个样本量能检出多小的效果
python agent.py causal --input data.csv --outcome spend --treatment plan \
    --confounders is_member,hours_peak --trials 200 --seed 0
python agent.py scinlp backend                              # S06 探测重后端
python agent.py domain list                                 # S07 omicverse 31 技能
python agent.py viz spec --input chart.json                 # S08 图表规格门禁
python agent.py selfmedia dashboard --input normalized.json # S09 自媒体看板

python agent.py contract list                               # T6 9 技能机器可读契约
python agent.py contract validate --skill explore --action saas --output r.json
python agent.py review --result r.json --skill explore --action saas --data orders.csv  # T7 对抗评审
python agent.py case list                                    # T8 案例库
python agent.py case validate --case retail-profitability
python agent.py harness plan --input plan.json               # 分析计划门禁
python agent.py harness semantic --input model.json --data orders.csv  # T5 语义门禁+联动
python agent.py harness dataset --input examples/orders.csv --semantic examples/semantic_model.json
python agent.py run --task <task_id>                        # 协作入口
```

## 能力域 → 技能模块

| # | 能力域 | 子命令 | 真实执行的动作 | 整合自 |
|---|---|---|---|---|
| S01 | 指标语义建模 | `semantics validate/tree/link/compute/reconcile` | dbt MetricFlow 语义模型校验(引用完整性) + 指标树 + 语义↔数据真联动(防幻觉) + 度量实算 + 口径对账 | semantic-model-builder / metric-reconciliation |
| S02 | 数据清洗质量 | `quality audit/clean` | 六维打分 + 缺失/重复/离群/新鲜度 + 清洗写回 | data-quality-audit / programmatic-eda |
| S03 | 探索产品分析 | `explore trend/groupby/funnel/cohort/rfm/saas/time_series/segment/metrics` | 趋势/分组/漏斗/留存/RFM/SaaS + 时间序列(季节强度+异常检测) + k-means分群(画像+策略) + 业务指标(SaaS/电商) | funnel / cohort / segmentation / time-series / business-metrics-calculator |
| S04 | 根因贡献度 | `rootcause decompose/drilldown` | 贡献分解(Δ/总变化) + 下钻帕累托 | root-cause-investigation |
| S05 | 统计因果实验 | `describe/correlate/ttest/chi2/anova/regression/abtest/power/causal` | 描述/Pearson r/Welch t/卡方/ANOVA/OLS/A/B(lift+SRM)，均带效应量分级；power=样本量/MDE反解（statsmodels 同口径）；causal=dowhy 四步（混淆识别/后门分层调整 ATE/安慰剂置换反驳，naive=效应+混杂偏差分解） | statsmodels / scipy / dowhy 四步 / ab-test |
| S06 | 科学计算NLP | `scinlp describe/textstats/backend` | 偏度 + 词频/bigram/类Zipf + 重后端探测 | scipy / spaCy |
| S07 | 专业领域分析 | `domain list/run` | omicverse 技能注册表 + 后端门禁 + 管线脚手架 | omicverse 31 skills |
| S08 | 可视化报告 | `viz spec/report/guide` | 图表规格 schema 校验(48 图类) + 报告组装(含QA清单) + 图表选型(48 类提示词) | plotly / 48图表提示词 / data-analysis-report-agent |
| S09 | 自媒体运营 | `selfmedia normalize/dashboard/report` | 多平台归一 + KPI+HHI校验 + ready/partial/failed日报 | self-media-data-console |

## 协作契约

- **inputs**：`dataset`（数据文件）、`metrics_spec`（口径，经端口 `note` 传 `key=value`）。
- **outputs**：`dataset`（清洗后）、`analysis_report`。
- 结果以一行 `__AGENT_RESULT__ {json}` 输出，供编排器以子进程方式消费。
- 协作入口 `run --task` 按**意图关键词 → 技能+动作**确定性路由（见 `_INTENT_ROUTES`），
  产物与报告写回 `workspace/artifacts/{task_id}/`。

## 关键纪律（保留自 reference，校验环不丢）

1. 质量是门禁：清洗/质检产出 `rows_after`、维度分、`overall_score` 才放行。
2. 指标无口径不可复算：语义层 `agg/type` 白名单 + 引用完整性校验，对账超容差直接 `fail`。
3. 语义必须落到真实数据：`link` 校验每个 `expr` 列存在（防幻觉），`compute` 实算度量验证口径。
4. 吐多少由契约锁死：`contract validate` 用 JSON Schema 校验每次产出，不符即 `fail`。
5. p 值≠效应量：统计模块同时报 lift / Cohen's d / η² / R² / Cramér's V；相关不写成因果。
6. 数据不足不制造确定性：`domain`（生信）后端不齐即返回 `blocked`。
7. 对抗评审默认拦截：`review` 用 6 项确定性挑战（契约/证据边界/驱动分解/建议授权/禁用词/报告价值），
   点名因果无分解、未授权建议、结论超数据边界 → `FAIL` 并按 react/writer/controller 回路由。
8. 业务知识进案例库：`case` 的语义层（grain/fields/术语/边界）+ 阈值 + 范例是跨请求资产，不硬编码进技能。

## 边界

数据不足时不制造确定性；正式财务/统计意见交 R03。dowhy 四步的核心逻辑（混淆识别/
后门分层调整/安慰剂反驳）已在本角色以纯标准库落地；EconML 级的 IV/双机器学习与
omicverse 生信重后端由 R19 蛙智模承载，本角色统计检验是探索前哨。causal 的结论只对
**已调整的观测混杂**成立，未观测混杂（隐藏共同原因）不可消除，结果 note 必须如实声明。

## 详细参考（9 个模块）

- [模块A 指标语义与口径](references/01-metric-semantics.md)
- [模块B 数据清洗与质量门禁](references/02-data-quality.md)
- [模块C 探索性与产品分析](references/03-exploratory-analysis.md)
- [模块D 统计与因果推断](references/04-statistics-causal.md)
- [模块E 可视化与报告输出](references/05-visualization-report.md)
- [模块F 根因与贡献度](references/06-root-cause.md)
- [模块G 科学计算与 NLP](references/07-scientific-nlp.md)
- [模块H 专业领域分析(生信)](references/08-domain-analysis.md)
- [模块I 自媒体数据运营](references/09-selfmedia-ops.md)
- [模块J SQL/Schema/元数据](references/15-sql-schema-catalog.md)

---

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `build-web-data-visualization` · Web 数据可视化（规范；消费方：r08, r09, r10）
- `data-processing` · 数据处理与可视化（规范；消费方：r18, r02）

查看：`python guagua.py capabilities --role r06`

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `build-web-data-visualization` · Web 数据可视化（规范；消费方：r08, r09, r10）
- `data-processing` · 数据处理与可视化（规范；消费方：r18, r02）

查看：`python guagua.py capabilities --role r06`
