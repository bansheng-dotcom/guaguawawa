# 业务→采集规格 推导 SOP（v4.0）：让 YAML 不是"猜的"

> 前置：`COLLECTION-SOP.md`（v3.0）定采集粒度，`docs/archive/SYSTEM-UPGRADE-SOP-v3.md`（v3.1）定系统接线。
> 这一份回答：**项目里的 `collection.yaml` 和 staging 到底该"怎么造"**。
> 依据：[AI-Driven Generation of Data Contracts (arXiv 2507.21056)](https://ar5iv.labs.arxiv.org/html/2507.21056)、
> [Kimball《Grain》](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/)。

---

## 0. 先认账：现在的 YAML 是"猜的"

2026-11-23 现状（汽车内饰项目）：

| 文件 | 怎么来的 | 依据 |
|---|---|---|
| `collection.yaml` 的 `source` | 手写 | 我想用 `manual_csv` |
| `rollups[].derive` | 手写 `token:title:0` | **我假设"标题第一个词是品牌"** |
| `measures` | 手写 `asp/gmv/discount_rate` | 我假设这三个有用 |
| `bucket:price:39,99` | 手写 39/99 | **我拍的** |
| `data/staging/*.csv` | `random.seed(23)` 生成 | **无** |

**三个凭空假设：**

1. `token:title:0` = 品牌 → 真实标题可能是「汽车脚垫全包围 大众朗逸 专用」，第一个词是**品类**不是品牌。
2. `39/99` 价格带 → 真实可能是 49/129/299。
3. `series: true` 12 个月 → 平台只给当下，**这个 claim 本来就该被 G-E 拦住**。

**这三条加起来 = 倒果为因：先想"我要分析什么"，再编数据让它成立。**

---

## 1. 业界依据：契约必须"从样本生成 + 强制验证"

[arXiv 2507.21056](https://ar5iv.labs.arxiv.org/html/2507.21056) 的结论直接对应我们的场景：

| 论文发现 | 对我们的含义 |
|---|---|
| 从**列名 + 样本行**生成契约，准确率 92%（未调优只有 58%） | YAML 必须**看着样本写**，不能凭想象 |
| **"always validating, falling back to a safe generic contract"** | 生成后必须过 `grain.check` + 样本回放 |
| **"the model might invent a sensible but incorrect field type"** | LLM 会编出"看起来合理"的 derive 规则 |
| **"models can be overly generic; multiple runs produce similar contracts"** | **过度通用**：生成的 YAML 会趋同，需要多样性检查 |
| **"human-in-the-loop for critical tables"** | 关键业务必须人确认 |
| 版本历史是治理前提 | 口径必须版本化 |

**一句话：契约可以自动生成，但生成结果必须被验证，且关键处人要签字。**

---

## 2. 正确的推导链（网格 → 规格）

**关键认知：网格已经把业务拆好了。YAML 不该另起炉灶，它应该是网格的「编译产物」。**

```
① 拆卡产物（已有）
   clarify.json     6 要素：品类/空间/时间/渠道/口径/交付
   semantic_layer   度量定义（share = 分子/分母）
   plan/grid.json   44–84 个格子，每格带 (measure, grain)
   perspectives     6 视角
        ↓
② 需求抽取（新）
   demand_of(grid, sem)
   → [{measure: asp, grain: brand×month, dims: [brand]}, ...]
   → 去重后的「需要哪些 (度量, 粒度) 组合」
        ↓
③ 源匹配（新，= 经典 view matching）
   match_sources(demand, sources)
   → 每个需求：哪个源的哪些字段能算出它
   → 匹配不上的，标 `uncollectable`
        ↓
④ 生成候选 YAML
   rollup = grain + derive(从源字段) + measures(用源字段算)
        ↓
⑤ 样本验证（新，最关键）
   preview(spec, n=20)     看 derive 出来前 20 行对不对
   quality(spec)           空值率 / 重复率 / 截断
        ↓
⑥ 人确认（关键业务）
   你看过前 20 行 + 质量报告，签字
        ↓
⑦ 采集 → staging → mart → 报告
```

**注意：第 ④ 步才开始写 YAML。前三步都不写 YAML，只做匹配。**

---

## 3. 三个必须补的工具

### 3.1 `demand_of(grid, sem)` —— 从格子抽需求

```python
# 输入：网格格子
[{"cell_id": "Q1.对象.脚垫", "measure": "share", "grain": "G_brand_channel_year",
  "dim": "对象", "entity": "脚垫"}, ...]

# 输出：去重后的需求
[
  {"measure": "share", "grain": ["brand", "category", "channel", "year"],
   "dims_required": ["brand"], "cells": 6},
  ...
]
```

**这一步会让"格子写不出的需求"暴露**：如果 `share` 要 brand 而格子只给 category，需求清单里就能看出来。

### 3.2 `match_sources(demand, sources)` —— 源匹配

```python
# 对每个需求，找能覆盖它的源
{"measure": "asp", "grain": ["brand", "month"]}
    ├── manual_csv: 有 price ✅，有 title（能 derive brand）✅，有 snapshot_date（能 derive month）✅
    │   → match: full
    ├── tmall_search: 有 price ✅，有 title ✅，但 history=snapshot_only ⚠️
    │   → match: partial（只能单期）
    └── gov_stats: 没有 price ❌ → match: none
```

**输出一张「需求 × 源」矩阵**，这就是"业务可达性"的可视化。

**匹配不上的需求 → 对应格子标 `uncollectable` → 拆卡要砍掉它。**

### 3.3 `preview(spec, n)` + `quality(spec)` —— 样本验证

```python
cs.preview(spec, n=20)
# brand | month   | price  | gmv
# 途美   | 2025-01 | 226.64 | 23846
# 汽车   | 2025-01 | 211.81 | 118483   ← 一眼看出 brand 提取错了
```

```python
cs.quality(spec)
# {"brand": {"empty_rate": 0.35, "distinct": 87, "top1_share": 0.12},
#  "month": {"empty_rate": 0.0, "distinct": 12}}
```

**`brand` 空值率 35% → 规则错了，退回第 ④ 步改 derive。**

---

## 4. 二阶影响：6 个模块会被牵动

| 模块 | 现在 | 加推导后 | 接线点 |
|---|---|---|---|
| **拆卡** `build_grid` | 格子只有 measure+grain | 加 `collectable` 标记（源匹配结果） | `build_grid` 末尾调 `match_sources` |
| **语义层** | measure 定义和 rollup 各写一套 | **必须引用同一处** | `semantic_layer.measures[].source = rollup.measures` |
| **门禁** | G-A~G-E | 加 **G-ROLLUP**（每格可采）+ **G-PREVIEW**（derive 质量） | `dataset_gates` |
| **报告** | 数字来自 claims | 数字来自 mart | 已接（v3） |
| **用户行为** | 自己写 YAML | **确认候选 YAML + 看前 20 行** | CLI 加 `--dry-run` |
| **配置管理** | YAML 是手写资产 | YAML 是**生成物**（可重建） | `configs/` 里生成物要标 `generated: true` |

### 最痛的二阶后果

**拆卡会缩水，而且这次是"源决定的缩水"。**

```
现在：84 格（业务想分析什么就拆什么）
加源匹配后：可能只剩 30 格（源能支撑的）
```

**但这是对的**——不可采的格子本来就是在骗自己。**代价是用户会感觉"分析变少了"。**

---

## 5. 三阶影响：四个"看起来没问题但会出事"的地方

### 5.1 过度通用（arXiv 明确指出的）

> "models can be overly generic; multiple runs produce similar contracts for similar input"

**表现**：不同业务的 YAML 会长得几乎一样（都是 `brand_month` + `asp/gmv`）。

**后果**：报告里 6 个节读起来像同一段话——**这正是我们 v2 遇到的问题（重复句 43%）**。

**对策**：
- `quality(spec)` 里加 **diversity** 指标：不同业务的 rollup 名称/度量组合的重合度。
- 报告层加 **shingle 检查**（已有）。

### 5.2 幻觉（编字段/编规则）

**表现**：`derive: "token:title:0"` 看起来很合理，但真实标题第一个词是品类。

**后果**：品牌解析错 → 份额算错 → 结论错，而且**数字看起来完全正常**。

**对策**：
- `preview` 强制人看前 20 行。
- `quality` 卡 `empty_rate < 0.1`、`distinct ≥ 2`。

### 5.3 口径漂移（阈值无版本）

**表现**：`39/99` 改了一次，老报告没标版本。

**后果**：跨期不可比，但读者不知道。

**对策**：`bucket:price:39,99:v1`，版本写进 mart 的 `caliber_version` 字段。

### 5.4 生成物 vs 手写物的混淆

**表现**：生成的 YAML 进了 git，后来有人手改，下次重新生成就覆盖了。

**后果**：**手改丢失**。

**对策**：
- 生成物标 `generated: true` + `generated_from: {grid_hash, source_hash}`。
- 手改过的标 `hand_edited: true`，重新生成时**跳过并告警**。

---

## 6. 接线图（文件级）

```
clarify.json / semantic_layer / plan/grid.json
        ↓
core/demand.py          ★ 新：demand_of(grid, sem)
        ↓
core/sources/source_match.py    ★ 新：match_sources(demand, sources)
        ↓
core/sources/collection_gen.py  ★ 新：generate(spec_draft) → YAML
        ↓
core/sources/collection_spec.py   已有：validate / run
        ↓
core/grain.py             已有：check / rollup_rows
        ↓
core/data/dataset_query.py     已有：查询 + 出图
        ↓
report_flow               已有
```

### 新增文件

| 文件 | 职责 |
|---|---|
| `core/demand.py` | 从网格抽需求（度量 + 粒度 + 维度） |
| `core/sources/source_match.py` | 需求 × 源 匹配矩阵 |
| `core/sources/collection_gen.py` | 生成 YAML 草稿（带 `generated` 标记） |

### 改动文件

| 文件 | 改什么 |
|---|---|
| `core/sources/collection_spec.py` | 加 `preview()` / `quality()` |
| `core/cards/card_upgrade.py` | `build_grid` 末尾调 `match_sources`，格子加 `collectable` |
| `core/data/dataset_gates.py` | 加 G-ROLLUP / G-PREVIEW |
| `report_flow` | 报告首页显示 `caliber_version` |

---

## 7. 迁移：Expand-Contract

```
Expand：新流程（demand → match → gen → preview）与手写 YAML 并存
Migrate：新业务走新流程；老项目的手写 YAML 保持不动
Contract：新业务连续 3 次"生成→确认→零手改"后，手写路径标 deprecated
```

**不做的**：不强制老项目迁移（手写 YAML 也能跑）。

---

## 8. 验收（三阶）

### 一阶
- [ ] `demand_of` 能从网格抽出需求清单
- [ ] `match_sources` 能给出"需求 × 源"矩阵
- [ ] `preview/quality` 能跑

### 二阶
- [ ] 拆卡格子带 `collectable` 标记
- [ ] G-ROLLUP / G-PREVIEW 生效
- [ ] 6 个模块接线（第 6 节）

### 三阶
- [ ] **同一个业务，两次生成结果一致**（可重现）
- [ ] **不同业务的 YAML 不雷同**（diversity 检查）
- [ ] **`brand` 空值率 < 10%**（真实样本验证）
- [ ] **口径版本写进 mart**
- [ ] **生成物与手改物不互相覆盖**

---

## 9. 不做清单

1. **不凭想象写 derive**（必须看样本）。
2. **不用随机数造 staging**（采不到就标 unavailable）。
3. **不跳过 preview**（前 20 行必须人看）。
4. **不让生成物覆盖手改物**。
5. **不给无版本的阈值**。
6. **不为"链路跑通"而编数据**（这是最根本的一条）。

---

## 10. 一句话总结

> **YAML 不是"写"出来的，是"从网格 + 源样本"编译出来的。**
> **编译要三步：抽需求 → 源匹配 → 样本验证。**
> **三步都不写 YAML，第四步才生成。**
> **生成物可以手改，但重新生成不能覆盖手改。**
