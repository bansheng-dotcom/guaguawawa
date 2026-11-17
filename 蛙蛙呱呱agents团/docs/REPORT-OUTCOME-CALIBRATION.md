# 月度结果校准（REPORT-OUTCOME-CALIBRATION.md）

> 版本：v0.1 · 2026-11-17（P9）
> 实现：`core/outcome_ledger.calibrate` + `scripts/outcome_calibration.py`

## 1. 每月做什么

```bash
python scripts/outcome_calibration.py
```

输出（默认 `workspace/outcomes/`）：

- `calibration_YYYY-MM.json`
- `calibration_YYYY-MM.md`

## 2. 字段

| 字段 | 含义 |
|---|---|
| `summary.open` | 还没到期/没回填 |
| `summary.overdue` | 过了 deadline 仍 open |
| `summary.hit_rate` | `hit/(hit+miss+partial)`；void 不进分母 |
| `due_unreviewed` | 本月应回填但没回填的 id |
| `verdict` | `NO_DUE_DATA` / `CALIBRATED` |

## 3. 铁律

1. **没有到期数据 → `NO_DUE_DATA`，不编命中率；**
2. 回填必须写 `result`：为什么算命中/失败；
3. 样本 <10 不出“角色/方法排名”，只做置信度校准；
4. `void` 不算命中也不算失败，但要写口径变化原因；
5. 命中率只反推 `confidence` 默认值，不做绩效。

## 4. 当前空跑

台账 10 条 open，最早 deadline 2027-02；本月校准结果应为：

```json
{"verdict": "NO_DUE_DATA", "summary": {"hit_rate": null, "open": 10}}
```

这不是失败，是“时间没到”。等真实回填后，同一脚本自动变成 `CALIBRATED`。
