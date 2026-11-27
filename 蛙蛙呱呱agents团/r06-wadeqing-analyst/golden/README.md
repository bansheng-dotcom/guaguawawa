# R06 黄金样本（T1）：三份分析报告草稿

> 状态：**黄金草稿**。用于回归质检与版式对照；R01 签发后才算对外黄金样本。
> 数据均为仓库内合成数据（预埋真因），不含项目资产。

| 样本 | 数据 | 预埋真因 | 质检 |
|---|---|---|---|
| `retail-report.html` | `cases/analysis-retail/data.csv` | 抖音 × 女装 折扣 10%→35% | 100 分 / research |
| `saas-report.html` | `cases/analysis-saas/data.csv` | basic 套餐 onboarding=pending 上升 | 90.9 分 / baseline |
| `selfmedia-report.html` | `cases/analysis-selfmedia/data.csv` | 抖音推荐流量翻倍 | 100 分 / baseline |

## 怎么重新生成

```bash
python r06-wadeqing-analyst/agent.py chain report \
  --question "9月利润为什么下滑" \
  --input r06-wadeqing-analyst/cases/analysis-retail/data.csv \
  --out-dir ../workspace/_report_retail \
  --before 2026-06-01 --after 2026-09-28 --split 2026-07-31 \
  --dimensions channel,category --qty qty
```

saas / selfmedia 的参数见 `docs/REPORT-LINES.md` 的 R06 报告链小节。

## 验收

```bash
python r06-wadeqing-analyst/run_tests.py
python scripts/check_analysis_chain.py --selftest
python scripts/check_claim_trace.py --report <报告> --evidence <链条目录>
python scripts/check_chart_fail_if_missing.py --spec <链条目录>/chart_spec_pack.json --report <报告>
```

## 说明

- `*-manifest.json` 记录的是生成时的本地运行，其中 `files` 哈希包含 `generated_at`，
  重新生成会变化；黄金对照看的是**质量分、可追率、图表与章节结构**，不是字节级哈希。
- manifest 固定 `author_role=r01`、`publishable=false`，即 R06 只产草稿。
