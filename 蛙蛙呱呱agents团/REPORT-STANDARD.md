# 一人公司 · 汇报规范（REPORT-STANDARD.md）

> 本文档规定**20 个角色给创始人写报告的标准**：写什么、什么文笔、什么排版、什么格式。
> 解决现状问题：多数角色把 agent 返回的 JSON 直接拍成 markdown（`## ok / ## 门禁` + 代码块），
> 没有叙事、没有结论、没有排版——那不是「汇报」，那是日志。
>
> 最低产出线沿用《角色Agent生成SOP》第十节（qiuqiu 编辑级证据报告）。

---

## 一、总原则

1. **结论先行**：第一段就让创始人知道「结果是什么、能不能用、要不要你决策」。
2. **每个数字可复算**：报告里出现的每个数值必须能回溯到某次技能真实输出（`result` JSON）
   或原始数据；模拟数据必须在 meta/notes 明确标注。
3. **以事实说话**：禁空话。禁用词（对齐 R06 T7 规范）：`需要关注` `有待进一步分析`
   `值得注意` `综合来看`（无数字支撑时）`可能存在问题`。
4. **诚实边界**：不制造确定性。数据不足写 `blocked`，未观测混杂写清「只对已调整的观测成立」。
5. **双格式**：`.md`（快读，贴终端/IM）+ `.html`（正式交付，自包含）。

---

## 二、三层报告（谁给谁写）

### 层级 1 · 一线执行汇报（单角色 → 创始人，1 页内）

一个角色被直接调用、独立完成任务后写。结构固定五段：

```markdown
# <角色名> · <任务标题>

**结论**：<一句话给结果 + 能不能用/要不要你决策>

## 执行摘要
- 做了什么（skill/action）
- 关键数字（3-5 个，带口径）
- 门禁结果（PASS/FAIL + 判据）

## 结论与证据
<每个结论 = 一句判断 + 支撑数字 + 数据来源>

## 边界
<这次没覆盖什么、假设是什么、哪里降级了>

## 下一步
<建议动作，或「已移交 Rxx，原因…」>
```

### 层级 2 · 跨域汇总汇报（R01 → 创始人）

多角色协作完成后，R01 汇总。结构：

```markdown
# <项目名> · 跨域汇总

**总体判断**：<这段带 <mark> 高亮核心结论>

## 背景与目标
## 各角色结论
| 角色 | 交付 | 关键结论 | 门禁 |
## 综合判断
<跨角色交叉验证后的判断，冲突点必须点出>
## 决策建议
<条件化建议 + 是否需创始人签字>
## 风险与边界
<未决问题、失效信号、假设>
## 附录
<产物清单 + 事件流关键节点>
```

### 层级 3 · 独立评审报告（R04 → 创始人，旁路直通）

R04 独立出具，**不得与执行角色同稿**，`reviewer == producer` 即 FAIL。结构：

```markdown
# 独立评审报告 · <被评对象>

**裁决**：PASS / FAIL / BLOCKED

## 证据链核查（三级）
| 物料 | L1存在 | L2实质 | L3接线 |
## 对抗挑战结果
| 挑战项 | 结论 | failure_category |
## 缺陷定位
## 复评说明
<本轮修改是否有效；保留清单>
```

---

## 三、文笔标准

| 维度 | 要求 | 反例 |
|---|---|---|
| 开篇 | 结论先行，不用「背景介绍」暖场 | ❌「随着业务发展…」 |
| 语气 | 平实、直接、专业；不谄媚、不夸张 | ❌「非常出色的表现！」 |
| 数字 | 带口径与单位，可溯源 | ❌「营收提升很多」 |
| 因果 | 点名因果必须有分解证据（T7 driver_decomposition） | ❌「因为A所以B」无分解 |
| 建议 | 决策建议须 `advice_authorized`；否则只陈述事实 | ❌ 未授权就替创始人拍板 |
| 长度 | 一线≤1页、汇总≤3页；宁可短而实 | ❌ 堆字数 |
| 语言 | **中文为主** | ❌ 中英混杂无必要 |

---

## 四、排版标准（对齐 SOP 第十节 · qiuqiu 编辑级五件套）

正式 `.html` 报告**五件套缺一不可**：

0. **版式主题（2026-11-15 起）**：默认 `paper`——**研究性报告样式**：白纸、细线、
   暖橙强调色、1120px 内容列、封面无深色底（顶部细线收口），KPI 带上下细线 + 左侧色标。
   与《内蒙古七类蛋白》基准报告同一视觉语言。
   备选 `sticker`（墨绿封面 + 粗黑描边 + 贴纸卡片 + 暖黄高亮，历史主题）。
   其余 `editorial/mono/annual/swiss/slate/noir` 保留为历史主题，新报告不再默认使用。
   打印时保留页边距；封面与正文同一内容列，左右留白对齐。
   已生成的历史 HTML 可用 python scripts/migrate_report_theme.py --root ../workspace --to paper
   一次切换（只改 data-theme，备份写到 _archive/theme_swap/；加 --pdf 可重出 PDF）。
   单个报告要回退旧样式，生成时传 --theme sticker。
   角色的标准报告出口（`role_runtime.emit` → kernel）与深度报告（`deep`/`depth`，经
   `shared/kernel_report_adapter.py` 把 REP-001 spec 映射成 contract）都走这套版式；
   旧模板可用 `GUAGUA_REPORT_ENGINE=legacy` / `GUAGUA_DEEP_ENGINE=legacy` 回滚。
   标题高亮由 contract 可选字段 `title_highlight` 指定（缺省自动取标题末段），渲染为 `<em class="hl">`，
   保证「一句标题里只有一个重点被划出来」。
1. **设计系统**：语义色令牌 `critical / watch / healthy / accent`（红=材料性不利、
   黄=边界、绿=已验证、accent=强调）+ `color-mix` 派生 soft 色 + 12 栏网格。
   **不是「好看的卡片」，是令牌化的证据语义。**
2. **信息架构**：doc-header（双行标题+导语+meta）→ metric-strip（4 KPI+形状标记+microbar）
   → 全文结论（4 段：总体判断/根因/实验结论/决策与边界，末段带 `<mark>`）
   → 分节（每节必有**验证问题** + 图后解读 + **证据边界块**）
   → 证据表（cell-key：判断/边界/下一步/用途）→ 口径说明 → footer。
3. **内嵌 SVG 图表**：坐标由数值确定性计算（异常窗口阴影、菱形标记、参考线、lift 标注框），
   每图带 embed-head（标题+单位）+ embed-source（来源+读图规则）。
4. **确定性渲染**：**不许手写一次性 HTML**。走
   `core/report_renderer.py`：report contract JSON → 校验必填字段（缺即 FAIL）→ 自包含 HTML。
5. **可追溯**：每个数字可回溯到技能真实输出；footer 标注生成角色、时间、数据来源。

### 契约 → 渲染管线（全角色通用）

```
角色技能真实输出（result JSON）
  → report contract JSON（编辑级内容：标题/结论/图表数据/边界）
  → core/report_renderer.py 校验 + 确定性渲染（共享 CSS + SVG 由数值计算）
  → 自包含 HTML（无外部依赖）
```

---

## 五、强制的 report contract（跨角色共享）

所有角色产出 HTML 报告统一走 `core/report_renderer.py` 的契约，顶层必填：

```json
{
  "doc_type": "…",
  "title_lines": ["主标题", "副标题"],
  "standfirst": "一句话导语",
  "metric_strip": [{"label": "…", "value": "…", "note": "…", "status": "critical|watch|healthy|accent|none"}],
  "summary": [{"text": "…", "emphasis": false}],
  "sections": [{"index": 1, "title": "…", "question": "本节的验证问题", "chart": {...}, "verdict": "…"}],
  "notes": ["口径说明…"],
  "footer": {"producer": "r06", "generated_at": "…", "data_source": "…"}
}
```

无 `chart` 的纯文字角色（如 R03 合规、R16 人事）可省略 `chart`，但其余字段必填。

---

## 六、各角色的报告侧重（填 report contract 时的口径差异）

| 角色 | 报告侧重 | 关键 section |
|---|---|---|
| R01 | 决策 + 汇总 | 综合判断、决策建议、风险边界 |
| R03 | 合规风险 | 条款风险表、整改清单、可发/不可发结论 |
| R04 | 独立裁决 | 证据链、对抗挑战、缺陷定位 |
| R05 | 研究证据 | 来源台账、测算链、失效信号 |
| R06 | 数据结论 | 指标树、根因分解、统计检验、图表 |
| R07 | 需求 | PRD、优先级、验收条件 |
| R09 | 工程 | 架构、测试报告、门禁证据 |
| R14 | 交易 | 订单/履约/账务合规结论 |

其余角色同理：**把自己领域的关键结论做成 metric_strip + 分节 + 证据边界块**，
不要吐字段名和 JSON。

---

## 七、验收（如何自检报告合格）

1. 是否有「结论先行」的第一段？
2. 每个数字能否回溯到 result/data？
3. 是否命中任一禁用词？（命中即不合格）
4. 是否声明了边界与假设？
5. HTML 是否由 `core/report_renderer.py` 生成（非手写）？
6. 缺数据时是否诚实标注，而非编造？

任一项不过 → 报告不合格，退回重写（对齐 PROTOCOL.md 模式 B 的 `expression_title_or_line_fit` 路由）。

---

## 八、版式硬规则（内核级，20 个角色自动继承）

这五条写进 `core/report_kernel` 与渲染器，不由角色自由发挥；违反时 `scripts/contract_test.py` 直接报错。

| # | 规则 | 为什么 |
|---|---|---|
| R1 | **首页只放业务结论**，不放保留率/溯源率/弃置率 | 读者先要知道"市场怎么了"，不是"系统跑通了" |
| R2 | **正文最后一节固定是「口径与分数」**，集中放 观测数 / 保留率 / 溯源率 / 弃置率 / 规格 | 自检信息该被看见，但不必挡在结论前面 |
| R3 | **记录层（全量观测表）标 `appendix: true`，渲染为默认折叠** | 数据一条不少（保真），但不占首屏 |
| R4 | **不生成"结论清单/摘要复述"章节** | 正文已说过的再总结一遍就是冗余；回指靠正文内联编号与证据台账 |
| R5 | **全篇禁用斜体**：标题、表头、图注、强调一律正体；标题/表头/图注不得用衬线体 | 中文斜体在 Windows 与 PDF 里是伪斜体（剪切变形），表头最糊；门禁 `scripts/check_report_style.py` |

落到数据结构上：

```python
# 内核产物顺序（不可调换）
sections = [业务章节...] + [{"title": "记录层", "appendix": True, ...}] + [{"title": "口径与分数", ...}]
metric_strip = [业务指标...]            # 只放业务信息；门禁/观测/规格一律进末节「口径与分数」
```

> 2026-11-13 修正：此前本节写的是 `metric_strip = [门禁, 观测, 规格]`，与 R1 自相矛盾，
> 导致内核默认产物首屏是「结果条目 9 / 门禁 10/10」。现已按 R1 改为业务指标，
> 实现见 `core/report_kernel/layers.py::_business_strip`。

### 写作层门禁（2026-11-13 新增，暂不阻断）

版式四规则之外新增四条**写作**判据，实现在 `core/report_kernel/structure.py::writing_errors`
（`guagua report build` 会打印「写作自检」，各角色 specialist 就位后并入硬门禁）：

| # | 规则 | 抓什么 |
|---|---|---|
| R5 | 首页指标带不得出现门禁/观测/规格/保留率 | 首屏是执行元数据而不是业务结论 |
| R6 | 每个业务章节至少有一句带数字的判断 | 整节只有废话或标题 |
| R7 | 结论句必须含数字 | 结论退化成「已完成/已通过」 |
| R8 | 正文「字段：值」回显率不得过半 | 把 result 字段念一遍冒充分析 |

审计口径：`core/report_kernel/structure.py` 的 `layout_errors()` 校验末节标题、appendix 标记、重复章节、首页分数四项，任一不合即测试失败；`scripts/contract_test.py` 与 r08 `htmlreport` 共用这一份实现。

### 怎么验（不靠自觉）

```bash
python scripts/check_report_layout.py --all        # 扫全部成品报告
python scripts/check_report_layout.py a.html b.html  # 指定文件
```

检查器只看 HTML 结果，**不关心报告是内核产的还是项目自绘的**，所以两条产线都管得住。
它同时挂在两处：`scripts/ci_report_checks.py`（第 6 项）与 `guagua report build` 的出厂自检。
规则自身也有例外：含保真分数的报告才强制末节为「口径与分数」；纯业务报告（经营/链路）可以以行动表收尾。

---

## 九、报告路径：默认 core，单智能体按需（2026-11-13）

| 路径 | 入口 | 什么时候用 |
|---|---|---|
| **core（默认）** | `shared/role_runtime.emit` → `core/report_pipeline.build_one` | 所有角色出报告；一次调用 = 一份 L1 + `manifest.json` |
| **单智能体（按需）** | `GUAGUA_REPORT_PATH=single` 或 `python guagua.py report one ... --path single` | 只在明确要旧 REP-001 / 角色专用模板时用；兼容 `GUAGUA_REPORT_ENGINE=legacy` |
| **项目级单份** | `python guagua.py report project --dir <项目目录>` | 跨角色/跨证据源的一份报告（如 R05 调研 × R06 分析）；输入 `data/report.contract.json` |
| **项目层（多角色）** | `python guagua.py report build --project <pid>` | 多角色汇总 L1×N → L2 → L3；单次调用不建 project |

默认 core 做的事：

```
result(+data+dataset)
  → 角色 spec + adapter 组 L1 contract
  → contract 校验 + spec_compliance + layout_errors + writing_errors
  → core/report_renderer 进程内渲染 HTML/MD
  → manifest.json（contract_hash / 三道自检 / fidelity / engine=core）
```

**自检现阶段只记录、不阻断**：`manifest.checks.policy = "warn"`、`blocking = false`。
`spec_compliance` 先按 `section_id` 匹配，再退回 `title`；研究稿的结论句标题因此可以动态生成。

当前对齐状态（2026-11-13）：

| 角色 | 稿子形状 | spec | 状态 |
|---|---|---|---|
| r07 | `decision` 四段 | 原生 | 31 个动作 `spec/layout/writing = 0/0/0` |
| r05 | `research` 10 节研究稿 | 原生（`section_id`） | `0/0/0`，标题仍是证据包结论句 |
| r06 单动作 | `data` 四段 + 图表 | 原生 | `0/0/0` |
| r06 深度稿 | `analysis` 11 节 | 原生（`section_id`） | `0/0/0`；`r06_deep` 单独一份 spec |

下一步：把 `policy` 从 `warn` 切 `hard`（需要加 no-fallback 的拦截逻辑，避免失败后回落旧引擎）。

项目级单份报告的出厂检查（个护报告为 golden）：

```bash
python guagua.py report project --dir 个护调研_2026-11-12 --pdf
python scripts/check_report_project.py --dir 个护调研_2026-11-12 \
    --sections 9 --charts 6 --tables 4
```

`report project` 读 `data/report.contract.json`，补 `section_id`（p1…p7 / A1 / p8），
按 `project` archetype 过 spec/layout/writing 三闸，输出 HTML/MD/PDF + `manifest.json`。
`project` 的 `policy` 是 `hard`：三闸任一失败，CLI 返回 1 并在 manifest 留痕。

单角色出报告的标准命令：

```bash
python guagua.py report one --role r07 --result r.json --input in.json \
  --skill prd --action prd --out workspace/out --name 蛙得明 --title 产品经理
# 只有明确要旧路径时：
python guagua.py report one ... --path single
```


---

## 十、图表引擎 v2 与报告分级（2026-11-15）

### 10.1 图表：v2 默认开启，v1 兜底

`core/charts/v2/` 是研报级图表引擎（matplotlib → 确定性内联 SVG）。
报告 contract 里 `"chart_engine": "v2"` 即生效，模块管线（20 角色）已默认开启；
v2 不支持的图型或数据不足时**自动回退** `chart_lib`，48 型能力不退化
（`python -m core.chart_capabilities --check` 仍须 48/48）。

六条设计规则（改图之前先读 `core/charts/v2/README.md`）：

1. 标题即结论——`chart.title` 必须是一句带数字的判断；
2. 固定几何——宽 980px、标题 13px、右上单位、左下来源，多图上下对齐；
3. 一个强调色——其余灰阶；红/绿只表达好坏，不表达类别；
4. 直接标注——≤3 系列不用图例，线末端标「系列名 + 末值」；
5. 去装饰——无外框、无纵网格、刻度取整；
6. 数据不够不画——schema 不合就回退，绝不出空白图。

画廊：`python scripts/chart_gallery_v2.py`（16 型单页预览）。

### 10.2 报告分级（L0—L4）

`scripts/grade_report_level.py` 只看 HTML 结果，不看报告怎么来的：

| 档位 | 判据（全部满足） |
|---|---|
| L0 日志 | 无结论、无表、无图 |
| L1 摘要 | ≥3 条带数字的结论 + ≥5 节 |
| L2 研究稿 | + ≥5 张表/40 格、≥4000 字、≥8 段、≥8 节、有口径/假设说明、无禁用词 |
| L3 分析稿 | + ≥3 张图且图图有来源、有口径冲突节、有统计复核节、数字密度 ≥1.2、字段回显 ≤30%、段落均长 ≥80 字 |
| L4 决策级 | + 图标题含数字（结论式）、≥1/3 表头带单位、结论带动作/停止条件、≥6000 字 |

基准（内蒙古七类蛋白 · 默认主题）= **L2**，是产线的最低线。
2026-11-15 现状：20 个角色报告 **L3**，宠物调研 **L4**。

```bash
python scripts/grade_report_level.py --dir workspace/all_role_reports
```

---

## 十一、实质门禁与 v2 生成线（2026-11-15）

### 11.1 为什么加这道门禁

分级（§10.2）数图、数表、数字符，模板填空能刷到 L3；2026-11-15 实测 20 份角色报告
被判 L3，但同时存在 260 个空小节、14.2% 的逐字重复句、100 处套话，正文数字来自
代码里的常量而不是语料。判断一份报告是不是「分析稿」，需要另一把尺子。

### 11.2 七条判据（`scripts/check_report_substance.py`）

| # | 判据 | 阈值 | 抓什么 |
|---|---|---|---|
| 1 | 空小节 | = 0 | 有标题没内容（旧报告每份 13 个） |
| 2 | 数字密度 | ≥ 55 个/千字 | 铺形容词（旧 36.1，基准 89.9） |
| 3 | 跨报告逐字重复句 | ≤ 10% | 20 份是同一份（旧 14.2%，新 3.0%） |
| 4 | 套话命中 | = 0 | 「先可逆再结构」这类放之四海皆准 |
| 5 | 表格有效数字格 | ≥ 35% | 表格里全是「—/无」 |
| 6 | 每节有数字判断 | 全部 | 章节只有标题与免责声明 |
| 7 | 数字可溯源 | ≥ 70% | 数字能在语料/台账里找到（新 100%，基准 96.4%） |

阈值用基准报告与旧报告双向标定：基准 100 分通过，旧报告 0/20 通过，新报告 20/20 通过。

```bash
python scripts/check_report_substance.py --dir workspace/all_role_reports \
    --evidence workspace/all_role_reports/r*_evidence.json
python scripts/check_report_substance.py --html <基准报告.html> \
    --evidence <计算指标.json> <证据台账_ledger.json>
```

### 11.3 v2 生成线：语料 → 观测 → 报告

```
角色语料（examples / cases / datasets/ports）
  → core/corpus_analysis.py：观测（source+path+formula）/ 画像 / 分层 / 核验 / 冲突 / 可行性
  → scripts/generate_role_reports_v2.py：结论先行 → 数据基础 → 字段覆盖 → 分布分层 → 越界
      → 核验 → 口径冲突 → 可行性 → 数据合同 → 动作 → 台账 → 记录层
  → core/report_writer + report_modules：HTML / MD / PDF + manifest
```

三条硬约束：

1. **正文每个数字来自观测**；算不出来写「算不出」，进「数据合同」，不补形容词。
2. **角色无关**：20 个角色跑同一套代码，差异来自数据，不来自每角色一段手写文案。
3. **报告长度由数据决定**：角色语料中位数 41.5 个数值，报告平均 2,037 字；基准有 869 个数字，
   8,591 字。要更长，先补数据，不改模板。

```bash
python scripts/generate_role_reports_v2.py --out ../workspace/all_role_reports --pdf
python scripts/ci_report_checks.py        # 第 [7] 步 = 实质门禁，不过即 CI 失败
```

两条硬规则（2026-11-15 追加）：

- **章节内不写小标题**：「构成 / 覆盖 / 分布 / 分层 / 判断」这类词只是复述章节名，
  一律不渲染（分组保留，标题层清空）。
- **CI 必须跑实质门禁**：`scripts/ci_report_checks.py` 第 [7] 步检查 20 份成品；
  旧版 20 份在这里是 0/20，新版是 20/20。

### 11.4 已修的历史缺陷

`core/report_writer.py` 曾同时按「句子」和「数字签名」去重：数字组合相同的不同句子会被整句删除
（「6 条观测/20 条门槛」与「6 个指标/20 条记录」被视为同一句），每份报告因此丢约 57 句、
留下 13 个空小节。现已只保留精确句级去重。

> 结论：报告质量 = f(数据)。模板能把 2,000 字撑到 4,700 字，但撑不出一个可复算的数字；
> 引擎已经能在真实语料上产出基准级数字（内蒙古 8 份 CSV → -5.65%~+4.76% 的分化结论），
> 剩下的差距是每个角色缺自己的「8 份 CSV」。
