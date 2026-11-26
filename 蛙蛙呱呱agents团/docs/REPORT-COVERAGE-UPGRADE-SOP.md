# 报告覆盖升级 SOP（v1.0）

> status: ARCHIVED · 2026-11-26
> 说明：本文描述的 `task_frame` / `task_research` / `coverage_cli` 已于 2026-11-26 删除；
> 覆盖矩阵与 pre_gate 仍由 `coverage_plan` / `coverage_confirm` / `coverage_policy` 承担。
> 当前口径见 `docs/CORE-MAP.md` 与 `docs/_migration/wiring-truth.md`。

> 适用：`蛙蛙呱呱agents团` 全部报告产线（R01 出具，R04 审计）。
> 目标：让“水果 v2 的 8 分”成为**系统可复现的最低标准**，而不是一次性手工稿。
> 本文是唯一口径；阈值集中在 `configs/report_coverage.yaml`，不散落在代码里。

---

## 0. 一句话

**先联网学这个任务该看什么，再生成覆盖矩阵，你确认后才采数；核心不全就停，长尾缺就标红，出稿前后各过一道门禁。**

---

## 1. 目标与非目标

### 目标

1. 换任何业务线，系统都能自己推出该任务的**分析单元、覆盖维度、深度分配、地图要求、页数下限**。
2. 每份报告都能回答：“我覆盖了谁、漏了谁、为什么漏、漏的代价是什么”。
3. 报告达到最低结构标准：封面/摘要/目录/A·B 节页/动作/附录/页码；调研级 ≥21 页。
4. 所有数字可回溯；估算逐项标 `*`；来源分级；媒体只做线索。
5. 覆盖不全时，系统**明确拦或明确标红**，不静默漏掉。

### 非目标

- 不预置水果/调味品/家居等业务线模板。
- 不复用旧任务的 TaskFrame。
- 不保证来源本身为真；只保证“可追溯 + 有分级 + 有冲突处理”。
- 不把文笔做成硬门禁；文笔只评分、给诊断。
- 不替代创始人做不可逆决策。

---

## 2. 术语

| 术语 | 含义 |
|---|---|
| TaskFrame | 任务框架：决策问题、分析单元、维度、深度、地图、页数、来源策略 |
| CoveragePlan | 覆盖矩阵：单元 × 维度 × 证据状态 × 核心/长尾 × 深/浅 × 页数 |
| 核心单元 | 按任务规则选出的 3–5 个单元，必须全深链 |
| 长尾单元 | 进矩阵但不进深链；缺数据可降旁证，标红 |
| 引用源 | 真正写进维度/矩阵/正文的来源，不是“搜过”的网页 |
| 饱和 | ≥50 个引用源，且连续 15 个新来源不再新增维度 |
| 硬门禁 | 不通过就不出报告 |
| 软门禁 | 不通过仍出，但封面/摘要标红，并记录在 gate.json |
| 深链 | 拆到成本项/链路节点/毛利/损耗/证据状态 |
| 旁证 | 只有单点价/角色/背景，不参与主结论 |

---

## 3. 十条原则

1. **研究先于结构**：先学行业，再定维度；8 个元维度只用于提问，不直接当报告目录。
2. **每个任务重新学**：不导入旧 TaskFrame；旧报告只能当来源，不能当模板。
3. **50 个引用源**：少于 50，不出报告；连续 15 个新来源无新增维度，才算饱和。
4. **来源分级**：官方 > 行业报告 > 公司披露 > 学术 > 专业社区 > 媒体线索。
5. **核心全深链**：核心单元缺关键数据就停；长尾可旁证但标红。
6. **先确认后采数**：矩阵没确认，不允许采数、不允许写稿。
7. **双地图强制**：全国 + 区域；城市级能画就画，不强制。
8. **页数由覆盖决定**：调研级 ≥21 页；内容够就继续加，不设上限。
9. **出稿前后双门禁**：`report_flow` 卡覆盖，`quality_gate` 卡成品。
10. **冲突不猜**：来源冲突、维度冲突、研究失败，停下来让人裁决。

---

## 4. 目标架构

```text
task brief
  │
  ├─[1] core/task_research.py      联网研究 50+ 源，饱和判定，来源账本
  │
  ├─[2] core/task_frame.py         TaskFrame：决策/单元/维度/深度/地图/页数
  │
  ├─[3] core/coverage_plan.py      矩阵 + 核心/长尾 + 证据状态 + 页数估算
  │
  ├─[4] confirmation.json          你确认（CLI + 对话），哈希锁定
  │
  ├─[5] report_flow pre-gate       核心深链 / 双地图 / ≥21 页 / 50 源 / 饱和
  │
  ├─[6] report_theme + charts      由 CoveragePlan 生成页面、图、地图
  │
  ├─[7] quality_gate post-audit    覆盖/数据/图表/版式硬，文笔软
  │
  └─[8] R04 签字 + manifest        哈希、来源账本、gate.json
```

---

## 5. RACI

| 环节 | R01 | methods/数据 | R04 | 你 |
|---|---|---|---|---|
| 任务研究 | A | C | I | I |
| TaskFrame | A/R | C | C | I |
| CoveragePlan | A/R | C | C | **C/批准** |
| 采数 | A | R | I | I |
| 出稿前门禁 | A/R | C | I | I |
| 渲染 | A/R | C | I | I |
| 五项全审 | C | I | **R/A** | I |
| 冲突裁决 | C | I | C | **A** |

> A=负责，R=执行，C=咨询，I=知会。角色目录不改；能力进 `core/`。

---

## 6. 端到端流程

| 阶段 | 做什么 | 产物 | 门禁 | Owner |
|---|---|---|---|---|
| S0 任务受理 | 解析 brief、决策问题、范围、约束 | `brief.json` | 决策问题必须一句话 | R01 |
| S1 研究 | 8 元维度提问 + 50 源 + 饱和 | `source_ledger.json` | 50 引用源 + 连续 15 源无新增 | R01 |
| S2 抽维度 | 单元/维度候选，逐条挂来源 | `dimensions.json` | 核心维度至少 1 个 A/B/C/D 源 | R01 |
| S3 框架 | 生成 TaskFrame | `task_frame.json` | 单元/维度不重复、可解释 | R01 |
| S4 矩阵 | 生成 CoveragePlan | `coverage_plan.json` | 核心/长尾标记完整 | R01 |
| S5 确认 | 你确认矩阵、来源、页数 | `confirmation.json` | 无确认不得采数 | 你 |
| S6 采数 | 按矩阵补数 | `data/*` | 核心格必须有数或明确缺 | methods |
| S7 出稿前 | 覆盖/页数/地图/来源 | `pre_gate.json` | 核心缺=BLOCK；长尾缺=红 | R01 |
| S8 渲染 | 页面/图/地图 | `report.html/pdf` | 页数≥21、双地图 | R01 |
| S9 全审 | 五项审计 | `gate.json` | 前四项硬，文笔软 | R04 |
| S10 交付 | manifest + 哈希 | `manifest.json` | 全部 PASS | R01 |

---

## 7. 研究协议（核心）

### 7.1 元维度只做提问

8 个检索起点：

1. 规模与增长
2. 链路与节点
3. 竞争与集中度
4. 渠道与价格
5. 成本与损耗
6. 合规与标准
7. 地理与产区
8. 风险与情景

> 这 8 个不是报告目录；最终维度必须由来源增删。若来源显示“账期/资金占用”是独立维度，就加；若“地理”不适用，就删并写原因。

### 7.2 来源分级

| 级别 | 类型 | 用途 |
|---|---|---|
| A | 国家统计局、海关、农业农村部、标准/法规 | 核心数字首选 |
| B | 行业协会、券商、咨询、产业研究院 | 维度与结构 |
| C | 上市公司年报/招股书/供应商披露 | 成本、渠道、竞争 |
| D | 学术论文/院校研究 | 机理与长期趋势 |
| E | 专业社区/论坛/从业者问答 | 可当证据，标“社区口径” |
| F | 媒体/公众号 | 只做线索，不作为核心维度唯一依据 |

**核心维度规则**：每个核心维度至少 1 个 A/B/C/D 来源；E 可以补证，但不能单独支撑核心维度；F 只能引出来源线索。

### 7.3 50 源与饱和

- 计数：**引用源**（写进维度/矩阵/正文），不是搜索次数。
- 饱和：≥50 个引用源，且连续 15 个新来源不再新增维度。
- 未饱和：停下，交你裁决；不降级、不凑数。
- 来源账本字段：`id,title,url,type(A-F),date,used_for,quote,credibility_note`。

### 7.4 研究失败

任一条触发 `RESEARCH_BLOCKED`：

- 引用源 <50；
- 连续 15 源仍在新增维度；
- 核心维度找不到 A/B/C/D 来源；
- 来源之间对同一维度定义冲突；
- 任务 brief 本身无法形成一句话决策问题。

处理：停止，输出 `research_blocked.json`，让你选“补范围/换问题/接受旁证/终止”。**不自动降级出报告。**

---

### 7.5 从 brief 到 TaskFrame 的推导（系统必须走的 7 步）

1. **定决策**：把 brief 收敛成一句话决策问题；写不出就 `RESEARCH_BLOCKED`。
2. **拆单元**：从来源里抽实体，归到 7 类分析单元：品类/产品大类、SKU/规格、客户群、渠道、城市/区域、竞品、供应商。同一实体只保留一个层级，避免“品类”和“SKU”混算。
3. **抽维度**：用 8 个元维度做提问，读到来源后再增删；每个维度写定义、口径、为什么与决策有关。
4. **聚类去重**：同义维度合并（如“渠道结构/销售通路”）；互相包含的维度只留上层；无法合并的列为冲突。
5. **打分排序**：每个维度按四项打分（1–5）：
   - 决策相关度：不答它，决策会不会变；
   - 证据强度：A/B/C/D 来源数量；
   - 变异性：不同单元之间是否有差异；
   - 可行动性：能不能导向动作/停止线。
6. **定核心/长尾**：按任务规则选 3–5 个核心单元（见附录 B），其余进长尾；核心单元必须覆盖全部必填维度。
7. **定深度/地图/页数**：核心=深链；长尾=旁证；全国+区域地图必填；页数按 `4 + 核心×2 + 长尾合并页 + 综合/动作/附录` 估算，且 ≥21。

> 这 7 步的中间结果都要落盘（`dimensions.json`、`unit_candidates.json`），R04 可逐条追溯；不能只在模型上下文里“想过”。

---

## 8. TaskFrame 规范

```json
{
  "schema": "dsh.task_frame/v1",
  "task_id": "2026-11-19-seasoning",
  "brief": "内蒙古调味料能不能做、从哪进",
  "decision": {
    "question": "一人公司能不能做调味料、从哪条路径进",
    "type": "inferred",
    "success_criteria": ["能判断做/不做", "能给出进入路径", "能给出停止线"]
  },
  "units": [
    {"id": "U1", "name": "酱油", "level": "category", "why_included": "份额最大、增速为正", "sources": ["S03", "S11"]},
    {"id": "U2", "name": "复合调味料", "level": "category", "why_included": "餐饮供应链增长", "sources": ["S07"]},
    {"id": "U3", "name": "餐饮渠道", "level": "channel", "why_included": "B 端主通路", "sources": ["S14"]}
  ],
  "dimensions": [
    {"id": "D1", "name": "规模与增速", "definition": "可复算的市场规模与同比", "why": "决定天花板", "required": true, "sources": ["S03"]},
    {"id": "D2", "name": "链路与加价", "definition": "出厂→一批→二批→零售", "why": "决定能不能进", "required": true, "sources": ["S07"]},
    {"id": "D3", "name": "渠道结构", "definition": "餐饮/商超/电商占比", "why": "决定进入路径", "required": true, "sources": ["S14"]}
  ],
  "depth": {
    "core_rule": "按任务：进入看规模+利润+可进入性；套利看价差+流动性；选品看毛利+周转",
    "core_units": ["U1", "U2"],
    "deep_dimensions": ["D1", "D2", "D3"],
    "long_tail_policy": "context_red"
  },
  "maps": [
    {"level": "national", "purpose": "主产区/流向", "required": true},
    {"level": "regional", "purpose": "盟市/城市节点", "required": true}
  ],
  "page_floor": 21,
  "source_policy": {"cited_min": 50, "saturation_no_new": 15, "grades": ["A", "B", "C", "D", "E", "F"]},
  "saturation": {"cited": 0, "no_new_streak": 0, "reached": false},
  "conflicts": []
}
```

规则：

- 每个 unit/dimension 必须有 `sources`；无来源的维度不能进核心。
- `core_units` 3–5 个；由任务规则推，不由行业名硬编码。
- 分析单元可多级：品类、SKU/规格、客户群、渠道、城市、竞品、供应商。
- 没有“业务线模板”字段；业务线只出现在 brief，不进框架常量。

---

## 9. CoveragePlan 规范

```json
{
  "schema": "dsh.coverage_plan/v1",
  "task_id": "2026-11-19-seasoning",
  "frame_hash": "sha256:...",
  "cells": [
    {"unit": "U1", "dimension": "D1", "status": "verified", "value_ref": "D_market_soy", "sources": ["S03"], "note": ""},
    {"unit": "U1", "dimension": "D2", "status": "estimated", "value_ref": "D_cost_soy", "sources": ["S07", "A2"], "note": "运费按同系数估算，标 *"},
    {"unit": "U3", "dimension": "D3", "status": "missing", "sources": [], "note": "缺餐饮渠道占比"}
  ],
  "core_units": ["U1", "U2"],
  "long_tail_units": ["U3"],
  "depth": {"U1": "deep", "U2": "deep", "U3": "context"},
  "page_estimate": 24,
  "maps": ["national", "regional"],
  "gate": "soft"
}
```

状态：

- `verified`：有 A/B/C/D 来源，可复算；
- `estimated`：用同系数/声明假设，正文标 `*`；
- `missing`：没有可用数据，正文写缺，不补平均值。

核心规则：

- 核心单元 × 必填维度，任何 `missing` → **BLOCK**；
- 核心单元 `estimated` 超过 30% → 警告，需你确认；
- 长尾单元 `missing` → 降 `context`，矩阵和封面标红；
- 长尾单元不能超过总单元 40%；超过则 TaskFrame 重新定义核心。

---

### 9.1 数据形状（shape）——为什么不是所有图都能画

48 型是能力清单，不是每份报告都要用。每个单元格除状态外，还要标 `shape`：

| shape | 含义 | 典型图型 |
|---|---|---|
| `scalar` | 单点标量 | 条形、区间、占比条 |
| `pair` | 同一单元的前后/两地/两方案 | 哑铃、斜率 |
| `panel` | 单元 × 时点/城市/渠道 | 分组柱、热力 |
| `matrix` | 单元 × 维度 | 覆盖矩阵、热力 |
| `timeseries` | 同一口径 ≥3 期 | 折线、同比、情景扇 |
| `breakdown` | 总额 = 分项之和 | 瀑布、堆叠、构成 |
| `flow` | 产地→销地，带量/额 | 流向地图、桑基 |
| `distribution` | 多观测点 | 气泡、散点 |
| `geo` | 点/面 | 地图 |

规则：

1. **问题 + shape 双约束**：先定问题，再定 shape，再选图；
2. shape 不匹配 → 退回表格，不硬画；
3. 图型要求的 shape 不存在，`chart_fit` 记硬失败；
4. 数据采集按 shape 下单：先定要画什么图，再决定采什么数；
5. 48 型不是 KPI；用 8 种合适的图，比凑 20 种不合适的图强。

实现：`core/data_shape.py`（`SHAPES / CHART_SHAPES / candidates / fits / choose / audit_sections`）。

---

## 10. 确认协议

### 10.1 确认物

必须同时给：

1. `coverage_matrix.md`：人读矩阵；
2. `coverage_plan.json`：机读；
3. `source_ledger.json`：50+ 引用源；
4. 页数估算与页面清单；
5. 研究失败/冲突清单（如有）。

### 10.2 确认动作

```bash
python guagua.py report plan "任务" --dir <项目> --out <目录>
# 输出 matrix + plan + ledger + page_estimate
python guagua.py report confirm --plan <coverage_plan.json> --approve \
  --note "核心改为 U1/U2，U3 降旁证"
```

- 确认后写 `confirmation.json`：`plan_hash`、`confirmed_by`、`confirmed_at`、`edits`。
- `plan_hash` 与后续 `task_frame`/`coverage_plan` 不一致 → 重新确认。
- 未确认：`report_flow` 拒绝采数/出稿。

### 10.3 交互规则

- CLI 输出矩阵，你在对话里说“确认/改哪一格”；
- 改核心/深度/页数，必须写进 `edits`；
- 不做 Web 确认页（Phase 2 再评估）。

---

## 11. 出稿前门禁（report_flow）

按顺序执行，任一硬失败即 `BLOCK`：

| # | 检查 | 硬/软 |
|---|---|---|
| G1 | `source_ledger` 引用源 ≥50 | 硬 |
| G2 | `saturation.reached == true`（连续 15 源无新增） | 硬 |
| G3 | `confirmation.plan_hash` 与当前 plan 一致 | 硬 |
| G4 | 核心单元 × 必填维度无 `missing` | 硬 |
| G5 | 核心单元全部 `depth=deep` | 硬 |
| G6 | 全国 + 区域地图都有数据计划 | 硬 |
| G7 | `page_estimate ≥21` | 硬 |
| G8 | 长尾单元已降 `context` 并标红 | 软（必须记录） |
| G9 | 核心 `estimated` 比例 ≤30% | 软（超了要你确认） |
| G10 | 每个图型都通过 `chart_lib.recommend(shape,intent)` 适配 | 硬 |

输出 `pre_gate.json`，写明每条的证据与失败原因。

---

## 12. 渲染契约

### 12.1 页面由 CoveragePlan 生成

页面清单（按顺序）：

1. 封面
2. 摘要（六条判断内）
3. 目录
4. 覆盖矩阵页
5. 核心单元深链页（每单元 1–2 页）
6. 长尾单元合并页（标红）
7. 全国地图页
8. 区域地图页
9. 跨单元综合页（价差/成本/竞争，按任务）
10. 情景/路径/红队
11. 动作页
12. 来源附录
13. 方法与边界

页数 = 由单元数、维度数、地图数决定；≥21。**不再手写 `facts.py` 的 SECTIONS 列表。**

### 12.2 每页必须有

- 结论标题（带数字）；
- 一个问题；
- 事实/解释/所以，或主文 + 右栏；
- 图/表 + 来源 + 口径；
- 边界；
- 页码。

### 12.3 地图

- 全国：主产区 + 流向；有官方产量/进口数据则加一层；没有就写缺。
- 区域：盟市/城市节点 + 市场层级。
- 城市级：有数据就画；不强制。
- 缺图 → 硬失败（G6）。

### 12.4 图表

- 复用 `core/charts/consulting.py` 的图型；不新造第二套语法。
- 一图一结论；直标；来源/单位/样本在图下。
- 估算数据标 `*`；图中不得把估算画成实测。

---

## 13. 出稿后 R04 五项全审

| 项 | 审什么 | 硬/软 | 失败动作 |
|---|---|---|---|
| 覆盖 | 矩阵单元/维度是否都进报告；核心是否深链；长尾是否标红；地图/页数 | 硬 | BLOCK |
| 数据 | 每个数字可回溯；来源账本；估算标 `*`；无孤立数字 | 硬 | BLOCK |
| 图表 | 图题即结论；来源/单位；无装饰；地图规范 | 硬 | BLOCK |
| 版式 | A4、页码、无溢出、打印对比度、字体 | 硬 | BLOCK |
| 文笔 | 判断句、无模板复读、术语解释、边界 | 软 | 评分 + 诊断，不拦 |

R04 输出 `gate.json` + 签字；R01 不能自己签。

---

## 14. 数据与引用规则

1. **一个数字一个来源**；派生量写公式。
2. **估算**：只允许同系数/声明假设；每项标 `*`；正文写“不是实测，不能对外报价”。
3. **缺失**：写“缺”，不补平均值、不补形容词。
4. **社区来源**：标 `E/社区口径`，不得单独支撑核心维度。
5. **媒体**：只做线索；最终依据必须是 A/B/C/D。
6. **冲突**：两个来源数字/定义冲突 → 停，列冲突表，让人裁决。
7. **时间**：每个来源标日期；跨年数据标年份；不混用。

---

## 15. 异常处理

| 异常 | 动作 |
|---|---|
| 引用源 <50 | `RESEARCH_BLOCKED`，停下 |
| 连续 15 源仍在新增维度 | `RESEARCH_BLOCKED`，扩范围或换问题 |
| 核心维度无 A/B/C/D 源 | `RESEARCH_BLOCKED`，让你裁决 |
| 核心单元缺关键数据 | `COVERAGE_BLOCKED`，列出缺项 |
| 长尾缺数据 | 降 `context`，矩阵/封面标红，继续 |
| 双地图缺一 | `COVERAGE_BLOCKED` |
| 页数 <21 | `COVERAGE_BLOCKED` |
| 未确认矩阵 | `FLOW_BLOCKED`，不采数 |
| R04 前四项任一失败 | `QUALITY_BLOCKED`，返工 |

所有异常写 `blocked.json`：`code,message,missing[],owner,next_action`。

---

## 16. 产物与目录

```text
out/
  brief.json
  source_ledger.json
  dimensions.json
  task_frame.json
  coverage_plan.json
  coverage_matrix.md
  confirmation.json
  data/
  pre_gate.json
  report.html
  report.pdf
  gate.json
  manifest.json
```

`manifest.json` 必须含：`task_id`、`frame_hash`、`plan_hash`、`confirmation_hash`、`source_count`、`page_count`、`gate.layers`。

---

## 17. CLI（拟）

```bash
# 1) 研究 + 框架 + 矩阵（不采数）
python guagua.py report plan "任务" --dir <项目> --out <目录>

# 2) 确认矩阵（可带修改说明）
python guagua.py report confirm --plan <coverage_plan.json> --approve --note "..."

# 3) 采数 + 出稿（无确认则拒绝）
python guagua.py report build --plan <coverage_plan.json> --out <目录> --pdf

# 4) 出稿后全审
python guagua.py report audit --plan <coverage_plan.json> --html <report.html> --json gate.json
```

旧 `report run-line` 保留兼容；新流程走 `plan → confirm → build → audit`。

---

## 18. 阈值配置

`configs/report_coverage.yaml`：

```yaml
coverage:
  cited_sources_min: 50
  saturation_no_new: 15
  page_floor: 21
  maps_required: [national, regional]
  core_units_min: 3
  core_units_max: 5
  long_tail_ratio_max: 0.40
  core_estimated_ratio_max: 0.30
  core_missing: block
  long_tail_missing: context_red
  quick_tier: false
audit:
  hard: [coverage, evidence, charts, layout]
  soft: [prose]
```

> 所有报告同一标准；`quick_tier: false` 是明确选择，不做快报例外。

---

## 19. 验收

### 19.1 调味料试点（第一个非水果任务）

必须做到：

- 50 个引用源，连续 15 源无新增；
- 矩阵经你确认；核心 3–5 个；核心全深链；
- 全国 + 区域地图；
- ≥21 页；
- 出稿前门禁 PASS；R04 前四项 PASS；
- 文笔评分 ≥ 基线（不硬拦）。

### 19.2 水果 v2 回归

- 24 页不回退；
- 10 品类、7 链、3 深链、双地图；
- 覆盖门禁仍 PASS；
- 不因新流程改动而丢页/丢图。

### 19.3 系统级验收

- 任选一个**未预置**的业务线，只给 brief，系统能产出 TaskFrame + Plan；
- 计划中不出现“水果/调味品”硬编码常量；
- 来源账本可逐条打开；
- 所有阈值只在 yaml 出现一次。

---

## 20. 实施计划

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 | 本文档 + `configs/report_coverage.yaml` + JSON schema + CLI 骨架 | 口径冻结，阈值唯一 |
| P1 | `task_research.py` + `task_frame.py`（50 源/饱和/来源分级） | 调味料能出 TaskFrame，不采数 |
| P2 | `coverage_plan.py` + 确认 + `report_flow` 出稿前门禁 | 未确认不能采数；核心缺 BLOCK |
| P3 | 渲染由 CoveragePlan 生成 + 双地图 + 页数 | 调味料 ≥21 页，核心全深链 |
| P4 | `quality_gate` 五项 + R04 签字 + manifest | 前四项硬，文笔软 |
| P5 | 水果 v2 回归 + 第二个业务线试点 | 不回退、可复制 |

---

## 21. 指标

| 指标 | 目标 |
|---|---|
| 引用源数 | ≥50 |
| 饱和 | 连续 15 源无新增 |
| 核心深链完成率 | 100% |
| 长尾标红率 | 100%（缺数据时） |
| 页数 | ≥21 |
| 双地图 | 100% |
| 出稿前门禁一次通过率 | ≥80% |
| R04 前四项一次通过率 | ≥80% |
| 返工率 | <20% |
| 单份报告研究时长 | 可接受范围内，不设硬上限 |

---

## 22. 风险与反模式

| 风险/反模式 | 处理 |
|---|---|
| 50 源导致极慢 | 异步任务 + 进度；不降标准 |
| 为了凑 50 源引垃圾 | 来源分级；核心维度必须 A/B/C/D |
| 维度爆炸 | 核心 3–5 个；长尾≤40% |
| 长尾偷偷当核心 | 矩阵/封面标红；R04 覆盖审计 |
| 用旧框架省事 | 禁止复用；旧报告只能当来源 |
| 估算冒充实测 | 标 `*`；正文写明不能对外报价 |
| 媒体当依据 | 只做线索；核心维度必须升级来源 |
| 文笔硬拦导致模板化 | 文笔软；只评分 |
| 确认变形式 | 无 `confirmation.json` 直接 BLOCK |
| 页数注水 | 页数由矩阵生成；每页必须有判断/证据 |

---

## 23. 附录 A：检查清单

### 研究前

- [ ] brief 能一句话说清决策问题
- [ ] 范围/时间/地域/币种/口径
- [ ] 8 个元维度只做提问，不写进目录
- [ ] 来源分级规则已知

### 研究中

- [ ] 每个维度/单元有来源
- [ ] 引用源计数（不是搜索数）
- [ ] 连续 15 源无新增
- [ ] 冲突已记录
- [ ] 媒体只做线索

### 确认前

- [ ] 矩阵含单元×维度×状态
- [ ] 核心/长尾标记
- [ ] 深/浅标记
- [ ] 页数估算
- [ ] 来源账本可打开

### 出稿前

- [ ] 50 源 + 饱和
- [ ] 确认哈希一致
- [ ] 核心无 missing
- [ ] 双地图
- [ ] ≥21 页

### 出稿后

- [ ] 覆盖/数据/图表/版式四项硬过
- [ ] 文笔评分
- [ ] R04 签字
- [ ] manifest 哈希完整

---

## 24. 附录 B：核心规则（按任务推导，不做业务线模板）

| 任务（系统推断） | 核心单元怎么选 | 必须深链的维度 |
|---|---|---|
| 能不能做/从哪进 | 规模 × 利润 × 可进入性 Top3–5 | 规模、链路、成本、渠道、合规 |
| 能不能套利 | 价差 × 流动性 Top3–5 | 价差、口径、运费、损耗、账期 |
| 先做哪个品类 | 毛利 × 周转 × 需求 Top3–5 | 毛利、周转、季节、渠道、竞争 |
| 成本为什么高 | 成本占比 Top3–5 | 成本项、链路节点、损耗、规模 |
| 竞争格局 | 份额 × 增速 Top3–5 | 份额、集中度、进入壁垒、替代 |
| 风险/合规 | 暴露 × 概率 Top3–5 | 合规、处罚、召回、替代、舆情 |

> 表里是**任务规则**，不是行业模板；业务线只影响来源和单元，不影响规则本身。

---

## 25. Definition of Done

一份报告只有在以下全部为真时才叫“完成”：

1. `source_ledger` ≥50 个引用源，饱和标记为 true；
2. `task_frame`/`coverage_plan` 哈希与 `confirmation.json` 一致；
3. 核心单元全深链，无 missing；
4. 长尾缺数据已降旁证并标红；
5. 全国 + 区域地图都有；
6. ≥21 页；
7. 出稿前 `pre_gate` PASS；
8. 出稿后 `gate` 前四项 PASS，R04 签字；
9. `manifest` 含全部哈希与来源数；
10. 报告里每个数字可回溯，每个估算标 `*`。

---

**版本**：v1.0 · 2026-11-19  
**Owner**：R01 蛙全局  
**Auditor**：R04 蛙挑剔  
**下一版触发条件**：调味料试点完成，或阈值需要调整（只改 yaml，不改文档口径）。
