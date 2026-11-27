# R10 蛙成美 · 厚度自述（T12 Tier C：补机制）

> 按升级方案 §16「厚度包」与 §17.1 T12 逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 13 篇 / 61.5KB（生图、Logo、UI/UX、品牌令牌、动效、图像工程、媒体、转写、设计系统、AI 生成等） |
| 设计库 | `references/design-library/` 33 套（含 LICENSE_STATUS.json 许可状态） |
| 风格包 | `styles/editorial-evidence-report`、`styles/internet-reporting`（各 page_style/global_prompt/sample） |
| 误用说明 | 每篇有「误用反例」；契约侧误用由 `design_contract.py` 12 条门禁兜住 |
| 能力卡 | `references/capabilities/`：brand-guardian、design-system、visual-hierarchy、whiteboard 等 |

## 2. 生产层

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1–15 | `skills/s01..s15` | 生图/Logo/UI/品牌/动效/图像/媒体/转写/渲染/设计系统… | 设计工件与门禁结论 |
| 16 | `harness.py` + `verify_loop.py` | 技能产出 | 确定性门禁与闭环矩阵 |
| 17 | **`design_contract.py`（T12 新增）** | HTML + 风格包 + 评审文档 | 12 条违规清单、风格包状态、V1–V10 清单、2 份黄金 |

`design_contract.py` 把「设计原则」变成可执行判据：12 条规则逐条返回错误码，误用样本可复现。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 两套版式黄金 | `golden/design-editorial.html`、`golden/design-internet.html` | 同内容、两风格包，各自 P1–P12 全过 |
| 风格包实物 | `styles/<id>/` | page_style.yaml / global_prompt.md / sample.html 全在 |
| 评审文档 | `docs/REPORT-VISUAL-REVIEW.md` | V1–V10 齐（只读引用，不改 docs） |

## 4. 门禁层

| 门禁码 | 判据 | 失败后果 |
|---|---|---|
| `P1_italic` | 不出现 `font-style:italic` | 拒绝交付 |
| `P2_print` / `P2_break` | `@page` + `A4` + `break-inside` | 拒绝交付 |
| `P3_contrast` | 正文/次要文字 ≥4.5:1 | 拒绝交付 |
| `P4_type_scale` | ≥4 档字号 | 拒绝交付 |
| `P5_figure` / `P5_refline` | 图有来源/单位/口径；有零线或均值说明 | 拒绝交付 |
| `P6_theme` / `P6_theme_active` | 单一 `--ink` + body `data-theme` | 拒绝交付 |
| `P7_measure` | max-width 680–1040px；行高 1.0–2.0 | 拒绝交付 |
| `P8_container` | 圆角 ≤6 档 | 拒绝交付 |
| `P9_linebreak` | p/h 内无 `<br>` | 拒绝交付 |
| `P10_table` | 每表有 thead + th | 拒绝交付 |
| `P11_antipattern` | 无居中正文、无 <11px、渐变 ≤1 且仅封面 | 拒绝交付 |
| `P12_heading` | 恰好 1 个 h1、不跳级 | 拒绝交付 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 机制单测（pytest） | `tests/test_mechanism.py` | 6 条（12 条规则/黄金/风格包/评审/逐条可失败/误用） |
| 角色端到端 | `run_tests.py` §T12 | 6 条 |
| 黄金成品 | `golden/*.html` | 2 份（两套版式） |
| 误用反例 | `misuse/*.json` | 2 份（斜体+无版心 / 跳级+无表头） |
| 全量 | `python run_tests.py` | 183 / 183 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r10-wachengmei-design/run_tests.py`
- 结果：通过 183 / 183，全绿
- 机制：`python design_contract.py goldens` → 两套版式均 0 违规；`packs`/`review` 均 `ok=true`
- 呈现（仓库脚本复核）：`python scripts/check_report_presentation.py r10-wachengmei-design/golden/*.html` → 2/2 PASS

## 7. 已知边界

- 12 条是**可测底线**，不判断“好不好看”；审美由 V1–V10 人工签字；
- P3 只校验令牌级对比度，不解析每个元素的层叠样式；
- P5 只查图卡四件套与参考线文案，不校验 SVG 数据是否与正文一致；
- 风格包是有限集合，本角色不新造主题；新增必须更新契约文档（需走 docs 归属人）。
