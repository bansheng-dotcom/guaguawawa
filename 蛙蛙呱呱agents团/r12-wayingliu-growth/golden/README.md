# golden · R12 增长链黄金看板

三份 HTML 都由 `growth_chain` 真实跑完 `fixtures/chain_spec.json` 后生成，
不是手写示例；重跑命令：

```bash
cd r12-wayingliu-growth
python fixtures/build_fixtures.py       # 重建确定性 fixtures（可选）
python golden/build_golden.py           # 跑链并覆盖本目录 3 份 HTML
```

| 文件 | 来源段 | 内容 |
|---|---|---|
| `selfmedia-dashboard-90d.html` | `selfmedia` | 单平台 90 天看板：KPI、周播放趋势、最近 14 天三态日报 |
| `attribution-budget.html` | `attribution` | 首触/末触/线性/位置四模型 + 增量状态 + 预算建议 |
| `cohort-ltv-cac.html` | `retention` + `paid` + `diagnose` | 队列留存矩阵、加权留存曲线、CAC/LTV/回收月 |

验收口径：

- `build_golden.py` 在 manifest `ok=false` 时直接退出，杜绝「链失败仍出黄金」；
- 看板离线、无外部脚本；缺失值显示「缺失」，不补 0；
- 生成结果确定性：同一 fixtures 重跑，工件 sha256 与看板内容一致
  （`tests/test_growth_chain.py::test_e2e_cli_is_deterministic` 复核）。
