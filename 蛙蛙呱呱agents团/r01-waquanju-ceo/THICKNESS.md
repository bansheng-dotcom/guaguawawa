# R01 蛙全局 · 厚度自述（T12 Tier C：补机制）

> 按升级方案 §16「厚度包」与 §17.1 T12 逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 8 篇 / 34.9KB（`references/00–05` + `engineering-notes.md` + `method-pack.md`） |
| 来源 | 每篇列公开来源（决策科学、公司 OS、治理审计、编排分解等），并单列适用边界 |
| 误用说明 | 每篇有「误用反例」；本仓对应门禁落在 `harness.py` / `skills/s03_decide.py` |
| 能力卡 | `references/capabilities/`：decision-gate、strategic-growth-compass，各带 selftest |

## 2. 生产层

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1 | `skills/s01_intent.py` | brief / 澄清问答 | 分级 + 澄清红黄绿 |
| 2 | `skills/s02_decompose.py` | 意图 | 任务卡 / 波次 / 路由 |
| 3 | `skills/s03_decide.py` | 决策卡 | 可逆性 / 升级 / 卡门禁 |
| 4 | `skills/s04_redteam.py` | 反方质询 | devil / crosseval / grove |
| 5 | `skills/s05_companyos.py` | 公司 OS | 六组件 / 记分卡 / IDS / 冷却锁 |
| 6 | `skills/s06_decisionlog.py` | 决策日志 | 条目 / 冲突 / 90 天复盘 |
| 7 | `skills/s07_boardroom.py` | 董事会材料 | memo / coach |
| 8 | `agent.py plan/run` | 经营意图 | 20 角色任务卡编排 |
| 9 | **`run_manifest.py`（T12 新增）** | 8 阶段工件 | `run-manifest.json` + 2 份 HTML 账本 |

`run_manifest.py` 是本次补的机制：把「意图→拆解→决策→红队→OS→留痕→汇报→交付」写成
账本，每阶段登记 inputs / outputs（sha256）/ decision / signoff。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 真实工件 | `golden/artifacts/*.json` | 由 `examples/` 复制，确定性、无联网 |
| 账本 | `golden/run-manifest.json` | 8 阶段、9 工件、64 位 sha256 |
| 决策包 | `golden/decision-pack.html` | 结论先行 + 决策链 + 工件可追 + 边界 |
| 账本报告 | `golden/run-manifest.html` | 逐步追踪 + 门禁明细 |

## 4. 门禁层

| 错误码 | 判据 | 失败后果 |
|---|---|---|
| `M00_SCHEMA` | 账本必须是 `guagua.run-manifest/v1` | 拒绝签收 |
| `M01_STAGE_ORDER` | 阶段序号 1..n 连续且唯一 | 拒绝签收 |
| `M02_MISSING_SHA256` | 每个工件 64 位 sha256 | 拒绝签收 |
| `M03_MISSING_DECISION` | 每阶段有决策 | 拒绝签收 |
| `M04_UNTRACEABLE_INPUT` | 输入由更早阶段产出 | 拒绝签收 |
| `M05_HASH_MISMATCH` | 磁盘工件与账本哈希一致 | 拒绝签收并回滚 |
| `M06_MISSING_SIGNOFF` | 不可逆阶段签名位已签 | 升级创始人 |
| `M07_DUPLICATE_ARTIFACT` | 工件名唯一 | 拒绝签收 |
| `M08_ARTIFACT_MISSING` | 工件在磁盘存在 | 拒绝签收 |

既有门禁不变：`harness.py`（brief/card/crosseval/freeze）、`review.py`（对抗评审）。

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 机制单测（pytest） | `tests/test_mechanism.py` | 6 条：构建/校验/篡改/HTML 契约/误用/全部变异 |
| 角色端到端 | `run_tests.py` §T12 | 7 条 |
| 黄金成品 | `golden/*.html` | 2 份 |
| 误用反例 | `misuse/*.json` | 2 份（缺哈希 / 断链+未签字） |
| 全量 | `python run_tests.py` | PASS 84 / FAIL 0 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r01-waquanju-ceo/run_tests.py`
- 结果：ALL GREEN，PASS 84 / FAIL 0
- 机制：`python r01-waquanju-ceo/run_manifest.py goldens` → 8 阶段、9 工件、0 违规
- 复核：`python run_manifest.py verify --file golden/run-manifest.json --dir golden` → PASS
- 呈现：`python scripts/check_report_presentation.py r01-waquanju-ceo/golden/*.html` → 2/2 PASS

## 7. 已知边界

- 账本记录的是「本次产线登记过的工件」，不替代项目侧的版本管理；
- 账本自身不写入自己的哈希（自引用），由账本渲染的报告不计入账本；
- 签名位只记录「谁签、何时签」，不校验签名真伪（本地无 PKI）；
- 阶段决策是文本，不含推理链全文；推理仍看 `decisionlog` 与 brief。
