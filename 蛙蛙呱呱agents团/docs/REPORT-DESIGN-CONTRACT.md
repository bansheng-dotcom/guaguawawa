# 报告设计契约（REPORT-DESIGN-CONTRACT）

> 版本：v1.0 ｜ 日期：2026-11-27 ｜ 适用：所有静态 HTML 报告（A4 打印优先）
> 依据：dar `human_authored_html_design_system.md` 的 12 条原则，改写为本仓可执行判据。
> 可执行门禁：`python scripts/check_report_presentation.py <report.html>`（P1–P12）。

## 为什么要有这份契约

渲染层已经能出报告，但设计原则散落在 `report_renderer.py` 与主题 CSS 里：
- 无法评审：改版后只能凭感觉说“好看/难看”；
- 无法继承：新报告不知道哪些是底线、哪些是风格；
- 无法回归：门禁只有 6 条底线，防得住事故，防不住“像人做的版面”。

本契约把设计意图写成 **12 条可测规则**。规则分两类：
- **底线（P1–P6）**：违反即事故，任何报告都不许破；
- **标准（P7–P12）**：违反即“不像人排版”，由 `check_report_presentation.py` 拦截。

## 12 条规则

| # | 规则 | 判据（可执行） | 反模式 | 门禁 |
|---|---|---|---|---|
| P1 | 无斜体 | 全篇不出现 `font-style: italic` | 中文伪斜体在 PDF 里糊成一团 | `P1_italic` |
| P2 | 打印就绪 | 有 `@page` + `A4`，figure/section 有 `break-inside` 保护 | 屏幕宽排版直接打印，图表跨页截断 | `P2_print` / `P2_break` |
| P3 | 对比度达标 | 正文/次要文字对纸底 ≥ 4.5:1 | 浅灰正文、彩色底上的白字 | `P3_contrast` |
| P4 | 字阶分层 | 同时存在 ≥4 档字号 | 全文一个字号，标题靠加粗硬撑 | `P4_type_scale` |
| P5 | 图四件套 | 每张图有来源、单位、口径副标题；有数据轴时有零线/均值线说明 | 图只有标题，没有来源与单位 | `P5_figure` / `P5_refline` |
| P6 | 主题单一 | 默认作用域只允许一套 `--ink`；body 显式声明 `data-theme` | 两套主题令牌拼在一份 HTML 里串色 | `P6_theme` / `P6_theme_active` |
| P7 | 版心与行宽 | 主容器 `max-width` 在 680–1040px；行高 1.0–2.0（禁止 0.9 挤压与 3.0 松垮） | 全文满屏 1920px 宽，一行 80+ 字 | `P7_measure` |
| P8 | 容器克制 | `border-radius` 去重后 ≤6 档（0/50%/999px 胶囊不计） | 每节不同圆角、不同阴影、不同底色 | `P8_container` |
| P9 | 断行卫生 | `<p>` 内不出现 `<br>`；标题不使用 `<br>` 手动折行 | 用 `<br>` 排版，屏幕与打印都错位 | `P9_linebreak` |
| P10 | 表格规范 | 每个 `<table>` 有 `<thead>` 且至少一个 `<th>` | 表格无表头，数字无法对齐阅读 | `P10_table` |
| P11 | 反模式清单 | 正文不居中、字号不小于 11px、装饰性渐变 ≤1 处且只在封面 | 渐变 Hero、居中大段正文、9px 注释 | `P11_antipattern` |
| P12 | 标题层级 | 恰好一个 `<h1>`；标题层级不跳级（h1→h3 违规） | 多个 h1、h2 下直接 h4 | `P12_heading` |

## 风格包（styles/）

设计契约是底线，风格包是“这一份报告像谁写的”。每个风格包必须包含：

```text
styles/<style-id>/
├── page_style.yaml    # 版心、字阶、色彩语义、图表强调规则
├── global_prompt.md   # 给写作/编排层的风格约束
└── sample.html        # 黄金样本（可打开的完整报告）
```

现有风格包：

| 风格 | 适用 | 样本 |
|---|---|---|
| `editorial-evidence-report` | 研究/诊断类长报告，证据优先、编辑式版面 | `styles/editorial-evidence-report/sample.html` |
| `internet-reporting` | 经营/增长类汇报，结论先行、指标密集 | `styles/internet-reporting/sample.html` |

## 视觉评审流程

1. 生成报告 → `python scripts/check_report_presentation.py --dir <out>` 必须 0 违规；
2. 打开 `docs/REPORT-VISUAL-REVIEW.md` 逐条签字（人读项：阅读路径、强调是否克制、图文是否互相解释）；
3. 黄金样本变更必须走版本化：改 `styles/<style>/sample.html` 时同步更新本文件与评审记录。

## 不做的事

- 不把 ECharts 交互搬进报告：静态 SVG 适配 A4 打印；
- 不为每份报告新造一套主题：风格包是有限集合，新增必须说明适用边界；
- 不用“补 CSS”代替“改结构”：层级问题先改标题与段落，不靠字号硬压。
