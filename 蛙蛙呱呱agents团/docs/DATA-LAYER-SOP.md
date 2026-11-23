# 数据层升级 SOP（v2.0）

> 起因：2026-11-23，用户指出「拆卡穷尽是对的，但你的误判让数据被压缩」。
> 本文回答：**拆卡层保留，数据层怎么长出来**。
> 上一份 `MASTER-UPGRADE-SOP.md`（v1.2）管的是「接线」；这一份管的是**分层模型**。

---

## 0. 问题定性（一句话）

**拆卡层没问题。错在把「分析单元」和「数据单元」压成了同一个东西：格子 = 一个数。**

结果：
- 想画「脚垫各品牌价格趋势」，就得开 `5 品牌 × 36 月 × 2 指标 = 360 格`；
- 格子一多，就想去砍数据（TOP-N）——**砍错了地方**；
- 砍完还是画不出图，因为**360 个标量 ≠ 一张能画的表**。

**数据层被压缩成了「事实清单」，撑不起图。**

---

## 1. 业界怎么做的（证据）

| 来源 | 关键结论 | 对本项目的意义 |
|---|---|---|
| [GROUND (arXiv 2608.26157)](https://arxiv.org/html/2608.26157) | 语义层要管住 7 类错：schema / **metric** / join / **grain** / filter / security / cost。grain 错了就是 fanout 重复计数（如 order line 当 order 数） | 格子的 `grain` 必须和度量的 grain 一致，且**聚合方式要声明** |
| [Intentional Analytics / OLAP](https://ar5iv.labs.arxiv.org/html/1812.07854) | 分析 = 在 cube 上 drill-down / roll-up；cell = (measure, 维度成员) | 「脚垫 → 品牌 → 价格 → 月」是标准 drill-down 路径，不是开 360 个格子 |
| [Semantic Layer 构建](https://www.knowi.com/blog/how-to-build-a-semantic-layer/) | metric 定义 + 维度 + grain，查询由引擎生成 | 判断层只声明「要什么」，查询由语义层编译 |
| [ODCS 数据契约](https://github.com/bitol-io/open-data-contract-standard) / [Soda 契约语言](https://docs.soda.io/reference/contract-language-reference) | 契约是**表级**的：schema / properties / quality / SLA | 采集契约应按「表」写，不是按「格」写 |

**业界共识：语义层（metric/dimension/grain）负责「怎么算」；数据集（表）负责「有什么」；图表从数据集直接取数。三层不合并。**

---

## 2. 三层模型（这是本 SOP 的核心）

```
L1 判断层（analysis cells）      10–30 个
   一个格子 = 一个可辩护的判断 + 它依赖的数据集查询
        ↓ 引用
L2 数据集层（datasets）          每张表几千行，一次采集
   一张表 = 一行一个观测，声明 grain / 列 / 时间粒度 / 行数
        ↓ 编译
L3 图表层（charts）              从数据集直接取数
   图 = 对数据集的一次 group by / 聚合
```

**三条铁律：**

1. **判断层不存数**——只存「判断文本 + 数据集引用 + 查询 + 最少行数」。
2. **数据集层不存判断**——只存表、列、grain、来源。
3. **图表层不经过格子**——直接从数据集取数；格子只提供「画什么」。

---

## 3. 什么叫「一个格子」（v1 vs v2）

### v1（现在）

```json
{
  "cell_id": "Q1.对象.脚垫",
  "entity": "脚垫",
  "measure": "share",
  "value": 12.3          ← 一个数
}
```

问题：
- 一个数撑不起趋势/分布/对比；
- `share` 是品牌份额，实体却是品类（语义错配）；
- 没有来源、没有查询、没有行数。

### v2（目标）

```json
{
  "claim_id": "C-脚垫-价格带",
  "claim": "脚垫主流价格带在 2026 已上移到 59–99 元，低价带（<39）份额两年掉了 8 个点",
  "dataset": "DS-脚垫-品牌月度",
  "query": {
    "filters": {"category": "脚垫", "year": [2025, 2026]},
    "group_by": ["price_band", "year"],
    "metrics": ["gmv_share"]
  },
  "min_rows": 24,          ← 支撑这个判断至少要 2 年 × 若干价格带
  "chart": {"type": "stacked", "x": "year", "series": "price_band"},
  "causal_level": "A",
  "falsifier": "若 2026 低价带份额回升到 2024 水平，本条作废"
}
```

**关键差别：格子从「一个数」变成「一个判断 + 一个查询」。**

---

## 4. 数据集（dataset）的定义

每张表必须声明（照 ODCS 的表级契约）：

```yaml
id: DS-脚垫-品牌月度
source:
  kind: 平台榜单 / 行业报告 / 统计局 / 第三方数据
  url: https://...
  fetched_at: 2026-11-23
grain: "品牌 × 月"              # 一行是什么（最重要的一条）
time_grain: month               # year / quarter / month
columns:
  - {name: brand,    type: string,  semantic: dimension}
  - {name: month,    type: date,    semantic: dimension}
  - {name: price_band, type: string, semantic: dimension}
  - {name: gmv,      type: number,  semantic: measure, unit: 元}
  - {name: asp,      type: number,  semantic: measure, unit: 元}
rows_expected: 180              # 5 品牌 × 36 月
quality:
  completeness: 90%
  source_grade: B
sla:
  freshness: 近 36 个月
```

**判断层只需要 `dataset` + `query`，不需要知道表长什么样。**

---

## 5. 拆卡 v2：两段式（保留穷尽）

### 第一段：横向 MECE（现在这套，保留）

六维各铺几格，回答「从哪些角度看」。**这一步不需要改。**

### 第二段：纵向钻取（新增）

对核心品类展开 `品牌 × 价格 × 时间`，但**产出的不是格子，是数据集需求**：

```yaml
- category: 脚垫
  drill:
    brand_level: TOP5 + 长尾合计
    price_band: 低价 / 中价 / 高价
    time_grain: month
    measures: [gmv, asp, share]
  datasets:
    - DS-脚垫-品牌月度       # 品牌 × 月
    - DS-脚垫-价格带月度     # 价格带 × 月
  claims:                     # 从这些表能得出的判断（10–30 个里挑）
    - 各品牌价差
    - 价格带上移
    - 价格战时段
```

**注意：钻取产出 2 张表 + 3 个判断，不是 360 个格子。**

---

## 6. 门禁改造（v1 → v2）

| 旧门禁 | 问题 | 新门禁 |
|---|---|---|
| G1 覆盖率（填了几格 / 总共几格） | 格子模型错了，覆盖率没意义 | **G1' 判断支撑率**：每个判断引用的数据集是否到手、行数是否 ≥ `min_rows` |
| G3 每格有来源 | 一个数一个来源，撑不起表 | **G3' 数据集有契约**：来源/URL/grain/行数齐 |
| — | 没有 grain 校验 | **G4' grain 一致**（照 GROUND）：查询的 group_by 必须在数据集 grain 内，聚合方式必须声明 |
| G15 因果阶 | 保留 | 保留 |
| — | 没有「表够不够画图」的校验 | **G5' 图形可行性**：图所需的维度组合，数据集里是否都有 |

---

## 7. 图表层改造

- **图从数据集画**：`chart = f(dataset, query)`，不经过 `cell.value`。
- **格子只声明「画什么」**：`chart: {type, x, series, metric}`。
- **1–2 点不画**（v1 已做）保留，但判断依据从「格子数」改成「数据集行数」。

---

## 8. 迁移路径（S0–S6，具体到文件）

| 步 | 改什么 | 退出条件 |
|---|---|---|
| **S0** | 新增 `core/dataset.py`：数据集 schema（id/source/grain/columns/rows_expected/quality/sla）+ 校验 | 能 load/validate 一个 YAML |
| **S1** | 新增 `core/cell_claim.py`：判断格 schema（claim/dataset/query/min_rows/chart） | 能把 v1 格子迁移成 v2 判断格 |
| **S2** | `card_upgrade.build_grid` 增加「钻取段」：对核心品类产数据集需求，不产 360 格 | 脚垫能产出 2 张表的声明 |
| **S3** | `cells_claims.build` 改成「判断格 → claims」，不再从标量拼 | 一个判断能生成一节 |
| **S4** | 门禁改 G1'/G3'/G4'/G5' | 支撑率、grain、图形可行性三条能跑 |
| **S5** | `chart_query` / `report_flow` 从数据集取数 | 脚垫价格趋势图能从表画出来 |
| **S6** | 全量迁移 + 旧格子只读兼容 | 老项目还能出报告 |

---

## 9. 不做清单（防偏移）

1. **不砍数据**（TOP-N 不是解药——病在「格子=数」，不在数据量）。
2. **不把判断做成表**（判断层的产物是文字 + 引用，不是行）。
3. **不合并三层**（合并就回到现在的病）。
4. **不让图表层碰原始格子的 value**（只允许 dataset + query）。
5. **不给每格写采集契约**（契约是表级的）。
6. **不重写六维定义**（第一段保留）。

---

## 10. DoD（可勾选）

- [ ] 数据集 schema 落地，能校验
- [ ] 判断格 schema 落地，v1 格子能迁移
- [ ] 脚垫钻取样板：2 张表声明 + 3 个判断 + 1 张价格趋势图
- [ ] 门禁 G1'/G3'/G4'/G5' 生效
- [ ] 图表从数据集画，能出「各品牌价格趋势」
- [ ] 老项目兼容（旧格子还能出报告）
- [ ] 全量测试零回归

---

## 11. 一句话总结

> **拆卡继续穷尽，但穷尽的是「判断」，不是「数」。**
> 判断挂在数据集上，数据集才是一行一个观测的表；
> 图从表来，不从数来。
