# R06 生成层：6 个 LLM 角色契约

> 这是把 `data-analysis-report-agent` 的「生成层」还原进 R06 的结果。
> R06 此前只有「校验层」（harness / contracts / review），缺「生成层」——本目录补齐。

## 核心原则（铁律）

**这些 agent 是「给 LLM 的角色契约」，不是 Python 代码。**
Python（`../../harness.py`、`../../contracts.py`、`../../review.py`）只做确定性校验；
LLM 按本目录 6 个角色的契约分工**推理生成**文字、图表规格、HTML。

一句话：**LLM 生成，Python 关笼子。** 生成和校验彻底分离，谁生成谁负责，谁校验谁裁决。

## 生成闭环（完整链路）

```
问题 + 数据 + 字段含义
   │
   ▼
① ReAct 分析（R06 skills：rootcause/abtest/explore/describe…）
   → analysis_material_pack（决策就绪的 findings + evidence + 边界）
   │
   ▼
② chart-spec-agent：每个图表 → chart_spec_pack（claim_to_prove + series + fail 条件）
   ▼
③ report-text-controller：报告问题拆成 bounded unit_packet + Chain of Verification
   ▼
④ report-text-editor：每 unit 反向写（证据→关系→结论→takeaway→标题），temperature=0
   ▼
⑤ report-text-adversarial-reviewer：独立语境挑战，3 类失败路由
   ▼
⑥ report-assembler：合并 text+chart，判关系，路由失败
   ▼
⑦ html-report-renderer：只复制批准字符串渲染 HTML
   ▼
harness/review 确定性校验（关笼子）
```

## 6 个角色职责（一句话）

| 角色 | 职责 | 禁止 |
|---|---|---|
| chart-spec-agent | 从结论选图表，产出可执行图表规格 | 不写正文、不重算、不渲染 |
| report-text-controller | 拆 unit、路由上下文、判定问题是否解决 | 不重算、不升级因果、不发明方案 |
| report-text-editor | 温度0写单个 unit 的完整句子 | 不查数据、不看全文、不写 HTML |
| report-text-adversarial-reviewer | 独立语境质疑，只给 verdict + 路由 | 不重写、不继承写手推理 |
| report-assembler | 仲裁 text-chart 关系，路由失败 | 不重算、不写新正文、不渲染 |
| html-report-renderer | 只复制批准字符串渲染 HTML | 不强化/缩短/新增分析声明 |

## 失败路由（关笼子的关键）

**文本评审 3 类（adversarial-reviewer）：**
- `evidence_does_not_support_conclusion` → 回 ReAct 分析
- `expression_title_or_line_fit` → 回 editor 改写
- `no_report_value` → controller 丢弃（omitted_units）

**组装仲裁 4 类（assembler）：**
- `analysis` → 回 ReAct（数据/粒度/分母冲突）
- `text_agent` → 回 editor（措辞/标题/行宽）
- `chart_agent` → 回 chart-spec（图表形式/标注/密度）
- `drop_or_bounded` → 降级为可拆卸模块，不进主摘要

## harness 校验时机（每个阶段都要过门禁）

| 阶段 | 校验 |
|---|---|
| 分析计划 | `../../harness.py`（plan 类门禁，R06 已有） |
| 数据 | `../../harness.py dataset` |
| 文本包 | `../../review.py`（PM/数据对抗评审，R06 已有） |
| 图表规格 | `../../contracts.py validate`（图表 schema） |
| 最终 HTML | 结构/颜色/字符串完整性人工复核 |

**凡失败必回路由到对应角色，不许在渲染层掩盖。**

## 温度权威

每个 agent 的 `manifest.yaml` 是唯一温度来源。全部 `0.0`（确定性），提示词文本不是温度来源。
