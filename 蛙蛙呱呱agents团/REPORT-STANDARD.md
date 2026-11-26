# 报告标准（REPORT-STANDARD.md）

> **v11 单入口（2026-11-18 · P1–P5 完成）**：唯一命令是
> `python guagua.py report "你的问题" --dir <项目> --out <目录> [--pdf]`。
> `build / decide / produce / pack / research / run` 与 `--lens / --thesis` **已全部删除**。
> 报告合格由 **三层质检** 判定（`core/quality_gate.py`）：
> **证据**（数字可复算、来源齐）+ **编辑**（每节有机理与可证伪条件、不复读）+ **呈现**（无斜体、A4 可打印、对比度、字阶、图四件套）。
> 三层全过才 `ok=true`；另有决策稿特有的 **binding**（问几个答几个）与 **图契约** 两道并列门禁。
> 本文以下关于「两个分支 / 22 纲领 / run/pack/produce/research」的内容是历史标准，保留作对照；
> 命令一律以 `docs/REPORT-LINES.md` 为准。

> 2026-11-15 产线收敛：**报告只有一个作者 —— R01 蛙全局**。
> 20 个执行角色只交 `result`（数字与证据），不再各自出报告。
> 本文规定这一份报告写什么、怎么判合格、怎么验。

---

## 一、总原则

1. **一个作者**：报告由 R01 出具并署名；执行角色没有报告出口。
2. **结论先行**：第一段就让创始人知道「结果是什么、能不能用、要不要他决策」。
3. **每个数字可复算**：正文数字必须能回溯到某份 `result.json` 的字段路径。
4. **以事实说话**：禁用词（命中即不合格）：`需要关注` `有待进一步分析`
   `值得注意` `综合来看` `可能存在问题` `有待观察` `进一步优化`。
5. **诚实边界**：数据不足写「未产出 / 算不出」，不补形容词。
6. **双格式**：`.md`（快读）+ `.html`（正式交付，自包含）。

---

## 二、一条产线，两个分支

```
用户意图
   │
R01 s01 意图识别 → s02 路由 / 拆卡（任务卡六段）
   │
   ├─ 分支 A：单角色够用 → 1 张卡
   └─ 分支 B：需要跨角色 → N 张卡 + 波次
                │
        执行角色跑技能 → 只交 result.json（role_runtime.emit）
                │
        R01 s09 解读（result → 带数字的判断：结论/驱动/边界/动作）
                │
        core/report/report_flow.py → core/report/report_renderer.py（唯一渲染器）
                │
        一份报告（HTML + MD + manifest，署名 R01）
```

分支只决定「发几张卡」，后半段（收集 → 解读 → 渲染 → 签发）完全共用。

| 分支 | 什么时候走 | 判据 |
|---|---|---|
| A | 一个角色的技能就能回答 | 路由只命中 1 个角色，且实际只拿到 1 份 result |
| B | 需要跨角色技能 | 路由 ≥2 个角色，或实际拿到 ≥2 个角色的 result |

实际参与角色以 `--results` 里出现的 `role` 为准：路由说 A、但真收到两份 result，报告按 B 出具。

---

## 三、命令（以 `core/report/report_cli.py` 注册为准：run / check / charts / capabilities / plan）

```bash
# 0) 证据打包：项目目录 → 可寻址的数字索引（调研级报告的前提）
python guagua.py report pack --dir 家居百货内蒙调研_2026-11-15 --out workspace/_pack_home

# 1) 单角色/跨角色：result → 一份报告（前面两条分支）
python guagua.py report run --intent "2月经营诊断" \
    --results workspace/artifacts/r06/xxx/result.json \
              workspace/artifacts/r13/yyy/result.json \
    --out workspace/reports/2026-02-diag [--pdf] [--theme paper]

# 2) 调研级：证据包 + 章节稿（模型写、逐节过账）
python guagua.py report run --intent "内蒙古家居百货市场调研" \
    --evidence workspace/_pack_home/evidence_pack.json \
    --draft workspace/_pack_home/draft_sections.json \
    --out workspace/reports/home_research

# 3) 自动纲领（v4）：读项目目录 → 选方法 → 出章节稿 → 过账 → 渲染
python guagua.py report produce --intent "内蒙古肉禽蛋市场调研" \
    --dir 内蒙古肉禽蛋调研_2026-11-12 --out workspace/reports/meat_v4
#   可选 --thesis research|operations|remediation|chain|forecast；旧 --profile 仍兼容

# 4) 验一份成品（CI 同款）
python guagua.py report check --html workspace/reports/home_research/report.html

# 5) v5 工程化：方法与角色适配（不产报告）
python guagua.py report capabilities               # 20 角色 / 195 技能：谁能进报告、输出什么
python guagua.py report plan --dir <项目> --intent "增长诊断"   # 这份数据会挂哪些方法
```

`--draft <file.json>`：单段判断稿（`judgement`）或整篇章节稿（`sections`），
由模型/人写，产线只做校验与渲染。

---

## 三之二、调研级报告：模型写章节，规则逐节过账

家居百货、肉禽蛋那种 9 节 × 每节图 + 4 条解读的报告，不是模板填出来的，
也不是手写 HTML——是**模型读证据包后逐节写稿，产线逐节验账**。

```
report pack            项目目录（data/obs_*.json / ledger / CSV / gates）→ evidence_pack.json + brief.md
      ↓                每个数字带 id、名称、值、单位、期、来源文件
模型读 brief           决定几个问题、每节用哪些 id、画什么图、写什么判断
      ↓                draft_sections.json：title/question/refs/chart/reading/boundary
report run --evidence --draft
      ↓                s09 sections 校验：标题带数、refs 存在、每个数字可由 refs 解释、图带来源与数据
渲染 + 门禁             9 节 / 每节 1 图 / 每节 600 字 / 密度 ≥25
```

「可由 refs 解释」= 等于某个 ref 的值（含 %/‰ 换算），或是两个 ref 的差/和/比/变化率。
编一个数会在校验时被点名（`第 N 节: 解读 J 的数字 X 无法由 refs 解释`），报告不渲染。

## 三之三、自动纲领（v4）：方法库按数据选节

v3 的章节计划把「哪张表、哪一列」写死在 profile 里，换项目就跑不动，也只会写一阶描述。
v4 把这一步拆成数据台 → 方法库 → 纲领 → 成稿（`docs/REPORT-LINES.md`）：

- `core/data/analysis_desk.py` 识别时间/实体/数值/单位，价格统一元/斤，每个数字有 id；
- `core/analysis_methods.py` 12 个方法产出「带数字的判断」（结构/节奏/轨迹/贡献/单位经济/
  传导/套利/保本/敏感性/风险/样本/台账），统计与成本步骤真调 r06/r19/r15 技能；
- `core/report/report_thesis.py` 五类纲领（调研/经营/整改/链路/预测）决定选哪些判断、开篇与动作；
- `core/report/report_assembly.py` 装配章节稿 → `report_flow` 逐节过账 → 唯一渲染器 → R04 清点。

口径纪律（写进代码）：活畜价不参与「产地→批发」价差；损耗率/冷链成本是声明假设；
技能因样本不足拒绝出斜率时，报告照写「引擎拒绝」，不自己补一个。

两个已验证样例（同一套产线、不同数据）：

| 样例 | 数据 | 规模 | 门禁 |
|---|---|---|---|
| 内蒙古家居百货市场调研 | 54 个来源 / 993 个数字 | 9 节 + 记录层 + 口径 / 7 图 / 4 表 / 5.9k 字 / 密度 86.6 | PASS |
| 内蒙古肉禽蛋经营诊断 | 19 个来源 / 228 个数字 | 5 节 + 记录层 + 口径 / 4 图 / 3.2k 字 / 密度 73.6 | PASS |


---

## 四、判断（解读）的五条硬判据

解读在 `r01-waquanju-ceo/skills/s09_interpret.py`，任一条不过就不渲染：

| # | 判据 | 抓什么 |
|---|---|---|
| 1 | 标题必须带数字 | 「经营情况良好」不是结论 |
| 2 | 每条结论必须带数字，且数字能在 result 里找到 | 编数字、拍脑袋 |
| 3 | 每条结论必须挂来源（角色/技能） | 无出处的判断 |
| 4 | 必须写边界（只对什么成立、哪里没观测） | 把局部结论说成普遍规律 |
| 5 | 动作必须带停止条件 | 只给建议不给退出条件 |

规则模式（mode=`rule`）只陈述能从 result 复算的东西，会显得朴素——这是有意的：
**宁可朴素，不可编造**。要更深的判断，给 `--draft`，让 R01 校验。

---

## 五、报告结构（contract，全产线唯一）

`core/report_flow.build_contract()` 固定产出：

| 顺序 | 章节 | 必有 | 说明 |
|---|---|---|---|
| 1 | 结论与证据 | ✓ | 每条结论 = 一句判断 + 数字 + 来源 |
| 2 | 数据基础 | 有数字时 | 可复算数字表（path / 值 / 来源） |
| 3 | 驱动与结构 | 有驱动项时 | 占比/贡献/增速类指标 |
| 4 | 动作与停止条件 | ✓ | 做什么 / 前置 / 停止 |
| 5 | 边界与缺口 | ✓ | 只对什么成立、没观测什么 |
| 附录 | 记录层 | ✓ | 证据台账，默认折叠 |
| 末节 | 口径与分数 | ✓ | 生成方式 / 证据规模 / 自检项 |

契约必填：`doc_type / title_lines / standfirst / metric_strip / summary /
sections / notes / footer`；渲染走 `core/report/report_renderer.py`，**禁止手写一次性 HTML**。

### 五之三、能力级别（SUPPLY-SOP v7.0）

口径节**第一条**必须是「能力级别」，写清计划与实际：

```
能力级别  计划 L1 / 实际 L1（点证据，能答现状与对比）
能力级别  计划 L2 / 实际 L1；计划 L2，实际只有点证据（未做序列采集）；补采条件：需采购第三方商品库
```

| 级别 | 含义 | 能答什么 |
|---|---|---|
| L0 | 只有拆解 | 出不了报告 |
| L1 | 点证据（数字+来源） | 现状、对比、排序 |
| L2 | 序列证据（长表） | + 趋势、分布、构成 |

**规矩**：计划 L1 交付 L1 是**按计划交付**，不叫降级；计划 L2 实际 L1 才叫降级，
且必须在供给方案里写 `L2_condition`（要多少钱/多少时间才能到 L2）。

### 五之二、无数据节（降级，FEASIBILITY-SOP v5.0）

采不到的判断**不许砍掉，也不许编数字**，而是保留成「无数据节」：

| 规则 | 说明 |
|---|---|
| 标题在 | 标题以 `（无数据）` 开头，仍是报告的正式一节 |
| 正文写原因 | 必须有 `why`（为什么采不到）+ `tried`（试过哪些源） |
| 不进数字校验 | 它没有数字，11 字段与 refs 校验都跳过它 |
| 但必须有 `why` | 没有 `why` 的降级节判失败——读者要知道缺什么 |
| 计入节数 | `has_sections ≥ 3` 时降级节也算一节 |

正文固定写法：`本节当前无数据支撑：<why>（已尝试来源：<tried>）`。

**为什么**：报告的价值不只在"答出了什么"，也在"诚实标出了哪些没答出来"。砍掉缺口 = 读者以为分析完整。

---

## 六、版式硬规则（内核级）

| # | 规则 | 为什么 |
|---|---|---|
| R1 | 首页只放业务结论，不放保留率/门禁/规格 | 读者先要知道「事情怎么样」 |
| R2 | 正文最后一节固定「口径与分数」 | 自检信息该被看见，但不挡在结论前 |
| R3 | 记录层标 `appendix: true`，默认折叠 | 数据一条不少，但不占首屏 |
| R4 | 不生成「结论清单 / 摘要复述」章节 | 正文说过的再总结一遍就是冗余 |
| R5 | 全篇禁用斜体；标题/表头/图注不用衬线体 | 中文伪斜体在 PDF 里糊 |
| R6 | 正文段落**不缩进首行、不用两端对齐**（`text-indent:0` + `text-align:left`），段间留 2.2mm | 2em 缩进让每段左边缘呈锯齿，与左侧 13mm 块标签打架；justify 在中文夹数字/百分号时把字距拉开，同一段每行松紧不一 |

> **R5 的例外（2026-11-21）**：flow 主题（`docs/REPORT-LINES.md` 的唯一版式）用衬线体做**展示标题**，
> 这是有意的设计。页面在 `<head>` 里显式声明
> `<meta name="report-serif-titles" content="allow">` 时，`check_report_style.py`
> 放行 `h1/h2/h3` 的衬线体；**表头 `th` 与图注 `figcaption` 仍然禁衬线**。
> 不声明就不放行——这条不是给 paper 线开后门，paper 线已于同天下线。

> **R6 的出处（2026-11-23）**：全国蔬菜调研报告的读者反馈「正文首行缩进看着丑、每行换行松紧不一」。
> 改的是 `core/report_theme/consulting.css`（flow 主路径）与 `core/report_theme/kit.py`
> （项目代码 flow 线）两处，`tests/test_report_contract_v4.py::test_body_has_no_first_line_indent`
> 把「不许回到 2em / justify」锁成回归。历史记录见 `交付/系统升级执行报告-2026-11-21.md`（当时的选择已废止）。

默认主题 `paper`（白纸、细线、暖橙强调、1120px 内容列）；备选 `sticker` 等 7 套历史主题。

---

## 七、门禁（7 类 → 1 个入口）

```bash
python scripts/check_report_flow.py --dir <输出目录>
python scripts/ci_report_checks.py      # CI：角色入口 + A/B 两条分支 + 门禁 + 图型
```

`scripts/check_report_flow.py` 的十条判据：F1 版式四规则（复用
`check_report_layout.py`）、F2 标题带数字、F3 结论段带数字、F4 每节带数字、
F5 有边界节、F6 末节口径与分数、F7 图有来源、F8 无 JSON 回显、F9 重复句 ≤10%
且数字密度 ≥25/千字且禁用词为 0、**F10 深度**（共用 `core/report/report_quality.py`，
按体量自动分 `research` / `baseline` 两档；同一份报告 `report check` 与
`python -m core.report.report_quality` 必须给出同一结论）。

历史七件套（depth / style / substance / diversity / project / analysis / spec+contract
测试）已删除：它们的前提是「20 个角色各出一份报告」，该前提已不存在。

---

## 八、验收（自检六条）

1. 是否有「结论先行」的第一段，且带数字？
2. 每个数字能否回溯到 `result.json` 的字段路径？
3. 是否命中任一禁用词？
4. 是否声明了边界与缺口？
5. HTML 是否由 `core/report/report_renderer.py` 生成（非手写）？
6. `manifest.json` 的 `producer` 是否为 `r01`、`ok` 是否为 `true`？

任一项不过 → 不发布。

---

## 九、已删除的产线（2026-11-15）

旧引擎（REP-001 五段式、内核 spec、深度稿）、12 个 CLI 子命令、7 类门禁、
20 角色批量脚本 3 套、真实数据专项脚本 10 个、`run_heavy_*` 手写 HTML 线、
`report_specs/` 规格层、角色侧 `report_contract.py`。

代码与文档已打包：
`workspace/_archive/report-lines-2026-11-15.tar.gz`、
`workspace/_archive/report-docs-2026-11-15.tar.gz`、
`workspace/_archive/_report_specs_snapshot/`。
