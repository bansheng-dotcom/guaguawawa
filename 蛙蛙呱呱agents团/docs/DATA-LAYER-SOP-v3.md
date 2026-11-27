# 数据层 SOP v3.0 —— 钻取通用化 + 数据充足度

> **取代** `docs/archive/DATA-LAYER-SOP.md`（v2.0）的 §5「拆卡 v2 第二段」与 §6「门禁改造」。
> **保留不动**：三层模型（L1 判断 / L2 数据集 / L3 图表）、`core/data/dataset.py` 的 schema、
> `core/claims/cell_claim.py` 的判断格、`core/grain.py` 的粒度校验。
> 本文只解决三件实测出来的事，**不引入新概念**。

---

## 0. 为什么升版：三个事实，都有文件出处

| # | 事实 | 出处 |
|---|---|---|
| P1 | 纵向钻取**只对前 2 个对象**跑，不是每格、也不是每问 | `core/cards/pipeline.py` `drills = [_drill.plan(cat) for cat in cats[:2]]`；本项目 143 格 → 2 格 |
| P2 | 钻取模板**写死了电商维度**：品牌 A–E、低价/中价/高价带、`gmv` | `core/drill.py` `DEFAULT_BRANDS` / `PRICE_BANDS`；本项目产出 `DS-全国产量规模-品牌month`（蔬菜没有品牌维度） |
| P3 | **"数据不够"没人判**：探测早就算出 1/6 可答，但它是软门禁，既不阻断也不转补采 | `plan/derivation.json`：`G-ROLLUP "需求有源：1/6 可答（全无源 5）"`，`hard: false`；`manifest.capability.actual_rows: null` |

---

## 1. 三条定性

1. **通用性不来自模板里的词，来自语义层。** 骨架可以固定，填进去的维度名必须从 `semantic_layer.yaml` 取。
2. **"数据够不够"是算出来的，不是感觉。** 先定每种图的 `min_points`，再算 `points_hit`，落在四档之一。
3. **钻取的产出是「表 + 缺口」。** 不是格子，也不是"有表就算完"——每张表必须带"缺哪几行、要不要补、补哪个源"。

---

## 2. 你的骨架是对的：一张骨架，两套词表

v2.0 的"每品类 2 张表"骨架本身通用，**它的问题是维度名硬编码**。v3 把它形式化成：

| 表 | 骨架（固定） | 蔬菜（词从 sem 取） | 女装（词从 sem 取） | 订单（词从 sem 取） |
|---|---|---|---|---|
| **A 主体表** | `party/structural 维度 × 时间` | 省 × 月 | 品牌 × 月 | 渠道 × 月 |
| **B 构成表** | `hierarchy 维度 × 时间` | 品类 × 月 | 价格带 × 月 | 品类 × 月 |

同一套代码，换 `semantic_layer.yaml` 就换行业。**判断依据只有一条：这个维度是不是 sem 里声明过的 entity。**

---

## 3. 三个对象，先定义清（v3 新增 `analysis_unit`）

```text
analysis_unit（分析单元）   = 度量 + 维度集 + 时间粒度 + 该单元的最低点数
dataset（数据集 / 表）      = 一个 analysis_unit 落地成的一张表（grain + columns + rows_expected）
slice（切片）               = 数据里实际存在的一组（度量 × 单位 × 维度成员组合）
```

- **钻取的输入是 analysis_unit**，不是格子、也不是格子名。
- 一个 unit 可以覆盖多个格子：本项目 143 格 → **22 个可画切片**（约 1:6.5）。
- 格子仍然保留，但只作为"这条判断被哪几个数支撑"的索引，**不再作为建表单位**。

---

## 4. 钻取算法（替换现有实现）

### 4.1 新增 `core/data/analysis_unit.py`（约 40 行）

```python
PERIODS = {"year": 3, "quarter": 12, "month": 36, "week": 104, "day": 365}

def from_measure(mid, sem):
    m = sem["measures"][mid]
    gd = sem["grain_declarations"][m["grain"]]["dims"]
    unknown = [d for d in gd if d not in sem["entities"]]
    if unknown:                      # 不许猜、不许套模板
        raise KeyError(f"MISSING_ENTITY {unknown}（sem 里没有这个维度）")
    dims = [d for d in gd if d != "period"]
    return {"measure": mid, "dims": dims,
            "time_grain": sem["entities"]["period"]["grain"],
            "unit": m["unit"], "agg": m["agg"]}

def rows_expected(unit, sem):
    n = 1
    for d in unit["dims"]:
        lv = sem["entities"][d].get("levels")
        if not lv:
            raise KeyError(f"NO_CARDINALITY {d}（维度没给枚举，算不出行数）")
        n *= len(lv)
    return n * PERIODS[unit["time_grain"]]
```

### 4.2 重写 `drill.plan(unit)`（删掉 `DEFAULT_BRANDS` / `PRICE_BANDS` / `gmv`）

```python
def plan(unit, sem, marts=None):
    dims, meas = unit["dims"], unit["measure"]
    ds = dataset.build(
        id=f"DS-{meas}-{'-'.join(dims)}",
        title=f"{meas} × {' × '.join(dims)}",
        grain=" × ".join(dims + [unit["time_grain"]]),
        time_grain=unit["time_grain"],
        columns=[{"name": d, "type": "string", "semantic": "dimension"} for d in dims] +
                [{"name": meas, "type": "number", "semantic": "measure",
                  "unit": unit["unit"], "agg": unit["agg"]}],
        rows_expected=rows_expected(unit, sem),
        quality={"source_grade": "按 supply.yaml 的 A/B/C"},
    )
    return {"unit": unit, "datasets": [ds],
            "claims": claims_for(unit), "grid_cells": []}
```

### 4.3 三条硬约束

| # | 约束 | 违反时 |
|---|---|---|
| C1 | `dims` 只能来自 `sem["entities"]` | 抛 `MISSING_ENTITY`，**不出表**（不是套默认值） |
| C2 | `rows_expected` 必须由「维度基数 × 期数」算出 | 没给枚举 → 抛 `NO_CARDINALITY` |
| C3 | 一个 must 问至少 1 个 unit | G6' 拦截，不发卡 |

---

## 5. 数据够不够：先定阈值，再算四档

### 5.1 每种图的 `min_points`（写进 `configs/chart_min_points.yaml`）

| 图型意图 | 最少点数 | 额外条件 |
|---|---|---|
| 排序 / 跨对象对比 | 3 个对象 | 同度量、同单位、同期次口径 |
| 趋势 / 时间序列 | 3 个期次 | 期次等距；不等距必须打标 |
| 结构 / 份额 | 2 个分项 | 分项必须可加总到 100% |
| 关系 / 散点 | 5 个点 | 两轴都是连续量 |

### 5.2 三级行数：把"数据不够"变成一个减法

```text
rows_grid     = Π(维度基数) × 期数        全格：这张表理论上长多少行
rows_planned  = supply.yaml 里本期打算采    计划：这期只采多少（可以少于全格）
rows_actual   = 实际交了多少条              实到：collect 必须写回
```

三个数一出，"够不够"就有刻度，不用争论：

| 指标 | 公式 | 含义 |
|---|---|---|
| 覆盖 | `rows_planned / rows_grid` | 这期打算覆盖全格的几成（承认采不全） |
| 履约 | `rows_actual / rows_planned` | 该交的交了没有 |
| 充足 | `points_hit / min_points` | 交来的数够不够画那张图 |

**本项目实算**：`asp` 全格 = 6 省 × 7 类 × 36 月 = **1512 行**；`supply.yaml` 计划 **480**；
`manifest.actual_rows` = **null**（没算）。—— 三级行数一个都没对齐，这就是"数据不够"说不清的原因。

### 5.3 四个充足度指标

```text
points_ratio   = points_hit / min_points        # 够不够画
period_depth   = 期次数 / 计划期数               # 序列深不深
dim_coverage   = 已覆盖维度成员 / sem 枚举基数     # 缺哪些市/省/品类
fulfilment     = rows_actual / rows_planned      # 表交齐没有
```

### 5.4 四档 + 每档动作

| 档 | 判据 | 出什么 | 本项目实测 |
|---|---|---|---|
| **L0 ready** | `points_ratio ≥ 1` 且 `rows ≥ 6` | 出图（正常） | **10 个切片** |
| **L1 thin** | `points_ratio ≥ 1` 且 `3 ≤ rows < 6` | 出图 + 图上标缺口，不画趋势线 | **12 个切片** |
| **L2 kpi** | `1 ≤ points_hit < min_points` | 不出图，进 KPI 卡或表 | 0 |
| **L3 gap** | `points_hit = 0` | 标 `unavailable`，进补采清单 | 34 个格子 |

> 这套判据的用处：现在报告里"图 7 负值被压成小棍""图 12 全白"，本质都是 L2/L3 的切片被当成 L0 画了。
> 判完之后这类图根本不会进渲染。

---

## 6. 补采清单：数据不够时的唯一产物

```yaml
- dataset: DS-asp-region-month
  unit: {measure: asp, dims: [region, category], time_grain: month}
  rows_expected: 6×7×36 = 1512
  rows_actual: 9
  missing:
    dims: ["province × category 组合 41/42 全缺"]
    periods: ["2024-12", "2025-01…09", "2026-04…08"]
  gap_level: L3
  candidate_sources:            # 从 supply.yaml 的 layers 里按同 grain 匹配
    - {layer: A, id: moa_wholesale, cost: 0, note: 公开周报，需按月手工快照}
    - {layer: C, id: paid_db, cost: 30000, note: 直接买序列}
  priority: P0                  # 按 must 问 + 依赖该 unit 的图数
```

**规则**：一个 unit 落 L3 就算"数据不够"，必须出这一条；没有补采清单的缺口，不算记录过。

---

## 7. 门禁改造（四道，两道改硬）

| 门禁 | 判据 | 级别 | 实现位点 |
|---|---|---|---|
| **G-ROLLUP**（改硬） | 每个 must 问的需求里，无源的不能进报告头条 | **hard** | `core/dataset_gates.derivation_gates` |
| **G6' 钻取覆盖** | 每个 must 问 ≥1 个 analysis_unit，且 unit 的 dims 全部来自 sem | hard | `card_issue.bootstrap` |
| **G7' 模板合规** | 代码/配置里不得出现 sem 之外的维度字面量 | hard（CI grep） | `scripts/check_chart_units.py` 新增 |
| **G8' 充足度** | 每个切片必须带 `min_points / points_hit / gap_level` | warn→hard | `dataset_gates` 新增 |
| **G9' 履约** | `actual_rows` 必填，且 `≥ min_rows` | hard | `dispatch.collect` 收尾 |

G7' 的白名单只有两个来源：`sem["entities"].keys()` 和 `configs/analysis_vocab.yaml`（通用词：时间、数量、金额）。

---

## 8. 实施步骤（S0–S6，文件级）

| 步 | 改什么 | 退出条件 |
|---|---|---|
| **S0** | 新增 `core/data/analysis_unit.py` + `configs/chart_min_points.yaml` | ✅ **已落地**：`core/data/analysis_unit.py` + `tests/test_analysis_unit.py`（7 条全绿）；本项目语义层展开出 **17 个单元、0 报错** |
| **S1** | 重写 `core/drill.py`：删 `DEFAULT_BRANDS`/`PRICE_BANDS`，`plan(unit, sem)` | 用本项目 sem 跑，产出 `DS-asp-region-category-month` 而不是 `品牌month` |
| **S2** | `card_issue.py:228`：`cats[:2]` → 遍历 G-ROLLUP 的 `full/partial` 单元 | 143 格项目产出 ≥6 个 unit |
| **S3** | `dataset_gates` 加 G8'；`derivation_gates` 的 G-ROLLUP 改 hard | 无源需求阻断 |
| **S4** | `collect` 收尾调 `fulfil`，写 `actual_rows` + 补采清单 | `manifest.capability.actual_rows` 不再是 null |
| **S5** | 图从 dataset 取数（`dataset_query` 已有，接上即可） | 每张图能指到 `dataset + query` |
| **S6** | 本项目回归：22 切片 → 22 张表；出充足度报告 | L0 10 / L1 12 / L2 0 / L3 34 |

---

## 9. DoD（可勾选，都能验）

- [ ] `grep -E '品牌|gmv|价格带|长尾' core/drill.py` → **0 命中**
- [ ] 本项目 `plan/drill.json` 里 **0 张表** 的 grain 含 `brand`
- [ ] 语义层展开出 ≥6 个分析单元（本项目实测 **17 个、0 报错**，见 `python -m core.data.analysis_unit`）
- [ ] 22 个切片全部 `dataset.validate` PASS
- [ ] 充足度报告：L0 10 / L1 12 / L2 0 / L3 34，且每个 L3 有补采条目
- [ ] `manifest.capability.actual_rows` 有数，且与 `底表_指标数字.csv` 行数对得上
- [ ] 每个 L0/L1 切片各出一张图（12+10=22 张，允许合并同类）
- [ ] 全量单测零回归（`pytest tests`）

---

## 10. 不做清单

1. **不按格子建表**——格子是索引，不是表；
2. **不在代码里写业务词**——品牌/品类/价格带一律从 sem 取；
3. **不为凑点数造数**——L3 就是 L3，写缺口；
4. **不把"缺"写成"无数据"了事**——每个缺口必须带补采源与成本；
5. **不动 v2.0 的三层模型**——v3 只改钻取的输入与维度来源、加充足度判定。

---

## 附：v2.0 → v3.0 只改了两处

| 处 | v2.0 | v3.0 |
|---|---|---|
| 钻取的输入 | 品类名（实际传进来的是格子名） | `analysis_unit`（度量 + sem 维度 + 时间粒度） |
| 维度从哪来 | `DEFAULT_BRANDS` 硬编码 | `sem["entities"]`，缺了报错 |
| 数据不够 | `G-ROLLUP` 软告警一句话 | 四档判定 + 补采清单 + 图型降级 |

> 一句话：**骨架通用没问题，问题在填空的词是写死的。v3 把填空交回给语义层，把"够不够"交给阈值。**
