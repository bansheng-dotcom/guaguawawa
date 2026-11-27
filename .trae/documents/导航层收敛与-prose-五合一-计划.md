# 导航层收敛与 prose 五合一 · 执行计划

## Context

四份 HTML 方案的诚实审计已完成，用户回复「做吧」，即按审计结论继续收口：
先做**第 1 块导航层**（零行为变更），再开**第 3 块 prose 五合一**。P0–P5 已闭片，不重做。

当前基线（已验证）：

- HEAD `4cec0ed`，分支 `refactor/wiring-truth`
- `python -m pytest tests -q` → **637 passed / 3 skipped**
- `ci_report_checks` ALL PASS；`guagua.py check` 20/20；`wiring_truth --check`、`check_dead_code --check`、`check_project_boundary` 全 PASS
- 根目录 HTML/PDF、`_compare/`、`_refs/` 为 untracked，一律不动

审计中发现与旧摘要不符的一处事实：`agents/` **不是空壳**，它通过
`agents/shared/__init__.py` 把 `__path__` 指向 `shared/`，且被 4 处
`from agents.shared.*` 引用（`shared/chat_cli.py`、`shared/dsh_integration.py` ×2、
`shared/role_runtime.py`）。直接删会断 `guagua.py chat` 的导入链，必须先改引用。

---

## A. 导航层（第一个 commit，零行为变更）

### A1. 新建 `docs/GLOSSARY.md`（≤120 行）

统一术语，明确「裸 card 禁用于新代码」：

- 任务卡 `Task`（`core/base/protocol.py`）：owner / inputs / outputs / deps / status，
  卡是信封，验收由 `expert_brief` 派生
- `CardBundle`：任务卡 + expert_brief 的合成体（`brief_version` + `acceptance_checks`）
- 探测卡 / probe（`core/cards/card_probe.py`，`dsh.probe/v1`）：收卡前的可行性三态
- `ClaimCard`：claims 的规范形状，字段只从 `core/claims/contract.py` 读
  （`CARD_KEYS` / `NUMBER_KEYS`），两种交付形态同一形状
- 格子 cell：拆卡网格中「单元 × 维度 × 度量」的一个采集格，按格交 numbers
- `Observation`（`core/data/data_standard.py`）：清洗后、可比较的唯一指标单元
- `ExperienceCard`（`shared/experience_cards.py`）：trigger / wrong_once /
  do_instead / boundary / last_verified
- `SkillCard`：`SKILL.md` 三层技能包（L1 引导 / L2 知识 / L3 校验）

### A2. 新建 `docs/ENTRYPOINTS.md`

- **唯一对外入口**：`python guagua.py report "问题" ...`（等价 `report run-line`）
- 拆卡线最短路径：`clarify → brief --plan --confirm → collect → run-line --claims`
- 其余 `guagua.py` 子命令与 `core/*` 模块一律标「内部实现 / 诊断入口」，不承诺外部兼容
- 附一段最小可复制示例与产物清单（report.html / .md / .pdf / manifest.json）

### A3. 新建 `scripts/gates_index.py` → `docs/GATES.md`

生成式门禁索引，规则：

1. 扫描 `scripts/check_*.py`
2. 分类优先级：`CI`（出现在 `ci_report_checks.py` / `ci_upgrade_checks.py`）→
   `GATES`（出现在 `configs/gates.yaml`）→ `INDIRECT`（被其他 `scripts/*.py` 调用）→
   `MANUAL`（脚本内显式登记 + 理由）→ **`UNREGISTERED`（`--check` 失败）**
3. `--write` 生成 `docs/GATES.md`（表格：脚本 / 状态 / 证据 / 用途），`--check` 比对文件是否最新
4. 接入 `scripts/ci_report_checks.py` 新增 `[0e] gates-index`
5. `check_gate_lock.py` 的锁目标只有 `check_report_flow.py` 与 `check_report_layout.py`，
   本次不改它们；仍跑一次 `check_gate_lock.py` 确认未被误动

### A4. 新建 `scripts/audit_core_paths.py` → `docs/_migration/couplings.md`

静态分析 `core/` 包内 import，输出确定性报告：

- 包间耦合边（`core.a.* → core.b.*`）的计数与代表文件
- 模块扇入 / 扇出 Top 20
- 模块级循环依赖（SCC）
- `--write` / `--check` 两种模式，报告头声明「由脚本生成，禁止手改」

用途：为后续 card/claim 合并提供「先动哪条边」的证据。

### A5. 归档 8 份 `status: ARCHIVED` 文档

移动到 `docs/archive/`（沿用已有目录，不新建 `_archive/`）：

`CHART-UPGRADE-SOP.md`、`DOMAIN-EXPERT-LAYER.md`、`REPORT-CAPABILITY-GRAPH.md`、
`REPORT-CLAIM-GATE.md`、`REPORT-COVERAGE-UPGRADE-SOP.md`、`REPORT-DECISION-GRADE.md`、
`REPORT-PRODUCTION-LINE-SPEC.md`、`REPORT-SYSTEM-UPGRADE-SOP.md`

同步更新引用（避免 `wiring_truth` 的 DOC_DEAD）：

- `docs/README.md`：从「现行」表移到「历史 / 限定使用」表
- `docs/MASTER-UPGRADE-SOP.md`、`docs/UPGRADE-PLAN.md`：`CHART-UPGRADE-SOP` 路径改 `archive/`
- `configs/report_coverage.yaml`：注释中的路径改 `archive/`
- `scripts/wiring_truth.py` 的债务理由文案改指归档路径

> 若移动后 `wiring_truth --check` 出现多份 DOC_DEAD，则回退本项，把归档单独作为一片并如实报告。

### A6. 删除 `agents/` 空壳（先改引用）

- `shared/chat_cli.py`：`from agents.shared.dsh_integration` → `from shared.dsh_integration`
- `shared/dsh_integration.py`：两处 `from agents.shared.knowledge_base` → `from shared.knowledge_base`；
  docstring 示例同步
- `shared/role_runtime.py`：`from agents.shared.role_profiles` → `from shared.role_profiles`
- grep 确认全仓无 `agents.shared` / `from agents` 后，删除整个 `agents/` 目录

### A7. 回归并提交

```bash
python -m pytest tests -q
python scripts/ci_report_checks.py
python scripts/wiring_truth.py --check
python scripts/check_dead_code.py --check
python scripts/check_project_boundary.py
python scripts/check_gate_lock.py
```

全绿后提交：`docs: 导航层收敛（GLOSSARY/ENTRYPOINTS/GATES/耦合表/归档/删 agents 壳）`

---

## B. prose 五合一（第二个 commit）

现状：`core/prose/{prose_spec, prose_candidates, prose_style}.py` +
`core/report/report_prose_gen.py`。目标两文件：

### B1. 新增 `core/prose/prose_contract.py`

并入：

- `prose_spec` 的 `FIELDS` / `LABELS` / `validate`
- `prose_style` 的 `DEFAULTS` / 阈值读法（唯一兜底仍来自 `report_contract.PROSE_DEFAULTS`）

### B2. 新增 `core/prose/prose_render.py`

并入：

- `prose_candidates` 的候选生成
- `core/report/report_prose_gen.py` 的受约束生成

### B3. 更新引用与登记

- 全仓 grep `prose_spec|prose_style|prose_candidates|report_prose_gen`，改 import
- 删除四个旧文件（`report_prose_gen` 随迁）
- 更新 `core/prose/__init__.py`、`configs/core_files.json`、
  `docs/CORE-MAP.md`、`docs/ARCHITECTURE-LEDGER.md`、`CHANGELOG.md`

### B4. 语义与门禁不变

- 产物 JSON 既有键不改；新增字段只加不删
- F10 / F12 正文门禁必须保持原判据
- 回归命令同 A7，另跑 `python scripts/check_report_flow.py --dir <样本>`（若样本存在）
- 提交：`refactor(prose): 五合一为 prose_contract + prose_render`

---

## 不做的事

- 不重做 P0–P5，不改报告产物语义
- 不动根目录 HTML/PDF、`_compare/`、`_refs/`
- 不做 card 六合一 / claim 四合一 / 版本词汇清理（留给后续独立片）
- 不为了「docs ≤10」强删现行文档；本片只归档已标 ARCHIVED 的 8 份
