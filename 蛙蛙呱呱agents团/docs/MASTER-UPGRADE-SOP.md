# 系统升级总纲 SOP（v1.1 · 2026-11-23）

> 目标：**照着做不会偏。** 每层有"该做 / 不该做 / 验收"，每条有"改哪个文件"。
>
> **文档权威（改规则只改 MASTER，其余是分册/历史）：**
>
> | 文档 | 地位 |
> |---|---|
> | **MASTER-UPGRADE-SOP.md（本文）** | **唯一总纲**：决策、优先级、该做/不该做、验收 |
> | `docs/CHART-UPGRADE-SOP.md` | L3 图表层细节分册 |
> | `docs/AUTHORING-CONTRACT-SOP.md` | L2 语义层细节分册 |
> | `docs/DATA-SHAPE-SOP.md` | L1 数据形状分册 |
> | `交付/拆卡升级-SOP-2026-11-21.md` | L1 拆卡原始定义（v1.4，历史件） |
> | `docs/REPORT-*-UPGRADE-SOP.md` | 旧版，以本文为准 |
>
> 已并入本文并删除的：`UNIFIED-DECARD-SOP.md`（避免双写漂移）。

---

## 0. 边界

### 0.1 这份 SOP 管什么

| 管 | 说明 |
|---|---|
| 一条产线、两个分支的**接线** | 喂数据分支 / 拆卡分支 |
| 四层的**实现+接线+验收**三件齐 | 采集/语义/图表/呈现 |
| 拆卡 v1.4 的**具体规则全量保留** | 五轴、G1–G25、图合同、MECE、grain、证据、因果 |
| 采集契约（新增） | 拆卡的真正产出 |
| 代码边界（core/projects/samples） | 含样例迁出 |

### 0.2 这份 SOP 不管什么

| 不管 | 理由 |
|---|---|
| 重新设计拆卡骨架 | 设计层已成立（S1–S12 全过） |
| 自动切换图型 | 已实测证伪（关键词推断不可靠） |
| 统一两个渲染器 | 只做"二选一"，不做合并 |
| 扩图型库 | 70 型已够，缺的是"用起来" |
| 新增数据抽象 | raw/evidence_pack/pack 已够 |

### 0.3 执行纪律（三件齐）

**每层必须"实现 + 接线 + 验收"三件齐全；只实现不接线 = 摆设（G1–G25 就是反例）。**

---

## 1. 真实审计：需要 vs 不需要

### 1.1 需要的（12 项，这轮要做）

| # | 项 | 层 | 现状 |
|---|---|---|---|
| 1 | G1–G25 接进产线 | L1 | 写完没接线 |
| 2 | cells_filled 闭环 | L1 | 断 |
| 3 | 采集契约 | L1 | 缺 |
| 4 | shape_ok_ratio 门禁 | L1 | 缺 |
| 5 | 有数据分支反推业务线 | L1 | 只读列名 |
| 6 | 动态澄清 | L1 | 固定 12 问 |
| 7 | 因果阶真赋值 + 驱动树 | L1 | 空转 + 缺 |
| 8 | 三前端接产线 | L2 | 纯函数未接 |
| 9 | 语义一致性测试 | L2 | 缺 |
| 10 | chart_query 接主出图 | L3 | 孤儿 |
| 11 | 派生图门槛 + 图级 causal | L3 | 门槛 ≥2 点 |
| 12 | 渲染器二选一 + 门禁串一条 | L4 | 两渲染器并存 |

### 1.2 不需要的（6 项，别再碰）

| # | 项 | 理由 |
|---|---|---|
| 1 | 重做拆卡骨架 | S1–S12 已全过（102 格/6 视角/22 度量/L3） |
| 2 | 自动切换图型 | 实测把对的图改错 |
| 3 | 全自动选型 | 反模式 |
| 4 | 合并两个渲染器 | 风险大收益小 |
| 5 | 加图型 | 70 型够用 |
| 6 | 加数据抽象层 | 已有 raw/evidence_pack/pack |

### 1.3 已完成但没接线的（4 项，属于"需要的"）

`G1–G25` · `三前端` · `chart_query` · `semantic_pipeline` —— 都是写完没接，不是没写。

---

## 2. L1 采集层（拆卡 SOP v1.4 全量保留）

### 2.1 五轴（完整定义，不许简化）

| 轴 | 定义 | 合格判据 |
|---|---|---|
| **L0 问题树** | 总问题拆成互斥穷尽的子问题；每条结论先写"要成立，需要什么" | 子项相加=总体（构成类 100%）；无两子问重复；拆到"一个度量可答" |
| **L1 视角** | 谁在看；≥3 视角，每视角 ≥1 问 | 六类：消费者/门店/经销商/竞品/监管/供应链 |
| **L2 维度** | 六维网格：对象/空间/时间/结构/机制/边界 | 每维下钻：空间到盟市、品类到子类、时间 ≥2 期；不适用最多 2 维且写原因；每适用维 ≥2 格；单问 ≤24 格 |
| **L3 度量** | dbt 五类：simple/cumulative/ratio/derived/conversion | 必填参数齐（见 2.1.1）；**grain 先声明**；`non_additive_dimension` + `fill_nulls_with` 必填 |
| **L4 证据** | 三层：来源等级 A/B/C/D + 质量六维 + 三角验证 | 每格带 source_file/grade/period/unit/scope/calc；关键结论 ≥2 独立来源 |
| **L5 因果** | 三阶：A 关联 / I 干预 / C 反事实 | 机制结论必须标阶；A 阶不得写"导致/因为/带来"；写不出**驱动树** = 没到机制 |

#### 2.1.1 L3 度量五类必填参数

| 类型 | 必填 |
|---|---|
| simple | agg / expr / time_granularity |
| cumulative | input_metric / window / grain_to_date |
| ratio | numerator / denominator |
| derived | expr / input_metrics |
| conversion | base_metric / conversion_metric / window / entity |

#### 2.1.2 驱动树（必做）

**结果指标 = 驱动因子相乘/相加**（例：零售额 = 门店数 × 单店动销 × 客单）。
**写不出驱动树，说明还没到"机制"，只能进 hypotheses。**

#### 2.1.3 图合同（完整字段，不许砍）

```yaml
chart:
  chart_id: c1
  claim_to_prove: "图要证明的那句话（含数字）"
  why_visual_not_text: "为什么文字列不出形状"
  decision_role: dominant | supporting | optional
  focus_target: "读者该盯哪一处"
  required_metrics: [share]
  required_annotations: ["前五累计 37.4%", "其他=长尾"]
  failure_conditions: ["口径混用", "份额求和"]
  data_points: 6          # 必须 ≥ grain 覆盖
  causal_level: A | I | C # 这张图证明到哪一阶
```

### 2.2 G1–G25 完整清单（收格后必跑）

> 代码：`card_upgrade.gates()`。**现状：只被 scripts + 测试调用，生产不跑（本轮要接）。**

| 门 | 判据 |
|---|---|
| G1 覆盖率 | 已填/应有 ≥0.7 |
| G2 深度 | must 题 ≥1 格 L3 |
| G3 证据字段 | source_file + period + unit 齐 |
| G4 口径唯一 | 同 scope+period+measure 只一个值 |
| G5 诚实 | 非 filled 的格带 tried + why |
| G6 结构 | 覆盖维度 ≥4 |
| G7 度量代数 | ratio 不得在时间维求和/平均 |
| G8 图全量 | 每图 data_points ≥3 |
| G9 新鲜度 | stale 占比 ≤0.2 |
| G10 回流闭环 | 每条 backfill 有 resolution |
| G11 分支日志 | 每 must 问 ≥3 条 stop |
| G12 候选拆解 | 每问 ≥2 变体 + chosen |
| G13 视角 | ≥3 视角 |
| G14 MECE | 构成类加总=100%（或说明） |
| G15 因果阶 | 机制格 causal_level ∈ A/I/C；**且 level≥3 不得停在 A** |
| G16 度量参数 | derived/ratio/conversion 必填公式 |
| G17 grain | 每格声明 grain |
| G18 质量六维 | 每格六维齐 |
| G19 归属 | 每格有 owner；weak 卡 ≤50% |
| G20 协作状态 | 交付状态合法 |
| G21 签收 | 签收数 = 契约数 |
| G22 仲裁 | 冲突有 arbiter + verdict |
| G23 SLA | 耗时 ≤ sla_min |
| G24 账本 | plan/dispatch/handoff/gates 四类事件齐 |
| G25 未兑现 | 无未兑现的承诺 |

### 2.3 S1–S12 发卡前门禁（已接线，保留）

S1 格子数 8–24 / S2 深度 L3 / S3 视角 ≥3 / S4 候选拆解 ≥2 / S5 语义层覆盖 / S6 格字段 / S7 六维 / S8 契约 / S9 分支日志 / S10 交接 / S11 波次 / S12 格度量与 grain 在册 / DOR。

### 2.4 采集契约（新增，缺的就是这段）

```yaml
apiVersion: dsh.collection/v1
id: fact_category_priceband_channel
purpose: 证明「纸尿裤 60–100 元 × 天猫」是唯一量价双高格子
grain: [category, price_band, channel, year]
rows_expected: 450
min_points_per_cell: 3
properties:
  - {name: category, semanticType: dimension, logicalType: string}
  - {name: price_band, semanticType: dimension, enum: [0-50, 50-100, 100-200, 200-500, 500+]}
  - {name: retail_sales, semanticType: measure, unit: 亿元, caliber: 平台内成交额含税}
  - {name: share, semanticType: measure, unit: "%", formula: brand_sales/retail_sales@total}
quality: {min_coverage: 0.7, cross_check: "关键结论≥2来源"}
slaProperties: {freshness: 2025, frequency: annual}
acquisition:
  path: 平台榜单/行业报告/统计局
  availability: high|medium|low     # 必填
  degradation: 缺格标 unavailable，不画不补零
```

### 2.5 数据形状门禁（新增）

```
shape_ok_ratio = 同 metric ≥3 行的指标数 / 总指标数
≥0.5 通过 | 0.3–0.5 只许 1D 图 | <0.3 FAIL 并写缺哪一维
```

### 2.6 L1 该做 / 不该做 / 验收

| 该做 | 不该做 | 验收 |
|---|---|---|
| 接 G1–G25 到收格后 | 重做五轴 | 母婴重跑出 `post_gates.json` |
| 打通 fill_cells → cells_filled → cells_claims | 再写一个格子编译器 | 格子能编译成 claims |
| 产出采集契约 | 穷尽到 450 格却不填 availability | 每份报告有 contract |
| 因果阶真赋值 + 驱动树 | 让 G15 依赖 level≥3（永远不触发） | G15 能拦 A 阶机制 |
| 有数据分支反推业务线 | 只读列名 | 给 CSV 能说出业务线+缺口 |
| 动态澄清 10–20 问 | 固定 12 问 | 不同意图问到不同问题 |

### 2.7 采集层五段怎么做（含判据）

1. **意图理解**：动态澄清 10–20 问，每题带 `changes_decisions`；**判据：答案不改变拆卡的问题不问**。按意图类型选问——行业调研（决策/时间窗/地域/对比玩家/已有结论）、数据分析（数据覆盖期/口径归属/最想答的 3 问/已有工具）、选品决策（预算/渠道能力/毛利底线/失败承受度）、诊断复盘（异常点/已排除原因/可改杠杆）。
2. **业务线理解**：
   - 无数据：输出 `business_model`——价值链条 / 玩家分层与集中度 / 常见度量与口径陷阱 / **这条业务线的延伸方向**；
   - 有数据：读 schema 反推——列名→业务实体（`region` 是省还是大区？`amount` 是零售额还是 GMV？）、单位量级→口径（万元 vs 亿元；含税否）、粒度→每行代表什么、覆盖期→能否做趋势、缺哪维→与契约对齐；
   - 产物 `data_profile.json`：`{entities, grain, coverage, caliber, gaps}`。
3. **分析设计**：五轴（§2.1 全量判据）+ 驱动树（§2.1.2）。
4. **采集契约**：`dsh.collection/v1`（§2.4）；**`availability` 必填**——穷尽的终点是"可执行的最小数据集"，不是"更长的清单"。
5. **缺口降级**：有数据 → `data_profile` 对 `collection_contract` → `{缺维/缺期/缺粒度}`；无数据 → 按 `availability` 排序，先 high 再 medium，low 进未答清单；缺格不补零、不静默删，进口径页。

---

## 3. L2 语义层

### 3.1 现有资产（纯函数，可测）

`core/report_ir.py`（富 IR）· `core/ir_adapters.py`（三前端）· `core/semantic_pipeline.py`（resolve/panel/apply_decisions）· `configs/facts_schema.json`。

### 3.2 该做 / 不该做 / 验收

| 该做 | 不该做 | 验收 |
|---|---|---|
| 三前端接进 run-line（build_sections_contract 前先转 IR） | 改渲染器语义 | 渲染器读 resolved model |
| 语义一致性测试（同一 IR 两个渲染器抽检） | 加第二套语义 | 一致性测试过 |
| 守住"最小公共子集" | 把三写法所有字段塞进 IR | IR 字段数不膨胀 |

---

## 4. L3 图表层

### 4.1 现有资产

`chart_candidates.py`（relation→候选+validate）· `chart_payload.py`（facts→payload）· `chart_query.py`（panel→heatmap/line/share_bar，**孤儿**）· `charts_pro`（70 型）。

### 4.2 该做 / 不该做 / 验收

| 该做 | 不该做 | 验收 |
|---|---|---|
| chart_query 接主出图路径 | 自动切换图型 | 有矩阵的节出热力图 |
| 派生图门槛按关系分档（≥3/≥4） | 2 点图充数 | 1–2 点图不出 |
| 图合同补 causal_level | 再扩图型 | 图带因果阶 |
| chart_validation 进门禁 | 只诊断不拦 | 不合法的图 FAIL |

---

## 5. L4 呈现层

### 5.1 该做 / 不该做 / 验收

| 该做 | 不该做 | 验收 |
|---|---|---|
| 渲染器二选一（建议 report_renderer） | 合并两个渲染器 | 一条渲染路径 |
| 门禁串一条：L1→L2→L3→L4 | 门禁各自为政 | 一个入口出全部结果 |
| content_hash 作最终闸 | 改 content_hash 口径 | 零回归可验 |

### 5.2 结论（2026-11-23 已定）

**统一线渲染器 = `core/report_renderer`。** 依据：
- `docs/REPORT-LINES.md` 已写明它是「唯一 HTML 渲染器」；
- 两个分支（拆卡 / 喂数据）已经全走 `report_flow → report_renderer`；
- `kit` 的封面/目录/摘要在 `report_theme/pages.py` 已有。

**`kit` + `flow --project` 标为 legacy（不删，可逆）**：
- `core/flow_report.py` / `core/report_theme/kit.py` 已加 `.. deprecated::` 说明；
- 迁移评估见 `docs/RENDERER-DECISION.md`（结论：迁移成本高且会丢 symbol/network，不如退役）；
- 退役动作等业务确认后再做（删 kit + 更新 REPORT-LINES）。

---

## 6. 代码边界与迁移

| 层 | 放什么 | 规则 |
|---|---|---|
| `core/` | 通用引擎 | 出现业务词 → 不许放 |
| `projects/` | 业务数据 | semantic_layer/raw/grid/contract |
| `samples/`（新） | 样例数据 | 内蒙古等；**不在专家团路径** |

迁移：pk_* → samples/；拆 `prokit2`（基元留 core，fig_*+DS 搬）；spec.py 改 import；geo 改 lazy。
准入：`scripts/scan_business_terms.py --check` 进 CI。

---

## 7. 实施顺序（具体到文件）

| 步 | 改哪个文件/函数 | 退出条件 |
|---|---|---|
| S0 | `report_flow.run` 收格后调 `card_upgrade.gates()` | 出 `post_gates.json` |
| S1 | `card_upgrade.fill_cells` 写 `out_v3/cells_filled.json`；`cells_claims.build` 接进 collect | 格子→claims 通 |
| S2 | 新增 `core/collection_contract.py` + schema；拆卡产出 | 每报告有 contract |
| S3 | `report_flow.build_sections_contract` 前调 `claims_to_ir` + `resolve` | 渲染器读 resolved |
| S4 | `build_sections_contract` 增加 `chart_query.build(panel_rows)` 一级 | panel 节出热力图 |
| S5 | `card_upgrade._causal_for` 按维度赋 A/I/C；G15 去掉 level≥3 依赖；图合同加 causal_level | G15 能拦 A 阶 |
| S6 | `report_cli.cmd_run_line` 二选一；门禁串一条 | 一条闸 |
| S7 | 样例迁出 + `scan_business_terms --check` | 扫描器过 |

---

## 8. 二阶 / 三阶影响

| 变化 | 二阶 | 三阶 |
|---|---|---|
| G1–G25 接线 | 收格质量第一次被拦 | 不达标卡会退回，产线变慢但可信 |
| cells_filled 闭环 | 格子开始回来 | 报告从"头条数字"变"矩阵" |
| 采集契约 | 采什么可执行 | 契约资产化，口径漂移需版本 |
| 三前端接产线 | 语义单源 | 渲染器改造回归风险 |
| chart_query 接主路径 | 有矩阵的节出热力图 | 图型真正多样化 |
| 派生图门槛 | 2 点图消失 | 报告图数下降，但每张能读 |
| 渲染器二选一 | 维护简化 | 视觉返工 |
| 门禁串接 | 一条闸 | 报告先变少再变好 |

---

## 9. 回滚

| 开关 | 作用 |
|---|---|
| `GUAGUA_IR_TREAT=0/1` | 图型自动切换（默认关） |
| `AUTHORING_MODE=legacy/contract` | 三前端接入 |
| `GATES_MODE=post/off` | G1–G25 接线 |
| `content_hash` 基线 | 零回归闸 |

---

## 10. DoD（可勾选）

- [ ] G1–G25 收格后必跑，结果进 `manifest.gate.post`
- [ ] cells_filled 闭环通（格子→claims）
- [ ] 每份报告有采集契约，含 `availability`
- [ ] shape_ok_ratio 门禁生效
- [ ] 因果阶真赋值；G15 能拦 A 阶机制；图带 causal_level
- [ ] 驱动树产出
- [ ] 有数据分支产出 data_profile
- [ ] 三前端接产线；语义一致性测试过
- [ ] chart_query 接主路径；1–2 点图不出
- [ ] 一条渲染路径 + 一条门禁链
- [ ] core/ 无业务词；样例在 samples/

---

## 11. 不做清单（防止偏移）

1. 不重做拆卡骨架（S1–S12 已成立）
2. 不做自动切换图型（已证伪）
3. 不做全自动选型
4. 不合并两个渲染器
5. 不扩图型库
6. 不加数据抽象层
7. 不把样例数据留在 core
8. 不让因果阶停在 A
9. 不做"穷尽但不看可获取性"
10. 不重写五轴定义
