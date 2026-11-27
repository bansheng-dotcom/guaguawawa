# R20 黄金样本：SLO 与演练报告 + 备份与复盘报告

> 由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具与确定性 SLO 参数。

| 样本 | 技能链 | 夹具/参数 | 验收点 |
|---|---|---|---|
| `slo-and-drill.html` | slo(99.9/30d/10min) → restore.drill → dr.rpo_rto | `drill.json` / `rpo_rto.json` | 错误预算剩余/燃尽率；恢复文件数与校验和；RPO/RTO 上限、依赖无环、回滚非空 |
| `backup-and-postmortem.html` | backup.backup → restore.restore → postmortem.postmortem → improvement | `backup.json` / `restore.json` / `postmortem.json` / `improvement.json` | 加密备份仓；恢复授权与真实快照；复盘四要素；改进项闭环 |

## 怎么重新生成

```bash
python r20-washouzhi-sre/golden/build_golden.py
```

## 验收

```bash
python r20-washouzhi-sre/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`slo_over_budget.json` 触发 `slo:budget`（错误预算透支）；
  `dr_missing_rollback.json` 触发 `dr.rollback`（无回滚）。

## 说明

- 备份存在 ≠ 恢复成功；成功演练必须带文件数与校验和证据；
- 灾难切换/恢复生产属高风险动作，R20 只校验不执行。
