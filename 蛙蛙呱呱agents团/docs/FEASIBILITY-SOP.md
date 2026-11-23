# 可行性测试与降级 SOP（v5.0）：先拆卡、后测试、再更新卡

> 纠正上一版（v4.0）的一个**顺序错误**：我原本把源匹配放在"发卡前"当门禁，
> 会让拆卡缩水。正确顺序是**拆卡 → 发卡 → 测试 → 降级 → 报告**。
>
> 前置：`COLLECTION-SOP.md`（v3.0 粒度）、`SYSTEM-UPGRADE-SOP-v3.md`（v3.1 接线）、
> `DERIVATION-SOP.md`（v4.0 推导）。
>
> 依据：[Positive Abstention（当正确答案是没有答案）](https://qu3ry.net/articles/positive-abstention-clinical-decision-support-abstention.pdf)、
> [Visualizing Missing Data（UMD HCIL）](http://www.cs.umd.edu/hcil/trs/2005-05/2005-05.pdf)、
> [Graceful Degradation](https://academia.sh/en/courses/resilience-patterns/graceful-degradation)。

---

## 0. 先认错：顺序错了

### 我原来设计的（错）

```
拆卡 → 源匹配门禁 → 只有 full 的格子才发卡 → 采集
```

**问题**：
1. **拆卡会缩水**（84 格 → 30 格），而拆卡是用户最看重的"穷尽 MECE"。
2. **缺口被藏起来了**：砍掉的格子无声无息，读者不知道哪里没数据。
3. **本该降级的格子被砍了**：系统本来就有 `availability: unavailable` 的降级机制，我绕过了它。

### 应该的（对）

```
拆卡（穷尽，先不管可采性）
   ↓
发卡（全部发出）
   ↓
可行性测试（每格去试：有源吗？能算吗？质量够吗？）
   ↓
更新卡（能采的 full；采不到的降级 unavailable + 写 tried/why）
   ↓
报告（不可用的格子标"数据不足"，保留在结构里）
```

**关键区别**：**测出来不能做，不等于这个格子不该拆；只是这个格子当前无数据。**

---

## 1. 业界依据

### 1.1 Positive Abstention：正确答案可以是"没有答案"

[临床决策支持研究](https://qu3ry.net/articles/positive-abstention-clinical-decision-support-abstention.pdf)：

> 当系统信息不足时，**主动弃答（abstention）**比给一个看似合理的错误答案更安全。

**对我们的含义**：`unavailable` 是一个**合法结论**，不是失败。报告里写"这个判断当前无数据支撑"，比编一个数字强。

### 1.2 Missing Data 必须可见，不能静默

[UMD HCIL《Visualizing Missing Data》](http://www.cs.umd.edu/hcil/trs/2005-05/2005-05.pdf)：

> 缺失数据有多种类型（缺失、未知、不适用、未采集），**必须区分并显式表达**，否则读者会把"没数据"误读成"值为 0"。

**对我们的含义**：`unavailable` 不能变成 `0`，也不能变成"这节消失了"。要**显式标记 + 写原因**。

### 1.3 Graceful Degradation：降级不是失败

[Graceful Degradation](https://academia.sh/en/courses/resilience-patterns/graceful-degradation)：

> 系统在部分能力不可用时，**保持核心功能可用**，只降低非核心能力。

**对我们的含义**：报告结构保持完整（节数不变），只是某些节的数字标 `unavailable`。

---

## 2. 正确顺序（五步）

```
① 拆卡      plan/grid.json   84 格，穷尽 MECE，不看可采性
              ↓
② 发卡      cards/*/TASK.md  全部发出
              ↓
③ 测试      plan/derivation.json
            demand_of(grid)          要采什么
            match_all(demands, srcs) 有没有源
            preview/quality          采到了质量够不够
              ↓
④ 更新卡    plan/grid.json 每格加：
              collectable: full | partial | none
              availability: available | unavailable
              tried: [源列表]
              why: "缺 channel 字段" / "空值率 35%"
              ↓
⑤ 报告      数字照常算（能算的），
            算不出的节标 unavailable，保留标题与 refs 结构
```

**注意第 ③ 步在"发卡之后"**——这样拆卡不受影响。

---

## 3. 降级而不是砍：三态

| 状态 | 含义 | 报告里怎么显示 |
|---|---|---|
| **full** | 有源、能算、质量达标 | 正常出数字和图 |
| **partial** | 有源但缺维度/只能采当下/低置信派生 | 出数字，**加脚注**"口径受限：xxx" |
| **none** | 没有源能答 | **保留节标题**，正文写"当前无数据支撑"+ tried 列表 |

### 为什么不砍

| 砍掉 | 降级 |
|---|---|
| 读者不知道缺了什么 | 缺口可见 |
| 拆卡要重做 | 拆卡不动 |
| 下一轮采到数据也找不回来 | 下一轮直接补上 |
| 违反"穷尽 MECE" | 保持穷尽 |

### 3.1 降级是三层的，不是一层的（2026-11-23 修正）

**之前的错**：只在「数据集层」判有没有数据，结果把老报告（如母婴用品调研）
误判成"没数据"——它有 130 个数字、每个挂 url+quote，只是没有长表。

**正确的三层：**

| 层 | 有什么 | 判成 | 能答什么 |
|---|---|---|---|
| **L2 数据集层** | 长表（mart，几千行） | `full` / `partial` | 能答"是什么 + 趋势 + 分布"，能画图 |
| **L1 证据层** | 数字 + 来源（url/quote），无长表 | `point` | 只能答"是什么"，**答不了趋势** |
| **L0 空** | 什么都没有 | `none` → `unavailable` | 只能说"无数据支撑" |

**判定顺序：L2 有 → full/partial；L2 没有但 L1 有 → point；两层都没有 → none。**

**关键规矩**：**只要有数据集层（`collection.yaml` / `mart.json` / `data/datasets/`），
数据集层就是权威**——`none` 就是真没有，不允许被证据层的数字"救回来"。
证据层兜底**只对完全没有数据集层的老报告生效**。

**为什么**：老报告的 130 个数字是"点证据"，它能证明"2025 年出生人口 792 万"，
但它证明不了"出生人口过去 12 个月的走势"——因为没做横向延伸。
把点证据当成长表用，就会画出 3 个点的"趋势线"。

---

## 4. 二阶影响：7 个模块

| 模块 | 现在 | 改后 | 接线点 |
|---|---|---|---|
| **拆卡** `build_grid` | 产出 84 格 | **不变**（穷尽性保住） | 不动 |
| **发卡** `card_issue.prepare` | 发全部卡 | **不变** | 不动 |
| **可行性测试**（新） `card_probe` | 无 | 每格三态 + tried/why | 新文件 |
| **收卡** `dispatch.collect` | 收 claims | 收 claims + `collectable` | 加一次 `probe` |
| **降级** `collection_contract` | `availability: medium` | 加 `unavailable` + `tried` + `why` | 扩 schema |
| **报告** `report_flow` | 数字来自 claims | `unavailable` 节保留标题、正文写原因 | 加分支 |
| **门禁** `dataset_gates` | G1'-G5' | 加 **G-DEGRADE**（降级必须带 why） | 加一条软门禁 |

### 最关键的二阶后果

**报告会出现"空节"**——标题在、数字没有。这会让报告看起来"不完整"。

**但这是对的**：一份诚实标出 8 个缺口的报告，比一份编满 84 个数字的报告有价值。

**要提前和读者沟通**：报告首页加"数据完整度：X/Y 格可采"。

---

## 5. 三阶影响：四个

### 5.1 用户行为：从"看报告"变成"看缺口"

读者会开始问"为什么这里没数据"，而不是"这个数字对不对"。

**这是好事**——它把注意力从"数字可信度"转到"数据可得性"。

**代价**：需要一份"缺口说明"（tried/why），否则读者会抱怨。

### 5.2 复杂度迁移：从"砍格子"迁移到"维护降级语义"

- 代码复杂度：低（加一个 probe）
- **语义复杂度：高**（full/partial/none 三态要一致地贯穿 7 个模块）

**如果三态在某一环丢了**（比如报告层把 none 当 0），整个降级就失效。

### 5.3 长期维护：缺口会累积

每轮采集都有新的缺口（源改版、字段没了）。**缺口台账会越来越长。**

**对策**：`plan/derivation.json` 按批次存，能看"哪些缺口是老的、哪些是新的"。

### 5.4 危险：`unavailable` 被当成"待办"

有人会把它当"以后补"，然后永远不补。

**对策**：报告里标 `unavailable` 的节，必须写**预计补数条件**（如"需采购第三方数据"），否则算未完成。

---

## 6. 接线图

```
① 拆卡   plan/grid.json          ← 不动
② 发卡   cards/*/TASK.md         ← 不动
              ↓
③ 测试   core/card_probe.py      ★ 新
         ├── demand.demand_of(grid, sem)
         ├── source_match.match_all(demands, sources)
         ├── collection_spec.preview/quality（有 spec 时）
         └── dataset_gates.derivation_gates
              ↓ 写 plan/derivation.json
              ↓ 写 plan/grid.json 的 collectable/availability/tried/why
④ 收卡   core/dispatch.collect
         └── 读 collectable，把 none 的格子标 unavailable
              ↓
⑤ 报告   core/report_flow
         └── unavailable 的节：保留标题 + 写原因 + 不进图
```

---

## 7. 死代码处置（**全部接线，不删**）

上一轮新增但没接线的 6 个函数，全部接进 `card_probe`：

| 函数 | 处置 |
|---|---|
| `demand.demand_of` | 接进 `card_probe.probe` |
| `source_match.match_all` | 接进 `card_probe.probe` |
| `collection_gen.generate` | 接进 `card_probe.probe`（生成候选 YAML） |
| `collection_spec.preview` | 接进 `card_probe.probe`（有 query.path 时） |
| `collection_spec.quality` | 接进 `card_probe.probe` |
| `dataset_gates.derivation_gates` | 接进 `card_probe.probe` |

**处置原则**：能接就接，接不上才删。**接完之后用 `grep` 复验"每个新函数都有人调"。**

---

## 8. 迁移：Expand-Contract

```
Expand：card_probe 默认只报告（--report-only），不改格子
Migrate：跑 2–3 轮，看降级比例合不合理
Contract：默认降级（--degrade），缺口进报告
```

**开关**：`GUAGUA_PROBE=report|degrade|off`

---

## 9. 验收

### 一阶
- [ ] `card_probe.probe` 能算出每格三态
- [ ] `plan/derivation.json` 有 tried/why
- [ ] `grid.json` 的格子带 `collectable`

### 二阶
- [ ] 7 个模块接线（第 4 节）
- [ ] `collection_contract` 支持 `unavailable`
- [ ] 报告里 `unavailable` 节保留标题
- [ ] **全系统 grep：每个新函数都有调用方**

### 三阶
- [ ] 拆卡不缩水（84 格还是 84 格）
- [ ] 缺口可见（报告有"数据完整度"）
- [ ] `unavailable` 带预计补数条件
- [ ] 全量测试零回归

---

## 10. 不做清单

1. **不在发卡前砍格子**（拆卡要穷尽）。
2. **不把 `unavailable` 变成 0**。
3. **不让缺口静默消失**（保留节标题）。
4. **不留没接线的函数**（能接就接，接不上就删）。
5. **不只改一个模块**（三态要贯穿 7 个模块）。

---

## 11. 一句话

> **拆卡要穷尽，测试要诚实，缺口要可见。**
> **不能做 ≠ 不该拆；不能做 = 标 unavailable + 写 why + 保留结构。**
