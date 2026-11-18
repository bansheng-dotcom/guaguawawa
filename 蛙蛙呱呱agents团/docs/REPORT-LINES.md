# 报告产线地图（REPORT-LINES.md · v11）

> 2026-11-18 重构（P1）。**一条线、四种输入、一个入口。**
> 旧版地图（12 条产线 → 1 条产线 2 分支 → v10 决策契约）已归档到 `_attic/docs/REPORT-LINES-v10.md`。
> 施工依据见仓根 `交付/报告产线重构-SOP-2026-11-18.md`。

---

## 一、唯一入口

```bash
python guagua.py report run-line --intent "你的指令" --dir <项目目录> --out <输出目录>
```

四种输入，同一条后端：

| 你给的 | 判定 | 走法 |
|---|---|---|
| `--dir` 有 CSV/JSON | `data` | 计算型专家作答（当前已可跑） |
| `--input <文件>` | `document` | 评审型：先审后写（P2 接入） |
| `--research` | `research` | 采集型：来源 + quote 回抓（P3 接入） |
| 只有 `--intent` | `instruction` | 假设型：结论标「假设」，不进头条（P2 接入） |

判定结果落在 `<out>/input_mode.json`，供编排器读。

## 二、七段

```
S0 输入识别      core/report_line.detect_mode()      → input_mode.json
S1 意图→域       （P2）core/orchestrator.plan()
S2 专家编排      （P2）roster / blocked / missing    → decisions.json
S3 专家作答      （P2）core/methods + 角色技能        → findings
S4 叙事装配      core/report_assembly（finding → 节 / 指标 / 计数）
S5 排版出图      core/report_flow → report_bridge → core/report_renderer（唯一 HTML）
S6 三层质检      （P5）证据 / 编辑 / 呈现
S7 交付          report.html + report.md + manifest.json
```

**P1 状态**：S0/S4/S5/S7 已就位；S1–S3、S6 在 P2/P3/P5 补齐。
当前 `report_line.build()` 在 data 形态下转发 `core/decision_report.build()`，产物与改造前逐字节一致
（回归判据：`report.md` 的 SHA256 = `A0357882…`）。

## 三、命令

| 命令 | 作用 |
|---|---|
| `report run-line` | **唯一入口**（一条命令 + 四种输入） |
| `report build` / `report decide` | 过渡别名，P5 删除 |
| `report check --html <报告>` | 验一份成品（九条 flow 门禁 + 深度门禁） |
| `report charts` | 48 型图表能力盘点 |
| `report capabilities` / `plan` / `gaps` | 诊断（不产报告） |

已删除（P1.7）：`report produce` / `report pack` / `report research` / `report run`。
已退役参数：`--lens`、`--thesis`、`--profile`、`--min-coverage`。

## 四、保留的零件（不是产线）

| 模块 | 职责 |
|---|---|
| `core/report_line.py` | 唯一入口与输入形态识别 |
| `core/report_assembly.py` | finding → 节/指标/计数（从旧 report_compose 拆出） |
| `core/report_flow.py` | 逐节过账（R01 s09）+ 渲染编排 + manifest |
| `core/report_bridge.py` | 渲染薄层：`render_html / write_markdown / render_pdf` |
| `core/report_renderer.py` | 唯一 HTML 渲染器（48 型图 + 8 套主题） |
| `core/decision.py` | 决策契约（3–5 问、对照、图型、证伪）与选图 |
| `core/report_thesis.py` | 只保留 `analysis` 一条纲领（v11 收敛） |
| `core/analysis_desk.py` · `core/methods/*` | 数据台 + 方法库（出带数字的判断） |
| `core/report_kernel/*` | 版式四规则 + 契约自检 |
| `core/report_quality.py` | 反模板深度门禁 |

已删除（P1）：`core/report_build.py`、`core/report_compose.py`、`core/question_bank.py`、
`core/question_derive.py`、`core/focus_contract.py`、`scripts/reason.py`。
详见 `_attic/DELETED.md`。

## 五、验收

```bash
python scripts/ci_report_checks.py        # 报告产线：run-line + 门禁 + 图型 + 风格
python scripts/check_report_flow.py --dir <输出目录>
python guagua.py report check --html <report.html>
python -m core.report_model --audit       # 语义层审计（P2 起必须下降，最终为 0）
```

## 六、下一步（P2）

1. `configs/experts.yaml`：20 个角色的专家卡（能答什么、要什么数据、什么情况不许开口），由 `scripts/gen_experts.py` 三方合并生成；
2. `core/orchestrator.py`：域判定 + 数据齐备度 + BLOCKED 硬规矩；
3. 把 `decision.draft()` 的问题来源从「数据能算什么」换成「编排器选出的专家要回答什么」。

**P2 必须过的验收**：问「招聘编制」+ 水果数据 → `INTENT_UNBOUND` 并说出缺 `table.headcount`，且不出报告。
