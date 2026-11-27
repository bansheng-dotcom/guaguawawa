# R09 蛙稳码 · 厚度自述（T7）

> 按升级方案 §5「五层可验收」、§12 r09 施工图、§17.2 与 §21 逐项自述。
> 只写能被命令复核的事实；数字以本仓当前磁盘为准。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 顶层方法文 7 篇 / 约 31.4KB；本轮新增 4 篇（约 17.1KB） |
| 新增篇目 | `references/adr-and-tradeoffs.md`、`openapi-contract.md`、`security-stride-asvs.md`、`sre-slo-dora.md` |
| 来源 | Nygard 2011、MADR 3.0、ISO/IEC/IEEE 42010:2022、OpenAPI 3.1.0、RFC 7807/9457、JSON Schema 2020-12、Pact、Microsoft STRIDE、Shostack 2014、OWASP ASVS 4.0.3/5.0、OWASP Top 10 2021、NIST SP 800-218、Google SRE 2016/2018、DORA/Accelerate 2018、12-Factor 2011 |
| 适用边界 | 每篇单列「适用边界」，写明何时该裁剪（离线工具、二进制协议、一次性脚本等） |
| 误用反例 | 每篇单列反例表，并标注本仓哪个门禁拦截（如 `api:migration_reversible`、`security:no_leaked_secrets`） |

无 TBD 占位；所有条目均为可核对的方法与门禁映射。

## 2. 生产层

`eng_chain` 一条命令串起 10 个模块：

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `eng_chain/adr.py` | 需求、约束、候选方案 | `adr.json`（背景/决定/后果 + 模块边界 + 取舍） |
| 2 | `eng_chain/api.py` | 数据模型、端点、错误码、迁移 | `api.json`（JSON Schema + OpenAPI 3.1 + RFC 7807 + 迁移） |
| 3 | `eng_chain/feature.py` | 用户故事、验收 | `feature.json`（UI/服务/状态/认证切片 + 可运行 + 回滚） |
| 4 | `eng_chain/testing.py` | 金字塔、契约、E2E | `testing.json`（金字塔 + 契约测试 + 验收映射） |
| 5 | `eng_chain/debug.py` | 缺陷、复现、假设 | `debug.json`（复现/假设/插桩/根因/最小修复/回归） |
| 6 | `eng_chain/release.py` | 流水线、版本、回滚 | `release.json`（CI/CD + 版本锁 + 幂等 + 回滚 + 重放） |
| 7 | `eng_chain/security.py` | 威胁、ASVS、扫描 | `security.json`（STRIDE + ASVS + 依赖/密钥 + 错误码对齐） |
| 8 | `eng_chain/performance.py` | 基线、预算、剖析 | `performance.json`（基线/预算/剖析/优化项） |
| 9 | `eng_chain/incident.py` | 时间线、SLO | `incident.json`（时间线/根因/行动项/错误预算/MTTD/MTTR） |
| 10 | `eng_chain/review.py` | 审查清单 | `review.json`（清单/风险分级/安全与测试已审） |

编排入口 `eng_chain/runner.py` 一次产出 10 份 JSON + 10 份 Markdown +
`eng_manifest.json`（每段 sha256 + 门禁 + 跨段一致 + 阻断项）。
技能入口 `skills/s09_eng_chain.py` 提供 12 个子命令：
`adr/api/feature/testing/debug/release/security/performance/incident/review/run/audit`。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 端到端夹具 | `eng_chain/fixtures/tiny-notes.json` | 小型笔记服务：3 模块、2 实体、4 端点、4 错误码、40 测试 |
| 故障复盘夹具 | `eng_chain/fixtures/incident-outage.json` | 搜索全表扫描 SEV-1：6 事件、4 行动项、预算 28/43.2 分钟 |
| 安全审计夹具 | `eng_chain/fixtures/security-audit.json` | STRIDE 6 类、ASVS 8 项、依赖 5 项 high=0、泄漏 0 |
| 黄金页 | `golden/*.html`（3 份） | 由 runner 真实跑上述夹具后渲染，含阶段指纹 |
| 误用样本 | `misuse/*.json`（3 份） | 无测试发布 / 不可逆迁移无回滚 / 密钥进仓库 |
| 运行账本 | `eng_manifest.json` | 10 段 sha256、门禁结论、跨段一致、blockers |

每次 `run` 在输出目录落 21 个文件（10 JSON + 10 MD + manifest）；
`audit` 可对任意历史目录只读复核哈希与门禁。

## 4. 门禁层

| 段 | 主要门禁（CRITICAL） | 失败后果 |
|---|---|---|
| adr | `adr:context/options/decision/boundaries/tradeoffs` | 无 ADR 不放行后续 |
| api | `api:schemas/openapi31/rfc7807/contract_refs/migration_reversible` | 契约悬空或迁移不可逆即阻断 |
| feature | `feature:story/slice/acceptance/runnable/rollback` | 切片不完整或不可回滚即阻断 |
| testing | `testing:pyramid/contract/e2e/acceptance_mapping/coverage/no_skipped` | 倒金字塔、漏端点、skip 即阻断 |
| debug | `debug:repro/hypotheses/instrumentation/root_cause/minimal_fix/evidence_chain/regression` | 无证据链或根因 unknown 即阻断 |
| release | `release:pipeline/tests_green/version_lock/idempotent/rollback_tested/replay` | 无测试发布、无锁、回滚未演练即阻断 |
| security | `security:stride/asvs/no_high/no_leaked_secrets/error_codes` | 高危、泄漏、错误码脱节即阻断 |
| performance | `performance:baseline/budget/profiling/optimizations/measurement` | 无基线或无预算即阻断 |
| incident | `incident:timeline/root_cause/actions/error_budget/blameless/detection` | 预算超支或复盘追责即阻断 |
| review | `review:checklist/all_pass/risk_classified/security_reviewed/tests_reviewed/risk_level` | 未闭环高风险项即阻断 |
| 跨段 | `consistency:api_security_error_codes`、`consistency:testing_acceptance`、`consistency:release_test_count`、`chain:*` | 任一段红或跨段不一致 → manifest FAIL、退出码 1 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 单段门禁 | `tests/test_eng_chain.py::TestStageGates` | 5 条（十段全 PASS + 关键结构） |
| 反向门禁 | `TestNegativeGates` | 11 条（逐段破坏关键条件，断言具名门禁变红） |
| 端到端 | `TestEndToEnd` | 3 夹具 + 1 条确定性（两次运行 sha256 相同） |
| 误用拦截 | `TestMisuse` | 3 条（断言 expect_block 出现在 manifest blockers） |
| 技能入口 | `TestSkillModule` | 1 条（12 动作 + 单段 + run + audit） |
| 角色验收 | `run_tests.py::T17` | 复用上述全部 20 条 |
| 全量 | `run_tests.py` | 68 条全绿 |
| pytest | `python -m pytest r09-wawenma-engineer/tests -q` | 37 条全绿 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r09-wawenma-engineer/run_tests.py` → `Ran 68 tests ... OK`
- 命令：`python -m pytest r09-wawenma-engineer/tests -q -p no:cacheprovider` → `37 passed`
- 命令：`python scripts/validate_profiles.py --role r09` → `[PASS] r09 tier=A actions=10 declared=6`
- 命令：`python scripts/check_role_thickness.py --check` → `问题 0`（refs=7、ref_kb=31.4、golden=3、misuse=3）
- 三份黄金：`tiny-notes` / `incident-outage` / `security-audit` 全部 `manifest.ok=true`
- 三份误用：分别被 `release:tests_green`、`api:migration_reversible`、
  `security:no_leaked_secrets` 拦下

### 已知边界

- `docs/actions_catalog.json` 由仓库统一导出且本轮禁止修改，因此 10 个链动作
  未登记为目录动作；已在 `prompt_profile.json` 用 `chain_actions` /
  `chain_semantic_fields`（每动作 ≤2 字段，来源 topic/stack/scale）声明，
  并以 `skills.CHAIN` 独立入口注册，保持既有 8 技能 × 2 动作契约不变。
- `audit` 只校验 JSON/MD 存在性、JSON 哈希、段齐全与跨段一致，
  不校验 Markdown 内容语义；MD 的 md_sha256 只记录不比对。
- 黄金 HTML 由一次性脚本运行后保存，未纳入 CI 自动重生成；
  夹具或渲染逻辑变更时需要人工重新生成并复核 diff。
- 性能段只做预算与计划校验，不执行真实压测；真实压测工具与数据归项目仓库。
