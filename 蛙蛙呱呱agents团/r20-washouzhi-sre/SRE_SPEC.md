# SRE_SPEC.md —— R20 蛙值守 · 可靠性领域唯一信任源 (SSOT)

> 版本：1.0.0 ｜ 角色：R20 蛙值守（可靠性与恢复官）｜ SOP v13.0 L04 领域账本层
>
> 本账本是 R20 所有技能的**唯一口径来源**：SLO、错误预算、MTTR、RTO/RPO、
> 备份保留、发布门禁全部在此定义。`engines/spec_ledger.py` 动态加载并计算
> SHA256 账本指纹；任何偏离本账本的输出判为门禁破损。

```json
{
  "spec_version": "1.0.0",
  "role": "r20",
  "owner": "蛙值守",
  "north_star": {
    "availability_slo": 0.999,
    "error_budget_ratio": 0.001,
    "mttr_max_minutes": 30,
    "mtta_max_minutes": 5,
    "rto_max_hours": 4,
    "rpo_max_hours": 1,
    "backup_restore_drill_days": 30,
    "snapshot_min_count": 1,
    "escalation_max_level": 3
  },
  "kpis": [
    {"id": "KPI-AVAIL", "name": "可用率", "formula": "success_probes / total_probes", "target": ">= 0.999", "unit": "ratio"},
    {"id": "KPI-BURN", "name": "错误预算燃烧率", "formula": "actual_error_rate / (1 - slo)", "target": "<= 1.0", "unit": "ratio"},
    {"id": "KPI-MTTR", "name": "平均恢复时长", "formula": "sum(resolved_at - started_at) / incidents", "target": "<= 30", "unit": "min"},
    {"id": "KPI-RTO", "name": "恢复时间目标", "formula": "declared rto_hours", "target": "<= 4", "unit": "hour"},
    {"id": "KPI-RPO", "name": "恢复点目标", "formula": "declared rpo_hours", "target": "<= 1", "unit": "hour"},
    {"id": "KPI-DRILL", "name": "恢复演练新鲜度", "formula": "today - last_drill_at", "target": "<= 30", "unit": "day"}
  ],
  "release_gates": [
    {"id": "G1", "name": "结构完整性", "dim": "structure", "threshold": "工件为对象且 checks 非空"},
    {"id": "G2", "name": "SLO 口径一致", "dim": "slo", "threshold": "reliability metric ∈ [0,1] 且 >= 0.999"},
    {"id": "G3", "name": "证据链完整", "dim": "evidence", "threshold": "至少 1 条通过判据且带 dim/msg"},
    {"id": "G4", "name": "授权与交接", "dim": "authorization", "threshold": "破坏性动作必须带 authorization/handoff"},
    {"id": "G5", "name": "回滚可执行", "dim": "rollback", "threshold": "恢复类动作必须有 rollback_plan 且步骤 >= 1"},
    {"id": "G6", "name": "可观测性", "dim": "observability", "threshold": "须有 monitor/alert/telemetry 证据"},
    {"id": "G7", "name": "值班与升级", "dim": "oncall", "threshold": "须有 owner 与升级链（<= 3 级）"},
    {"id": "G8", "name": "卫生与凭据", "dim": "hygiene", "threshold": "无凭据明文、无 TODO/待定 占位"}
  ]
}
```

## 口径说明

1. **可用率**：`success_probes / total_probes`，四舍六入保留 6 位；
   低于 `availability_slo` 即判 `meets_slo=false`。
2. **错误预算**：`1 - availability_slo = 0.001`；燃烧率 `> 1` 视为预算透支，
   必须触发降级与人工决策，禁止静默续跑。
3. **MTTR**：只统计同时具备 `started_at` 与 `resolved_at` 的事件，
   未恢复事件不参与均值（避免把「还在烧」算成「很快恢复」）。
4. **RTO/RPO**：以声明值为准，超过上限即 `feasible=false`，不得对外承诺。
5. **备份**：快照数 >= 1；恢复演练距今 <= 30 天，否则视为「无有效恢复能力」。
6. **红线**：未授权生产恢复、凭据明文、擅自删快照、越权财务/统计/法律结论、
   假演练均属 BLOCKER，必须 `[REDLINE BLOCKED]` 并移交责任人。
