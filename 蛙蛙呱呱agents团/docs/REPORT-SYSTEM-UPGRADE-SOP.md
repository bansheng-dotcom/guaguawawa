# 报告系统升级 SOP（v1.0）

> status: ARCHIVED · 2026-11-26
> 说明：本文提出的 evidence_graph / argument_plan / spec_extract / prose_critic
> 已于 2026-11-26 删除（未接入产线）。当前正文门禁见 F10/F12 与 `prose_style`。

> 目标：把“能写出一份报告”升级为“任何分析都按同一最低标准产出”的报告工厂。  
> 适用范围：R01 报告产线、R04 验收、`core/report_theme/*`、`core/prose_*`。

## 0. 结论先行

当前系统缺的不是排版，也不是字数，而是四层基础设施：

1. **证据图**：claim → source → quote → span，数字可逐句回溯；
2. **论证规划**：每节先定 claim tree，不共用一套三段模板；
3. **盲评官**：20 节逐节盲评 + 跨节重复检测，不只看 prose_style；
4. **自动 spec**：从来源抽 claim/evidence，不靠人手写 `prose_specs.py`。

本 SOP 的顺序是：**证据图 → 规划器 → 盲评 → 自动 spec → flow 产线 → 回归**。

---

## 1. 参考的公开做法

- 证据图：claim/source/evidence/stance（supports / contradicts / context）与“无证据、缺来源、支持与反驳并存”检查，见 [Evidence Graph Studio](https://github.com/paladini/evidence-graph-studio)。
- 引用是否真的支持 claim：报告生成评估工具把“citation support”作为独立指标，见 [faerie-eval](https://pypi.org/project/faerie-eval/)。
- 结构化论证：Minto 金字塔/SCQA，先结论、再分组支撑、再回答疑问，见 [Monash Minto 样本](https://www.monash.edu/student-academic-success/excel-at-writing/annotated-assessment-samples/business-and-economics/business-paper-using-the-minto-approach)。
- 评审偏差：LLM-as-judge 存在位置/长度/自偏好偏差，必须盲评、成对比较、固定 rubric，见 [LLM-As-A-Judge 综述](https://www.scilit.com/publications/5f35c4122b3c863cbc9652b7edd7e2c4)。
- 文本重复/多样性：跨文档 n-gram 重复与多样性指标应作为独立质量维度，见 [Text Diversity Measurement](https://aclanthology.org/2025.ijcnlp-demo.5/)。
- 证券研报合规：来源、数据、结论可追溯是执业规范要求，见 [发布证券研究报告执业规范](https://www.guosen.com.cn/download/201602/05/2458.pdf)。

---

## 2. 目标架构

```text
TaskFrame
  ↓
SourceLedger（50+，饱和）
  ↓
EvidenceGraph（claim / source / quote / span / stance）
  ↓
CoveragePlan（维度 × 单元 × 页数）
  ↓
Confirmation（用户确认）
  ↓
ArgumentPlan（每节 claim tree + 论证类型）
  ↓
ProseDraft（R01 / generator）
  ↓
ProseCritic（20 节盲评 + 重复检测 + 引用支撑）
  ↓
FlowRender（HTML 一条流 + PDF 自动分页）
  ↓
R04（覆盖/数据/图表/版式/文笔/证据）
```

---

## 3. 数据契约

### 3.1 EvidenceGraph

```json
{
  "schema": "dsh.evidence_graph/v1",
  "sources": [
    {"id": "S05", "title": "...", "url": "...", "grade": "A", "date": "2025-01-01"}
  ],
  "claims": [
    {
      "id": "C017",
      "section": "s3",
      "text": "酱油是唯一又大又在涨的品类",
      "evidence": [
        {"source_id": "S05", "stance": "supports",
         "quote": "份额 20.68%，同比 +0.26pp", "span": "p.3"}
      ],
      "rival": "只是促销换手",
      "discriminator": "下一期份额是否继续 +0.26pp",
      "action": "先上 1 个零添加酱油 SKU",
      "boundary": "全国监测口径，不含本地餐饮",
      "estimated": false
    }
  ]
}
```

硬规则：

- `stance` 只能是 `supports/contradicts/context`；
- 每个 claim 至少 1 条 `supports`；
- 每个数字必须能在至少一条 `quote` 中找到；
- `estimated: true` 的数字必须带 `*`，且不能作为唯一支撑；
- 缺 `rival` / `discriminator` / `boundary` 的 claim 不允许进入 `ArgumentPlan`。

### 3.2 ArgumentPlan

```json
{
  "schema": "dsh.argument_plan/v1",
  "sections": [
    {
      "id": "s3",
      "type": "causal",
      "main": "C017",
      "supports": ["C018", "C019"],
      "rival": "C020",
      "discriminator": "下一期酱油份额",
      "action": "先上零添加 SKU",
      "boundary": "全国监测口径"
    }
  ]
}
```

论证类型：`causal` / `tradeoff` / `counterintuitive` / `path` / `risk` / `scenario` / `comparison`。  
同一类型不能连续超过 2 节；20 节至少覆盖 5 种类型。

### 3.3 ProseCritic

每节 7 维，100 分：

| 维度 | 分 |
|---|---|
| 判断力 | 20 |
| 机理 | 20 |
| 判别/证伪 | 15 |
| 具体性 | 15 |
| 反方/边界 | 10 |
| 节奏/人称 | 10 |
| 证据密度 | 10 |

额外硬扣分：

- 跨节 8-gram 重复 >3 次；
- 固定过渡句命中；
- 数字无法回溯到 evidence；
- 无 `rival` 或 `discriminator`。

---

## 4. 工作包

### P0-1 证据图

- 新增 `core/evidence_graph.py`；
- 支持 `add_claim` / `validate` / `audit_text` / `traceability`；
- 把 v3 的 facts/specs 迁成 graph（先人工，后自动）；
- R04 加 `evidence` 层：数字回不到 quote 直接 BLOCK。

验收：

- 20 节正文数字可追溯率 100%；
- 缺来源/缺 stance/支持与反驳并存 = 0。

### P0-2 论证规划

- 新增 `core/argument_plan.py`；
- 按 `kicker` 自动选类型；
- 每节输出 main/supports/rival/discriminator/action/boundary；
- 生成器只消费 plan，不再套统一三段。

验收：

- 20 节类型 ≥5 种；
- 连续同类型 ≤2；
- 跨节 8-gram 重复 = 0。

### P0-3 盲评官

- 新增 `core/prose_critic.py`；
- 支持 `score(text)`、`compare(a,b)`、`audit_sections(bodies)`；
- 20 节逐节评分；与水果同题节盲评；
- 低于 85 分退回。

验收：

- 20/20 ≥85；
- 重复 BLOCK = 0；
- 盲评记录留档。

### P1-1 自动 spec

- 新增 `core/spec_extract.py`；
- 输入 EvidenceGraph，输出 `SPECS`；
- 每个字段必须挂 claim/quote；
- 冲突 claim 进 `review_queue`，不自动写。

验收：

- 17 节 spec 不再手写；
- 每节 spec 的每个数字都有 quote/span；
- 冲突项有 review_queue。

### P1-2 Flow 产线

- `guagua.py report` 支持 `--layout flow`；
- `contract["layout"]="flow"` 直接走 `core.report_theme.flow`；
- 摘要必填项校验；
- 附录 1 页；
- PDF 目录页码两遍回填。

验收：

- 一条命令出 flow HTML + PDF；
- 无 A4 页卡片；
- 附录 1 页；
- TOC 页码正确。

### P2 回归

- `evals/report_bench/`：水果/调味料/奶食品/预制菜；
- 每次改生成器跑：盲评分、重复率、可追溯率、flow 页数；
- 任一指标退化 >5% 阻止合并。

---

## 5. 两周执行表

| 天 | 工作 | 产出 |
|---|---|---|
| 1–2 | EvidenceGraph schema + v3 迁移 | `evidence_graph.json` |
| 3–5 | spec_extract | `specs.auto.json` |
| 6–8 | argument_plan + 去三段模板 | `argument_plan.json` |
| 9–10 | prose_critic 20 节盲评 + 重复检测 | `prose_critic.json` |
| 11–12 | flow 产线 + 附录/TOC | `report_flow_all.pdf` |
| 13–14 | 四行业回归 | `report_bench.json` |

---

## 6. 风险

| 风险 | 处理 |
|---|---|
| 证据图人工成本高 | 先 v3 迁移，再自动抽取 |
| LLM 评审偏差 | 盲评、成对、固定 rubric、双评审 |
| 自动 spec 幻觉 | 只允许 quote 内数字；冲突进 review_queue |
| 模板句复发 | 8-gram 重复 + 固定句黑名单 |
| flow 打印失控 | `break-inside: avoid` + 附录固定 1 页 |
| 页数/目录错 | 两遍排版，先 PDF 后回填 |

---

## 7. 完成定义

- 20 节全部由 `ArgumentPlan → ProseDraft` 生成；
- 20/20 盲评 ≥85；
- 数字可追溯率 100%；
- 跨节 8-gram 重复 = 0；
- `guagua.py report --layout flow` 一条命令出 HTML/PDF；
- R04 六层 PASS。
