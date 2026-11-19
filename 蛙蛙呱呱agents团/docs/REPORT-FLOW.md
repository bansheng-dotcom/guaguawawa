# Flow 报告规范（HTML 一条流 + PDF 自动分页）

> 页面是输出容器，不是写作容器。  
> 核心实现：`core/report_theme/flow.py`；区块：`core/report_theme/blocks.py`；配置：`configs/report_flow.yaml`。

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
