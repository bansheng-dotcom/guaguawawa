# SRE SLO、DORA 与 12-Factor：把「稳定」和「可交付」变成数字

> 适用角色：R09 工程官；对应工程链第 6 段 `release`、第 8 段 `performance`
> 与第 9 段 `incident`。R20 负责持续监控与备份，本文只覆盖工程侧可验证部分。

## 1. 来源

- Google, *Site Reliability Engineering*（2016）：提出 SLI/SLO/SLA 与错误预算，
  明确「100% 可用性不是目标」。
- Google, *The Site Reliability Workbook*（2018）：给出错误预算策略、
  多窗口燃烧率告警与复盘模板。
- DORA, *Accelerate*（2018）及历年 *State of DevOps Report*：用部署频率、
  变更前置时间、变更失败率、恢复时长四项指标衡量交付能力。
- Adam Wiggins, *The Twelve-Factor App*（2011）：配置、依赖、进程、日志等
  12 条可移植应用原则。
- RFC 2119：本文中的「必须 / 应当」按该文档的关键词含义使用。

## 2. 适用边界

适合：

- 有真实用户与可用性承诺的在线服务；
- 需要持续交付、频繁发布、要求可回滚的工程；
- 需要把故障复盘转化为行动项与预算管理的团队。

需裁剪：

- 一次性脚本、内部小工具：可只保留发布可回滚与依赖锁定，不强行定义 SLO；
- 无历史数据的早期项目：先记录基线，再定 SLO，禁止拍脑袋写 99.99%；
- 12-Factor 不是教条：把配置放环境变量不等于可以明文存密钥，
  密钥必须走密钥管理或至少不入库、不入镜像。

## 3. 方法：预算 → 发布 → 复盘

1. **SLI/SLO**：选一个用户可感知的指标（成功率、p95 延迟），
   定目标和统计窗口（如 99.9% / 30 天），换算错误预算分钟数。
2. **错误预算**：预算 = 窗口分钟 × (1 − SLO)。预算耗尽时冻结非紧急发布，
   先做稳定性工作；预算有消费记录，不能只写目标。
3. **发布可回滚**：CI 至少包含 lint/test/security/build/deploy 五阶段；
   依赖锁定 lockfile；写操作有幂等键；回滚步骤演练过；整链可重放且确定。
4. **性能预算**：先有基线（p95、吞吐），再定不高于基线的预算，
   最后才列优化项；测量方法与噪声控制写清楚。
5. **复盘不追责**：时间线 ≥4 个时刻、根因、行动项（有负责人/截止/状态）、
   MTTD/MTTR、错误预算消耗；行动项进入后续迭代，而不是停在文档里。

## 4. 仓内落点

| 门禁 | 检查内容 | 失败级别 |
|---|---|---|
| `release:pipeline` | 含 lint/test/security/build/deploy | CRITICAL |
| `release:tests_green` | 0 失败 0 跳过、覆盖 ≥80% | CRITICAL |
| `release:version_lock` | 依赖锁定 lockfile | CRITICAL |
| `release:idempotent` | 写操作幂等键已验证 | CRITICAL |
| `release:rollback_tested` | 回滚步骤 ≥2 且演练过 | CRITICAL |
| `release:replay` | 发布链可重放且确定 | CRITICAL |
| `performance:baseline` / `performance:budget` | 有基线、预算不高于基线 | CRITICAL |
| `incident:timeline` / `incident:root_cause` / `incident:actions` | 复盘三件套 | CRITICAL |
| `incident:error_budget` | 预算未超支 | CRITICAL |
| `incident:blameless` / `incident:detection` | 不追责、有 MTTD/MTTR | CRITICAL |

DORA 四项指标不直接做门禁，但应在发布记录里可计算：部署频率看发布流水，
变更前置时间看提交到部署，变更失败率看回滚/热修次数，恢复时长看 MTTR。

## 5. 误用反例

| 反例 | 后果 | 拦截门禁 |
|---|---|---|
| SLO 定 100% | 错误预算为 0，任何故障都无法容忍 | 人工评审（预算必须 >0） |
| 有 SLO 但无消费记录 | 预算耗尽仍继续发新功能 | `incident:error_budget` |
| 测试全跳过仍发布 | 假绿上线 | `release:tests_green` |
| 依赖不锁版本 | 构建不可复现，故障难定位 | `release:version_lock` |
| 回滚只写在文档里 | 真出事时命令跑不通 | `release:rollback_tested` |
| 复盘追责到个人 | 信息被隐藏，根因失真 | `incident:blameless` |
| 只比发布速度不比稳定性 | 变更失败率与恢复时长恶化 | DORA 四项一起看 |
| 12-Factor 教条化，密钥进环境变量文件 | 密钥随仓库泄漏 | `security:no_leaked_secrets` |

## 6. 检查清单

- [ ] SLO 目标、窗口、错误预算分钟数三者齐全且预算 >0；
- [ ] 发布流水线五阶段齐全，测试 0 失败 0 跳过；
- [ ] 依赖有 lockfile，构建可复现；
- [ ] 写操作幂等键已验证；
- [ ] 回滚步骤演练过，且有明确触发条件；
- [ ] 性能基线与预算都有数字，测量方法可复现；
- [ ] 复盘时间线、根因、行动项、MTTD/MTTR、预算消耗齐全；
- [ ] 复盘结论只对系统与流程，不对个人。
