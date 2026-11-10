# R07 蛙得明 · 产品经理（PM）三轮自升级终验报告

**Agent**：`r07-wademing-pm`（蛙得明 · 产品经理）  
**执行标准**：《SOP_AGENT_EVOLUTION_UNIVERSAL.md v13.0》十维演进元模型 · 五步闭环  
**执行方式**：`workflow` 三轮编排（每轮 = 一次完整 SOP：体检 → 对标 → 跃迁 → 物理工件 → 双轨回归）+ `auto_evolve_runner.py` 十轮状态机  
**完成时间**：2026-11-10 19:40–20:04（Asia/Shanghai）  
**最终结论**：**三轮 3/3 PASS，十轮状态机 10/10 PASSED，双轨零破坏回归全绿**

| 门禁 | 结果 |
| :--- | :--- |
| 历史契约定点验收 `python run_tests.py` | **56 / 56 PASS**（升级前为 33 / 55，红） |
| 演进集成测试 `python -m pytest tests -q` | **56 passed**（升级前 25 passed，且不含 L07–L10） |
| 29 动作 × 干净/脏 闭环矩阵 `python verify_loop.py` | **58 / 58 PASS**（29 干净 ok=True + 29 脏 ok=False/exit 1） |
| 十轮状态机 `python auto_evolve_runner.py --status` | **Round 10 / 10，completed_rounds=[1..10]** |
| 独立审计（workflow 3 个审计 Agent） | 首轮 3/3 PASS（报 5 项 MAJOR）→ 修复 → **复检 3/3 RECHECK PASS** |

---

## 一、三轮的定义与编排方式

| 轮次 | 主题 | 覆盖阶梯 | 物理工件 |
| :--- | :--- | :--- | :--- |
| **第 1 轮** | 执行基石还原 + 伴生消费 | L01–L06 真实性还原、L07 | `workspace/bundles/` 5 件（bundle/AST/SARIF/Vega/manifest） |
| **第 2 轮** | 增量热修 + 会话记忆 | L08、L09 | `workspace/patched/` 2 件、`workspace/session_state.json` |
| **第 3 轮** | 工业容灾 + 十轮终验 | L10 | `workspace/telemetry.jsonl`、`workspace/evolution_state.json` |

编排：`workflow` 三次 phase 串行，每轮由一个独立子 Agent（R04 挑刺视角）执行「跑状态机 → 跑三门禁 → 抽查工件 → 代码真实性抽检 → 写审计 JSON」，源码由主 Agent 实施；审计结论落盘为 `workspace/evolution_round{1,2,3}_audit.json`。执行器每轮强制执行五步，任一步失败即熔断且**不写状态机**。

---

## 二、第 1 轮：执行基石还原 + L07 伴生消费

### 2.1 穿透体检：真实病灶（不是套模板）

审计发现 R07 的「产品技能层」是被掏空的假实现，十维元模型的 L01「真实手脚」根本不存在：

| # | 病灶 | 证据（升级前） |
| :--- | :--- | :--- |
| 1 | RICE 回填固定分 | `skills/s04_priority.py`：`_rice()` 直接 `res["ranked"] = [{"score": 28.0}]`；`ice = _rice`（ICE 是 RICE 的别名） |
| 2 | PRD 八门禁键名与真实 PRD 不符 | `s03_prd.py` 查 `problem/stories/rules/out_of_scope/assumptions`，而 `examples/prd.json` 用 `problem_statement/users/scope/risks/acceptance_criteria` → 干净样例 passed=1/8 |
| 3 | 多条门禁恒真 | `s02_ost.poc/assumption/research`、`s05_roadmap.releasenotes`、`s06_metrics.metrics/vision/canvas`、`s07_techbrief.uibrief`、`s08_decision.decision/demand` 均 `make_result(True, ...)` |
| 4 | 判据结构被压扁 | `_common.make_result()` 把失败项统一成 `{"ok": False}`/`Passed`，harness 的 BLOCKER 分级与 SARIF 维度全部丢失 |
| 5 | 门禁口径分裂 | `rules/pm_thresholds.json` 仍要求 `stories/rules/out_of_scope` 旧键；`experience/thresholds.json` 用 `problem/user/value/...` 八门禁 |
| 6 | CLI/协作入口断裂 | `agent.py` 不支持 `prd story --kind`；`run_task()` 直接 `mod.run()`（技能模块没有 `run()`）→ `AttributeError`，协作闭环不可用 |
| 7 | 历史契约已红 | `run_tests.py` **33/55**：22 项失败（PRD 门禁、POC、Opportunity 5.6、backlog、premortem、虚荣指标、releasegate、run_task、闭环矩阵 9/58…） |
| 8 | 契约超集被破坏 | `run_tests.py` 硬编码 `len(cases.list_cases()) == 2`，而案例库已有 3 个（违反 SOP §5.10） |
| 9 | 演进执行器假打卡 | `EVOLUTION_STAGES[6..9]` 的 `verify_cmd` 是 `print('L07 Ready for Round 3')`；无 `--stage`、无工件验收、第 1/2 步恒为 `ok: True` |
| 10 | 状态机自相矛盾 | `evolution_state.json`：`current_round=2` 但 `completed_rounds=[1..6]`，round_history 重复记录 1/2 |
| 11 | 恒真死代码 | `skills/adapter.py`：`validate()→(True, [])`、`execute()→{"status": "mock_executed"}` |

### 2.2 标杆对齐（Stars > 1k）

| 阶梯 | 对标 | 吸收的机制 |
| :--- | :--- | :--- |
| L01 | Productboard / Airfocus / Jira Product Discovery | 八门禁维度模型、RICE 量纲与门禁分级 |
| L07 | microsoft/sarif-tools（OASIS SARIF 2.1.0）、vega/vega-lite v5 | 静态结果交换格式（规则表/结果/调用）、声明式图表契约 |
| 审计 | reviewdog / Vale | 可失败判据 + 逐维度 BLOCKER，而非叙述 |

### 2.3 架构跃迁（≥3 项）

1. **真实八门禁 PRD 引擎**：`skills/s03_prd.py` 重写为 8 gate（problem/user/value/scope/metric/acceptance/risk/read），输出 `gates[]`、`gate_ok{}`、`passed_gates`；Gherkin 验收、承重假设 ≥3、价值主张 before/how/after 均为可失败判据；阈值来自 `experience/thresholds.json`（SSOT）。
2. **确定性优先级算子**：RICE=(R×I×C)/max(E,E_min)、ICE=I×C×E、Opportunity 双量纲（0–1 用 `Imp×(1−Sat)`，10 分制用 `Imp+max(Imp−Sat,0)`）；Backlog 改为「依赖先行 + 同层分数降序」的 Kahn 贪心，循环依赖直接 BLOCKER。
3. **8 个技能模块 / 29 个动作全部还原为真实判据**：JTBD 三段式、访谈时间盒与 Mom Test、OST 四层与 POC 乘算打分、假设四象限、指标分层、OKR 3×3、技术翻译五模块、UI 五态、代码反推、发布门禁、需求卡/经验卡；每条 `check(ok,msg,dim,sev)` 结构化，失败即 BLOCKER。
4. **L07 伴生消费引擎** `engines/asset_bundle.py`：
   - `PRDASTBuilder` → `prd_ast.json`（schema `pm.prd.ast/v1`，8 个 GATE 节点带状态与证据，含 `ast_sha256`）；
   - `SARIFReporter` → `prd_audit.sarif.json`（SARIF **2.1.0**，规则 PM000–PM008 全声明，`ruleIndex` 与声明序一致，仅逻辑定位、**不伪造源码行号**）；
   - `VegaChartBuilder` → `prd_gates_chart.vega.json`（vega-lite v5 门禁柱状图）；
   - `prd_bundle.json` + `artifact_manifest.json`（内容寻址，`artifacts[]` 只登记子工件，杜绝自指哈希悖论）。
5. **门禁感知的 CLI**：`agent.py evolve bundle` 在门禁未过时 `rc=1`（工件仍落盘取证），审计员实测 `examples/prd_dirty.json → rc=1`、干净 PRD `rc=0`。
6. **执行器真实化**：步骤 1 校验引擎源码存在与非空壳（行数/探针声明），步骤 2 校验源码内显式引用对标项目（`bench_tokens` 全命中），步骤 4 校验工件存在 + 本轮新生成（mtime），步骤 5 三门禁；新增 `--stage 1|2|3` 批次、前置轮次校验（`--force` 才允许越级）、状态机历史去重与自愈。

### 2.4 物理工件（第 1 轮）

| 工件 | 字节 | 校验点 |
| :--- | ---: | :--- |
| `workspace/bundles/prd_ast.json` | 5,703 | 8 gate 全 PASS，`schema=pm.prd.ast/v1` |
| `workspace/bundles/prd_audit.sarif.json` | 2,806 | `version=2.1.0`，9 条规则声明，干净输入 `results=[]` |
| `workspace/bundles/prd_gates_chart.vega.json` | 1,610 | vega-lite v5，8 条 mark 数据 |
| `workspace/bundles/prd_bundle.json` | 1,596 | 8/8 门禁、20 checks 0 失败、`sarif_results=0` |
| `workspace/bundles/artifact_manifest.json` | 1,140 | 4 条 SHA256 逐件可重算 |

### 2.5 双轨回归（第 1 轮）

```
run_tests.py    : 56 / 56 通过（升级前 33 / 55）
pytest tests/   : 56 passed（升级前 25）
verify_loop.py  : total=58 passed=58 failed=0
```

---

## 三、第 2 轮：L08 局部差量 + L09 会话记忆

### 3.1 体检

- 改一条验收标准就要全量重生成 PRD，已评审通过字段被冲掉，无法回答「只改了什么」；
- 多轮需求对话里「按刚才第二套方案」「把它加上移动端适配」无法消歧，跨进程重启即失忆，且**越界序数/无指代时静默放行**（首轮审计实测）。

### 3.2 对标

RFC 6902（JSON Patch）/ RFC 6901（JSON Pointer）、google/diff-match-patch；MemGPT(Letta) / LangGraph State Store / ConversationBufferMemory。

### 3.3 架构跃迁

1. **`engines/diff_patch_engine.py`（L08）**
   - `JSONPointer` 完整解析（`~0`/`~1` 转义、数组下标、`-` 追加）；
   - 严格实现 **add / remove / replace / move / copy / test** 六算子，`test` 失败抛 `PatchTestFailed` 并强制阻断（不带病落盘）；
   - `diff()` 递归生成最小差量，`apply(diff(a,b), a) == b` roundtrip 可验证；
   - **字段级零漂移证明**：逐叶子比对，未被算子覆盖的改动计入 `untouched_drift`（修复前只做计数推断）；
   - 导出 `prd_patched.json` + `prd_patch.diff.json`（`schema=pm.prd.patch/v1`、前后 SHA256、`gate_after_patch` 复检）。
2. **`engines/session_memory.py`（L09）**
   - 持久化记忆池（`workspace/session_state.json`），槽位与顶层实体字段**双向同步**；原子写（同目录临时文件 + 跨盘回退）、TTL 文件锁；
   - 指代/序数消歧：第 N 套方案（一~九十九 / 0~999，越界与 0 → `unresolved` + `needs_clarification`）、刚才/上次回溯、它/这个/该方案、渠道切换、追加特性（无挂载目标也必须澄清）；
   - 快照树（版本单调、父子链）+ 一键回滚；**对话历史 append-only**，回滚只追加 system 标记并真实递增 `turn`；
   - 8 步确定性自检（双向同步 / 序数 / 渠道 / 快照链 / 代词 / 回滚 / 落盘 / 跨进程重载）。
3. **CLI 与夹具**：`agent.py evolve patch|session`；`examples/prd_patch_ops.json`（4 个 RFC 6902 算子）。

### 3.4 物理工件（第 2 轮）

| 工件 | 字节 | 关键数据 |
| :--- | ---: | :--- |
| `workspace/patched/prd_patched.json` | 1,909 | 8/8 门禁；仅 `acceptance_criteria[0].then` 变化 |
| `workspace/patched/prd_patch.diff.json` | 2,197 | 4 算子全 ok；`common_leaves=29`、`changed_common_leaves=[/acceptance_criteria/0/then]`、`added=6`、`untouched_drift_count=0`、`untouched_ratio=0.9655`、`bytes_saved_ratio=0.6662` |
| `workspace/session_state.json` | 2,564 | `turn=4`、interactions 轮次 [1,2,3,4]（用户轮全保留）、快照 v1(parent 0)/v2(parent 1) |

### 3.5 双轨回归（第 2 轮）

三门禁全绿（56 passed / 56-56 / 58-58）。

---

## 四、第 3 轮：L10 工业容灾 + 十轮终验

### 4.1 体检

外部依赖抖动/超时直接瘫痪：无三态熔断、无退避重试、无进程级超时隔离、无全链路遥测，故障只能人肉复现。

### 4.2 对标

temporalio/temporal、open-telemetry/opentelemetry-python、jd/tenacity（指数退避 + Full Jitter）。

### 4.3 架构跃迁

1. **`CircuitBreaker`**：CLOSED/OPEN/HALF_OPEN 三态，失败阈值 → OPEN、冷却 → HALF_OPEN、半开成功 → CLOSED、半开失败 → OPEN，全程落 `transitions`（可注入时钟，确定性可测）。
2. **`retry_with_backoff`**：`delay_i = U(0, min(max, base·2^(i-1)))`，`jitter=False` 时精确退化为 2 的幂（审计独立复算：ceiling 0.04/0.08/0.16/0.2）。
3. **`Watchdog`**：线程软超时 + **子进程级硬隔离** `run_isolated`（`subprocess.run(timeout=...)`，5s 任务 0.41s 返回 `killed=True`，主进程不受污染）。
4. **`TelemetryTracer`**：JSONL 全链路（TraceID 32 hex / SpanID 16 hex / ParentSpanID / SHA256 / 耗时 / 状态），随机盐保证 ID 唯一；**payload 只落 SHA256**，`attributes` 按元数据白名单脱敏、`error` 只落类名+指纹；`verify_chain` 校验键完整性、父引用悬空、跨 trace 引用、重复 span（append-only，不擦历史）。
5. **执行器遥测同源**：runner 在步骤 5 之后写入真实门禁 span，父 span 状态与子 gate 状态同源（失败时父 span 也写 `ERROR`，修复前父 span 恒 OK）。

### 4.4 物理工件（第 3 轮）

| 工件 | 值 |
| :--- | :--- |
| `workspace/telemetry.jsonl` | append-only，34 行，含本轮 4+5 条 span，全部 `sha256` 64 位、父引用可解析 |
| `workspace/evolution_state.json` | `current_round=10`、`completed_rounds=[1..10]`、10 条 round_history 唯一且全 PASSED |

### 4.5 十轮状态机终验

```
Round 01 [L01] ✅  Round 02 [L02] ✅  Round 03 [L03] ✅  Round 04 [L04] ✅  Round 05 [L05] ✅
Round 06 [L06] ✅  Round 07 [L07] ✅  Round 08 [L08] ✅  Round 09 [L09] ✅  Round 10 [L10] ✅
批次 1 执行基石 3/3 ｜ 批次 2 专业深度 3/3 ｜ 批次 3 工业交付 4/4
```

每轮均记录：`pytest_summary`（第 7–10 轮为 `56 passed`）、`legacy_summary`（`全绿 · R07 端到端验收通过`）、`artifacts[]`。

---

## 五、独立审计与修复闭环（workflow 3 Agent）

首轮审计（`workflow r07-three-round-sop-evolution`，3 个独立审计 Agent）判 3/3 PASS，但报出 MAJOR 共 11 项（第 1 轮 5 项、第 2 轮 5 项、第 3 轮 1 项，去重后 8 类根因）与若干 MINOR。全部修复后复检（`workflow r07-three-round-sop-recheck`）为 **3/3 RECHECK PASS**。

| # | 审计发现（严重度） | 修复 | 复检证据 |
| :---: | :--- | :--- | :--- |
| 1 | `prd_bundle.json` 自指哈希陈旧，下游第 4 件校验必失败（MAJOR） | bundle 只登记 3 件子工件，新增 `artifact_manifest.json` 写盘后计算 bundle 哈希 | manifest 4 件 SHA256/bytes 逐件按磁盘重算命中 |
| 2 | `AssetBundleExporter.export()` 恒返回 `ok=True`，脏 PRD 仍 rc=0（MAJOR） | `ok=gate_ok`，新增 `exported` 标识；CLI 以 `ok` 决定退出码 | 脏 PRD `rc=1`、`gate_ok=false`；干净 PRD `rc=0` |
| 3 | 失败项引用未声明规则 PM999、`ruleIndex` 错位（MAJOR） | 汇总规则独立为 PM000，`ruleIndex` 取自声明表 | 14 条 dirty findings 全部命中 PM000–PM008，索引一致 |
| 4 | SARIF 伪造源码行号（8 行文件出现 startLine=20）（MAJOR） | 删除 `region`，只保留 artifactLocation + logicalLocations | 0 条含 region，全部 `prd.gate.<dim>` 逻辑定位 |
| 5 | runner 步骤 1/2 恒 `ok=True`（MAJOR） | 真实校验引擎源码行数/存在性 + 源码内标杆 token（负控实测 FAIL） | 步骤 1/2 各 5 组负控返回 False |
| 6 | L08 `patch_and_export()` 恒 `ok=True`（MAJOR） | `ok` 与 `gate_after_patch.ok` 绑定 | 删 `north_star`+`given` 后 `gate_ok=false`、rc=1 |
| 7 | L09 第 7/11/0 套方案静默放行（MAJOR/MINOR） | 序数正则扩到 0~999 与一~九十九，越界/0 → `unresolved`+`needs_clarification` | 第 7 套 → unresolved、rc=1；第 11/0 套同样阻断 |
| 8 | 回滚抹掉用户轮次、`turn` 不递增（MINOR） | 快照只固化 slots/entities，interactions append-only，回滚递增 turn | 两次回滚后 interactions=[1..5]，用户轮全保留 |
| 9 | 遥测 `gate.regression` 写死 `legacy/evolution=pass`（MAJOR） | 状态由真实 rc 推导，父 span 与子 gate 同源 | 注入 `regression.ok=False` → gate ERROR、父 span ERROR |
| 10 | trace/span id 可由 seq 预测（MINOR） | 混入进程级随机盐 | 两个 tracer 同 seq 产生不同 trace_id |
| 11 | `verify_chain` 不校验父引用/重复 span（MINOR） | 悬空父、跨 trace 父、重复 span 全部纳入 `ok` | 构造脏文件实测三项均被识别 |
| 12 | `attributes`/`error` 可明文泄漏（MINOR） | 元数据白名单 + 其余值 SHA256；error 只落类名+指纹 | marker 三通道（payload/attributes/error）均不泄漏 |
| 13 | 遥测每次探针被 truncate，历史不可审计（MINOR） | 改 append-only，自检只校验最近 4 条窗口 | 34 行历史保留，最近窗口自洽 |
| 14 | S06 北极星七判据 zip 错位、阈值外置失效（MINOR） | 判据与名称显式绑定，并读取 `metrics.nsm_criteria` | 单点失败维度与 `nsm_criteria` 严格互补 |
| 15 | 步骤 1/2 与 CLI rc 无回归测试（MINOR） | 新增 `tests/test_runner_gates.py`（9 项） | pytest 由 47 → 56 passed |
| 16 | `skills/adapter.py` 恒真存根（MINOR） | 删除（全仓无引用） | grep 无 adapter 引用 |
| 17 | 案例库硬编码 `== 2` 违反超集契约（历史红） | 改为 `>= 2` + 存在性校验 | run_tests 56/56 |
| 18 | `rules/pm_thresholds.json` 与 SSOT 口径分裂 | 对齐八门禁 ID，标注 `_superseded_by` | 全仓无旧键引用 |

---

## 六、残留风险与边界（不粉饰）

1. **步骤 2 的对标校验是源码文本级**（token 命中），理论上注释即可满足，尚未做 AST/符号级校验；
2. **步骤 1 的「非空壳」是行数启发式**（≥50 非空行），无法拦截「50 行样板 + 空实现」；
3. **SARIF 不含源码行号**：R07 不解析 PRD 源文件，仅给逻辑定位（`logicalLocations`），行号映射应由消费方按 `artifactLocation` 完成；
4. **遥测脱敏是键白名单**：非白名单键的字符串值一律落指纹，可能牺牲部分诊断可读性；
5. **会话锁是 TTL 咨询锁**（非 `O_EXCL` 抢占），并发写者仍可能同时 `save()`；
6. **L09 的 round-9 工件是自检夹具**：`--self-test` 会 `reset()` 后覆盖 `session_state.json`，用于证明能力而非累积真实会话；
7. **状态机仍允许 `--force` 定点重跑**（默认有前置轮次校验），该开关是修复手段而非日常路径；
8. 本轮修复以「命令级/工件级/字段级」证据为准，未做跨机器/跨 Python 版本的矩阵回归（仅 Win + Python 3.12 实测）。

---

## 七、交付件清单

| 类别 | 路径 | 说明 |
| :--- | :--- | :--- |
| 技能层 | `skills/s01_discover.py` … `s08_decision.py`、`skills/_common.py` | 8 模块 / 29 动作真实判据 |
| 引擎 | `engines/asset_bundle.py` | L07 AST/SARIF/Vega/Bundle/Manifest |
| 引擎 | `engines/diff_patch_engine.py` | L08 RFC 6902 六算子 + 零漂移证明 |
| 引擎 | `engines/session_memory.py` | L09 记忆池/消歧/快照/回滚 |
| 引擎 | `engines/telemetry_watchdog.py` | L10 三态熔断/退避/隔离/遥测 |
| 执行器 | `auto_evolve_runner.py` | 五步闭环 + `--stage` + 真实步骤 1/2/4 + 前置校验 |
| 入口 | `agent.py` | `evolve bundle/patch/session/watchdog`，门禁感知退出码 |
| 测试 | `tests/test_evolution_l01_l10.py`、`tests/test_runner_gates.py`、`tests/test_contracts.py` | 56 passed |
| 状态 | `workspace/evolution_state.json` | 10/10 PASSED |
| 工件 | `workspace/bundles/*`、`workspace/patched/*`、`workspace/session_state.json`、`workspace/telemetry.jsonl` | 见各轮工件表 |
| 审计 | `workspace/evolution_round1_audit.json`、`round2`、`round3` | 独立审计原始结论 |

---

## 八、复现命令

```powershell
cd 'D:\蛙蛙呱呱\蛙蛙呱呱agents团\r07-wademing-pm'
$env:PYTHONIOENCODING='utf-8'

python auto_evolve_runner.py --status        # 10/10 看板
python auto_evolve_runner.py --stage 3       # 仅跑批次 3（L07–L10）
python auto_evolve_runner.py --run-all       # 连续推进未完成轮次

python -m pytest tests -q                    # 演进集成测试
python run_tests.py                          # 历史契约端到端
python verify_loop.py                        # 29 动作 × 干净/脏 闭环矩阵

python agent.py evolve bundle  --input examples/prd.json --out-dir workspace/bundles
python agent.py evolve patch   --input examples/prd.json --ops examples/prd_patch_ops.json --out-dir workspace/patched
python agent.py evolve session --self-test
python agent.py evolve watchdog --self-test
```

> 结论：R07 已从「Markdown + 硬编码假判据」升级为「真实门禁 + 机器可消费工件 + 增量热修 + 跨轮记忆 + 工业容灾」的可审计实体，十轮演进 10/10 通过；剩余风险均已在第六节显式披露，不构成「升级成功」之外的隐性债务。
