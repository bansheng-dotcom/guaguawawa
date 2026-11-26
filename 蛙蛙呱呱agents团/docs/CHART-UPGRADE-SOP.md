# 报告产线下游收敛 SOP（v5.0 · 定稿）

> status: ARCHIVED · 2026-11-26
> 说明：本文是早期升级计划，其中 `core/gate.py` 统一门禁层未按此实现；
> 现行门禁为 `check_report_flow`（F1–F12）、`check_charts_pro`、`check_gates`。
> 当前口径见 `docs/CORE-MAP.md` 与 `docs/_migration/wiring-truth.md`。

> 三条线外壳不动，内脏三段（契约 / 选型 / 门禁）收敛成一套。
> 核心问题（按优先级）：①图表太单调 ②数字/证据不可信 ③系统越改越乱。
> 三条硬约束：三条线任何一条都不能断；已有产出可以变，只要更好；可以系统级重构。

---

## 0. 改什么、不改什么（一句话）

**改**：三条线各自通向渲染器之前的三件事——交的契约长什么样、怎么选图、出报告前过什么校验。
**不改**：命令、入口、上游取数方式、渲染器、产出格式、三条线的存续。

**渲染不收敛**：前两条线（拆卡线 / A 线）共享 `report_flow → report_renderer`；第三条线（`report flow`）用 `report_theme.kit + charts_pro`。两套渲染器是它们各自的"外壳"，本版不动。

---

## 1. 系统真相（三条线现状，已核验）

| 线 | 入口 | 契约 | 选型 | 门禁 | 渲染 |
|---|---|---|---|---|---|
| 拆卡线 | `run-line --claims` | 卡片 → claims → sections | `chart_grammar`/`chooser`（关键词猜） | `cells_claims` + `quality_gate`（不阻断） | `report_flow → report_renderer` |
| A 数据线 | `run-line --dir` | decision 契约 → sections | `decision.choose_chart`（relation，**已是正确答案**） | `decision.validate` + `bind` | `report_flow → report_renderer` |
| flow 线 | `report flow --project` | `facts.SECTIONS` + `chart_spec` | **作者直接写 chart_spec**（最纯粹的人选定） | `r04_audit` + `prose_style`（`gate_hard` 默认 False） | `report_theme.kit + charts_pro` |

**六个已核验事实：**

- **F1** 前两条线尾部共享 `report_flow.run`；flow 线是独立渲染器（`flow_report._assemble` 用 `kit`）。
- **F2** A 线的选型已经正确（`decision.choose_chart` 读 `chart_by_relation.yaml`）。
- **F3** flow 线已经是"作者选定图型"——它没有 chooser，作者直接交 `chart_spec`，`charts_pro` 渲染。这其实就是我们要的目标形态之一。
- **F4** 拆卡线两座数据岛共享 `number_id`：collect 产 `raw.*`（有 entity/period），渲染读 `evidence_pack`（拷贝）。join 543/555，**291 个干净 entity**。
- **F5** 门禁存在但不阻断：拆卡线 112 格 89 缺陷照发；flow 线 `gate_hard` 默认 False。
- **F6** 三条线里只有拆卡线有黄金语料；A 线只有单测无端到端快照；flow 线有 `baselines/_golden_flow_specfruit/`（原 `examples/spec-fruit` 的产物，源已下线）。

---

## 2. 收敛目标（内脏三段，各成一套）

```
三条线（外壳不动）
  拆卡线 / A 线 / flow 线
        │
        ▼  统一契约：section{relation, comparison, intent, chosen, why_this_chart, data_refs, dims}
        ▼  统一选型：作者选定 + relation 白名单（configs/chart_by_relation.yaml）校验
        ▼  统一门禁：gate.py（变更台账 + 口径 + 图拟合 + 绑定 + 引文）
        │
        ▼  各自渲染器（report_renderer / kit）——不收敛
```

---

## 3. 四条不变量

**I1 变更台账**：`content_hash` 不是"锁"，是"台账"——每次输出 diff 都必须附"改了什么、为什么更好"。变好是允许的，静默漂移是禁止的。
**I2 上游两套**：取数方式不改，不把网页证据和本地数据并成一张表。
**I3 单一选型**：relation→allowed 只有一份来源（`chart_by_relation.yaml`），作者从候选面板选，规则只验。
**I4 单一门禁**：三条线出报告前都过同一个 `gate.py`，不通过就不渲染。

---

## 4. 六步（约 11.5 人日）

| 步 | 做什么 | 工时 | 退出条件 | 回滚 |
|---|---|---|---|---|
| S0 三线快照 + 台账 | 三条线各一份黄金语料；content_hash 变台账 | 1d | 三条线 hash 可复现 | 只读 |
| S1 接门禁（拆卡线先行） | 口径/图表/台账三道门接阻断，存量豁免 | 1.5d | warn 过 / block 拦 | `GATE_MODE=warn\|block` |
| S2 接桥 | `evidence_pack` join `raw.rows` 补 entity | 0.5d | join ≥95%，291 entity 进图 | 只改编译 |
| S3 统一契约 | 定义 chart 契约 v2，三条线都交同一形状 | 2.5d | 三条线产出同一契约 | 兼容层 |
| S4 统一选型 | 拆卡线换掉 grammar/chooser；A线/flow线补字段；候选面板 | 2.5d | 三条线都走 relation 白名单 + 作者选定 | `CHART_ENGINE=legacy\|v2` |
| S5 统一门禁 | 单一 `gate.py`，三条线都过 | 2.5d | 三条线同一门禁且阻断 | 门禁回退 |
| S6 清死代码 | 删 4 个失去消费者的旧答案 | 1d | 全绿，孤儿 0 | git revert |

---

## 5. 各步细节

### S0 三线快照 + 台账（1d）
- 拆卡线黄金语料：呼包鄂、小码女装 `out/`、`out2/`；
- A 线：补一份合成 CSV 快照（跑 `run-line --dir`，存 `contract.json`）——F6 的补课；
- flow 线：`baselines/_golden_flow_specfruit/`；
- `content_hash` 改为**台账**：记录每次 diff + 附解释；`check_content.py` 从"阻断 diff"改成"阻断无解释的 diff"。

### S1 接门禁（拆卡线先行，1.5d）
| 门 | 判据 | 实现 |
|---|---|---|
| G1 口径 | `problems/cells ≤ 0.2`（当前 0.79） | `cells_claims.audit_cards` |
| G2 台账 | 黄金语料 diff 必须有解释 | `scripts/check_content.py` |
| G3 图表 | mark 在 relation 白名单；`chart_units.sanitize` 通过 | `chart_by_relation.yaml` + `chart_units` |
存量豁免：`gates.yaml` 写原因 + 到期日，过期失效。

### S2 接桥（0.5d）
`compile_agent_report` 用 `number_id` join `raw.rows`，补 `entity`/`scope`/`value_base`；join 不上的标 `dims_missing`。

### S3 统一契约（2.5d）
chart 契约 v2（三条线都交）：
```json
{
  "relation": "ranking",
  "comparison": {"kind": "compare_two_points", "left": "寿光", "right": "包头", "metric": "大白菜批发价"},
  "intent": "比较大小",
  "chosen": "dumbbell",
  "why_this_chart": "本节问三地价差，哑铃图直接编码同一品类两地价差",
  "data_refs": ["r03:N25", "r03:N26"],
  "dims": [{"name": "city", "type": "categorical"}]
}
```
- 拆卡线：卡片补 `relation`/`intent`/`why_this_chart`；
- A 线：`comparison` 已有，补 `relation`（由 `comparison_to_relation` 映射）与 `why_this_chart`；
- flow 线：`chart_spec.type` → `chosen`，补 `relation`/`intent`/`why_this_chart`。

### S4 统一选型（2.5d）
- 拆卡线：`chart_grammar`/`chooser` 换成"候选面板 + 作者选定"（候选来自 `chart_by_relation.yaml`，最多 3 个）；
- A 线：`decision.choose_chart` 已对，补候选面板 + `why_this_chart`；
- flow 线：已是作者选定，只补字段 + 过白名单校验，不动它写 spec 的方式；
- 完成后 `chart_grammar`/`chart_chooser` 失去唯一消费者。

### S5 统一门禁（2.5d）
单一 `core/gate.py`，三条线渲染前都过，按序：
1. 台账（diff 有解释）
2. 口径（每条 fact 有 scope/currency/price_basis/denominator + measure 在册，折叠 `cells_claims`）
3. 图拟合（relation×mark 合法；二维只在 ≥2 维时允许；跨源不画趋势；`why_this_chart` 对齐本节问题）
4. 绑定（拆卡线 question→section；A 线 decision→finding；flow 线 r04_audit 五层保留为 gate 的一层）
5. 引文（复用 `source_verify`）

### S6 清死代码（1d）
| 对象 | 理由 |
|---|---|
| `core/charts/chart_grammar.py`、`core/charts/chart_chooser.py` | S4 后失去唯一消费者 |
| `core/charts/chart_plan.py` | 仅 r01 技能引用，改指向 `decision` |
| `configs/chart_type_by_question.json` | 0 引用 |
| `core/data/data_shape.py` 重复映射 | 保留 `fits`，删重复表 |

> 净减少：**模块 -3、配置 -1**。同 PR 更新 `.convergence-baseline.json`、`docs/CHART-GRAMMAR.md`、`gen_agent_packs`、`sync_dsh_skills`。

---

## 6. 已被否决的方案

| 方案 | 为什么否 |
|---|---|
| 上游并成一张表 | 网页证据与本地数据输入不同，伪统一 |
| 渲染器并成一套 | flow 线的 kit 是它的视觉外壳，动它风险大、收益小 |
| 只修拆卡线 | 你明确三条线都怕断，且问题①②同根 |
| 单一自动选型 | 自动推荐向通用图收敛（HCI 证据） |
| 新增 `analytic/v1` | join 就够，不必第 7 套抽象 |
| 大重写 | second-system；内脏三段逐块收敛即可 |

---

## 7. 影响：直接 / 二阶 / 三阶

| 面 | 一阶 | 二阶 | 三阶 |
|---|---|---|---|
| 契约 | 三条线同一 section/chart 形状 | 三套作者（卡片/decision/facts）都要改，短期返工 | 新功能只写一处，三线受益 |
| 选型 | 权威 7→1，作者选定 + 白名单校验 | grammar/chooser 删除触碰拆卡线热路径 | 加图型只改一处 yaml |
| 门禁 | 三条线同一阻断 | 存量报告（89 缺陷）出不来，需豁免 | 质量升但交付变慢，可能被绕开 |
| 数据 | join 让 291 数字有 entity | A 线快照从无到有，暴露未测路径 | 三线同源后报告可复算 |
| 维护 | 模块 -3 | 单点门禁，一处错全错 | 收敛疲劳，需季度审计 |
| 读者 | 图更贴问题 | 二维图误读率上升 | 要求交互，超出静态报告 |

对冲：S4/S5 影子对比 + 台账护栏；存量豁免 + 增量严管；三线快照；季度净减少审计。

---

## 8. 指标与 DoD（验收 = 可测的"更好"，不是"0 diff"）

| 指标 | 基线 | 目标 |
|---|---|---|
| 选型权威 | 7 | 1 |
| 下游契约 | 3 套 | 1 套 |
| 门禁 | 3 套且不阻断 | 1 套且阻断 |
| join 覆盖率 | 97.8% | ≥95% 且不降 |
| 带干净 entity 数字 | 0 | ≥291 |
| 口径缺陷密度 | 0.79 条/格 | ≤0.2 |
| 引文核验率 | 101/163 | 上升 |
| intent 判对率 | — | ≥80% |
| 二维覆盖（合格节） | 0 | ≥80% |
| 图比表多信息（盲测） | — | 10 中 ≥7 |
| 台账 | — | 每处 diff 有解释 |
| 死代码 | 4 | 0 |

**DoD**：12 项全绿 + 三条线各跑通一份端到端 + R04 签字 + 回滚演练。

---

## 9. 回滚

三级开关：`GATE_MODE=warn|block`、`CHART_ENGINE=legacy|v2`、`section.chart_engine=legacy`。
自动回滚：台账 diff 无解释、页数 >+15%、出报告失败、缺陷密度上升。
演练：S1/S5 各一次，验证降级 warn 后三条线仍可出。

---

## 10. 角色与排期

| 角色 | 职责 |
|---|---|
| R01 | 签发、门禁策略、豁免 |
| R04 | 独立评审、回滚签字 |
| R06 | 口径门禁行级证据、relation 标注规范 |
| R18 | 接桥（join）、Row 视图、A 线快照 |
| R09 | 契约 v2、统一选型、统一门禁、影子对比 |
| R10 | 版面基线（两条渲染器各一份） |

排期：第 1 周 S0–S2；第 2 周 S3–S4；第 3 周 S5–S6；第 4 周观察。

---

## 11. 不做清单

- 不砍任何一条线；不并上游数据表；不并渲染器；
- 不新增数据抽象、不新增选型模块（复用 `decision` + `chart_by_relation.yaml`）；
- 不让规则替作者决定图型（只验）；不为二维而二维；不跨源拼趋势线；不做交互图。

---

## 12. 检查单

- [ ] S0：三条线各一份黄金语料可复现；content_hash 已改台账
- [ ] S1：三道门阈值 + 豁免到期日；warn 过 / block 拦
- [ ] S2：join ≥95%，291 entity 进 pack
- [ ] S3：三条线产出同一 chart 契约 v2
- [ ] S4：三条线都走 relation 白名单 + 作者选定；grammar/chooser 无消费者
- [ ] S5：三条线渲染前过同一 gate.py 且阻断
- [ ] S6：4 个旧答案已删；baseline/docs/packs 同 PR 更新
- [ ] 全程：台账每处 diff 有解释；页数 ±10%；引文率不降
