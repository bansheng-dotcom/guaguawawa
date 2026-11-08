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

## 三、三条红线（对抗评审 T7 硬门禁）

| 红线 | 触发词（外置于 review.credential_words / execution_words / scope_terms） | 处置 |
|---|---|---|
| 红线 1：凭据不入工件 | api_key/secret/password/token/私钥/密钥/密码/restic密码/access_key | → writer（走密钥管理） |
| 红线 2：不擅自执行高风险动作 | 直接删除快照/直接灾难切换/直接改生产告警/直接恢复生产 | → writer（走人工授权） |
| 红线 3：不做统计结论/业务归因 | 统计结论/业务归因/财务结论/法律意见 | → writer（移交 R06/R03） |

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
```

## Honest capability status and safe local execution

`manifest` marks local backup/hash/restore drill `real` and production restore `blocked`. `python agent.py local --input {"source":"<local-directory>"} --output <manifest.json>` builds a SHA-256 manifest and verifies a copy in a temporary directory. It never writes to production. A missing/unreachable source yields `blocked`, not success.


```
r20-washouzhi-sre/
  agent.py            # 薄调度器：CLI 分发 + run_task 协作入口
  harness.py          # 14 门禁确定性验证器 + runlog
  contracts.py        # 7 技能 × 14 动作契约（JSON Schema）
  review.py           # T7 对抗评审（含三条红线）
  cases.py            # 案例库加载/结构校验/阈值合并
  verify_loop.py      # 28 行闭环矩阵
  run_tests.py        # T10 端到端验收
  SKILL.md            # 本文件
  skills/             # s01..s07 技能模块 + _common 共享基础
  examples/           # 28 个夹具（14 干净 + 14 脏）
  experience/         # thresholds.json（全局阈值，与 _common._DEFAULT_THRESHOLDS 双源同步）
  cases/              # 2 个案例（backup-no-restore / incident-escalation）
  references/         # 7 篇四层参考（方法论/口径/算例/踩坑）
```
