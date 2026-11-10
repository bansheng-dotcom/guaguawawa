# R18 蛙数仓 · 十维渐进式演进升级报告

> 执行标准：《人机协作·智能体十轮渐进式演进标准作业程序 SOP v13.0》
> 执行对象：`r18-washucang-dataeng`（R18 蛙数仓 · 数据工程与管道官）
> 执行方式：`workflow` 多智能体编排驱动 3 轮完整 SOP（每轮 = 体检 → 对标 → 跃迁 → 工件 → 双轨回归）
> 底层状态机：`auto_evolve_runner.py` 逐轮落盘 10 轮打卡
> 结论：**ALL GREEN · 10/10 轮 / 10/10 引擎层 · 基准轨 133/133 · 演进轨 75/75**

---

## 一、结论看板

| 项目 | 升级前 | 升级后 |
|---|---|---|
| 基准测试套件 | **107 / 126（红）**，`agent.py` 任何子命令 `ModuleNotFoundError: No module named 'agents'` | **133 / 133（绿）** |
| 演进集成测试 | 不存在 | **75 / 75（绿）** |
| 十维引擎层 | 0 / 10 | **10 / 10** |
| 演进状态机 | 无 `auto_evolve_runner.py` | **10/10 轮 PASS，`overall_status=ALL_GREEN`** |
| 领域账本 SSOT | 无（阈值散落 13 处） | **`DATAENG_SPEC.md` v1.0（8 指标 / 8 门禁 / 4 红线）** |
| 主链路产物 | 单一 `{skill}.json` + Markdown | + `delivery_dag.json`、`scenario_matrix.json`、`bundles/`（SARIF/Vega/AST/Bundle）、`session_state.json`、`telemetry.jsonl` |

状态机落盘：`workspace/evolution_state.json` → `rounds_passed=[1..10]`、`layers_passed=[L01..L10]`、`overall_status=ALL_GREEN`。

---

## 二、升级前真实体检（不是模板话术）

以 `git HEAD` 原码逐条复现，三处**基线级**故障：

1. **基线整体跑不起来**：`agent.py:26-28` 只把仓库根 `D:/蛙蛙呱呱` 注入 `sys.path`，而 `agents` 包实际在 `蛙蛙呱呱agents团/agents`；第 36 行 `from agents.shared.chat_cli import ...` 比正确目录注入（原 40-44 行）早 6 行执行 → 任何子命令在 argparse 之前就 `ModuleNotFoundError` 崩溃。实测基线 **107/126**。
2. **占位伪代码**：`harness.py` 末尾 `run_strict_validation()` 只有 `# 占位补充...` 注释就 `return ok=True`，属于典型假代码。
3. **历史契约僵化**：`run_tests.py` 硬编码 `len(cases.list_cases()) == 2`，而案例库已有 3 个（新增 `metric-reconcile`），导致基线永久挂红（SOP §5.10 明令用严格超集判据）。

修复：动态三目录引导（`_HERE/_AGENTS/_REPO_ROOT`）、删除占位函数、案例契约改 `>=2` 并逐个校验存在性、补 `tests/__init__.py`、临时目录收敛到 `workspace/tmp`（SOP §5.5/§5.7/§5.9）。

---

## 三、三轮 SOP 执行台账

### 第 1 轮 · 执行基石（L01~L03）

| 步骤 | 内容与证据 |
|---|---|
| **1 体检** | L01：`skills/s04_quality.py:59/63/70/77` 的 `row_count/null_ratio/dup_ratio/invalid_count` 全部 `c._num(data.get(...))` 直读输入自报；`_common._num` 缺值返回 `0.0` 造成 fail-open，实测 `{"table":"dw_orders","row_count":1}` 直接 PASS 且 0 项检查。L02：`agent.py:279-284` 仅 14 条关键词子串匹配 + 静默兜底，`s03_pipeline.py:51-71` 只返回「有没有环」的布尔。L03：红线只写在 SKILL.md，`review.py:62-83` 是事后文本扫描且声明 handoff 即解除；`s01_elt.py:53-59` 只扫顶层字段名，实测嵌套 `password` 与 DSN 均漏检；无资金红线；阈值缺键直接 `KeyError`。 |
| **2 对标** | `duckdb/duckdb`(~43k, MIT) / `apache/arrow`(~17k) / `dbt-labs/dbt`(~14k)；`dspy`(~39k) / `ray`(~44k) / `airflow`(~47k)；`reflexion`(~3.4k) / `autogen`(~62k) / `AutoGPT`(~188k)。 |
| **3 跃迁** | 新建 `engines/runtime_engine.py`（真实嵌入式 DuckDB 沙箱：`run_sql`、SQL 聚合 `profile_table`、`gate_quality`、`incremental_conservation` 容差 0、SHA256 指纹）；`engines/intent_compiler.py`（实体抽取 + 5 阶段 Kahn DAG + 环检测 + 关键路径/工时）；`engines/reflexive_healer.py`（4 条红线硬拦截 + 别名/骨架自愈 + 有界反思重试）。 |
| **4 工件** | `workspace/rounds/L01_probe.json`（249B，`status=HEALTHY, engine=duckdb 1.2.0`）；`L02_dag.json`（2 984B，5 阶段 / 6 边 / 35.7h / 4.46 人天）；`L03_heal.json`（1 297B，`healed=true` + 5 条 reflections）。 |
| **5 回归** | 基准 `133/133` + 演进 `26/26` → 全绿。 |

### 第 2 轮 · 专业深度（L04~L06）

| 步骤 | 内容与证据 |
|---|---|
| **1 体检** | HEAD 全树无 `DATAENG_SPEC.md`，`north_star/北极星` 零命中；`thresholds.json` 散落 13 处，`run_tests.py:322` 与 SKILL.md 各自写死阈值；`slop/套话/行动力` 零命中（narrative 直接 f-string 拼接，无任何闸门）；`scenario/MCDA/ROI` 零命中（一锤子单方案）。 |
| **2 对标** | `dbt`(~14.1k) / `OpenAPI-Specification`(~31.3k) / `metricflow`(~1.9k)；`reviewdog`(~9.7k) / `vale-cli/vale`(~6.4k) / `textlint`(~3.2k)；`optuna`(~15k) / `pymoo`(~3k)。已剔除不存在的 `huashu-design/Stylescapes`（GitHub 404）并把 `errata-ai/vale` 更正为重定向后的 `vale-cli/vale`。 |
| **3 跃迁** | `DATAENG_SPEC.md`（8 北极星指标 PSR/FSR/DQR/LCR/BCR/MTTD/DMR/ORT、G1~G8、6 阈值、4 红线）；`engines/spec_ledger.py`（fail-closed 解析 + 容差判定 + 8 维 BLOCKER + 导出 JSON/DDL CHECK/dbt schema）；`engines/slop_guard.py`（套话定位 + 可行动重述 + 行动力/DRI 评分，**严禁伪造实测值**）；`engines/scenario_matrix.py`（三维方案 + 5 维 MCDA + ROI 比值 + 上下文修正）。 |
| **4 工件** | `L04_spec.json`（497B，`8/8/4`）+ `workspace/spec_exports/{dataeng_spec.json 4 988B, dataeng_gates.sql 1 265B, dbt_schema.yml 1 750B}`；`L05_slop.json`（1 381B，5 词命中、行动力 5 分）；`L06_scenarios.json`（2 749B，`balanced 68.0 / fast 64.1 / strict 45.0`，`roi_ratio` 齐备）。 |
| **5 回归** | 基准 `133/133` + 演进 `54/54` → 全绿。 |

### 第 3 轮 · 工业交付（L07~L10）

| 步骤 | 内容与证据 |
|---|---|
| **1 体检** | HEAD 全树 `sarif/vega/bundle` 零命中（产物只有 `{skill}.json` + Markdown）；`jsonpatch/6902/create_patch` 零命中（改一处只能全量重跑并覆盖旧门禁）；`session_state/记忆` 零命中（第二轮彻底失忆）；`circuit/telemetry/watchdog/backoff` 零命中，且有 `review.py:56-57` `except Exception: contracted = True` 的 **fail-open 伪容灾**。 |
| **2 对标** | `semgrep/semgrep`(~17.6k) / `vega/vega-lite`(~5.5k) / `dbt`(~14.1k) + OASIS SARIF v2.1.0；`evanphx/json-patch`(~1.2k) / `google/diff-match-patch`(~8.1k) / RFC 6902；`letta`(~25.4k) / `langgraph`(~44.7k)；`temporal`(~24.3k) / `opentelemetry-python`(~2.7k) / `tenacity`(~8.8k)。审计同时纠正：`microsoft/sarif-tools` 仅 160★，未达 1k，已从 docstring 标杆位替换为 semgrep。 |
| **3 跃迁** | `engines/asset_bundle.py`（bundle + SARIF 2.1.0 + Vega-Lite v5 + 血缘 AST + 自校验）；`engines/diff_patch_engine.py`（RFC 6902 六算子 + 指针前缀→门禁影响面 + 未知指针保守全量重验）；`engines/session_memory.py`（槽位双向同步 + 代词消歧 + 快照/回滚）；`engines/telemetry_watchdog.py`（CLOSED/OPEN/HALF_OPEN 三态 + 指数退避全抖动 + 超时看门狗 + TraceID/SpanID/SHA256 遥测）。 |
| **4 工件** | `workspace/bundles/` 4 件（合计 14 411B，SARIF `version=2.1.0` / `results=1`）；`L08_patch.json`（4 287B，3 个 op、仅 G1 受影响、7 个门禁复用、无需全量重验）；`L09_session.json` + `workspace/session_state.json`（2 888B，`resolved=true`，回滚使 `sla_hours 4→2`）；`L10_telemetry.json` + `workspace/telemetry.jsonl`（26 729B，重试第 3 次成功、超时判 TIMEOUT、每行含 TraceID/SpanID/SHA256/耗时）。 |
| **5 回归** | 基准 `133/133` + 演进 `74/74` → 全绿；最终收口 `75/75`。 |

---

## 四、十层引擎清单（`engines/`）

| 层 | 引擎类 | 文件 | 真实能力（非空壳证据） |
|---|---|---|---|
| L01 | `DataEngRuntimeEngine` | `runtime_engine.py` | DuckDB 1.2.0 真实建表/参数化插入/聚合；空值率、重复率、越界行数由 SQL 算出；增量守恒 `target==base+inserted` 容差 0；行集 SHA256 指纹 |
| L02 | `DataEngIntentCompiler` | `intent_compiler.py` | 表/时间窗/SLA/模式/目的地抽取；5 阶段 Kahn 拓扑 + 环检测；关键路径 DP + 人天预算 |
| L03 | `DataEngReflexiveHealer` | `reflexive_healer.py` | 4 条红线 `[REDLINE BLOCKED]` + 移交对象；别名归一/骨架补齐且标记 `needs_revalidation`；有界反思重试 |
| L04 | `DataEngSpecLedger` | `spec_ledger.py` | 解析 `DATAENG_SPEC.md`（8/8/4）；容差判定；8 维 BLOCKER；导出 JSON + DDL CHECK + dbt schema |
| L05 | `DataEngSlopGuard` | `slop_guard.py` | 17 类套话定位；物理重述为「量化目标/待实测清单/DRI/截止期」；行动力 + DRI 双门槛；**零伪造实测值** |
| L06 | `DataEngScenarioMatrix` | `scenario_matrix.py` | 三维方案；5 维 MCDA 权重；ROI 比值；SLA/预算/强一致上下文修正；默认推荐稳健批流版 |
| L07 | `DataEngAssetBundle` | `asset_bundle.py` | Bundle + SARIF v2.1.0 + Vega-Lite v5 + 管道 AST；导出后自校验 |
| L08 | `DataEngDiffPatchEngine` | `diff_patch_engine.py` | RFC 6902 六算子；`create_patch` 最小差量；指针→G1~G8 影响面；未知指针保守全量重验 |
| L09 | `DataEngSessionMemory` | `session_memory.py` | `slots`/`active`/`active_*` 三写防漂移；第 N 套方案/SLA 改 X/上一版/该管道消歧；快照树 + rollback |
| L10 | `DataEngTelemetryWatchdog` + `CircuitBreaker` | `telemetry_watchdog.py` | 三态熔断；指数退避 + Full Jitter（可注入随机源）；超时守护线程；`telemetry.jsonl` 全链路留痕 |

---

## 五、主链路接入（防「侧库漂亮、用户路径照旧」）

审计明确指出「引擎真实但未接入主链路」后，已把十层能力接进 `agent.py run_task`：

| 接入点 | 行为 |
|---|---|
| L02 | 每次任务把意图编译为 5 阶段 DAG → `{task}/delivery_dag.json`，结果含 `delivery_dag` |
| L03 | `narrative/summary/next` 过 4 条红线，命中即 `ok=false`、`verdict=FAIL`、强制 handoff |
| L04 | 运行时加载 `DATAENG_SPEC.md`；`skills/_common.load_thresholds()` 以账本覆盖 JSON 兜底（改账本即改判定） |
| L05 | 9 个 `conclusion_keys` 全部过反套话清洗（不只 narrative），写入 `slop_audit` |
| L06 | 按任务 SLA / 强一致上下文生成三维矩阵 → `{task}/scenario_matrix.json`，含 ROI 比值 |
| L07 | 伴生导出 `{task}/bundles/` 四件套（bundle/SARIF/Vega/AST），结果含 `asset_bundle` |
| L09 | `workspace/state/session_state.json` 记忆池：消歧 + 轮次留痕 |
| L10 | 技能执行包在 `execute_with_resilience`（重试 + 熔断）内，结果含 `trace{trace_id,attempts,status}`，遥测落 `workspace/telemetry.jsonl` |
| L08 | 新增主入口子命令 `python agent.py patch --base ... --patch ... --out ...` |

另修复 `review.py` 的 fail-open：契约校验器异常由「判为符合」改为 **fail-closed 阻断**。

---

## 六、双轨零破坏回归证据

- 每一轮打卡都真实执行并记录：`workspace/rounds/round_01_gate.json` … `round_10_gate.json`。
- 10 份记录一致显示：`baseline={passed:133,total:133}`、`evolution={tests:75,ok:true}`、`status=PASS`，并记录该轮工件路径 / 字节数 / SHA256。
- 状态机 `workspace/evolution_state.json`：`rounds_passed=[1..10]`、`layers_passed=[L01..L10]`、`overall_status=ALL_GREEN`。
- 一键复验：`python run_tests.py`（含第二轨）与 `python auto_evolve_runner.py --run-all`。

---

## 七、物理工件清单

```
workspace/
├── evolution_state.json          # 10/10 打卡状态机（ALL_GREEN）
├── telemetry.jsonl               # TraceID/SpanID/SHA256 全链路遥测（append-only）
├── session_state.json            # L09 演示会话（消歧 + 快照回滚）
├── state/session_state.json      # 主链路会话记忆（r18-main）
├── rounds/
│   ├── round_01..10_gate.json    # 每轮五步闭环 + 工件 SHA256 + 回归数字
│   ├── L01_probe.json            # L01 引擎健康探针
│   ├── L02_dag.json / .md        # L02 五阶段 DAG
│   ├── L03_heal.json             # L03 自愈包络
│   ├── L04_spec.json             # L04 账本解析
│   ├── L05_slop.json             # L05 套话审计
│   ├── L06_scenarios.json / .md  # L06 三维矩阵
│   ├── L07_bundle.json           # L07 导出清单 + 自校验
│   ├── L08_patch.json            # L08 RFC6902 补丁 + 影响面
│   ├── L09_session.json          # L09 消歧/回滚证据
│   ├── L10_telemetry.json        # L10 熔断/重试/超时探针
│   └── SOP_round_2_benchmark.json# 第 2 轮标杆对齐证据（16 条 sources）
├── bundles/                      # dataeng_bundle / audit.sarif / chart.vega / lineage.ast
└── spec_exports/                 # dataeng_spec.json / dataeng_gates.sql / dbt_schema.yml
```

---

## 八、独立审计发现 → 修复闭环（workflow 三轮）

三轮 workflow 的体检 agent 均给出 `CONFIRMED`，并额外发现 6 个真实缺陷，已全部修复：

1. **L03 工件不自证**：`--out` 只写扁平工件，`healed/reflections` 只存在 stdout → 落盘并入自愈元数据。
2. **L05 伪造实测值**（最严重）：旧模板把「整体良好」替换成凭空生成的 `PSR=99.6% / 95% CI [0.6,3.0]` → 重写为**只重述不造数**（目标值/待实测清单/DRI/截止期），实测数字只能由调用方传入。
3. **RL-03 正则漏网**：`环比/同比/置信区间/CI` 未纳入统计越界红线 → 已补入。
4. **L04 账本被影子覆盖**：`skills` 仍只读 `thresholds.json`，改文档不改变判定 → `load_thresholds()` 改为账本优先并写 `_spec_source` 标记。
5. **L06 上下文恒空 / 不落盘 / 无 ROI**：`generate({})` → 按 DAG 的 SLA 与强一致意图生成上下文；矩阵落盘；新增 `roi_ratio`。
6. **L07~L10 未接主链路 + `review.py` fail-open**：见第五节，已接入并改为 fail-closed；`microsoft/sarif-tools` 仅 160★ 也已在 docstring 纠正。

---

## 九、残余风险（如实披露，不粉饰）

1. **意图路由仍是关键词匹配**：`agent.py _route` 未替换，L02 DAG 是并行附加产物；错路由风险仍在（正确做法是让 DAG 反推技能，属下一轮候选）。
2. **L07 的 8 维门禁是整体判真/假**：当前由任务总体 `ok` 统一映射，尚未做到逐门禁真实判定（需 harness 逐维结果回填）。
3. **L08 未在 `run_task` 自动生成补丁**：避免误伤历史产物，目前通过 `agent.py patch` 与 runner 使用。
4. **L09 为 agent 级单会话**（`r18-main`），非多人类会话隔离；消歧只覆盖已登记句式。
5. **`telemetry.jsonl` 无轮转**：长期运行需加 rotate/归档；DuckDB 缺失时回退 SQLite，SQL 方言覆盖变窄。
6. **外部连接器仍为 blocked**：本角色设计上不真连库、不真跑 dbt、不真回填（红线不变）。
7. **回归耗时**：每轮重跑 133 + 75 项，全量 10 轮约分钟级；CI 中建议按批次并行或缓存。

---

## 十、复现命令

```bash
cd "D:/蛙蛙呱呱/蛙蛙呱呱agents团/r18-washucang-dataeng"

python run_tests.py                     # 双轨验收：133 基准 + 75 演进，期望 ALL GREEN
python auto_evolve_runner.py --status   # 10/10 ALL_GREEN 看板
python auto_evolve_runner.py --stage 1  # L01~L03
python auto_evolve_runner.py --stage 2  # L04~L06
python auto_evolve_runner.py --stage 3  # L07~L10
python auto_evolve_runner.py --run-all  # 全量 10 轮
python agent.py evolve --status         # 等价入口
python agent.py patch --base a.json --patch p.json --out r.json   # L08 局部热修
```

---

*报告生成：2026-11-10 · 全部数字取自真实命令输出与落盘工件，可逐项复验。*
