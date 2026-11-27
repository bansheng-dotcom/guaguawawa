# 报告产线地图（REPORT-LINES.md · v12）

> **2026-11-19 起：默认版式已切 flow（一条内容流 + PDF 自动分页），见 [`REPORT-FLOW.md`](REPORT-FLOW.md)。**
> 默认值在 `configs/report_flow.yaml` 的 `flow.default_layout`；`--layout paper` 已于 2026-11-21 下线。
> flow 版按 `prose_contract` 记文笔分（默认只记录不拦），页式版仍走下面的三层质检。
>
> 2026-11-18 重构完成（P1–P5）。**一条线、四种输入、一个入口、三层质检。**
> 旧版地图与过程稿已于 2026-11-22 清理（`_attic/` 不再保留），现行口径以本文件为准。
> 施工记录保留在 `交付/`：拆卡见 `交付/拆卡升级-SOP-2026-11-21.md`，
> 报告系统升级见 `交付/报告系统升级SOP-2026-11-21.md`。
>
> **v12 补的是「能力在模型、规则只管验」**：报告不再只能由方法库算出，
> 也可以由领域专家（模型 + 工具）调研后写出来，规则负责逐节过账与交叉质询。

---

## 零、出报告只有一条默认路（2026-11-22 起）

| 路 | 谁写内容 | 命令 | 状态 |
|---|---|---|---|
| **拆卡线（默认）** | R01 发卡 → 子智能体按 nonce 各写各的 → R01 只做合并与判断 | `clarify → brief --plan --confirm → collect → run-line --claims` | **唯一默认**，缺 `issued.json` 直接拒收 |
| **A 数据驱动** | 方法库从结构化数据算 | `report "问题" --dir <项目> --out <目录>` | 可用（已有干净数据时） |
| **B 单人稿** | 一个人写完 claims | `run-line --solo-claims --allow-solo --claims …` | **应急**，必须显式授权，过 50 源门槛，产物标 `solo_no_dispatch` |

拆卡线每步的硬门：brief 未签不拆卡；DoR 未过不发卡；没有 nonce/签名的卡不收；
`collect` 默认 `--min-sources 50`（唯一 URL）+ 逐条回抓；`run-line --claims` 只接受收卡产物。

`report run-line` 用 `--source data|cards` 显式区分取数来源：`cards` 必须同时给 `--claims`，
`data` 不接受 `--claims`。两条路共用同一渲染与质检主干，证据契约仍分开。

**先定供给方案（SUPPLY-SOP v7.0）**：项目根目录的 `supply.yaml` 声明
A/B/C 三层源、`L1_possible` / `L2_possible` / `L2_condition` / `planned_rows`。
**这是拆卡的前提**——不写供给方案就开拆卡，拆的是"想要的"不是"能采的"。
`report collect` 收卡时会算「计划级别 vs 实际级别」，写进 `merged.capability` 与 manifest，
报告口径节第一条显示。

**收卡前先探测（FEASIBILITY-SOP v5.0）**：`collect` 会自动跑一次 `core/card_probe`，
算清每个格子「要采什么 / 有没有源 / 采到质量够不够」，结果写进
`plan/derivation.json` 与 `merged.probe`。默认 `report` 模式**只记录不改输出**；
`GUAGUA_PROBE=degrade` 时才把无数据的判断补成「（无数据）…」节保留在报告里。
**不砍格子**——拆卡是穷尽的，缺口要可见。

**A 路是快捷路，不是默认**：`report "问题" --dir <有 CSV/JSON 的项目> --out <目录>` 走
`decision_report`，不经过 `preflight / issued / nonce`。它只适合「已有干净数据、不需要外部取证」；
一旦结论依赖外部来源，必须回拆卡线。

**人必须在环里（2026-11-22）**：
- 12 问要问给用户；`intake --by agent` 代答不算，`user_answers<10` 签不了 brief；
- `clarify --confirm` 必须带 `--user-said "用户原话"`；
- 发卡前先 `brief --plan` 把卡片清单摊给用户看，确认时带 `--ack-cards`；
- `preflight` 的 P8/P9 就是查这三件事，不通过不进收卡。

### B 路（应急单人稿）

```bash
# 只有在你明确接受「生成与校验不分离」时才用
python guagua.py report run-line --intent "…" --claims claims.json \
  --solo-claims --allow-solo --min-sources 50 --out <目录> --pdf
```

内部顺序：`compile`（证据包+章节稿）→ `claim_consistency`（口径冲突/来源等级/边界）
→ `report_flow` 逐节过账 → `quality_gate` 三层闸 → 渲染。

**交叉质询的硬规则**：同一指标同期出现两个不同值，必须在 `claims.conflicts` 里写明口径差；
沉默即拦。这条规则来自真实事故（全国预制菜 2024 年 4850 亿 vs 6831.6 亿；B 端 80% vs 67%）。

---

## 一、唯一入口

```bash
python guagua.py report "你的问题" --dir <项目目录> --out <输出目录> [--pdf]
```

也可以写全子命令名（等价）：

```bash
python guagua.py report run-line --intent "你的问题" --dir <项目> --out <目录>
```

四种输入，同一条后端：

| 你给的 | 判定 | 走法 |
|---|---|---|
| `--dir` 有 CSV/JSON | `data` | 计算型专家作答（已可用） |
| `--input <文件>` | `document` | 评审型：先审后写（P2 起，待接） |
| `--research` | `research` | 采集型：来源 + quote 回抓（待接） |
| 只有问题 | `instruction` | 假设型：结论标「假设」，不进头条（待接） |

判定结果落在 `<out>/input_mode.json`，供编排器读。

### 项目根与 brief（2026-11-25 起）

- `--project` 指定**项目资产根**（默认 `GUAGUA_PROJECT` 或 `<仓库根>/projects`）；
  `--out`/`--dir` 只是项目内的子目录。写团内会被 `core/base/paths.py` 拒绝。
- 拆卡时每张卡都带 `expert_brief`（v2 七层：决策语境 / 定义口径 / 结构分解 /
  机制归因 / 判断情景 / 行动可逆 / 反证不确定），与卡合成 `CardBundle`：
  卡是信封，brief 是内容。
- **验收只由 brief 派生**：`report collect` 会校验 bundle 的
  `brief_version` 与 `acceptance_checks`；卡里出现 acceptance 明细即拒收。
- 报告层（`core/report_*.py`）不得 import 知识库或读 brief；
  由 `scripts/check_report_isolation.py` 守卫。

## 二、七段（S0–S7）

```
S0 输入识别      core/report_line.detect_mode()      → input_mode.json
S1 意图→域       core/orchestrator.plan()            → decisions.json
S2 专家编排      roster / blocked / missing
S3 专家作答      core/methods + 角色技能              → findings
S4 叙事装配      core/report_assembly（finding → 节 / 指标 / 计数 + 机理/证伪）
S5 排版出图      core/report_flow → report_bridge → core/report_renderer（唯一 HTML）
S6 三层质检      core/quality_gate：证据 / 编辑 / 呈现 → quality_gate.json
S7 交付          report.html + report.md + report.pdf + manifest.json
```

## 三、命令

| 命令 | 作用 |
|---|---|
| `report "指令" …` | **唯一入口**（等价 `report run-line`）；只出 flow，paper 文档线 2026-11-21 下线 |
| `report clarify --intent … --out <项目>` | 接任务先对齐意图：出澄清卡（问句/假设/待确认项） |
| `report clarify --dir <项目> --answer C1=…` | 把会话里问到的答案写回并确认 |
| `report brief --dir <项目> --plan [--confirm]` | 出「问题→角色」映射表；`--confirm` 确认即发卡（带 nonce） |
| `report exchange --dir <项目>` | 卡间协商：路由 needs → INBOX，出闭环台账 `exchange.md` |
| `report collect --dir … --out …` | 收卡：**先跑可行性探测** + 非卡 nonce/执行者校验 + 来源/覆盖门禁 + 合并 |
| `report attest --out <项目产出>` | 交付口径：门禁/来源/核验/降级（从 manifest 回填） |
| `report check --html <报告>` | 验一份成品（九条 flow 门禁 + 深度门禁） |
| `report charts` | 48 型图表能力盘点 |
| `report capabilities` / `plan` / `gaps` | 诊断（不产报告） |

> **项目代码放项目文件夹（2026-11-23 更正）**：`report flow --project <项目目录>` 是
> 「项目自带 `facts.py` / `charts.py` / `prose_specs.py`」的加载器——项目代码落在
> `projects/<项目>/`（或 `workspace/<项目>/`），`core/` 只提供引擎、不含任何项目内容。
> 这跟 `run-line`（两个分支：拆卡 `--claims` / 喂数据 `--dir`）是**互补关系**：
> 前者管「项目自带代码」，后者管「项目自带数据」。

拆卡与防代写的规则见 `docs/REPORT-DISPATCH.md`。

### 拆卡 SOP 已进产线（v1.5 · 2026-11-21）

`report brief --dir <项目> --plan` 不再只做「问题→角色」映射，而是先跑**拆卡升级 SOP v1.4**：

- R01 内容层：`plan/issue_tree.json`、`perspectives.json`、`grid.json`、`decomposition_log.json`、`branch_log.json`
- R02 协作层：`plan/dispatch.json`（能力卡 / 分配 / 契约 / DAG / 缺口请求）
- 发卡门禁 S1–S9（阈值在 `configs/report_card_spec.yaml`）：每 must 问 8–24 格、≥1 格 L3、
  ≥3 视角、每问 ≥2 种拆法、语义层须为本题真实层、每格 measure/grain/期次/因果阶/质量六维齐、
  六维均有格、契约覆盖全部 owner、每问 ≥3 条 stop
- **门禁不过 → 不发卡**，返回 `plan/pre_issue_gates.json` 的失败项
- 卡里直接带「你负责的格子」表与 **R02 任务契约**（task_id / 验收门禁 / 截止 / 升级）
- 实现：`core/cards/card_issue.py`；回归：`tests/test_cards.py`

### 全入口统一 + 协作层接线（2026-11-21 晚）

- **入口**：`brief --dir`、`brief --intent/--out`（老路径）、`report research`（并行调研）
  三条都走 `card_issue.bootstrap()`；缺 `semantic_layer.yaml` 一律拒绝（写模板并报错）。
- **协作层**：`core/collab.py` 真调 R02：
  - `handoff package` × 每个角色 → `plan/handoffs.json`（package_id）
  - `portfolio plan` → `plan/r02_waves.json`（波次/负载）
  - `plan/ledger.jsonl` 记录 plan / dispatch / handoff / r02_waves / issue
- 发卡门禁新增 **S10 R02 交接包齐**、**S11 R02 波次可排**；不过同样拒发。

已全部删除：`report build` / `decide` / `produce` / `pack` / `research` / `run`
与 `--lens` / `--thesis` / `--profile` / `--min-coverage`。

## 四、保留的零件（不是产线）

| 模块 | 职责 |
|---|---|
| `core/report/report_line.py` | 唯一入口与输入形态识别 |
| `core/report/report_clarify.py` | 接任务先对齐意图：意图/问句/假设/待确认项（clarify.json） |
| `core/cards/report_dispatch.py` | 问题→角色映射、发卡 nonce、收卡校验（防代写） |
| `core/orchestrator.py` | 专家编排：意图 → 域 → 名单（BLOCKED 硬规矩） |
| `core/report/report_assembly.py` | finding → 节/指标/计数 + 机理/落点/证伪 + 判断型标题 |
| `core/report/report_flow.py` | 逐节过账（R01 s09）+ 渲染编排 + manifest |
| `core/quality_gate.py` | 三层质检聚合：证据 / 编辑 / 呈现（三层全过才放行） |
| `core/report/report_bridge.py` | 渲染薄层：`render_html / write_markdown / render_pdf` |
| `core/report_theme/` | consulting 主题：固定 A4 页式 + A/B 两种节页（`docs/REPORT-LAYOUTS.md`） |
| `core/report/report_editorial.py` | 旧契约补 verdict/kicker/rail/actions/sources + 契约门禁 |
| `core/data/data_shape.py` | 数据形状 → 图型适配（问题 + shape 双约束） |
| `core/sources/coverage_plan.py` | 覆盖自动化：CoveragePlan + 出稿前门禁 |
| `configs/report_coverage.yaml` | 50 源/15 源/21 页/双地图唯一阈值 |
| `core/charts/consulting.py` | consulting 主题的 14 型确定性 SVG 图表 |
| `core/report/report_renderer.py` | 唯一 HTML 渲染器（charts_pro 70 型 + 8 套主题 + 呈现层规则） |
| `core/decision.py` | 决策契约（3–5 问、对照、图型、证伪）与选图（读 `configs/chart_by_relation.yaml`） |
| `core/report/report_thesis.py` | 只保留 `analysis` 一条纲领 |
| `core/data/analysis_desk.py` · `core/methods/*` | 数据台 + 方法库（出带数字的判断） |
| `core/report_kernel/*` | 版式四规则 + 契约自检 |
| `core/report/report_quality.py` | 反模板深度门禁（Q1–Q9） |
| `configs/experts.yaml` | 20 角色专家卡（由 `scripts/gen_experts.py` 生成） |
| `configs/chart_by_relation.yaml` | 按数据关系选图（v1 48 型全覆盖） |

已删除（P1/P4）：`core/report_build.py`、`core/report_compose.py`、`core/question_bank.py`、
`core/question_derive.py`、`core/focus_contract.py`、`scripts/reason.py`、
`configs/role_report_specs.json`、`datasets/ports/`、`pipelines/out/`。
详见 git 历史中的 2026-11 大清理提交。

## 五、验收

```bash
python scripts/ci_report_checks.py        # 角色/报告/门禁/图型/风格/语义层/呈现 + 门禁锁 + 默认 flow
python scripts/check_report_flow.py --dir <输出目录>
python scripts/check_gate_lock.py         # 门禁脚本有没有被改过而没更新锁
python scripts/check_r04_inputs.py --dir <输出目录>   # R04 输入是不是从产物派生的
python guagua.py report attest --out <输出目录>       # 交付口径（门禁/来源/核验/降级）
python scripts/check_report_presentation.py --dir <输出目录>
python -m core.quality_gate --draft <draft_sections.json> --pack <evidence_pack.json> --html <report.html>
python -m core.report.report_model --audit       # 语义层六项悬空边必须为 0
python guagua.py report check --html <report.html>
```

> **v2（2026-11-20）**：门禁已并进 `report run-line`，结论写在 `manifest.gate.flow`；
> 默认 flow 版式的产物必须过门禁（CI 有专门用例）。判据与标记契约见
> `docs/REPORT-GATE-CONTRACT.md`。**不要再在对话里宣布「门禁通过」**——用 `report attest`。

> **拆卡（2026-11-21）**：每一问下发时必须带「6 维 × 5 层」格子表，
> 角色交格子而不是段落；覆盖率/深度/证据等级是验收项。
> 见 `交付/拆卡升级-SOP-2026-11-21.md`。

## 六、已知边界（不是 bug，是选择）

1. **图型覆盖率**：选型层支持 48 型全覆盖，但方法目前只产出 `hbar / line / grouped_bar /
   vbar / dot / pie` 一类 payload，所以报告实际用不到 10 型。要扩图型，先扩方法的数据结构。
2. **四种输入只打通一种**：`document / research / instruction` 仍是显式报错或退回同一条后端。
3. **`report_policy.yaml`** 仍未被门禁读取（阈值在 `decision_report` 与 `report_quality.PROFILES` 里）。
