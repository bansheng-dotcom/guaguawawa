# 报告产线地图（REPORT-LINES.md · v11）

> 2026-11-18 重构完成（P1–P5）。**一条线、四种输入、一个入口、三层质检。**
> 旧版地图（12 条产线 → 1 条产线 2 分支 → v10 决策契约）已归档到 `_attic/docs/REPORT-LINES-v10.md`。
> 施工依据见仓根 `交付/报告产线重构-SOP-2026-11-18.md`，逐阶段验收见 `交付/SOP-P*-验收-*.md`。

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
| `report "指令" …` | **唯一入口**（等价 `report run-line`） |
| `report check --html <报告>` | 验一份成品（九条 flow 门禁 + 深度门禁） |
| `report charts` | 48 型图表能力盘点 |
| `report capabilities` / `plan` / `gaps` | 诊断（不产报告） |

已全部删除：`report build` / `decide` / `produce` / `pack` / `research` / `run`
与 `--lens` / `--thesis` / `--profile` / `--min-coverage`。

## 四、保留的零件（不是产线）

| 模块 | 职责 |
|---|---|
| `core/report_line.py` | 唯一入口与输入形态识别 |
| `core/orchestrator.py` | 专家编排：意图 → 域 → 名单（BLOCKED 硬规矩） |
| `core/report_assembly.py` | finding → 节/指标/计数 + 机理/落点/证伪 + 判断型标题 |
| `core/report_flow.py` | 逐节过账（R01 s09）+ 渲染编排 + manifest |
| `core/quality_gate.py` | 三层质检聚合：证据 / 编辑 / 呈现（三层全过才放行） |
| `core/report_bridge.py` | 渲染薄层：`render_html / write_markdown / render_pdf` |
| `core/report_renderer.py` | 唯一 HTML 渲染器（48 型图 + 8 套主题 + 呈现层规则） |
| `core/decision.py` | 决策契约（3–5 问、对照、图型、证伪）与选图（读 `configs/chart_by_relation.yaml`） |
| `core/report_thesis.py` | 只保留 `analysis` 一条纲领 |
| `core/analysis_desk.py` · `core/methods/*` | 数据台 + 方法库（出带数字的判断） |
| `core/report_kernel/*` | 版式四规则 + 契约自检 |
| `core/report_quality.py` | 反模板深度门禁（Q1–Q9） |
| `configs/experts.yaml` | 20 角色专家卡（由 `scripts/gen_experts.py` 生成） |
| `configs/chart_by_relation.yaml` | 按数据关系选图（48 型全覆盖） |

已删除（P1/P4）：`core/report_build.py`、`core/report_compose.py`、`core/question_bank.py`、
`core/question_derive.py`、`core/focus_contract.py`、`scripts/reason.py`、
`configs/role_report_specs.json`、`datasets/ports/`、`pipelines/out/`。
详见 `_attic/DELETED.md`。

## 五、验收

```bash
python scripts/ci_report_checks.py        # 17 项：角色/报告/门禁/图型/风格/语义层/呈现
python scripts/check_report_flow.py --dir <输出目录>
python scripts/check_report_presentation.py --dir <输出目录>
python -m core.quality_gate --draft <draft_sections.json> --pack <evidence_pack.json> --html <report.html>
python -m core.report_model --audit       # 语义层六项悬空边必须为 0
python guagua.py report check --html <report.html>
```

## 六、已知边界（不是 bug，是选择）

1. **图型覆盖率**：选型层支持 48 型全覆盖，但方法目前只产出 `hbar / line / grouped_bar /
   vbar / dot / pie` 一类 payload，所以报告实际用不到 10 型。要扩图型，先扩方法的数据结构。
2. **四种输入只打通一种**：`document / research / instruction` 仍是显式报错或退回同一条后端。
3. **`report_policy.yaml`** 仍未被门禁读取（阈值在 `decision_report` 与 `report_quality.PROFILES` 里）。
