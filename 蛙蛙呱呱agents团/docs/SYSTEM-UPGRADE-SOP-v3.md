# 系统级升级 SOP（v3.1）：采集粒度改造的连锁影响与接线

> 前置：`docs/COLLECTION-SOP.md`（v3.0）讲清了**采集粒度怎么设计**。
> 这一份讲**改它会牵动什么**——不是一个模块的升级，是系统的升级。
> 依据：[Kimball《Grain》](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/)、
> [dbt 分层](https://docs.getdbt.com/best-practices/how-we-structure/3-intermediate)、
> [AWS《Second-Order Effects》](https://builder.aws.com/content/386hy8jIPr3Q7o5YYeEy5hUq2TR/second-order-effects-the-hidden-cost-of-decisions)、
> [Azure Strangler Fig](https://learn.microsoft.com/azure/architecture/patterns/strangler-fig)。

---

## 0. 一句话定性

**表面上改的是"表怎么建"，实际上改的是"系统信谁"。**

- v1/v2：系统信**claims**（判断 + 数字是手写在卡里的）。
- v3：系统信**mart 表**（数字由表算，判断引用表）。

**"信谁"一变，下面 6 个模块的输入输出全变。**

---

## 1. 一阶效果（直接，可见）

| 项 | 从 | 到 |
|---|---|---|
| 表 | 分析粒度（brand × month） | 原子粒度（sku × snapshot）+ rollup |
| 代码 | 无采集层 | `source_profile / grain / collectors / collection_spec` |
| 校验 | 无 | G-A~G-E 五条 |
| 数字来源 | claims 手写 | mart 表现算 |

**这部分 `COLLECTION-SOP.md` 已讲，不再重复。**

---

## 2. 二阶影响：6 个模块会被牵动

### 2.1 拆卡层（`card_upgrade.build_grid`）

| | 现在 | 改后 |
|---|---|---|
| 输出 | 格子带 `measure` + `grain` | 格子必须**能对应到一个 rollup** |
| 风险 | 格子写了采不到的度量 | 加了 rollup 后，**大部分格子会"无表可采"** |

**接线点**：`build_grid` 生成格子后，必须过一道 **G-ROLLUP 校验**：

```python
# 每个格子的 (measure, grain) 必须能在 rollups 里找到覆盖它的表
def check_cell_collectable(cell, rollups) -> bool:
    return any(r.covers(cell.measure) and r.grain_include(cell.grain) for r in rollups)
```

**二阶后果**：**拆卡会被迫缩水**。原本 84 格，加上"可采性"后可能只剩 30 格。

**这反而是对的**——不可采的格子本来就是在骗自己。但**用户会感觉"拆得少了"**，要提前说。

### 2.2 语义层（`semantic_layer.yaml`）

| | 现在 | 改后 |
|---|---|---|
| 度量定义 | 分析度量（`share = brand_sales / retail_sales`） | 要和 rollup 的 `measures.expr` **对齐** |

**风险：两套定义漂移。**

- 语义层说 `share = brand_sales / retail_sales@total`
- rollup 说 `share = sum(price*30d_sales) / total_gmv`

**两个 `share`，口径不同，数字对不上。**

**接线**：**语义层的 measure 必须引用 rollup 的 measure**，不能各写一套。

```yaml
# semantic_layer.yaml
measures:
  - id: share
    source: rollup.brand_month.measures.share    # ← 单一事实来源
```

### 2.3 图表层（`chart_candidates` / `chart_units`）

| | 现在 | 改后 |
|---|---|---|
| grain 校验 | 比格子 grain | 比 **mart grain** |
| 数据点 | 来自 claims.numbers | 来自 mart 查询结果 |

**接线**：`chart_units.sanitize` 的输入从 `pack["numbers"]` 改成 `mart_rows`。

### 2.4 报告层（`report_flow`）

| | 现在 | 改后 |
|---|---|---|
| 数字来源 | `claims_merged.json` 的 numbers | mart 查询结果 |
| 可追溯 | `refs → number.id` | `refs → number.id → mart 行 + 查询` |

**接线**：`build_sections_contract` 的数字解析要多一跳：`ref → mart_cell`。

**三阶后果**：**报告的可追溯性变强了，但也变长了**（一个数字要追到"哪张表哪一行"）。审计成本 ↑，可信度 ↑。

### 2.5 门禁（`dataset_gates`）

| 门禁 | 现在 | 改后 |
|---|---|---|
| G1' 判断支撑 | dataset 行数 ≥ min_rows | **mart 实际行数** ≥ min_rows |
| 新增 G6' | — | **每个数字能追到 mart 行**（否则拒） |
| 新增 G7' | — | **口径版本一致**（同一 report 内不能混两个 price_band 阈值版本） |

### 2.6 收卡（`dispatch.collect`）

| | 现在 | 改后 |
|---|---|---|
| 收什么 | claims（判断 + 数字） | claims（判断）+ **采集回执**（采了多少行/缺什么） |
| 拒绝理由 | 缺 refs/quote | 加：**mart 表没到位** |

---

## 3. 二阶影响：复杂度会迁移（这是最容易被忽略的）

[AWS 那篇文章](https://builder.aws.com/content/386hy8jIPr3Q7o5YYeEy5hUq2TR/second-order-effects-the-hidden-cost-of-decisions)的核心：

> 灵活的工具减少前期决策、降低门槛。
> **二阶效应：复杂度不会消失，它会迁移——从工具迁移到人，从系统迁移到部落知识，从规则迁移到假设。**
> 速度提升了，但长期清晰度下降。

**套到我们身上：**

| 复杂度从 | 迁移到 |
|---|---|
| 代码（业务词） | **YAML 配置** |
| 硬编码规则 | **derive 表达式** |
| 编译期错误 | **运行时错误**（grain 写错只有跑到才炸） |

**三个具体的"迁移陷阱"：**

1. **YAML 写错了，编译器不管。** `grain: [brand, month]` 少写一个 `month`，要到出图才发现。
2. **derive 表达式是字符串。** `"parse_brand(title)"` 写错，运行时才报。
3. **配置爆炸。** 10 个业务 × 5 个源 × 3 个 rollup = 150 个 YAML。

**对策（必须写进 SOP）：**

- **YAML 也要测**：`tests/test_configs_valid.py` 遍历 `configs/**/*.yaml`，跑 `grain.check`。
- **配置即代码**：YAML 进 git、走 review、CI 校验。
- **derive 表达式要有"可执行样例"**：每个 derive 配一个 `example: {input, output}`，测试时跑。

---

## 4. 三阶影响：用户行为会变

**这是最容易被低估的。**

| | 现在用户做什么 | 改后用户做什么 |
|---|---|---|
| 拆卡 | 看格网、发卡 | 看格网 **+ 看格子有没有表** |
| 采集 | 角色自己去搜、填 claims | **写 collection YAML + 跑采集器** |
| 出报告 | `collect → run-line` | `collect → rollup → run-line` |

**三阶后果：**

1. **上手成本变高**（要懂 grain）。
2. **"角色"的角色变了**：从"研究员"变成"配置员 + 审核员"。
3. **出错更隐蔽**：以前数字错是因为人写错，能看出来；现在可能是 YAML 写错，数字看起来完全正常。

**对策：**

- **提供模板**：`templates/collection/*.yaml`，改关键字就行。
- **提供"体检"命令**：`report collect --dry-run`，只校验不采。
- **报告首页显示"数据口径版本"**：让读者知道这份报告用的是哪版阈值。

---

## 5. 三阶影响：五个"看起来没问题但会出事"的地方

| # | 风险 | 为什么会出事 | 对策 |
|---|---|---|---|
| 1 | **口径漂移** | `price_band` 阈值（39/99）改了，老报告没标版本，跨期不可比 | **口径版本化**：`price_band_v1`，阈值写进版本 |
| 2 | **解析质量** | `parse_brand(title)` 把"XX 汽车脚垫"解析成"XX 汽车" | **解析置信度** + 人工抽检 10% |
| 3 | **源变更** | 平台改版，选择器失效，采集静默返回 0 行 | **行数下限**：<预期 70% 就报错，不静默 |
| 4 | **历史断档** | 某月漏采，序列缺一个点 | **快照台账**：每月记录"采了/没采"，缺的标红 |
| 5 | **跨业务不可比** | 汽车内饰和母婴的"低价带"阈值不同 | 口径版本里带 `domain` 字段 |

---

## 6. 接线图（模块级）

```
configs/sources/*.yaml ──┐
configs/collections/*.yaml ──┤
                         ↓
                 core/source_profile.py
                 core/collection_spec.py
                         ↓
                 core/collectors/*.py  →  staging（原子行）
                         ↓
                 core/grain.py: rollup_rows()  →  mart（分析粒度）
                         ↓
                 core/dataset.py（扩展 rollup）
                         ↓
      ┌──────────────────┼──────────────────┐
      ↓                  ↓                  ↓
card_upgrade        dataset_gates       chart_units
（G-ROLLUP 校验）    （G1'/G6'/G7'）      （mart grain）
      ↓                  ↓                  ↓
      └──────────────────┼──────────────────┘
                         ↓
                 report_flow（数字从 mart 解析）
                         ↓
                 manifest（每个数字 → mart 行）
```

### 文件级接线清单

| 文件 | 改什么 |
|---|---|
| `core/card_upgrade.py` | `build_grid` 后加 G-ROLLUP 校验 |
| `core/cells_claims.py` | `from_drill` 的 dataset 引用改成 rollup id |
| `core/dataset.py` | 加 `rollup` / `staging_ref` 字段 |
| `core/dataset_gates.py` | G1' 改用 mart 实际行数；新增 G6'/G7' |
| `core/dataset_query.py` | 查询从 mart 行跑（已有），加 `source_rows` 回溯 |
| `core/report_flow.py` | 数字解析多一跳：ref → mart cell |
| `core/dispatch.py` | collect 收"采集回执" |
| `core/analyze/`（新） | 采集回执 schema |

---

## 7. 迁移策略：Expand-Contract + Strangler Fig

**不要一次替换。** 用两段式：

### 7.1 Expand（扩张期）

```
新路径：collector → staging → mart → claim → report
旧路径：cells_filled → claims → report        ← 保留，不动
```

在 `dispatch.collect` 加一个 **facade**：

```python
if has_collection_spec(project):
    merged = run_v3_path(project)      # 新
else:
    merged = run_v2_or_v1_path(project) # 旧
merged["pipeline"] = "v3" if ... else "v2"
```

**旧路径只读不改**，直到三业务回归通过。

### 7.2 Migrate（迁移期）

- 新业务（汽车内饰/母婴/蔬菜）走 v3。
- 老项目保持 v2/v1，不做迁移。
- 每迁移一个业务，跑一次"同数据双路径对比"：v2 的数和 v3 的数差多少。

### 7.3 Contract（收缩期）

- 三业务连续两个周期一致后，v2/v1 标 `deprecated`。
- 老项目只读，下线时间另定。

### 7.4 兼容矩阵

| 项目状态 | 走哪条 | 产物标记 |
|---|---|---|
| 有 `collection.yaml` + `staging/` | v3 | `pipeline: v3` |
| 有 `drill.json` + `data/datasets/` | v2 | `pipeline: v2` |
| 有 `out_v3/cells_filled.json` | v1 | `pipeline: v1` |

**三条并存，不互相污染。**

---

## 8. 回滚

| 层 | 怎么回滚 |
|---|---|
| 配置 | YAML 在 git，`git revert` 即可 |
| 采集数据 | `staging/` 按 `snapshot_date` 分区，删某天即可 |
| 代码路径 | `GUAGUA_PIPELINE=v2` 强制切回旧路径 |
| 报告 | 报告里有 `pipeline` 字段，能看出是哪条路径产的 |

**关键：所有回滚都不需要改代码，只切开关/删数据。**

---

## 9. 长期维护成本（诚实算账）

| 成本项 | 估算 | 为什么 |
|---|---|---|
| 每个源一个 collector | 新源 +1~2 人天 | 选择器/解析各不相同 |
| 每个业务一套 YAML | 2~4 小时 | 模板 + 改关键字 |
| 每季度源变更 | 1~2 人天/源 | 平台改版 |
| 口径版本升级 | 半天 + 全量重跑 | 阈值改了要重算 |

**总账**：**采集层的维护成本，主要不在代码，在"源会变"。**

**这是必须承认的**：采集器是"易腐件"，不是"一次性资产"。

---

## 10. 验收（一阶 + 二阶 + 三阶）

### 一阶（能跑）
- [ ] `grain.check` 五条校验通过
- [ ] `csv_manual` collector 能产原子表
- [ ] rollup 能产出 mart 表
- [ ] claim 能引用 mart 出图

### 二阶（接了）
- [ ] 6 个模块全部接上（第 2 节清单）
- [ ] 全量测试零回归
- [ ] 旧路径（v1/v2）仍能跑（兼容矩阵）

### 三阶（真的适配）
- [ ] **三套业务 YAML（汽车/母婴/蔬菜），代码零改动，都出图**
- [ ] 口径版本化（`price_band_v1` 带 domain + 阈值）
- [ ] 解析置信度（`brand_parse_confidence` ≥ 0.9）
- [ ] 源变更能被发现（行数 < 预期 70% 就报错）
- [ ] 快照台账（每月采没采都有记录）

---

## 11. 不做清单（防偏移）

1. **不做"万能爬虫"**——每个源一个 collector，宁可多写。
2. **不合并三条路径**——v1/v2/v3 并存到收缩期结束。
3. **不让代码认业务词**——业务词只活在 YAML。
4. **不为"全"伪造数据**——采不到标 unavailable。
5. **不做无版本的阈值**——`price_band` 必须带版本。
6. **不在 expand 期删旧代码**——Strangler Fig 的第一条纪律。

---

## 12. 一句话总结

> **采集粒度改的是"系统信谁"：从信 claims 改成信 mart 表。**
> **信谁一变，拆卡/语义/图表/报告/门禁/收卡六个模块全要重接。**
> **复杂度不会消失，只会从代码迁移到配置——所以配置也要测。**
> **迁移用 Expand-Contract：新旧并存，三业务回归通过再收缩。**
