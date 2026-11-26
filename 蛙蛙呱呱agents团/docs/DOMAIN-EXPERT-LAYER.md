# 领域专家层（DOMAIN-EXPERT-LAYER）

> status: ARCHIVED · 2026-11-26
> 说明：分析引擎 `core/analysis_lab.py`（557 行）已于 2026-11-26 删除，未接入任何产线；
> 统计方法由 r06 / r19 / r15 的技能包承担。当前领域层口径见 `docs/CORE-MAP.md`。

> 解决的问题：产线会算、会论证，但只对「已有数据的项目」有效；换一条业务线，
> 就不知道该看什么指标、用什么方法、先验证什么。
> 本层不碰数据，只解决「懂不懂这个领域」与「会不会做这条业务线的分析设计」。

---

## 一、三层结构

```text
knowledge/roles/r01..r20.json      20 个角色的领域包（书/方法/指标/决策/远见/误判/章节）
        │
core/domain_pack.py                业务线意图 → 行业假设 + 任务编队 + 分析设计 + 数据清单
        │
core/analysis_lab.py               归因 / A-B / DiD / 弹性 / 队列（可复算引擎）
        │
report produce（原有产线）          数据到位后出报告；证据等级决定措辞强度
```

---

## 二、角色领域包 schema

每个 `knowledge/roles/rXX.json`：

| 字段 | 作用 |
|---|---|
| `role/name/title/domain` | 角色与能力域 |
| `keywords` | 业务线匹配词 |
| `books[]` | 5 本：`title/author/year/lang/concept/move`；中英各至少 1 本 |
| `methods[]` | 6 条：`name/formula/when`；formula 必须是公式或算法 |
| `kpis[]` | 6 个核心指标 |
| `decisions[]` | 4 类决策 |
| `foresight[]` | 3 个领先信号 |
| `failure_modes[]` | 4 个常见误判 |
| `report_sections[]` | 6 个报告必备章节 |

生成：`python scripts/build_role_packs.py`（源数据在同一脚本里，改源再生成）。
校验：`python scripts/check_role_packs.py`（20/20、书≥5、方法≥6、公式长度、指标/决策/误判数量）。

---

## 三、行业假设 schema

`core/domain_pack.py::INDUSTRIES`，每条：

| 字段 | 作用 |
|---|---|
| `keywords` | 业务线关键词 |
| `hypothesis` | 这条业务线的胜负手一句话 |
| `critical` | 先验证什么 |
| `kpis/questions` | 指标树与关键问题 |
| `scenarios` | 两个不确定性轴 |
| `benchmarks` | 行业基准区间（必须标「需校准」） |
| `data` | 数据清单：表/字段/用途 |
| `role_boost` | 这条业务线优先哪几个角色 |

新增行业：在 `INDUSTRIES` 加一条，跑
`python guagua.py domain --intent "<业务线>"` 自检；不需要改代码。

---

## 四、分析引擎（`core/analysis_lab.py`）

| 函数 | 用途 | 输出等级 |
|---|---|---|
| `decompose_mix_rate` | 量价/结构归因，率效应+结构效应+交叉项，精确闭合 | L1 |
| `ab_proportion` / `ab_mean` | 两比例 z / Welch t；CI、p、功效、MDE、样本量 | L3（有随机分流） |
| `bh_correction` | 多重比较 FDR | — |
| `did_twfe` | 双向固定效应 DiD，聚类稳健 SE | L3（有对照组） |
| `event_study` | 事件研究，目检平行趋势 | L3/L2 |
| `placebo_did` | 安慰剂检验（假时点） | L2 |
| `elasticity` | 对数-对数价格弹性 | L2 |
| `cohort_retention` | 队列留存与衰减 | L1 |

纪律：
- A/B 样本 <100/组 或 peeking → 只给 warning，不给「显著」；
- DiD 没做事件研究 → `level=L2`，报告禁用「导致/替代/驱动」；
- 所有函数返回 `claim` 字段，报告层只消费，不重写公式。

---

## 五、业务线 → 计划的流程

```text
intent
  → match_industry（关键词）
  → score_roles（角色关键词 + 行业 role_boost + r01/r06 底座）
  → plan（行业假设 + 编队 + 分析设计 + 90 天 + 数据清单）
  → to_markdown（人读）/ --json（机器读）
```

CLI：

```bash
python guagua.py domain --intent "县域加油站非油业务增长" --out plan.md
```

产物：`plan.md` + `plan.json`；不写项目数字，行业基准标「需校准」。

---

## 六、与报告产线的衔接

1. `domain` 产出计划 → 按数据清单补数；
2. 数据进项目目录（`data/obs_*.json` 等）→ `report produce`；
3. 报告的证据等级由 `analysis_lab` 的输出决定：L3 才允许因果词；
4. `C1_causal_language` 门禁兜底（当前软告警，阈值 20%）。

---

## 七、边界

- 领域包是「方法地图」，不是「结论」；没有数据就不编数字。
- 书单是第一批（每角色 5 本），后续按 `SOP_ANALYTIC_LEARNING.md` 的七步环继续补。
- 行业基准必须用项目数据校准，不能直接当结论。
- 新增角色/书/方法，必须过 `check_role_packs.py` 与 `check_move_cards.py`。
