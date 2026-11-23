# 采集层升级 SOP（v3.0）：业务无关的粒度设计

> 起因：2026-11-23，用户指出「采集粒度不能写死业务，系统要能适配各种业务」。
> 本文回答：**采集粒度怎么设计成业务无关的代码**。
> 前置：`docs/DATA-LAYER-SOP.md`（v2.0）解决了「表→查询→图」；这一份解决「表怎么来」。

---

## 0. 问题定性（一句话）

**v2 把"分析粒度"当成了"采集粒度"，所以那张表根本采不到。**

```yaml
# v2 写的（错）
DS-脚垫-品牌month
grain: brand × month          # ← 这是分析粒度
rows_expected: 216            # ← 没有任何源会直接给这个
```

平台给你的是**一行一个商品**，不是"一行一个品牌月汇总"。
所以 v2 的表只能由更细的表聚合出来 —— 而那张更细的表，我们从来没定义过。

**这就是"采集没做"的技术根因：采集粒度缺位。**

---

## 1. 业界依据（两条硬规矩）

### 1.1 Kimball：grain 是绑定契约，原子粒度优先

[Kimball《Grain》](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/)：

> 声明 grain 是维度设计的关键一步。grain 确立「事实表的一行代表什么」，并成为设计的**绑定契约**。
> **grain 必须在选维度/度量之前声明**，因为每个候选维度/度量都必须与 grain 一致。
> **原子粒度**是某个业务流程能捕获的最低层级。**从原子粒度开始**，因为它能扛住不可预测的查询；
> 汇总粒度可以后加，但它**预设了业务常见问题**。
> **每个 grain 对应一张独立物理表；不同 grain 不能混在一张表里。**

**对我们的直接含义：**
- 采集表 = 原子粒度（源能捕获的最低层）。
- 分析表 = 汇总粒度（按 claim 需要的 grain 聚合）。
- **不能把两者混在一张表。**

### 1.2 dbt：staging → intermediate → marts

[dbt 项目结构](https://docs.getdbt.com/best-practices/how-we-structure/3-intermediate)：

| 层 | 做什么 |
|---|---|
| **staging** | 「原子积木」：贴近源，一行一个源记录 |
| **intermediate** | **re-graining**：把数据 fan out / collapse 到正确的复合 grain |
| **marts** | 业务定义的、可直接给分析用的实体 |

> 「窄化 DAG，加宽表」：从源走向 mart，是从「多、窄、孤立」走向「少、宽、连接」。

**对我们的直接含义：**
- 采集器只产 **staging**（原子行）。
- 聚合器把 staging → **mart**（分析粒度）。
- 中间可以有 intermediate 做复杂变换（可选）。

### 1.3 结论

```
采集 grain（原子，源给什么）  ⊆  分析 grain（汇总，claim 要什么）
        ↑ 必须先声明                 ↑ 必须是它的投影
```

**分析 grain 的每个维度，都必须能从采集 grain 的列推导出来。**

---

## 2. 三层模型

```
L0  staging（采集层）
    一行 = 源的一条记录（原子粒度）
    列 = 源给什么就是什么，不改写
    表 = 每个源一张
        ↓ rollup（group by + agg）
L1  mart（分析层）
    一行 = 分析 grain（brand × month / price_band × year …）
    表 = 每个 grain 一张
        ↓ query
L2  claim（判断层）
    引用 L1 表 + 一个查询 + min_rows
```

**三条硬规矩：**

1. **L0 只存源里有的，不派生。** 派生放 L1。
2. **每个 grain 一张表。** 不同 grain 不能混。
3. **L1 必须是 L0 的投影。** 分析维度 ⊆ 原子维度。

---

## 3. 四个业务无关的抽象

**业务词只允许出现在「源查询参数」和「语义层」里，代码里一个都没有。**

### 3.1 source（源画像）：这个源天然给什么

```yaml
# configs/sources/tmall_search.yaml
id: tmall_search
kind: platform_search          # platform_search / pdf_report / csv_manual / api
atomic_grain: [sku_id, snapshot_date]     # ← 原子粒度（源能捕获的最低层）
fields:
  - {name: sku_id,      type: string}
  - {name: snapshot_date, type: date}
  - {name: title,       type: string}
  - {name: price,       type: number, unit: 元}
  - {name: list_price,  type: number, unit: 元}
  - {name: sales_30d,   type: number}
  - {name: review_count, type: number}
  - {name: shop_name,   type: string}
  - {name: url,         type: string}
history: snapshot_only         # snapshot_only（只能采当下）/ historical（有历史）
```

**注意 `atomic_grain` 是源决定的，不是业务决定的。** 同一个源服务所有业务线。

### 3.2 collection（采集规格）：怎么采

```yaml
# configs/collections/auto-interior.yaml
id: auto_interior_skus
source: tmall_search
query:
  keyword: "${category}"        # ← 业务词只出现在这里
  sort: sales_desc
  pages: 3
schedule: monthly
snapshot_at: "01 09:00"
```

**换业务 = 换 `keyword` 的值，代码不变。**

### 3.3 rollup（重粒度）：原子 → 分析

```yaml
# 每个分析 grain 一个 rollup（业务无关的声明）
rollups:
  - id: brand_month
    from: staging.tmall_search
    grain: [brand, month]                 # ← 分析粒度
    derive:                               # 从原子列派生
      brand: "parse_brand(title)"         # 业务规则，可换
      month: "substr(snapshot_date,1,7)"
    measures:
      asp:          {agg: mean, expr: price, unit: 元}
      gmv:          {agg: sum,  expr: "price * sales_30d", unit: 元}
      discount_rate: {agg: mean, expr: "1 - price/list_price", unit: "%"}
  - id: price_band_month
    from: staging.tmall_search
    grain: [price_band, month]
    derive:
      price_band: "case when price<39 then '低价带' when price<99 then '中价带' else '高价带' end"
      month: "substr(snapshot_date,1,7)"
    measures:
      gmv: {agg: sum, expr: "price * sales_30d", unit: 元}
```

**`derive` 里的 `parse_brand` / `price_band` 是业务规则，但它们**在 YAML 里**，不在代码里。**

### 3.4 claim（判断）：引用分析表

```yaml
claims:
  - id: brand_price_gap
    dataset: brand_month            # ← 引用 L1 表
    query: {group_by: [brand], metrics: [asp]}
    min_rows: 5
    chart: {type: hbar, x: brand, metric: asp}
```

---

## 4. 硬校验（业务无关，可单测）

| 校验 | 规则 | 违反后果 |
|---|---|---|
| **G-A 原子粒度已声明** | `source.atomic_grain` 非空 | 采集器拒绝执行 |
| **G-B 分析粒度可推导** | `rollup.grain` 的每个维度 ∈ `derive` 或 ∈ `source.fields` | rollup 拒绝编译 |
| **G-C 度量可算** | `measures[].expr` 里引用的列 ∈ `source.fields` 或 `derive` | rollup 拒绝编译 |
| **G-D grain 不混** | 一张 mart 表只有一个 grain | 校验失败 |
| **G-E 历史可得** | `claim` 需要序列（`group_by` 含时间且 `min_rows > 1 期`）时，`source.history` 必须是 `historical` | 拒绝，并提示"只能采当下" |

**G-E 是关键**：这条能自动拦住「用只能采当下的源去做趋势判断」——也就是 v2 里"价格战在哪些月份"那种做不了的判断。

---

## 5. 代码结构（文件级）

```
core/
├── source_profile.py      # 读 configs/sources/*.yaml，暴露 fields/atomic_grain/history
├── collection_spec.py     # 读 configs/collections/*.yaml，校验 query 参数
├── grain.py               # ★ 核心：grain 运算与校验
│     atomic_of(source) -> [dim]
│     analysis_of(rollup) -> [dim]
│     check(atomic, analysis) -> [err]        # G-A/B/C/D/E
│     rollup_rows(staging_rows, spec) -> mart_rows
├── collectors/
│   ├── base.py            # Collector 协议：fetch(spec) -> [atomic rows]
│   ├── web_search.py      # 平台搜索页（business-agnostic：只认 query 参数）
│   ├── pdf_report.py      # PDF 表格抽取
│   ├── csv_manual.py      # 手工 CSV（半自动，主力）
│   └── api.py             # 通用 HTTP API
└── dataset.py             # 已有：扩展 rollup 字段
```

### 5.1 Collector 接口（业务无关）

```python
class Collector(Protocol):
    def fetch(self, spec: CollectionSpec) -> list[dict]:
        """返回原子行。每行必须包含 source.atomic_grain 的全部列。"""
    def fields(self) -> list[str]:
        """这个源给什么字段。"""
```

**采集器不知道"脚垫"，只知道 `spec.query` 里的参数。**

### 5.2 grain.py（核心，可单测）

```python
def check(atomic: list[str], rollup: dict, source: dict) -> list[str]:
    """G-A~G-E 的纯函数校验；空 = 合法。"""
```

---

## 6. 适配性验收（硬证据）

**同一个代码，换三套 YAML，跑通三条业务线：**

| 业务 | source | collection.query | rollup.grain |
|---|---|---|---|
| 汽车内饰 | tmall_search | `keyword: 汽车脚垫` | brand × month |
| 母婴 | tmall_search | `keyword: 婴儿纸尿裤` | brand × month |
| 蔬菜价格 | gov_price_csv | `city: 呼和浩特` | category × week |

**代码零改动，只换 YAML，三条线都出图——这才叫"适配各种业务"。**

这条要写进 CI：`tests/test_grain_generic.py` 用三套 YAML 跑同一套函数。

---

## 7. 迁移路径（S0–S6）

| 步 | 做什么 | 退出条件 |
|---|---|---|
| **S0** | `core/source_profile.py` + `configs/sources/tmall_search.yaml` | 能 load/validate 一个源 |
| **S1** | `core/grain.py`：`atomic_of / analysis_of / check / rollup_rows` | G-A~G-E 五条能跑 |
| **S2** | `core/collectors/csv_manual.py`（先做最简单、最可控的） | 手工 CSV → 原子表 |
| **S3** | `core/collection_spec.py` + 一个真实 collection YAML | 规格校验通过 |
| **S4** | 把 v2 的 `drill.plan` 改成「从 rollup 推导」，不再手写 216 行 | 钻取产物来自 rollup |
| **S5** | `collect` 接采集链：collector → staging → rollup → mart → claim | 一条命令从源到图 |
| **S6** | 三业务 YAML 回归（汽车/母婴/蔬菜） | 代码零改动跑通三条线 |

---

## 8. 不做清单（防偏移）

1. **不在代码里写业务词**（脚垫/母婴/蔬菜只能出现在 YAML）。
2. **不把分析粒度当采集粒度**（v2 的错）。
3. **不混 grain**（Kimball 明令）。
4. **不做"万能爬虫"**（每个源一个 collector，宁可多写几个）。
5. **不为了"全"去伪造数据**（采不到就标 unavailable，不生成假表）。
6. **不让采集器做业务判断**（`parse_brand` 在 YAML 的 derive 里，不在代码里）。

---

## 9. DoD（可勾选）

- [ ] `source_profile` 能声明原子粒度 + 字段 + 历史可得性
- [ ] `grain.check` 五条校验能跑，有单测
- [ ] `csv_manual` collector 能从手工 CSV 产原子表
- [ ] 一条 collection YAML 能校验通过
- [ ] v2 的 `drill.plan` 从 rollup 推导，不再手写行数
- [ ] `collect` 一条命令：源 → staging → mart → claim
- [ ] **三套业务 YAML 用同一套代码跑通**（CI 证据）
- [ ] 全量测试零回归

---

## 10. 一句话总结

> **采集粒度不是"业务设计的"，是"源决定的"。**
> **源给什么粒度，就采什么粒度（staging）；分析要什么粒度，就 rollup 什么粒度（mart）。**
> **业务词只活在 YAML 里，代码只认 grain。**
