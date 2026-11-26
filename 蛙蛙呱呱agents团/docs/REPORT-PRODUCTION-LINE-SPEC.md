# 统一生产线需求规格（v1.0）

> status: ARCHIVED · 2026-11-26
> 说明：本文为历史需求确认稿，其中 `prose_critic` 等模块已删除；
> 当前产线见 `docs/REPORT-LINES.md` 与 `docs/CORE-MAP.md`。

> 状态：需求确认稿。未改生产代码。  
> 目标：20 个角色的所有任务，走同一入口、同一契约、同一编排、分类门禁、统一交付；报告统一用 `report_flow_all.html` 的视觉/结构骨架。

## 1. 已确认的需求

| 项 | 决定 |
|---|---|
| 统一范围 | 统一入口 + 统一契约 + 统一门禁 + 统一产物 + 统一编排 |
| 任务范围 | **所有任务**，不只报告 |
| 非报告角色 | 同契约，分类门禁 |
| R04 | **所有任务都审，包括内部草稿** |
| 默认策略 | 硬门禁；失败即不完成 |
| 入口 | `guagua.py`、`report`、Trae 技能、chat/MCP/API 全部纳入 |
| 报告骨架 | `workspace/seasoning_v3_2026-11-19/report_flow_all.html` 是所有报告的唯一视觉/结构样板 |
| 非报告交付 | `result.json + evidence.json + artifact` |

## 2. 唯一生产路径

```text
任何入口
  → guagua.py（唯一入口）
  → R01 任务卡（owner / 输入 / 输出 / 门禁 profile）
  → R02 排期（依赖 / 交接 / 容量）
  → 角色执行
  → result.json
  → evidence.json
  → artifact
  → 分类门禁
  → R04 独立验收（所有任务）
  → manifest + 签名
```

### 入口规则

- `guagua.py call rXX`、`dispatch`、`plan`、`report` 都必须走同一 runtime；
- Trae 技能、chat、MCP、API 只能调用 `guagua.py` 暴露的 runtime，不直接 import 角色 `agent.py`；
- 生产环境直接执行 `rXX/agent.py` 视为绕过，拒绝；
- `--draft` 只允许“标记为草稿”，**不能绕过 R04**；草稿也必须 R04，只是交付状态为 draft。

## 3. 统一任务契约

每个任务必须产出：

```text
out/<task_id>/
  result.json       # 结构化结论
  evidence.json     # 证据/引用/计算
  artifact.*        # 报告 / 决策卡 / 代码 / 方案 / 工单
  manifest.json     # 输入、owner、门禁、R04、时间、哈希
```

`result.json` 最小字段：

```json
{
  "task_id": "...",
  "role": "rXX",
  "owner": "...",
  "status": "done|draft|blocked",
  "summary": ["..."],
  "claims": [{"id": "...", "text": "...", "evidence": ["..."]}],
  "artifact": "artifact.html",
  "boundary": "...",
  "next": "..."
}
```

`evidence.json` 最小字段：

```json
{
  "claims": [
    {"id": "...", "quote": "...", "source_id": "...", "span": "..."}
  ],
  "numbers": [{"value": 0, "source_id": "...", "quote": "..."}]
}
```

## 4. 角色分类与门禁

| 类型 | 角色 | 门禁 |
|---|---|---|
| 报告/研究 | R01/R05/R06 | 证据 + 文笔 + 图表 + R04 |
| 决策/方案 | R02/R03/R04/R07/R10/R11/R12 | 证据 + 决策/设计/内容门禁 + R04 |
| 执行/运维 | R08/R09/R13–R20 | 结果 + 证据 + 角色专项门禁 + R04 |

所有类型共同要求：

- `result.json` / `evidence.json` / `artifact` / `manifest.json` 四件套；
- 结论必须有 evidence；
- 失败必须 blocked，不能假 done；
- R04 对所有任务出 pass/fail。

## 5. 报告生产线：目标形态

**唯一报告骨架** = `report_flow_all.html` 的结构：

```text
flow-paper
  cover（hero，272mm，内容宽与正文一致）
  summary（六条判断 + 三动作 + 读法/样本/回答/必读/证据）
  toc（PART I–III）
  sections（flow 连续，不按 A4 页切）
  action（谁/何时/停止线）
  appendix（55 条来源，1 页两栏）
  footer（logo 左，机构/日期右）
```

### 目标路径

```text
guagua.py report
  → report_cli（默认 layout=flow, theme=consulting）
  → report_flow.run
  → build_sections_contract(layout=flow, theme=consulting)
  → core.report_theme.flow.render_flow(contract)   # 直接出，不经过 report.html
  → report_bridge.write_markdown / render_pdf
  → 页码后处理
```

### 关键要求

- 不再用 `flow_all.py` 做“先生成固定 A4 再转换”；
- `flow_all.py` 只作为参考/回归 fixture，不进入生产；
- 所有报告只换内容，不换骨架；
- 默认主题 = `consulting`，默认 layout = `flow`；
- 摘要必填项由 `configs/report_flow.yaml` 校验；
- 附录 1 页、footer 小页脚、cover 内容宽与正文一致；
- PDF 页码由导出后处理，不在 HTML 写死；
- 报告 R04 必须审：证据、数据、图表、版式、文笔、盲评。

## 6. 当前 `report_flow_all.html` 的真实生产路径

现在不是系统默认，是 v3 工作区脚本：

```text
workspace/seasoning_v3_2026-11-19/facts.py
workspace/seasoning_v3_2026-11-19/charts.py
workspace/seasoning_v3_2026-11-19/kit.py
        ↓
workspace/seasoning_v3_2026-11-19/make.py
        ↓
report.html（固定 A4 页）
        ↓
workspace/seasoning_v3_2026-11-19/flow_all.py
        ↓
report_flow_all.html
        ↓
Chrome headless → report_flow_all.pdf
        ↓
PyMuPDF 盖页码
```

问题：

- `flow_all.py` 是 v3 专用转换器，不是 core；
- `make.py` / `kit.py` 是 v3 专用；
- 换项目就不可复用；
- 默认 `guagua.py report` 不走这条。

目标：把 `flow_all.py` 的转换逻辑上收为 `core.report_theme.flow` 的**直接渲染**，`flow_all.py` 退役。

## 7. 迁移顺序

1. **报告线**：`guagua.py report` 默认 `theme=consulting, layout=flow`，直接出同骨架；
2. **契约**：`report_flow` 接 `evidence.json` / `argument_plan.json` / `prose_critic`；
3. **全角色**：`call/dispatch/plan` 统一走 runtime；所有任务四件套；
4. **R04**：所有任务 R04；内部草稿也审；
5. **入口**：Trae/chat/MCP/API 包到 `guagua.py` runtime；
6. **文档**：README/SKILL/REPORT-STANDARD/REPORT-LINES/Trae 技能同步；
7. **测试**：一条 `guagua.py report` 端到端 + 20 角色四件套 + R04 拒绝用例。

## 8. 验收

- `python guagua.py report ... --pdf` 直接产出 `report_flow_all.html` 同骨架；
- 不再调用 `flow_all.py`；
- 20 角色所有任务都有 `result/evidence/artifact/manifest`；
- 所有任务 R04 有 pass/fail；失败不完成；
- 直接 `agent.py` 调用被拒绝；
- Trae/chat/MCP/API 与 `guagua.py` 同一行为；
- 文档与 Trae 技能说明同步。
