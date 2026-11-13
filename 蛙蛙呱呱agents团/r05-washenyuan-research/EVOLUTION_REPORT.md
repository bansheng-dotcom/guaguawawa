# R05 蛙深远（战略研究官）三轮渐进式自升级报告

> **演进角色**：R05 蛙深远 · 战略研究官（`r05-washenyuan-research`）
> **指导规范**：`SOP_AGENT_EVOLUTION_UNIVERSAL.md` v13.0（十维演进元模型 / Audit-First / 双轨零破坏）
> **执行方式**：Workflow 外循环编排 + `auto_evolve_runner.py` 状态机；**一次完整 SOP 五步闭环 = 一轮**，共执行 **3 轮**
> **执行日期**：2026-11-10（Asia/Shanghai）
> **终验结论**：✅ **3/3 轮 PASS ｜ 10/10 阶梯 PASS ｜ 双轨回归全绿（63 + 10 + 40 + 62）｜ 对抗性复核 34/34 PASS**

---

## 一、执行模型：为什么是“三轮”，每轮如何算完成

SOP 的四-节给出“十维演进三轮批次”推荐划分；本次按用户口径将**一次完整 SOP 执行计为一轮**，因此：

| 轮次 | SOP 阶段 | 覆盖阶梯 | 本轮必须完成的五步 |
| :---: | :--- | :--- | :--- |
| **Round 1** | 执行基石 | L01 工具实体 / L02 意图解构 / L03 自愈反思 | 体检 → 对标 → 架构跃迁 → 物理工件验收 → 双轨零破坏回归 |
| **Round 2** | 专业深度 | L04 领域账本 / L05 质感去劣化 / L06 横向决策 | 同上（每轮独立打卡，失败即熔断，禁止带病进入下一轮） |
| **Round 3** | 工业交付 | L07 伴生消费 / L08 局部差量 / L09 会话记忆 / L10 工业容灾 | 同上 + 10/10 阶梯下钻复核 |

**自动化载体**：`auto_evolve_runner.py`

```powershell
python auto_evolve_runner.py --status          # 三轮 / 十层看板
python auto_evolve_runner.py --round 1|2|3     # 执行一轮完整 SOP（等价 --stage 1|2|3）
python auto_evolve_runner.py --layer L01..L10  # 单层下钻体检打卡
python auto_evolve_runner.py --run-all         # 顺序推进三轮，任一轮失败即阻断
python auto_evolve_runner.py --reset           # 重置状态机
```

状态机逐轮落盘 `workspace/evolution_state.json`，每轮独立生成：
- `workspace/rounds/roundN_journal.json`（五步原始证据：体检、对标、探针、工件、回归）
- `artifacts/evolve/roundN/`（物理工件 + `round_artifact_manifest.json` 含逐文件 SHA256）

---

## 二、十维演进总览：先体检真实断点，再对标落地（拒绝模板八股）

| 阶梯 | 升级前真实断点（穿透体检结论） | Stars > 1k 对标标杆 | 本轮落地物理架构 |
| :---: | :--- | :--- | :--- |
| **L01 工具实体** | 原 `engines/manager.py` 只有 `calc_hhi` / `verify_tam_variance` 两个算子；证据分级、单位经济、敏感性、双口径三角测量散落 `skills/`，无独立确定性沙箱与算子探针 | OpenBB 28k⭐（provider 注册表 + 逐源探针）、Celery 25k⭐（算子执行契约） | `engines/runtime_engine.py`：`ResearchRuntimeEngine` 六算子 + `EvidenceTierValidator` |
| **L02 意图解构** | 原 `engines/prompter.py` 只按关键词命中顺序串链，`depends_on` 是伪造的 `S{i-1}`；无 Kahn 拓扑、无环检测、无五阶段研究标准与工时预算 | DSPy 19k⭐（签名→声明式计算图）、Ray 34k⭐（DAG 编排） | `engines/intent_compiler.py`：审计→寻源→分析→验证→交付五阶段 Kahn DAG + 实体抽取 + 工时/人天 |
| **L03 自愈反思** | 原 `engines/critic.py` 只改顶层字符串；嵌套 `sections/list` 内拍板用语无法自愈；越权代付款不阻断、无跨角色移交、自愈后不复检 | Reflexion 5.8k⭐（反思-自愈-复检）、OpenHands 40k⭐（Guardrail + handoff） | `engines/reflexive_healer.py`：递归深层自愈 + 3 轮复检 + `RedlineBlocked`（R01/R03 移交） |
| **L04 领域账本** | `RESEARCH_SPEC.md` 是纯散文；`engines/ledger.py` 把 HHI/方差/证据等级阈值硬编码，改文档不影响运行；无 8 维发布门禁与快照 | dbt-core 9.5k⭐（语义层 SSOT）、Great Expectations 9.8k⭐（声明式期望套件） | `RESEARCH_SPEC.md` v2.0.0 机器可读 SSOT + `engines/spec_ledger.py`（动态解析 / 8 维加权门禁 / 快照导出） |
| **L05 质感去劣化** | 原 `slop_guard.py` 仅 5 条正则、按次扣 10 分的粗评分；无证据密度/行动力/等级，无法阻断“相关细节待定”和无 DRI 报告 | Vale 4.5k⭐（词库 Lint）、reviewdog 7.5k⭐（门禁分级） | `engines/slop_guard.py` v2：31 条词库 + 证据密度/行动力/A-D 分级 + 占位与无证据阻断 + DRI 强制注入 |
| **L06 横向决策** | 原 `scenario_matrix.py` 三档份额/毛利率全部写死；无 MCDA 权重、无 ROI 矩阵与排序推荐 | Scenario Planning / MCDA、Superset 62k⭐（多维决策看板）、Vega-Lite 4.6k⭐ | `engines/scenario_matrix.py` v2：四维权重（和=1）+ ROI/LTV-CAC/回收期 + 排序推荐 + ROI 看板 |
| **L07 伴生消费** | 原 `asset_bundle.py` 只导出 `research_spec.json` 与图表描述；无 SARIF 审计结果、无 SHA256 清单与篡改校验 | microsoft/sarif-tools 1.2k⭐、OASIS SARIF 2.1.0 标准 | `engines/asset_bundle.py` v2：SARIF 2.1.0 五规则 + `bundle.json` 资产清单 + `verify_bundle()` |
| **L08 局部差量** | 原 `patch_editor.py` 仅 replace/add/remove；JSON Pointer `~0/~1` 未转义；无 `test/copy/move`、无 `create_patch`、无改前改后摘要 | RFC 6902、evanphx/json-patch 2.5k⭐、diff-match-patch 7k⭐ | `engines/diff_patch_engine.py`：RFC 6902 六算子 + 指针转义 + 差量反推 + 完整性摘要 |
| **L09 会话记忆** | 原 `memory.py` 的 `rollback` 只弹两个列表、不恢复业务状态；无 `update_slot`；槽位不落顶层字段；“第二套方案”无法消歧 | MemGPT 14k⭐（分层记忆池）、LangGraph 11k⭐（checkpoint） | `engines/session_memory.py`：槽位双向同步 + 中文序号/代词消歧 + 快照真实回滚 + 持久化 |
| **L10 工业容灾** | 原 `telemetry.py` 在函数返回后才比对耗时（无法真中断）；无三态熔断、无 half-open 试探、退避无抖动、无 Trace/Span 父子上下文 | Temporal 14k⭐、Tenacity 6.5k⭐、OpenTelemetry 2.1k⭐ | `engines/telemetry_watchdog.py`：CLOSED/OPEN/HALF_OPEN + 真超时看门狗 + 全抖动退避 + Trace/Span JSONL |

---

## 三、Round 1：执行基石阶段（L01~L03）—— PASS

### 3.1 体检（实扫 `engines/manager.py`、`prompter.py`、`critic.py` 行数与 SHA256 后判定）

- **L01**：只有 2 个算子，研究精算能力无法被 CLI/下游确定性复用；`probe` 只验证 `math.sqrt`，不反映真实算子清单。
- **L02**：`compile_intent` 输出单链 DAG，`depends_on` 为装饰字段；无拓扑排序、无环检测、无五阶段标准与工时。
- **L03**：`heal_payload` 只遍历顶层字符串；嵌套结构、跨角色越权、自愈后复检全部缺失（SOP 五-13 红线）。

### 3.2 架构跃迁（6 项，SOP 最低 3 项）

1. `ResearchRuntimeEngine`：`calc_hhi / verify_tam_variance / evidence_chain / unit_economics / sensitivity_swing / tam_triangulate` 六算子，全部纯标准库真实计算、非法输入 fail-closed；
2. `EvidenceTierValidator`：Tier0 拦截、孤立断言、置信度不足、覆盖率与 `gate_ok`；
3. `ResearchIntentCompiler`：五阶段 DAG + **真实 Kahn 拓扑排序** + 自环/互环 `DagCycleError`；
4. 实体抽取（金额/币种/比例/地域/市场）+ 复杂度判定 + 工时与人天预算（不同诉求得到不同预算，实测 75.65h vs 45.8h）；
5. `ReflexiveResearchHealer`：递归自愈份额/来源/拍板词，最多 3 轮复检，幂等；
6. `RedlineBlocked`：越权拍板 → R01、越权代付款 → R03，`[REDLINE BLOCKED]` 阻断并写入 `handoff`。

### 3.3 物理工件与门禁

| 工件 | 大小 | SHA256（前 16） |
| :--- | ---: | :--- |
| `artifacts/evolve/round1/l01_runtime_probe.json` | 3,453 B | `8491d96d8568ce30` |
| `artifacts/evolve/round1/l02_intent_dag.json` | 3,282 B | `c72d40998c2ed881` |
| `artifacts/evolve/round1/l03_reflexive_heal.json` | 2,878 B | `cd9d282c96489eba` |
| `artifacts/evolve/round1/l03_redline_block.json` | 334 B | `20043f6c98a61dca` |

- CLI 实跑：`agent.py evolution probe`（rc=0）、`agent.py evolution ledger`（rc=0）；
- 五步探针 8/8 PASS（六算子、探针、Tier0 拦截、证据门禁、五阶段 Kahn、工时、R03 移交、深层自愈复检）；
- **双轨回归**：原基准 **63/63**、L01~L10 演进套件 **10/10**、本轮契约 **13/13**、全量 pytest **35/35**；耗时 19.42s。

---

## 四、Round 2：专业深度阶段（L04~L06）—— PASS

### 4.1 体检

- `RESEARCH_SPEC.md` 无机器可读块；`ledger.py` 阈值写死 → 文档与运行口径脱钩，多轮/多 Agent 必然漂移；
- `slop_guard.py` 仅 5 条规则、无证据/行动力/等级，无法阻断占位套话与无 DRI；
- `scenario_matrix.py` 三档份额/毛利率硬编码，无 MCDA 与 ROI，人类拿不到可权衡看板。

### 4.2 架构跃迁（4 项）

1. `RESEARCH_SPEC.md` **v2.0.0**：内置 JSON 机器可读 SSOT（版本 / TAM 方差 / HHI 区间 / 四级证据置信度 / 北极星 / **8 维门禁权重**），改文档即改全链路口径；
2. `ResearchSpecLedger`：正则抽取 SSOT、**非硬编码**（覆盖文件实测解析出 `9.9.9` / `0.18` / `2400`）、`evaluate()` 加权评分、`export_json()` 快照；
3. `ResearchSlopGuard` v2：31 条词库 + 证据密度 / 行动力 / A-D 分级 + `enforce_quality()`（`PENDING_PLACEHOLDER` / `NO_QUANTIFIED_EVIDENCE` / `SLOP_HIGH` 阻断 + DRI 缺省注入“蛙深远”）；
4. `ScenarioMatrixExplorer` v2：`market_upside/margin/cost_risk/speed` 四维权重（和=1）+ 各情景 `score/roi/ltv_cac_ratio/payback_months` + `ranking` / `recommended` + ROI 权衡看板。ROI 采用**量纲一致**的营销回报口径（SOM→件数→获客投入），默认三情景为 191.26% / 177.78% / 160.87%；份额 15%→20% 时因 CAC 抬升 ROI 降至 150.0%，而 TAM 放大 8.3 倍 ROI 保持不变（不虚增）。

### 4.3 物理工件与门禁

| 工件 | 大小 | SHA256（前 16） |
| :--- | ---: | :--- |
| `artifacts/evolve/round2/l04_spec_snapshot.json` | 2,736 B | `d230a531379af7f9` |
| `artifacts/evolve/round2/l04_gate_evaluate.json` | 3,922 B | `6568261c5e7d274b` |
| `artifacts/evolve/round2/l05_slop_enforce.json` | 504 B | `8682d40c805f3296` |
| `artifacts/evolve/round2/l06_scenario_matrix.json` | 4,863 B | `99be7a5678b2726b` |
| `artifacts/evolve/round2/l06_scenario_board.md` | 2,134 B | `71983d38b834330d` |

- CLI 实跑：`agent.py evolution slopguard --polish`（rc=0）、`agent.py evolution explore --output ...`（rc=0）；
- 五步探针 7/7 PASS（SSOT 解析、8 门禁权重和=1、快照导出、质量三维、占位阻断+DRI、MCDA/ROI、排序）；
- **双轨回归**：63/63 + 10/10 + 本轮契约 **11/11** + 全量 pytest **46/46**（含 Round 1 契约零破坏）；耗时 19.04s。

---

## 五、Round 3：工业交付阶段（L07~L10）—— PASS

### 5.1 体检

- `asset_bundle.py` 无 SARIF、无资产清单/哈希，CI 无法回放发现、无法发现篡改；
- `patch_editor.py` 缺 `test/copy/move` 与指针转义，无差量反推与完整性摘要；
- `memory.py` 回滚不恢复状态、无槽位同步、数量代词失忆（违反 SOP 五-14）；
- `telemetry.py` 看门狗事后比对，无法真超时；无三态熔断/抖动/Trace。

### 5.2 架构跃迁（4 项）

1. `asset_bundle.py` v2：`research_result.sarif.json`（SARIF 2.1.0，`tool.driver.name=r05-washenyuan-research`，规则 `R05-EVIDENCE-GAP / R05-TAM-VARIANCE / R05-TIER0 / R05-SCENARIO-GAP / R05-HHI-MISSING`）+ `bundle.json`（逐文件 `sha256/bytes/media_type`）+ `verify_bundle()`（实测追加 1 字节即报 size/sha256 双 mismatch）；
2. `ResearchDiffPatchEngine`：RFC 6902 全算子（add/remove/replace/move/copy/test）、JSON Pointer `~1→/`、`~0→~`、数组 `-` 追加、`create_patch` 反推（含类型变更）、`apply_with_integrity()` 改前改后 SHA256；
3. `ResearchSessionStore`：槽位 ↔ 顶层字段双向同步、中文序号/数量代词（“第二套方案”“方案三”）、快照先存后改、`rollback()` 整体恢复业务字段、JSON 持久化；
4. `TelemetryWatchdog`：三态熔断（实测 OPEN→HALF_OPEN→CLOSED，half-open 试探失败重新 OPEN）、真超时（0.5s 任务 0.02s 超时立即抛 `TaskTimeout`）、指数退避上限封顶（`[1.0, 2.0, 2.0]`）、Trace/Span 父子链路 + `health()`。

### 5.3 物理工件与门禁

| 工件 | 大小 | SHA256（前 16） |
| :--- | ---: | :--- |
| `artifacts/evolve/round3/l07_bundle/research_spec.json` | 729 B | `73a241e8ee1d4255` |
| `artifacts/evolve/round3/l07_bundle/research_chart_spec.json` | 590 B | `eb3a916de5127b91` |
| `artifacts/evolve/round3/l07_bundle/research_result.sarif.json` | 4,511 B | `d5a959046e7ede93` |
| `artifacts/evolve/round3/l07_bundle/bundle.json` | 749 B | `1bab2da4c5719361` |
| `artifacts/evolve/round3/l08_patch_integrity.json` | 951 B | `c1c996e1744e1e1f` |
| `artifacts/evolve/round3/l09_session_evidence.json` | 2,422 B | `7eb5f204bcfdf911` |
| `artifacts/evolve/round3/l10_telemetry.jsonl` | 596 B | `ec9c740c7807b221` |
| `artifacts/evolve/round3/l10_health.json` | 121 B | `84d0e4253e6e907a` |

- CLI 实跑：`agent.py evolution bundle --output-dir ...`（rc=0）、`agent.py evolution telemetry`（rc=0）；
- 五步探针 6/6 PASS（SARIF+清单+verify、RFC6902 往返、槽位/序号/回滚、三态熔断、退避+真超时、Trace/health）；
- **双轨回归**：63/63 + 10/10 + 本轮契约 **16/16** + 全量 pytest **62/62**；耗时 17.71s。

---

## 六、双轨零破坏回归总账（终验实测）

| 轨道 | 命令 | 结果 |
| :--- | :--- | :--- |
| 原基准套件（严格超集守护） | `python run_tests.py` | **Ran 63 tests — OK**（rc=0，18.4s） |
| L01~L10 演进集成套件 | `python tests/test_evolution_suite.py` | **Ran 10 tests — OK**（rc=0） |
| Round 1 契约 | `pytest tests/test_round1_foundation.py -q` | **13 passed** |
| Round 2 契约 | `pytest tests/test_round2_depth.py -q` | **11 passed** |
| Round 3 契约 | `pytest tests/test_round3_industrial.py -q` | **16 passed** |
| 全量 pytest（旧 22 + 新 40） | `pytest tests -q` | **62 passed**（rc=0） |
| 三轮流水线 | `python auto_evolve_runner.py --run-all` | **3/3 PASS**（rc=0） |
| 十层下钻 | `--layer L01` … `--layer L10` | **10/10 LAYER PASS** |

> 说明：新增契约按“每轮只校验本轮及此前轮次”执行；后续轮次未实现前不得反向污染当前轮门禁，这既遵守 SOP“禁止跨轮伪造打卡”，也保证每轮是旧系统的严格超集。

---

## 七、独立对抗性复核（34 项，全部 PASS）

除契约测试外，用非契约输入的独立探针复核“是否真算、是否真拦、是否真恢复”：

- L01：单位经济换上 `200/0.5/0.01/1000` → LTV 10000、比率 10、回收期 10；敏感性三因子按摆动重排 `B→C→A`；双口径 400 vs 400000 判不收敛；
- L02：两条不同诉求得到不同工时（75.65h vs 45.8h）；自环/互环均抛 `DagCycleError`；Kahn 对无依赖节点保持稳定顺序；
- L03：干净工件 `clean=True`；嵌套列表内“代付款”仍触发 R03 移交并归一为 50/50；
- L04：自定义 spec（3.1.0 / 0.11 / 2 门禁）被动态解析；缺一项门禁时得分精确为 50.0；
- L05：无 DRI 报告自动注入“责任人 DRI：蛙深远”；干净量化文本 grade=A；4 处套话全部替换；
- L06：ROI 采用量纲一致的营销回报口径（默认三情景 191.26%/177.78%/160.87%，不再出现 4212% 的伪 ROI）；TAM 放大 8.3 倍 ROI 不变，份额 15%→20% 因 CAC 抬升降至 150.0%；排序严格降序；
- L07：追加 1 字节即被 `verify_bundle()` 同时以 size/sha256 双证据判定篡改；
- L08：数组中间插入/移动/复制/删除、类型变更、缺失路径删改均符合 RFC 6902 语义；
- L09：`方案三` → 索引 2；`rollback(2)` 后槽位被真实清除；重新载入会话 ID 一致；
- L10：阈值 3 时前两次不熔断、第三次 OPEN；half-open 试探失败重新 OPEN；退避封顶；嵌套 Span 父子 ID 一致。

---

## 八、状态机与可追溯性

`workspace/evolution_state.json`（终态）：

```json
{
  "status": "ALL_GREEN_10_OF_10",
  "rounds_completed": 3,
  "layers": {"L01": "PASS", "...": "PASS", "L10": "PASS"},
  "rounds": [
    {"round": 1, "tests": {"baseline_63": 63, "evolution_l01_l10": 10, "round_contract": 13, "full_pytest": 35}},
    {"round": 2, "tests": {"baseline_63": 63, "evolution_l01_l10": 10, "round_contract": 11, "full_pytest": 46}},
    {"round": 3, "tests": {"baseline_63": 63, "evolution_l01_l10": 10, "round_contract": 16, "full_pytest": 62}}
  ]
}
```

每轮 journal 保留五步原始证据（体检扫描清单与哈希、标杆清单、探针明细、CLI 返回码、四轨测试计数）；`round_artifact_manifest.json` 保留逐工件 SHA256，可直接复算。

---

## 九、SOP 工业级避坑对照

| SOP 条款 | 本角色的落实 |
| :--- | :--- |
| 五-1 运行时引导 | `agent.py` / `auto_evolve_runner.py` 顶部同时注入自身目录、agents 根、仓库根 |
| 五-2 Windows 编码 | runner 与子进程统一 `PYTHONIOENCODING=utf-8` + `reconfigure`，63 基准在 GBK 控制台零崩溃 |
| 五-3/4 临时文件隔离 | 所有测试与探针临时文件落在 `workspace/tmp`，不碰系统全局 temp |
| 五-7 `mkdtemp` 死循环 | 全链路不使用隐式系统临时目录；固定 `workspace/tmp` |
| 五-13 跨角色红线 | 越权代付款 → `[REDLINE BLOCKED]` + R03；越权拍板 → R01，均写 `handoff` |
| 五-14 槽位双向同步 | `update_slot()` 同时写 `slots[key]` 与顶层 `state[key]`，实测重载后一致 |
| 六-1 无体检不开工 | 每轮 `step1_audit.json` 记录真实文件行数/哈希与逐层断点 |
| 六-2 无标杆不开工 | 每轮 `step2_benchmark.json` 列出 Stars>1k 项目与被吸收机制 |
| 六-3 无物理工件不汇报 | 17 个验收工件 + 4 个 CLI bundle 文件落盘并计算 SHA256 |
| 六-4 回归失败不算成功 | 任一轮任一轨失败即熔断，不写 PASS 打卡 |
| 六-5 禁止单轮伪造十层 | 三轮独立执行、独立 journal、独立工件与状态机打卡 |
| 六-6 禁止破坏旧契约 | `run_tests.py` 63 项、旧 `critic/prompter/manager/patch_editor/memory/telemetry` 全部零改动 |

---

## 十、本轮额外工程修正（透明披露）

1. **门禁取数修正**：`unittest` 把 `Ran N tests` / `OK` 写入 `stderr`，原 runner 只读 `stdout` 会造成结构性假阴性；已改为合并 `stdout+stderr` 取数，阈值（63/10/8/32）未放宽。
2. **会话序号扩展**：独立复核发现“方案三”这类中文数字在 `方案N` 分支不命中，已把正则扩展到中文数字（契约不受影响，能力严格增强）。
3. **公开 CLI 扩展**：`agent.py evolution` 新增 `compile / heal2 / spec / diff / session / breaker` 六个子命令，让本轮新引擎可被人工与下游直接消费（旧 10 个子命令与退出码语义保留）。
4. **healer 反思措辞**：修正“不可自愈”与实际“替换措辞 + 登记移交”并存的矛盾表述，语义与行为一致。
5. **L06 ROI 量纲修正**：复核发现原公式 `(SOM×单价 − SOM×成本)/成本` 量纲不一致（产出 4212% 的伪 ROI），已改为“SOM→可服务件数→获客投入”的一致口径（191.26%/177.78%/160.87%），并以 34 项对抗探针复验“TAM 放大不虚增、份额上升因 CAC 抬升而降 ROI”。

---

## 十一、残余风险与下一轮建议（如实说明）

1. **数据仍是确定性夹具驱动**：证据链、集中度、竞品数据来自本地样例；接入真实数据源（OpenBB provider、监管披露 API）需要新增外部适配层与速率限制。
2. **L10 线程超时无法强杀**：Python 线程不可强制终止，`WatchdogRunner` 只能“放弃等待”；对 CPU 死循环建议升级为子进程隔离（`multiprocessing`）并加进程级 kill。
3. **SARIF 规则集最小化**：当前 5 条规则覆盖证据/方差/Tier0/情景/HHI；后续可扩展到 8 维门禁全量映射与 `fixes` 建议。
4. **记忆层无向量检索**：当前按轮次/槽位/序号精确消歧，跨长会话语义检索（“上次那个类似的东南亚市场”）需引入 embedding 索引。
5. **遥测无轮转/采样**：`telemetry.jsonl` 单文件追加，生产需按大小轮转与采样，并接入 OTLP exporter。
6. **CLI 的 spec 子命令为门禁语义**：评估不通过时退出 1 属预期行为，批处理脚本需按退出码分支。

---

## 十二、复现与验收命令

```powershell
cd D:\蛙蛙呱呱\蛙蛙呱呱agents团\r05-washenyuan-research
$env:PYTHONIOENCODING='utf-8'

python run_tests.py                    # 63/63 OK
python tests/test_evolution_suite.py         # 10/10 OK
python -m pytest tests -q              # 62 passed

python auto_evolve_runner.py --status  # ALL_GREEN_10_OF_10
python auto_evolve_runner.py --run-all # 3/3 轮五步闭环全绿
python auto_evolve_runner.py --layer L07
```

---

## 十三、交付清单

| 类别 | 文件 |
| :--- | :--- |
| 调度状态机 | `auto_evolve_runner.py`、`workspace/evolution_state.json`、`workspace/rounds/round{1,2,3}_journal.json` |
| L01~L03 | `engines/runtime_engine.py`、`engines/intent_compiler.py`、`engines/reflexive_healer.py` |
| L04~L06 | `RESEARCH_SPEC.md` v2.0.0、`engines/spec_ledger.py`、`engines/slop_guard.py`、`engines/scenario_matrix.py` |
| L07~L10 | `engines/asset_bundle.py`、`engines/diff_patch_engine.py`、`engines/session_memory.py`、`engines/telemetry_watchdog.py` |
| 契约测试 | `tests/test_round1_foundation.py`、`tests/test_round2_depth.py`、`tests/test_round3_industrial.py` |
| 物理工件 | `artifacts/evolve/round{1,2,3}/`（17 个验收工件 + 3 份 SHA256 清单） |
| 公开接口 | `agent.py evolution compile/heal2/spec/diff/session/breaker` |
