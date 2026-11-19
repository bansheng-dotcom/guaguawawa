# Flow 报告规范（HTML 一条流 + PDF 自动分页）

> 页面是输出容器，不是写作容器。  
> 核心实现：`core/report_theme/flow.py`；区块：`core/report_theme/blocks.py`；配置：`configs/report_flow.yaml`。

## 0. 默认与开关（2026-11-19 接线）

- 默认版式 = `flow`，来源是 `configs/report_flow.yaml` 的 `flow.default_layout`（`core/report_layout.py` 读它）。
- 回退：`python guagua.py report "…" --claims x.json --layout paper`。
- 文笔门禁默认开：不达标直接 BLOCK；调试时加 `--no-prose-hard` 只记录不拦。
- 数据型自动报告（`--dir`）也走 flow；页式三层质检不适用，改记 `quality.json → mode=flow`。
- 已知边界：flow 版没有 A4 页容器，`check_report_flow.py` / `report_quality` 这类按页 DOM 写的检查不适用；
  版式回归基线在 `scripts/ci_report_checks.py` 里显式钉 `--layout paper`，默认 flow 由 `[21]` 单独冒烟。

## 0.2 项目化入口（facts + charts + prose_specs）

```bash
python guagua.py report flow --project workspace/<项目> --out workspace/<项目>/out --pdf
```

- `facts.py`：META / KPI / SUMMARY / SECTIONS / ACTIONS / SOURCES / FILES；
- `charts.py`：`section["chart"]` 对应的函数，用 `core.report_theme.chartkit`（hbar/grouped_bar/range_bar/share_bar + SVG 基元）；
- `prose_specs.py`：可选。默认交给 `core.report_prose_gen` 合成 1,000 字正文；
  加 `--author-first` 时只校验 11 字段，保留 `facts.SECTIONS` 里的人工正文；
- 模板：`templates/flow-report/`（复制即用）；内核：`core/flow_report.py` + `core/report_theme/{kit,chartkit}.py`。

`--paper` 出页式；缺省版式为 `flow`（`configs/report_flow.yaml`）。

`--author-first`：人工正文优先。仍然加载并校验 `prose_specs.py` 的 9 字段
（缺字段照样记入 `prose_spec.issues`，`--prose-hard` 时 BLOCK），但不调用
`report_prose_gen`，页面正文直接用 `facts.SECTIONS[i]["body"]`。
适合“R01 已经写成稿、specs 只作底稿”的项目；`flow_manifest.json` 会写
`prose_mode: "author-first"`。

文笔门禁默认开（`--prose-hard`）：不达标直接 BLOCK（退出码非 0，
`flow_manifest.json` 里 `ok=false`）。调试稿可加 `--no-prose-hard` 只记录分数。

r04 门禁默认开（`--gate-hard`）：项目里有
`coverage/{task_frame,coverage_plan,source_ledger}.json` 时，`report flow` 自动跑
r04 五项（页数按 PDF 实际页数），不过就 BLOCK；`--no-gate-hard` 只记录。
这使 flow 与页式**共用同一套 r04 门禁**，不再各判各的。

## 0.3 证据链：发卡 → 收卡 → 回抓（v3 生产方式）

```bash
# 一条命令：发卡 → 写 PROMPT.md → 16 卡并行执行 →（可选）收卡
python guagua.py report research --intent "……" --out workspace/<项目> \
  --worker-cmd "claude -p {prompt}" --workers 8 --collect
```

- 执行器由 `--worker-cmd` 或 `GUAGUA_WORKER_CMD` 提供，占位符
  `{role} / {card_dir} / {prompt} / {claims}`；不传时只出
  `research_plan.json` + 每卡 `PROMPT.md`，不伪造调研结果；
- `--only r05,r06` 可只跑部分角色；`--collect` 跑完后自动收卡；
- 收卡（也可单独跑）：

```bash
python guagua.py report collect --dir workspace/<项目> --out workspace/<项目>/out
```

- **`collect` 只产证据，不再渲染报告**：产物是 `claims_merged.json`、
  `gaps.json`、`source_verify.json`、`coverage/source_ledger.json`；
- 默认来源下限 **50 条**（`--min-sources 0` 关闭）；
- 默认联网逐条打开 URL、回抓 quote，未核过即失败；离线调试可加
  `--no-verify-quotes` / `--no-strict-quotes`；
- `report brief` 会初始化 `coverage/` 三件套（单元/维度留空，`source_ledger.json`
  由 `collect` 回填），flow 端 r04 因此有据可查；
- 缺 quote 的卡整张拒收，不把“有 URL 但没原文”的来源混进报告；
- 正式稿仍由 `report flow --project … --author-first --pdf` 出。

## 0.4 每节 11 字段（固定契约）

`facts.SECTIONS` 必填 2 个：`verdict`、`question`；
`prose_specs.SPECS` 必填 9 个：`fact / evidence / mechanism / alternative /
signal / implication / action / stop / boundary`。

校验器：`core/prose_spec.py`。少一个字段记问题；`--prose-hard` 时直接 BLOCK。
两种成稿路径：默认把 11 个字段写死，再让 `report_prose_gen` 扩写成 1,000+ 字；
`--author-first` 则只校验字段，正文由 R01 直接写成稿，避免模板腔。

CI 的 `[22] flow-project` 会用模板跑两遍（软/硬），验「软过、硬拦」两态都成立。

## 1. 契约

```json
{
  "layout": "flow",
  "theme": "consulting",
  "sections": [
    {"id": "s1", "body": "…", "chart": {"type": "line", "shape": "timeseries"}}
  ],
  "sources": [["S01", "来源标题", "2024-01-01"]]
}
```

`layout: "flow"` 时，`core.report_renderer.render()` 直接走 `flow.render_flow()`，不再经过 A4 页容器。

## 2. HTML

- 一个 `.flow-paper`，封面是 hero，其余 block 连续；
- 不写死 A4 页、不写死页码；
- 章节可跨屏，图/表 `break-inside: avoid`；
- 目录锚点跳转，页码只在 PDF 出现。

## 3. PDF

- 浏览器/导出器自动分 A4 页；
- 页码由导出后处理盖戳；
- 附录自动压成两栏紧凑来源表，目标 1 页；
- 尾页是小页脚，不是整张深色页。

## 4. 摘要必填

`configs/report_flow.yaml`：

- 读法
- 样本 / 单位 / 截止
- 本报告回答 / 不回答
- 必读图
- 证据规模

缺一项，R04 / 人工验收按不合格处理。

## 5. 门禁

- `prose_style`：每节 1,000–1,600 字，事实/解释/所以/边界，数字密度；
- `coverage_plan.pre_gate`：来源/饱和/矩阵/双地图/G10；
- `r04_audit --prose-hard`：文笔纳入 BLOCK。

## 6. 还没自动的

- 17 节正文的自动写作（当前 R01 仍要写）；
- 目录 PDF 页码回填（flow 版暂不显示页码）；
- 摘要“六条判断”的自动展开。
