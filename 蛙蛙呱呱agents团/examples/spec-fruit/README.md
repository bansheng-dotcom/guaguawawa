# 示例：facts 内联 spec 的水果三城报告（无 charts.py）

- 14 节 / 13 图，全部 `"chart": {"type": ...}` 写在 `facts.py`；
- 地图用 `symbol`（真实市界底图），产地版图用 `network` 替代；
- 复现：

```bash
cd 蛙蛙呱呱agents团
python guagua.py report flow --project examples/spec-fruit --out examples/spec-fruit/out --pdf
```

预期：`flow_manifest.json` 的 `files.chart_engine = {pro: 13, legacy: 0, table: 1}`，文笔 100。
