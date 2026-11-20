# 示例：facts 内联 spec 的蔬菜报告（无 charts.py）

- 19 节 / 16 图，全部 `"chart": {"type": ...}` 写在 `facts.py`；
- 没有 `charts.py`，flow 直接走 `core/report_theme/charts_pro`；
- 复现：

```bash
cd 蛙蛙呱呱agents团
python guagua.py report flow --project examples/spec-vegetable --out examples/spec-vegetable/out --author-first --pdf
```

预期：`flow_manifest.json` 的 `files.chart_engine = {pro: 16, legacy: 0, table: 3}`，文笔 100。
