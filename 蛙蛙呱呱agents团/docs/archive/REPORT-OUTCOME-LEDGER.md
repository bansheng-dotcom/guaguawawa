> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 结果台账（REPORT-OUTCOME-LEDGER.md）

> 版本：v0.1 · 2026-11-17（P6）
> 实现：`core/outcome_ledger.py`
> 默认路径：`workspace/outcomes/ledger.json`（运行态，不进 git）

---

## 1. 为什么需要

报告发出去之后，系统必须能回答：

- 这条判断后来对了吗？
- 这个决定后来好了吗？
- 哪类方法 / 角色 / 来源等级，长期命中率更高？

没有台账，报告系统只能“越写越像”，不能“越写越准”。

---

## 2. 一条台账长什么样

```json
{
  "id": "O-20261117-a1b2c3",
  "report_id": "RPT-20261117-analysis",
  "claim_id": "structure",
  "kind": "claim",
  "prediction": "6 个品类在涨、6 个在跌，芒果 4.39%、梨 -3.33%",
  "decision": "哪些品类继续做",
  "deadline": "2027-02-15",
  "status": "open",
  "result": "",
  "recorded_at": "2026-11-17T20:30:00",
  "reviewed_at": ""
}
```

状态机：

```
open → hit / miss / partial / void
```

- `hit`：方向与幅度都在约定范围内；
- `miss`：方向反了，或幅度超出容忍；
- `partial`：方向对、幅度错；
- `void`：数据/口径变化导致不可比，不算命中也不抹掉。

**回填必须写 `result`**：为什么算命中/失败。口头“差不多”不算。

---

## 3. 命令

```bash
# 登记
python -m core.outcome_ledger add \
  --report-id RPT-20261117-analysis \
  --claim-id structure \
  --prediction "6 个品类在涨、6 个在跌" \
  --decision "哪些品类继续做" \
  --deadline 2027-02-15

# 看 open / 逾期 / 即将到期
python -m core.outcome_ledger summary
python -m core.outcome_ledger list --status open

# 到期回填
python -m core.outcome_ledger review O-20261117-a1b2c3 \
  --status hit --result "复盘：芒果/梨方向一致，幅度在 ±5% 内"

# 从一份报告的 analysis_trace 批量登记（默认 +90 天）
python -m core.outcome_ledger seed \
  --report-id RPT-20261117-analysis \
  --intent "内蒙古三城水果市场调研" \
  --trace workspace/report_upgrade/p6_build_outcomes/analysis_trace.json
```

---

## 4. 和 `report build` 的集成

`report build` 新增 `--record-outcomes`：

```bash
python guagua.py report build --intent "内蒙古三城水果市场调研" \
  --dir 内蒙古水果三城调研_2026-11-16_pipeline \
  --out workspace/reports/fruit --lens market \
  --record-outcomes --outcome-deadline 2027-02-15
```

行为：

1. 报告正常生成；
2. 从 `analysis_trace.json` 的 findings 各登记一条 open；
3. `manifest.json` 增加 `outcomes: {seeded, path}`；
4. 同一 `report_id + claim_id` 的 open 不会重复登记。

**登记的是“预测/判断”，不是“动作执行”**；动作执行结果由 R02/R04 单独回填。

---

## 5. 汇总口径

`summary` 输出：

| 字段 | 含义 |
|---|---|
| `open` | 还没到期/没回填 |
| `overdue` | 过了 deadline 仍 open |
| `due_soon` | 30 天内到期 |
| `hit / miss / partial / void` | 回填结果 |
| `hit_rate` | `hit / (hit+miss+partial)`；void 不计入分母 |

**不要用 hit_rate 给角色排名**：样本少、口径不同，排名会变成另一种“编数字”。它只用来校准置信度。

---

## 6. 当前状态（P6 试点）

`report build --record-outcomes` 在水果 pipeline 上登记了 **10 条 open**：

```
structure / coverage / momentum / trajectory / contribution
economics / transmission / arbitrage / risk / sample
```

`summary` 当前：`total=10, open=10, hit_rate=null`。
等 2027-02 到期后再看命中率；现在没有结论。

---

## 7. 维护规则

1. **一条预测一个 deadline**：没有 deadline 的判断不许登记；
2. **回填必须写结果**：命中/失败都要写“为什么”；
3. **不删失败记录**：miss 比 hit 更有信息量；
4. **口径变了标 void**：不要用“数据不可比”当 miss，也不要用 void 洗掉判断；
5. **样本 <10 不出命中率结论**：只记录，不排名。
