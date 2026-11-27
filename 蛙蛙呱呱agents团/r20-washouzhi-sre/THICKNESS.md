# R20 蛙值守 · 厚度自述（T11 / L2）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写可被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | `references/` 10 篇 / 约 44.1KB（`check_role_thickness --report` 可复核） |
| 来源 | Google SRE（SLO/错误预算/复盘）、restic（备份/快照/恢复）公开口径 |
| 适用边界 | 每篇单列「适用边界」 |
| 误用说明 | 每篇单列误用反例，并对应本仓门禁 |

## 2. 生产层

`skills/` 8 个能力域：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `monitor` | 监控配置 | 类型/目标/间隔 |
| 2 | `alert` | 告警规则 | 条件/阈值/渠道/严重度 |
| 3 | `statuspage` | 状态页 | 组件与事件 |
| 4 | `backup` | 仓库/快照 | 加密、排除规则、保留策略 |
| 5 | `restore` | 恢复请求/演练 | 目标、授权、文件数与校验和 |
| 6 | `dr` | RPO/RTO/依赖/回滚 | 上限、无环、回滚计划 |
| 7 | `postmortem` | 复盘/改进项 | 四要素、严重度、闭环 |
| 8 | `slo` | SLO/窗口/停机 | 允许停机、已用、剩余、燃尽率 |

黄金链：`slo → restore.drill → dr.rpo_to`；
`backup.backup → restore.restore → postmortem.postmortem → improvement`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 干净/脏夹具 | `examples/*.json`（28 个） | 每动作配对，脏件断言被拦 |
| 案例包 | `cases/`（18 个文件） | 演练与事故 SOP |
| 黄金成品 | `golden/slo-and-drill.html`、`golden/backup-and-postmortem.html` | 含夹具 sha256 与 27 条门禁 |
| 阈值 | `experience/`、`SRE_SPEC.md` | SLO/RPO/RTO/新鲜度上限 |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 错误预算不透支 | `slo` → `slo:budget` | CRITICAL |
| 燃尽率 ≤1 | `slo` → `slo:burn` | HIGH |
| RPO/RTO 上限 | `dr.rpo_rto` → `dr.rpo_max/rto_max` | BLOCKER |
| 依赖图无环 | `dr.rpo_rto` → `dr.acyclic` | BLOCKER |
| 回滚计划非空 | `dr.rpo_rto` → `dr.rollback` | BLOCKER |
| 演练文件数与校验和 | `restore.drill` → `drill.restored/checksum` | BLOCKER |
| 恢复须授权/演练 | `restore.restore` → `restore.authorized` | BLOCKER |
| 备份仓加密 | `backup.backup` → `backup.encrypted` | BLOCKER |
| 复盘四要素/改进闭环 | `postmortem.*` → `postmortem.sections` / `improvement.*` | BLOCKER |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 技能与契约 | `tests/test_skills.py`、`tests/test_contracts.py` | 覆盖全部动作 |
| 黄金成品 | `tests/test_thickness_samples.py::ThicknessSamples` | 2 份 |
| 误用反例 | `misuse/*.json` + 同测试 | 2 个（预算透支、无回滚） |
| 端到端 | `run_tests.py` T01–T16 | 全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r20-washouzhi-sre/golden/build_golden.py`
- 产物：`slo-and-drill.html`（13 条门禁，0 未过）、
  `backup-and-postmortem.html`（14 条门禁，0 未过）
- 命令：`python r20-washouzhi-sre/run_tests.py`
- 结果：全绿（含厚度样本 T16）

## 7. 已知边界

- 备份存在 ≠ 恢复成功，成功演练必须带文件数与校验和证据；
- 灾难恢复是预案不是已发生切换，不擅自执行灾难切换/恢复生产；
- 复盘是学习不是追责，根因描述不等于责任认定。
