# flow 报告模板（facts + charts + prose_specs）

一套三件，`python guagua.py report flow --project <目录> --out <输出目录> --pdf` 直接出报告。

| 文件 | 必填 | 写什么 |
|---|---|---|
| `facts.py` | 是 | 内容层：META / KPI / SUMMARY / SECTIONS / ACTIONS / SOURCES / FILES |
| `charts.py` | 是（有图时） | 每个 `section["chart"]` 对应的函数，返回 SVG 字符串 |
| `prose_specs.py` | 否 | 每节十段证据，交给 `core.prose.prose_render` 生成 1,000 字论证体 |

## 一条节的最低要求

- `title` 带数字，且是结论（不是栏目名）；
- `body` ≥850 字（`prose_contract` 硬下限），包含 事实 / 解释 / 所以 / 边界 四块；
- `boundary` 写清不能外推到哪；
- 有 `chart` 就配 `fig_title` / `fig_unit` / `fig_src`，且图表函数返回的 SVG 里每个点都有 `data-tip`。

## 用一个新项目

```bash
cp -r templates/flow-report workspace/<项目名>
# 改 facts.py / charts.py / prose_specs.py
python guagua.py report flow --project workspace/<项目名> --out workspace/<项目名>/out --pdf
```

`--paper` 可回一节一页 A4；缺省版式见 `configs/report_flow.yaml`。
