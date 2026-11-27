> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 协调 SOP（v6.0）：基线 → 增强 → 降级

> 起因（2026-11-23）：用户指出「以前我们的产物也能产出报告；现在做了更严格的东西（分析之后再采集），
> 那数据补全不严格的时候就要降级。以前的产物只是穷尽拆解后的分析，现在是分析后又继续采集，
> 这部分要协调起来。」
>
> 前置：`COLLECTION-SOP.md`（v3.0 粒度）、`docs/archive/SYSTEM-UPGRADE-SOP-v3.md`（v3.1 接线）、
> `DERIVATION-SOP.md`（v4.0 推导）、`FEASIBILITY-SOP.md`（v5.0 降级）。
> **这一份是总纲：把两代产物收进同一个能力模型。**
>
> 依据：[Progressive Enhancement](https://livebook.manning.com/learn/concepts/progressive-enhancement--technique/design-for-developers)、
> [WCAG SCR38 合规回退](https://wcagrules.com/fixes/scr38-conforming-alternate-for-scripted-pages)、
> [Data Maturity Pyramid](https://www.kdnuggets.com/the-data-maturity-pyramid-from-reporting-to-a-proactive-intelligent-data-platform)。

---

## 0. 定性：这不是"新旧替换"，是"基线 + 增强"

| | 旧产物 | 新产物 |
|---|---|---|
| 做了什么 | 穷尽拆解 → **分析** | 穷尽拆解 → 分析 → **采集** |
| 数据形态 | 数字 + 来源（点证据） | 长表（序列） |
| 能出报告吗 | **能**（有 800 个数字、8 张图、门禁 PASS） | 能 |
| 能画趋势吗 | 不能（没有序列） | 能 |

**关键认知**：旧产物不是"残缺版"，它是**基线版**。

Web 界的同一件事叫 **Progressive Enhancement**：

> 先做一个在**任何环境**都能工作的基线；增强层可选，增强不可用时基线照样工作。

**套到我们身上：**

```
基线（永远能出）：拆解 + 分析 → 点证据报告
增强（可选）：    + 采集 → 长表 → 趋势/分布/构成图
降级（增强失败）：退回基线，但**显式标注"未做采集增强"**
```

**"显式标注"是全部要害**——不标注，读者以为"这就是全部"。

---

## 1. 三级能力模型（能力金字塔）

| 级别 | 有什么 | 能出什么 | 状态码 | 今天有吗 |
|---|---|---|---|---|
| **L0 拆解** | 只有格子/问题 | 只能出目录 | `outline_only` | ✅（但不可交付） |
| **L1 分析** | 数字 + 来源（点证据） | **点证据报告**：现状、对比、排序 | `point_evidence` | ✅ **所有老产物** |
| **L2 采集** | 长表（序列/多主体） | **全量报告**：+ 趋势、分布、构成 | `series_evidence` | 🟡 只有合成/手工数据 |

**三句话：**

1. **每一级都能交付**——L1 不是"没做完"，是"基线交付"。
2. **L2 是在 L1 之上加东西**，不是替代 L1。
3. **降级 = 从 L2 退回 L1，并写明退到哪一级、为什么退。**

---

## 2. 降级规则（协调的核心）

### 2.1 降级不是二值，是"退级"

```
采集成功        → L2（series_evidence）  报告出趋势图
采集部分成功    → L2 局部 + L1 补其余     报告标"部分判断只有点证据"
采集完全失败    → L1（point_evidence）    报告标"本次为点证据报告，未做序列采集"
连分析都没有    → L0（outline_only）      不出报告，只出目录
```

### 2.2 报告上必须写清的三个字段

| 字段 | 写什么 | 写在哪 |
|---|---|---|
| `capability_level` | `series_evidence` / `point_evidence` | 报告首页 + manifest |
| `degraded_from` | 期望做 L2，实际退到 L1 | manifest + 附录 |
| `gaps` | 哪些判断因为没序列而做不了 | 边界与缺口节 |

### 2.3 一条硬规矩

**降级绝不允许把"没采到"写成"没有"或"0"。**

- ❌ "低价带份额 0%"（其实没采到）
- ✅ "低价带份额：本期未采到序列，无法判断趋势"

---

## 3. 二阶影响：8 个模块

| 模块 | 现在 | 改后 | 接线点 |
|---|---|---|---|
| **拆卡** `build_grid` | 格子只有 measure+grain | 格子加 `needs: point\|series` | `card_upgrade` |
| **发卡** `card_issue` | 发全部卡 | 不变（穷尽性保住） | 不动 |
| **探测** `card_probe` | 判 full/partial/none | 判 `L2/L1`（能不能做增强） | 已存在，改判定词 |
| **收卡** `dispatch.collect` | 收 claims | 收 claims + `capability_level` | 加字段 |
| **契约** `collection_contract` | `availability: high/medium/low` | 加 `capability_level` | 扩 schema |
| **报告** `report_flow` | 按节渲染 | 首页显示能力级别 + 缺口说明 | 加一段 |
| **门禁** `dataset_gates` | G1'–G5' | 加 **G-CAPABILITY**（降级必须带 `degraded_from`） | 加一条软门禁 |
| **验收** `scripts/audit_dod` | 13 项 | 加"能力级别可追溯" | 加一项 |

### 最关键的二阶后果

**报告会分成两类，读者要知道自己在看哪一类。**

| 报告类型 | 读者预期 | 风险 |
|---|---|---|
| `point_evidence` | "这是现状快照" | 读者误当"趋势分析" |
| `series_evidence` | "这有走势" | 读者误当"全量"（其实只采到 30%） |

**对策**：首页一行字，必须显眼。

---

## 4. 三阶影响：五个

### 4.1 用户行为：从"看报告"变成"先看级别"

读者会先看"这是点证据还是序列"，再决定信多少。

**这是好事**，但**要教育**——否则读者会说"为什么这份报告没有趋势图"。

### 4.2 复杂度迁移：从"能不能采"迁移到"采到几级"

以前判"有/没有数据"；现在判"三级中的哪一级"。

**如果某一环把级别丢了**（比如报告层默认写 `series_evidence`），**整个降级就变成谎言**。

**对策**：`capability_level` 由**采集层算**，报告层**只读不改**。

### 4.3 长期维护：两代产物的口径会漂移

老产物（L1）的数字来自"网页 quote"，新产物（L2）的数字来自"长表聚合"。

**同一个指标，两条路径可能算出不同值。**

**对策**：`gaps` 里记"口径来源：quote / table"。

### 4.4 危险：降级被当成"以后补"

`point_evidence` 的报告会被当成"待补采集"。

**对策**：`degraded_from` 必须写**预计补采条件**（如"需采购近 12 个月历史数据"）。

### 4.5 危险：L2 只在演示层

真实平台采不到（反爬），L2 现在只有合成数据。

**如果这关过不去，L1 永远是主力，L2 永远是演示。**

**对策**：先在 L1 上把"能力级别"做扎实；L2 只对"手工 CSV / 公开 API"开放。

---

## 5. 接线图（全系统）

```
① 拆卡        plan/grid.json        格子加 needs: point|series
                   ↓
② 发卡        cards/*/TASK.md       不变
                   ↓
③ 探测        core/cards/pipeline.py     判 L2 可行 / 只 L1 / L0
                   ↓ 写 plan/derivation.json
④ 采集        core/collectors/*     能采就采，采多少记多少
                   ↓
⑤ 收卡        core/dispatch.collect 合并 + 算 capability_level
                   ↓ merged["capability"] = {level, degraded_from, ...}
⑥ 报告        core/report_flow      首页写级别；缺口节写补采条件
                   ↓
⑦ 门禁        core/dataset_gates    G-CAPABILITY：降级必须带 degraded_from
```

### 文件级接线清单（**全系统，不只一个模块**）

| 文件 | 改什么 | 类型 |
|---|---|---|
| `core/cards/card_upgrade.py` | 格子加 `needs` 字段（默认 `point`，兼容老格） | 改 |
| `core/cards/pipeline.py` | 判定从 `full/partial/none` 改成 `L2/L1/L0` | 改 |
| `core/sources/source_match.py` | `match` 增加 `can_series` 判定 | 改 |
| `core/cards/pipeline.py` | `collect` 算 `capability_level`，写进 merged | 改 |
| `core/sources/collection_contract.py` | 加 `capability_level` 枚举 | 改 |
| `core/report/report_flow.py` | 首页能力级别 + 缺口补采条件 | 改 |
| `core/data/dataset_gates.py` | 加 G-CAPABILITY（软） | 改 |
| `scripts/compile_agent_report.py` | 透传 `capability_level` | 改 |
| `scripts/audit_dod.py` | 加"能力级别可追溯"一项 | 改 |
| `docs/REPORT-LINES.md` | 主线图加"能力级别" | 改 |
| `REPORT-STANDARD.md` | 加"报告必须标能力级别" | 改 |
| `README.md` / `SKILL.md` | 同上 | 改 |
| `AGENTS.md` | 由 `gen_agent_packs.py` 重生成 | 生成 |

**新增文件**：0 个。**这一版全是接线，不加新模块。**

---

## 6. 迁移：Expand-Contract

```
Expand   capability_level 字段可选；老产物没有也照常跑
Migrate  新项目自动算；老产物读的时候默认 point_evidence
Contract 所有报告都必须带 capability_level（CI 卡）
```

**老产物不需要重跑**：读的时候按 `point_evidence` 处理即可。

---

## 7. 验收（一阶/二阶/三阶）

### 一阶
- [ ] 格子能声明 `needs: point|series`
- [ ] `card_probe` 能判 L2/L1/L0
- [ ] `merged.capability.level` 有值

### 二阶
- [ ] 8 个模块接线（第 5 节清单）
- [ ] 报告首页显示能力级别
- [ ] G-CAPABILITY 生效（软）
- [ ] **全系统 grep：每个新字段都有读写方**

### 三阶
- [ ] 老产物（如 `母婴用品调研_2026-11-22`）读出来是 `point_evidence`，不报错
- [ ] `point_evidence` 报告明确写"未做序列采集"
- [ ] `degraded_from` 带预计补采条件
- [ ] **拆卡不缩水**（`needs` 只是声明，不砍格子）
- [ ] 全量测试零回归

---

## 8. 不做清单

1. **不砍格子**（穷尽性第一）。
2. **不把"没采到"写成"0"或"没有"**。
3. **不让报告层改能力级别**（由采集层算，报告层只读）。
4. **不为 L2 强推真实爬虫**（采不到就退回 L1，标清楚）。
5. **不要求老产物重跑**（读时按 L1 处理）。
6. **不在没有 `degraded_from` 时静默降级**。

---

## 9. 一句话

> **拆解 + 分析 = 基线（永远能出报告）。**
> **采集 = 增强（能出趋势）。**
> **增强失败不是失败，是退回基线——但要告诉读者"你拿到的是基线，不是全部"。**
