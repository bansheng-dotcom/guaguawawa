# R20 蛙值守 · 可靠性与恢复官 — 技能说明（SKILL.md）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/skills/incident-response/SKILL.md
>


> 角色：R20 蛙值守 ｜ 可靠性与恢复官（Reliability & Recovery Officer）。已引入真实执行层，不再仅仅是门禁校验。
> 能力域 → 技能子命令：7 能力域 → 7 技能模块 → 14 个确定性动作
> 来源：restic__restic（备份/快照/恢复/保留策略）、louislam__uptime-kuma（监控/告警/状态页）

## 一、能力域 → 技能子命令映射

| 能力域 | 技能模块 | 子命令 | 一句话职责 |
|---|---|---|---|
| 可用性监控 | `monitor` | `monitor` | 监控项结构校验（探测定义，不是探测结果） |
| | | `uptime` | 可用性记录校验（ratio 实算） |
| 告警升级 | `alert` | `alert` | 告警规则校验（severity/channel 白名单） |
| | | `escalation` | 值班升级链校验（level 严格单调递增） |
| 状态页沟通 | `statuspage` | `statuspage` | 组件状态校验（对外事实） |
| | | `incident` | 事件时间线校验（ts 单调、resolved 带结束时间） |
| 加密增量备份 | `backup` | `backup` | 备份仓结构校验（加密是硬要求） |
| | | `snapshot` | 快照清单/保留策略校验（id 唯一） |
| 恢复演练 | `restore` | `restore` | 恢复请求校验（源快照 + 授权声明） |
| | | `drill` | 恢复演练记录校验（restored_count>0 + checksum 证据） |
| 灾难恢复回滚 | `dr` | `rpo_rto` | RPO/RTO 与恢复手册校验（上限 + 依赖无环） |
| | | `rollback` | 回滚计划校验（步骤 + 人工决策点） |
| 运行复盘 | `postmortem` | `postmortem` | 复盘结构校验（四要素齐备） |
| | | `improvement` | 改进项闭环校验（owner/due/status，无 open） |

## 二、协作契约（inputs → outputs）

```
inputs:  topology + asset_list     ← 上游：R09 拓扑、R02 事故流程、各角色资产清单
outputs: monitor_config + backup_repo
```

- `topology`：服务拓扑（谁依赖谁），喂给 `monitor`/`dr` 的依赖图与监控项。
- `asset_list`：资产清单（哪些要备份、哪些要监控），喂给 `backup`/`monitor`。

## 三、红线（T7 三条 + L03 五条）

T7 对抗评审保留三条外置红线（词表见 `experience/thresholds.json`）：

| 红线 | 触发词（外置于 review.credential_words / execution_words / scope_terms） | 处置 |
|---|---|---|
| 红线 1：凭据不入工件 | api_key/secret/password/token/私钥/密钥/密码/restic密码/access_key | → writer（走密钥管理） |
| 红线 2：不擅自执行高风险动作 | 直接删除快照/直接灾难切换/直接改生产告警/直接恢复生产 | → writer（走人工授权） |
| 红线 3：不做统计结论/业务归因 | 统计结论/业务归因/财务结论/法律意见 | → writer（移交 R06/R03） |

L03 自愈引擎把红线扩展到五条（`engines/reflexive_healer.py`）：
RL-01 未授权生产恢复/切换、RL-02 凭据泄露、RL-03 擅自删除/清空快照、
RL-04 越权财务/统计/法律结论、RL-05 假演练/未演练即宣称可恢复。

**核心边界**（能力全景原话）：*备份存在 ≠ 恢复成功，必须演练；不擅自删除
快照、修改生产告警或执行灾难切换。*

## 四、确定性验证器（harness）

14 个门禁 = 14 个动作，每个返回 `{ok, grade, checks[]}`，`ok=false` 时退出码
非 0。运行：

```bash
python agent.py harness backup   --input examples/backup.json
python agent.py harness rollback --input examples/rollback.json
python agent.py harness runlog --n 5
```

## 五、验收入口（T10）

```bash
python run_tests.py      # 全量端到端：manifest / 28 夹具 / 契约 / 评审 / 案例 / 阈值 / harness / demo / run_task / verify_loop
python verify_loop.py    # 14 干净 + 14 脏 = 28 行闭环矩阵
python tests/test_evolution_l01_l10.py   # L01~L10 演进层 45 条回归
```

## 六、SOP v13.0 十维演进层（真实引擎）

| 层 | 引擎 | 能力 | 入口 |
|---|---|---|---|
| L01 | `runtime_engine.py` | SLI/错误预算/燃烧率/MTTR/RPO-RTO/分位精算 | `evolve probe` |
| L02 | `intent_compiler.py` | 复合故障 → 5 阶段 Kahn DAG + 关键路径 | `evolve decompile` |
| L03 | `reflexive_healer.py` | 告警归一 + Reflexion 闭环 + 五条红线 | `evolve heal` |
| L04 | `spec_ledger.py` | SRE_SPEC.md 账本指纹 + 8 维发布门禁 | `evolve spec` |
| L05 | `slop_guard.py` | 假大空清洗 + 量化证据 + DRI + 行动力 | `evolve slop` |
| L06 | `scenario_matrix.py` | 三维处置方案 + 四准则 MCDA + 敏感性 | `evolve scenario` |
| L07 | `asset_bundle.py` | Bundle + SARIF 2.1.0 + Vega-Lite v5 | `evolve bundle` |
| L08 | `diff_patch_engine.py` | RFC 6902 差量热修 + 配置不变量 | `evolve patch` |
| L09 | `session_memory.py` | 持久记忆 + 代词消歧 + 快照回滚 | `evolve memory` |
| L10 | `telemetry_watchdog.py` | 三态熔断 + Full Jitter + 全链路遥测 | `evolve watchdog` |

自动演进（每轮 = 一次完整 SOP 周期，含双轨零回归门禁）：

```bash
python auto_evolve_runner.py --status
python auto_evolve_runner.py --stage 1     # Round 1: L01-L03
python auto_evolve_runner.py --run-all     # 断点续跑剩余轮次
```

## Honest capability status and safe local execution

`manifest` marks local backup/hash/restore drill `real` and production restore `blocked`. `python agent.py local --input {"source":"<local-directory>"} --output <manifest.json>` builds a SHA-256 manifest and verifies a copy in a temporary directory. It never writes to production. A missing/unreachable source yields `blocked`, not success.


```
r20-washouzhi-sre/
  agent.py            # 薄调度器：CLI 分发 + run_task 协作入口 + evolve L01~L10
  auto_evolve_runner.py # SOP v13.0 三轮自动演进执行器（断点续跑 + 零回归门禁）
  harness.py          # 14 门禁确定性验证器 + runlog
  contracts.py        # 7 技能 × 14 动作契约（JSON Schema）
  review.py           # T7 对抗评审（含三条红线）
  cases.py            # 案例库加载/结构校验/阈值合并
  verify_loop.py      # 28 行闭环矩阵
  run_tests.py        # T10 端到端验收
  SRE_SPEC.md         # SRE 领域唯一信任源（SLO/错误预算/8 维门禁）
  SKILL.md            # 本文件
  engines/            # L01~L10 十个真实演进引擎 + PEP 562 懒加载
  skills/             # s01..s07 技能模块 + _common 共享基础
  tests/              # 演进层 45 条回归（test_evolution_l01_l10.py）
  examples/           # 28 个夹具（14 干净 + 14 脏）
  experience/         # thresholds.json（全局阈值，与 _common._DEFAULT_THRESHOLDS 双源同步）
  cases/              # 3 个案例（backup-no-restore / incident-escalation / sla-incident）
  references/         # 7 篇四层参考（方法论/口径/算例/踩坑）
  workspace/          # 演进证据：rounds/round{1,2,3}/gate.json、bundles/、telemetry.jsonl
```
