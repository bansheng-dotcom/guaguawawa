# consulting 主题与 A/B 页式（core 移植说明）

> 2026-11-19 移植。默认仍是 `paper` 文档流；`consulting` 是**可选出口**，不替换旧渲染器。
> 入口：`core.report_theme.pages.render_contract`；由 `core/report_renderer.render()` 在
> `contract["theme"]=="consulting"` 或 `contract["layout"] in ("pages","hybrid")` 时调用。

## 1. 怎么开

```bash
# 渲染器直接跑
python core/report_renderer.py --contract c.json --output out.html --theme consulting
```

或在 contract 里写：

```json
{
  "theme": "consulting",
  "layout": "hybrid"
}
```

`layout` 可省略；`hybrid` 与 `pages` 等价：按 section 有没有 `rail` 自动选 A/B。

## 2. 两种节页

### A · 三块版（默认）

```json
{
  "index": 1,
  "kicker": "价差",
  "title": "批发价差 1.98 倍，零售只剩 8.0%",
  "question": "跨城搬水果，能不能赚价差？",
  "verdict": "跨城套利不成立。",
  "reading": [
    {"text": "事实段……", "strong": ""},
    {"text": "解释段……", "strong": ""},
    {"text": "边界……", "strong": "本节边界　"}
  ],
  "chart": {"type": "hbar", "title": "同品篮子", "source": "……", "unit_meta": "元/公斤",
            "bars": [{"label": "呼市", "value": 10.6}]}
}
```

- `reading` 里带 `strong: "本节边界　"` 的那条会变成页面底部的「边界」，不混进正文；
- 其余 `reading` 按句数均分成「事实 / 解释 / 所以」三块；
- `chart` 或 `table` 二选一；表用 `caption/columns/rows`。

### B · 研报版（主文 + 右侧关键数字栏）

在 section 里加 `rail`，页面自动走 B：

```json
{
  "rail": {
    "items": [
      ["10.60", "呼市 6 品", "元/公斤"],
      ["5.35", "赤峰 6 品", "元/公斤"],
      ["1.98×", "批发倍数", "倍"],
      ["8.0%", "零售差", ""]
    ],
    "line": "价差在批发，不在零售；先对齐口径，再谈调拨。"
  }
}
```

- 右栏固定 43mm：3–4 个数字 + 一句结论；
- 正文绕排到栏下，不是死板两栏；
- 正文超过 520 字自动退回 A，避免压到页脚（`pages._section` 有硬判断）。

## 3. 旧契约自动补编辑层

旧 draft 只有 `reading`，没有 `verdict/kicker/rail/actions/sources`。
`core/report_editorial.enrich(contract, pack)` 在 `report_flow.build_sections_contract`
末尾运行，只从已有内容抽字段，不造数：

| 补什么 | 从哪来 |
|---|---|
| `kicker` | 标题冒号前的短词（准入/标准/产能/格局/大盘/价格带/履约…） |
| `verdict` | 本节第一条判断（reading 首句） |
| `rail` | 图表里最大的 3–4 个数字（bars/items/steps/series） |
| `blocks` | reading 的 `观察/机理/判断/落点` 分组，避免混成一段 |
| `actions` | reading 的「落点 / 所以」+ 本节 falsifier 作停止线 |
| `sources` | 证据包文件清单 |
| 封面指标 | 标题里的「数字+单位」抽 4 个，抽不到就留空 |

三道契约门禁（`report_editorial.check_contract`，接在 `quality_gate --contract`）：

1. 标题必须带数字（口径/记录层除外）；
2. 图必须有 `source` 与 `unit_meta`；
3. 走 B 页时 `rail` 至少 3 个数字。
   软提示：本节无图/表、正文 >650 字。

consulting 主题在 `quality_gate` 里走 `pages` 层（封面/节页/页码/图表 aria），
不再用旧 DOM 判据误杀。

## 4. 13 型图表

`core/charts/consulting.py` 注册 `RENDERERS`，由 `core.report_theme.pages` 调用。
输入沿用 contract 的 chart 字段，缺字段返回空图，不抛异常。

| type | 数据 | 用途 |
|---|---|---|
| `hbar` / `vbar` | `bars[]` | 排名/比较 |
| `grouped_bar` | `groups[]` + `series[]` | 跨期、跨组对比 |
| `dumbbell` / `slope` | `rows[]`（label,a,b） | 两期/两组差距 |
| `range` / `error_bar` | `rows[]`（label,low,high） | 区间、不确定性 |
| `share` / `stacked_bar` | `segments[]` | 构成、占比 |
| `waterfall` / `bridge` | `steps[]`（kind=start/delta/end） | 变化归因 |
| `pareto` | `items[]` | 贡献集中度 |
| `bubble` / `scatter` | `points[]`（x,y,size,label） | 关系/分布 |
| `coverage` / `heatmap` | `rows[]`（values 0/1） + `columns[]` | 数据覆盖矩阵 |
| `yoy` | `items[]`（label,value） | 同比/涨跌 |
| `fan` / `forecast` | `series[]` + `xlabels[]` | 情景/趋势 |
| `path_matrix` | `points[]`（x,y,label） | 路径/矩阵 |
| `gantt` | `tasks[]`（start,end） | 执行节奏 |
| `line` / `area` | `series[]` + `xlabels[]` | 连续序列 |

> 地图不在 13 型里：`consulting` 出口暂不接地理边界，地图页请继续用 charts_pro 的
> `choropleth/symbol_map/geo_flow`，或把地图作为 `image` block 传入。这样避免在 core
> 里再存一份 GeoJSON，也不让 48 型注册表出现第二套词汇。

## 5. 新增/修改的 core 文件

| 文件 | 作用 |
|---|---|
| `core/report_theme/consulting.css` | 咨询白底令牌 + 封面/摘要/节页/A·B/动作/附录/封底 |
| `core/report_theme/pages.py` | contract → 固定 A4 页（封面/摘要/目录/节页/动作/附录/封底） |
| `core/report_editorial.py` | 旧契约补 verdict/kicker/rail/actions/sources + 契约门禁 |
| `core/charts/consulting.py` | 14 型确定性 SVG 图表（13 型 + pareto） |
| `core/report_renderer.py` | `THEMES` 增加 `consulting`；`render()` 分流到页式出口 |
| `core/quality_gate.py` | `contract` 层 + consulting `pages` 层 |
| `tests/test_consulting_port.py` | 图表 + A/B 页 + 编辑层 + 门禁回归 |

## 6. 边界

1. 不替换 `paper`；旧报告、旧门禁、旧预览行为不变。
2. 页式出口不做三表/图契约校验；契约校验仍由 `report_renderer.validate_contract` 负责。
3. B 页的 `rail` 可以由内容侧给，也可以由 `report_editorial` 从图表抽；抽数是启发式，需内容侧复核。
4. 页数 = 3 + 节数 + 动作页（有 actions）+ 附录页（有 sources）+ 封底；没有固定 21 页。
5. 目前 consulting 图表不计入 `chart_stats`；需要统计时在 `pages._chart_html` 里加计数。
6. 编辑层只做装配，不重写正文；长句、机理、行动标题仍要靠方法/模型产出。
