---
name: html-report-presentation
description: 单文件 HTML 报告技能包。把「写个报告」变成可校验的阅读结构：标题定调、meta 交代读者与目的、章节 ≥3 且每章有结论摘要、核心论点 ≥3 条、来源 ≥3 条可核，产出单文件 HTML 可离线打开与打印。当需要出深度报告、扫描结论、复盘文档，或判断一份报告能不能直接发给决策者时使用。不负责幻灯片（见 ppt-generator）、不做 Excel 表格（见 office-plugin）、不替代研究本身。
license: MIT
compatibility: 通用。门禁在角色根目录 agent.py（htmlreport plan / htmlreport html），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工六项核对，此时不得标记「可发」。
metadata:
  owner: r08
  version: "2.0.0"
  kind: skill
  triggers: "HTML报告,深度报告,扫描结论,复盘文档,单文件报告,打印"
  verify: python agent.py htmlreport plan --input <报告.json>
  entry: "python agent.py htmlreport plan"
  consumers: "r05,r06,r01"
  supersedes: "README.md"
---

# 单文件 HTML 报告（HTML Report）

> 一句话定位：**这个技能存在的意义，是防止「写了很多、但决策者读不出结论」**。
> 报告最贵的失败不是篇幅，而是**结构不承载结论**：
> 没有交代读者与目的、章节只是资料归类、没有明确论点、来源数不出来。
> 这些都能在渲染成页面之前判掉。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「出个报告」「把这次扫描写成文档」
- 「这份报告能发给老板吗」「结论在哪」
- 「要一份能打印的」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 讲给人听 | 本角色的 `ppt-generator` | 报告是读的，deck 是讲的 |
| Excel / Word 交付物 | 本角色的 `office-plugin` | 那是 Office 格式 |
| 研究本身（找数据、做访谈） | `r05` 的 `industry-panorama-research` | 本包只管组织与呈现 |
| 数据校验与口径 | `r06` 的 `data-validation` | 那是质量门禁 |

**最小可开工输入**：**读者是谁 + 一句核心结论**。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| `title` | 必需 | 无标题无法定调 |
| `meta.audience` / `meta.purpose` | 必需 | 缺则门禁直接拦 |
| `chapters[]`（≥3，各含 summary） | 必需 | 少于 3 章说明还没想清结构 |
| `thesis[]`（≥3 条论点） | 必需 | 没有论点就是资料合集 |
| `sources[]`（≥3 条，各含 label） | 必需 | 来源数不出来则无法核查 |
| 数据与图表 | 建议 | 缺则标注"待补数据" |

**追问纪律**：最多一轮，只问**给谁看、要他做什么决定**。

---

## §3 执行流水线（Workflow）

### Step 1 · 结构校验（六条硬规则）
```bash
python agent.py htmlreport plan --input <报告.json>
```
实测六项，缺任一项即 FAIL：

| # | 规则 | 判据 |
|---|---|---|
| 1 | 标题非空 | `report.title` |
| 2 | `meta` 含 `audience` 与 `purpose` | `report.meta` |
| 3 | 章节 **≥3** | `report.chapters` |
| 4 | 每章有 `title` 与 `summary` | `report.chapter` |
| 5 | 核心论点 **≥3** | `report.thesis` |
| 6 | 来源 **≥3**，各含 `label` | `report.sources` / `report.source.label` |

**最容易漏的是 5 和 6**：章节写得挺多，但通篇没有一个明确论点，
来源只有"公开资料"一条——这种报告读完了什么也留不下。

- **产出**：报告 JSON（结构合法）
- **过关条件**：`agent.py htmlreport plan` 退出码 0

### Step 2 · `meta` 是给读者的导航
`audience` 决定详略（给老板要结论，给同行要过程）；
`purpose` 决定取舍（要决策就给选项与代价，要了解就给背景与格局）。

**判据**：把 `audience` 换成另一类人，这份报告还合适吗？合适 → 说明没为具体读者写。

### Step 3 · 章节顺序（结论先行）
推荐结构：**结论 → 依据 → 分歧 → 建议**
不要"背景 → 背景 → 背景 → 结论"，决策者读到第三页就走了。

### Step 4 · 论点必须可被反驳
每条 `thesis` 都要满足：**能想象出什么证据会推翻它**。
不能想象 → 它是口号不是论点。

### Step 5 · 渲染单文件 HTML
```bash
python agent.py htmlreport html --input <报告.json>
```
要求：样式内联、无外链、离线可开、**打印友好**（页面分页不切断表格与图）。

- **产出**：`report.html`
- **过关条件**：双击能开、打印预览正常、目录可跳转

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 报告 JSON（结构合法） | `.json` | `tests/report-pass.json` |
| 2 | 单文件 HTML | `.html` | `agent.py htmlreport html` 产出 |
| 3 | 论点与反驳条件清单 | `.md` | 本文 §3 Step 4 |

- 命名：`report_<主题短码>_<YYYYMMDD>.html`
- **论点与来源必须随报告交付**；只有正文，决策者无法核。

---

## §5 质量门（一票否决，不过不给交付）

1. **标题非空**；
2. **`meta` 含 `audience` 与 `purpose`**；
3. **章节 ≥3**，每章有 `title` 与 `summary`；
4. **核心论点 ≥3**，且每条可被反驳；
5. **来源 ≥3**，每条有 `label`（可核）；
6. **单文件 HTML**：样式内联、无外链、打印不切断表格。

> 验收命令：`python agent.py htmlreport plan --input <报告.json>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许编造来源凑够 3 条**。

---

## §6 交付前自检清单

- [ ] 标题能一句话说明这份报告讲什么
- [ ] `meta` 写了读者是谁、要他做什么决定
- [ ] 章节 ≥3，每章有 summary（不是只有标题）
- [ ] 核心论点 ≥3，每条我都能说出"什么证据会推翻它"
- [ ] 来源 ≥3，每条都有可核的 label
- [ ] 单文件 HTML 双击能开、无外链
- [ ] 打印预览没切断表格与图
- [ ] 结论在前面，背景在后面
- [ ] 没有任何"公开资料显示"这类无法核的表述

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 章节只有标题没有 summary | 每章给一句结论摘要 |
| EX-02 | `meta` 只写作者日期 | 必须写 audience 与 purpose |
| EX-03 | 章节 <3 就想交付 | 少于 3 章说明结构没想清 |
| EX-04 | 通篇没有明确论点 | ≥3 条 thesis，且可被反驳 |
| EX-05 | 来源只有"公开资料" | ≥3 条具名来源，可核 |
| EX-06 | 背景写三页才出结论 | 结论先行：结论→依据→分歧→建议 |
| EX-07 | 论点无法被证伪 | 每条都想清"什么会推翻它" |
| EX-08 | 产出多文件 + CDN | 单文件 HTML，样式内联 |
| EX-09 | 没看打印预览 | 检查分页不切断表格与图 |
| EX-10 | 为凑数编造来源 | 宁可少写，不可编造 |
| EX-11 | 一份报告给所有人看 | 按 audience 决定详略 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `agent.py` 门禁跑不了 | 按 §6 人工核对，标注「未跑门禁」；**不得标记"可发"** |
| 数据不足 | 标注"数据缺口"与影响哪条结论，不用假数据填 |
| 只有 2 个论点 | 说明还不足以成报告，先补研究 |
| 来源无法具名（涉密/口述） | 写"口述来源·不可公开核"，并说明可信度 |
| 需要互动图表 | 单文件 HTML 内联轻量图表，或转外部工具 |
| 读者要求 PPT 版 | 转 `ppt-generator`，不把报告硬压成页 |

**明确不做**
- 不做幻灯片（归 `ppt-generator`）；
- 不做 Excel/Word（归 `office-plugin`）；
- 不做研究本身（归 `r05`）；
- 不做数据质量校验（归 `r06`）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 正例（6 项结构全过） | `tests/report-pass.json` |
| 反例（无 meta、章节不足、来源不足） | `tests/report-fail.json` |
| 工程细节与子命令 | `../../../references/engineering-notes.md` |
| 研究结论与来源分级 | `r05` 的 `industry-panorama-research` / `evidence-ledger` |
| 数据口径校验 | `r06` 的 `data-validation` |
| 门禁是否还有效 | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `htmlreport plan` 对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 从能力卡升级为十节技能包。
  **新增夹具**（此前无任何报告夹具）：`tests/report-pass.json`（六项全过，实测 exit 0）/
  `tests/report-fail.json`（缺 meta/章节/来源，实测 exit 1）。
  含 §1–§10、`scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `agent.py htmlreport`（plan / html），未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，无 frontmatter/触发语/夹具）。
