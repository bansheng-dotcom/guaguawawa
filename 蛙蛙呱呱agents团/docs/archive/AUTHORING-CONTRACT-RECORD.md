> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 语义模型收敛 · 升级记录（2026-11-22）

> 对应 SOP：[AUTHORING-CONTRACT-SOP.md](./AUTHORING-CONTRACT-SOP.md)（v3.0）。
> 本记录只记「做完什么」和「两个反直觉决定」，供交接与回滚查阅。

## 一句话

三种作者写法（claims.json / decision.json / facts.yaml）收敛到同一富 IR
（`dsh.report_ir/v1`），语义管道给出 relation + 图拟合校验，**但图表最终决定权
回到作者**（候选面板确认），系统只提示、不替作者拍板。

## 交付物

| 文件 | 作用 |
|---|---|
| `core/report/report_ir.py` | 富 IR + `validate()` + `infer_relation()` |
| `core/ir_adapters.py` | 三前端：claims / decision / facts → IR |
| `core/semantic_pipeline.py` | 语义管道：`resolve` / `panel` / `apply_decisions` |
| `core/charts/chart_payload.py` | payload 构建器（facts → 各图型数据形状） |
| `core/report/report_flow.py` | 影子落盘 + 诊断挂载（治疗默认关） |
| `configs/facts_schema.json` | 声明式作者格式（替换 facts.py 的 schema） |
| `scripts/ir_shadow.py` | 影子对比 CLI（三写法 → IR → 图型变更报告） |
| 测试 | 28 个新单测，全仓 363 通过 |

## 两个反直觉决定（实测证伪后定下的）

### 1. 自动切换图型 = 关（`GUAGUA_IR_TREAT` 默认 `0`）

- 实测呼包鄂：开自动切换，13 节被改，但大半改错（line→hbar、diverging→hbar、
  排名→treemap）。
- 根因：`infer_relation` 是关键词推断，真实问题含"结构/占比"等词时误判
  composition，把本应对的 deviation/ranking/trend 图改错。
- 结论：**关键词推断只能当提示，不能当自动决策**。自动切换仅作者显式
  `GUAGUA_IR_TREAT=1` 才生效；正常路径是候选面板人工确认。

### 2. 不删 grammar / chooser（S6 按实测改方向）

- 原 SOP S6 计划删 `chart_grammar` / `chart_chooser` / `chart_plan.audit`。
- 实测 treat=0 的呼包鄂已是 7 种图型（dot/diverging/lollipop/hbar/vbar/share_bar/line），
  说明 grammar/chooser 仍在做有效选型，"图表单调"早在前一轮图表收敛已解决。
- 结论：保留 grammar/chooser；保留 `chart_plan.audit`（r01 s09_interpret 仍引用）。
  S6 的实质是「诊断挂载 + 候选面板」，不是删选型器。

## 回滚

- `GUAGUA_IR_TREAT=0`（默认）：只诊断（每节挂 relation + chart_validation），不改图。
- `GUAGUA_IR_TREAT=1`：开自动切换（已证伪，勿用于生产）。
- 影子文件 `ir_shadow.json` / `ir_chart_report.json` / `panel.json` 每次跑产线都落盘，
  可随时对照"图该不该改"。

## 数据质量发现（附带）

- A 线（analysis_desk）的数字**缺单位**（111/141 条 unit 为空），IR 校验把它暴露出来。
  这是 A 线数据模型的历史缺口，不是本次收敛引入的，但统一 IR 后第一次可量化。
