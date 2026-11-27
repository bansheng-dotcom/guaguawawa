# R10 黄金成品（golden）：两套版式的设计交付说明

两份 HTML 由 `design_contract.py` 用同一份内容、两套风格包渲染，并逐条跑完设计契约 12 条。

```bash
cd r10-wachengmei-design
python design_contract.py goldens                 # 重建两套版式
python design_contract.py check --input golden/design-editorial.html
python design_contract.py packs                   # 两套风格包齐套
python design_contract.py review                  # 视觉评审 V1–V10 齐
python design_contract.py misuse --case misuse/italic-no-measure.json
```

| 文件 | 风格包 | 验收点 |
|---|---|---|
| `design-editorial.html` | `styles/editorial-evidence-report` | P1–P12 全过；证据优先、结论先行；V1–V10 签字表 |
| `design-internet.html` | `styles/internet-reporting` | P1–P12 全过；指标密集版式；V1–V10 签字表 |

## 契约与评审的唯一出处

- 12 条规则：`docs/REPORT-DESIGN-CONTRACT.md`（P1–P12，错误码与本地检查一致）；
- 人读清单：`docs/REPORT-VISUAL-REVIEW.md`（V1–V10，机器门禁 0 违规后才进入人工评审）；
- 两套风格包：`styles/<id>/{page_style.yaml,global_prompt.md,sample.html}`。

## 本地检查口径

`check_html()` 与 `scripts/check_report_presentation.py` 同口径：
`P1_italic / P2_print / P2_break / P3_contrast / P4_type_scale / P5_figure / P5_refline /
P6_theme / P6_theme_active / P7_measure / P8_container / P9_linebreak / P10_table /
P11_antipattern / P12_heading`。

## 误用样本（misuse/）

| 文件 | 故意违规 | 期望错误码 |
|---|---|---|
| `italic-no-measure.json` | 中文伪斜体 + 删除版心宽度 | `P1_italic`、`P7_measure` |
| `skip-heading-no-thead.json` | h2 跳 h4 + 表格无 thead | `P12_heading`、`P10_table` |
