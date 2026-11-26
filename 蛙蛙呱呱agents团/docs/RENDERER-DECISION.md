# 渲染器二选一：决策文档（2026-11-23）

> ⚠️ **本文档结论已更正（2026-11-23 晚）**：原结论"退役 kit + flow --project"是**错的**。
> 真实情况是：`flow --project` 不是"第二个渲染器"，而是**项目代码的宿主**——
> `core/report/flow_report.py` 从 `--project` 目录加载 `facts.py` / `charts.py` /
> `prose_specs.py`，让项目代码留在项目文件夹、不进 `core/`。删掉它等于
> **拆了项目代码的家**，只会逼人把代码塞回 `core/`。
>
> 正确处理：**两条路径是分工（run-line 管项目数据 / flow --project 管项目代码），
> 都保留。** 下文保留为历史分析记录，结论见 §7。

> 对应 MASTER-UPGRADE-SOP S6。这一份只做"摆证据 + 给建议"，最终由你拍板。

---

## 1. 事实：两个渲染器的真实关系

**它们不是两个独立渲染器，而是共享 `report_theme/` 底座的两套页面编排。**

| 模块 | 行数 | 作用 |
|---|---|---|
| `report_theme/pages.py` | 730 | **共享底座**：`_cover` / `_summary` / `_toc` / `_page` / `_reading_blocks` |
| `report_theme/flow.py` | 161 | flow 版式：`flowify` / `render_flow` |
| `report_renderer.py` | 1599 | run-line 编排：`validate_contract` + `render_chart` + `render`，**用 pages.py** |
| `kit.py` | 648 | flow --project 编排：`cover / summary_page / toc_page / section_page / action_page / appendix_page / back_page` |
| `flow_report.py` | 245 | **项目代码加载器**：从 `--project` 目录加载 `facts.py` / `charts.py` / `prose_specs.py` |

**更正：`kit` 不是纯重复**——`pages.py` 有 cover/summary/toc，但 `kit` 还多
`action_page` / `appendix_page` / `back_page`。更要紧的是 `flow_report.py`：
它是把项目代码挡在 `core/` 之外的唯一机制。

---

## 2. 逐项对比

| 维度 | report_renderer | kit |
|---|---|---|
| 契约校验 | ✅ `validate_contract`（图表必填字段、单位、来源） | ❌ 无 |
| 图表能力 | ✅ 70 型 charts_pro（经 compat） | ✅ charts_pro（直接 spec） |
| 封面/目录/摘要 | ✅ pages.py 已有 | ✅ 自己重写 |
| 输入形态 | contract（meta/sections/chart） | facts.py（META/KPI/SUMMARY/ACTIONS） |
| 调用方 | `report_flow.run`（run-line：拆卡分支 + 数据分支） | `flow_report.build`（flow --project） |
| 产线归属 | **两个分支都汇到它** | 第三条路径（facts.py） |
| 依赖 | charts_pro.compat / flow / pages | report_marks / report_theme |

---

## 3. 建议：选 `report_renderer`，退役 `kit`

**理由：**

1. **归属对**：统一线的两个分支（拆卡 + 喂数据）已经汇到 `report_flow → report_renderer`；`kit` 只服务 `flow --project` 这条第三条路径。
2. **能力不丢**：`kit` 的封面/目录/摘要，`pages.py` 已有；真缺什么再补到 `pages.py`（一份实现，两处受益）。
3. **有契约校验**：`report_renderer` 有 `validate_contract`，`kit` 没有——统一线必须要有校验。

**代价（诚实说）：**

- `flow --project`（facts.py）要改走 `report_renderer`，需要把 facts.py 转成 contract：
  `facts.py → facts_to_ir → resolve → contract → report_renderer`。
  这条链的适配器（`facts_to_ir`）已经写好了，但**从 IR 到 contract 的转换器还没有**。
- `kit` 退役前要确认：`flow --project` 的用户（如果有）不受影响。

---

## 4. 迁移路径（如果选 report_renderer）

> **2026-11-23 更新**：第 1 步已就绪（`core/ir_to_contract.py`），并做了**影子渲染对比**。
> **结论：还不能切**——见 4.1。

| 步 | 做什么 | 风险 |
|---|---|---|
| 1 ✅ | `resolved_model → contract`（`core/ir_to_contract.py`） | 已完成 |
| 1b ✅ | `facts.py → IR`（`ir_adapters.facts_module_to_ir`） | 已完成，有损 |
| 3 ✅ | 影子对比（`scripts/render_flow_via_report_flow.py`） | **已跑，发现差距** |
| 2 | `flow_report.build` 改为调用 `report_flow.render` | **阻塞：见 4.1** |
| 4 | `kit` 标 `deprecated` | 待 2 |
| 5 | 删 kit.py + 更新 REPORT-LINES.md | 待 4 |

### 4.1 影子对比结果（spec-fruit 实测）——**迁移会丢图，且丢能力**

同一份 `spec-fruit/facts.py`：

| | kit（现） | report_flow（新） |
|---|---|---|
| 图数 | **13** | 4（第一次跑） |

**挖到根因（比"丢图"更严重）**：

1. **两个渲染器的图表词汇表不同**
   - `charts_pro` spec（facts.py 用的）：`items / rows / matrix / series / nodes`
   - `report_renderer` contract（校验要求的）：`bars / cells / points / items`

2. **`report_renderer` 不认某些图型**
   - `symbol`、`network` 在 contract 校验里直接判"type 非法"
   - 也就是说：facts.py 里这两类图**迁过去会彻底丢失**

3. **要迁就得写 spec→contract 转换器**
   - matrix→cells、series→items、nodes/edges→?（无对应）
   - 且要为 symbol/network 扩展 `report_renderer` 的校验

**结论：迁移成本远高于"补几个 payload 键"。**

### 4.2 成本对比（决定性的）

| 方案 | 成本 | 能力影响 |
|---|---|---|
| **退役 `flow --project` + kit** | 低（删代码 + 更新文档） | 不丢能力（这条路径本来就只服务极少数场景） |
| **保留并迁移到 report_renderer** | 高（spec→contract 转换器 + 扩校验 + 补 symbol/network） | 迁移中会丢 symbol/network 图 |

**所以从工程成本看，推荐"退役 `flow --project`"，不是"迁移它"。**

**不建议**直接删 `kit`——先走"影子对比"，确认 `report_renderer` 能出等价报告再退役。

---

## 5. 如果你选 kit

需要做反向迁移：
- 把 `report_flow` 的 contract 转成 facts.py 结构；
- 把 `validate_contract` 移植到 kit；
- 两个分支的渲染路径全部改道。

**成本明显更高，且丢掉已有的契约校验。** 所以我不推荐。

---

## 6. 需要你回答的一个问题

**`flow --project`（facts.py）这条路径还要不要？**

- 要 → 按 §4 迁移（5 步）；
- 不要 → 直接退役 `flow --project` + `kit`，统一线只剩两个分支（拆卡 + 喂数据），`report_renderer` 是唯一渲染器。

回答这一个问题，S6 就能收尾。

---

## 7. 最终结论（2026-11-23 晚，已更正）

**两条路径都保留，分工明确：**

| 路径 | 管什么 | 项目代码放哪 |
|---|---|---|
| `report run-line --claims` | 项目自带**判断卡** | 不需要 |
| `report run-line --dir` | 项目自带**数据** | 不需要 |
| `report flow --project` | 项目自带**代码** | `projects/<项目>/{facts,charts,prose_specs}.py` |

**为什么不能删 `flow --project`**：它是「项目代码留在项目文件夹」的唯一加载器。
删掉它，项目要定制图/定制方法就只能改 `core/` → 正是历史上 `core/` 被业务内容
污染的原因。**先有家，才谈得上关门。**

**`core/` 的防线（保留）**：
- `configs/core_files.json` 文件白名单（新增模块必须显式加白）；
- `configs/business_terms_baseline.json` 业务词基线棘轮（新增命中即拦）。

**`kit` 与 `pages.py` 的关系（更正）**：`kit` 有 `action_page` / `appendix_page` /
`back_page`，`pages.py` 没有；它不是纯重复，保留。
