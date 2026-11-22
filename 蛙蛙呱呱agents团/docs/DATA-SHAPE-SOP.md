# 数据形状升级 SOP（v1.0）

> 对应问题：母婴项目（最新代码）8 节 8 图，但 5 张只有 1–3 个点，看着"覆盖率低"。
> 本文回答：**不是渲染层不会画，是数据形状撑不起高级图；而"数据层升级"没接进
> "出图"这一段。**

---

## 0. 核心诊断（一句话 + 铁证）

**采集层产出的是「130 条互不相干的头条数字」，不是「同指标 × 实体 × 期次的结构化数据集」。**

铁证（母婴 `projects/muying-2026/raw.json`）：

```
rows: 130
distinct metric_id: 129          ← 130 行里有 129 个不同指标
同指标最多行数: 2                ← 只有一个指标出现 2 次
entity TOP: 全市场 97, 中国 11   ← "实体"绝大多数是"全市场"这种填充值
theses: []                       ← 论点合成一个都没出
```

**"130 行 / 129 指标"这个比例（≈1:1）就是"事实清单"的签名；真正的数据集应该是
"1 个指标 × 30 个实体 × 12 期 = 360 行"。**

---

## 1. 为什么"数据层升级"对出图没提升（四个断点）

```
拆卡（卡片模板要求"≥3 可比点"）          ✅ 写了
  → agent 交 130 个数字（129 个指标）     ❌ 断点A：可比点理解成"多给几个数"，
                                            不是"同一指标 × 不同实体/期次"
raw.json（130 行 / 129 指标）            ❌ 断点B：忠实记录成"事实清单"
  → synthesis.theses(rows) = []          ❌ 断点C：找不到"同指标跨主体"论点
  → chart_query.build 永不被调用         ❌ 断点D：panel→矩阵图的桥空转
主报告出图退回 section.refs 的零散数字    → 1D 图（dot/bar/line）
```

关键代码位置：

| 断点 | 位置 | 说明 |
|---|---|---|
| A | `core/dispatch.py:199-205` | 卡片写"≥3 可比点（不同规格/地区/期次/主体）"，但**没规定"同一 metric_id 重复"** |
| B | `core/data_model.py` / `scripts/compile_agent_report.py` | claims numbers → raw rows，逐条记，不校验同指标重复度 |
| C | `core/synthesis.py:93` + `theses` | `synthesis.sections` 只在 `theses` 非空时跑 |
| D | `core/chart_query.py:52` | `chart_query.build` 只被 `synthesis.sections` 调用（`synthesis.py:99`），**主报告出图路径不调用** |

**结论：面板（panel）采到了结构化数据、`chart_query` 也有"矩阵→热力图"的桥，
但桥的入口挂在 `theses` 上——`theses` 空了，桥就是死的。**

---

## 2. 目标：让"数据形状"达标

| 高级图 | 需要的数据形状 | 当前达标？ |
|---|---|---|
| 热力图 / 小倍数 | 同 metric × ≥5 实体 × ≥6 期次，稠密 | ❌ 同指标最多 2 行 |
| 散点 / 气泡 / 平行 | 每实体 ≥2 个 metric | ❌ 每个实体基本 1 个 metric |
| 旭日 / 树图 | 层级（父-子） | ❌ 无层级字段 |
| 桑基 / 网络 | 节点 + 边 + 流量 | ❌ 无流向字段 |

---

## 3. 四层改造（从上游到下游）

### 3.1 拆卡契约：把"可比点"写成结构化定义

卡片模板从"≥3 个可比点"改成：

> **同一个 `metric_id` 必须出现 ≥3 次，且分属不同 `entity`（或不同 `period`）。
> 交的时候按 `cells[]` 交：`metric_id / entity / period / value / unit / source`。
> 同指标不足 3 行 → 该指标记为 `shape_insufficient`，不得用它画图。**

### 3.2 采集/编译：加"形状校验"

`compile_agent_report` 生成 raw.json 时，逐 metric 统计行数：

- 同 metric ≥3 行 → `shape_ok`；
- 同 metric 1–2 行 → `shape_thin`（只允许 1D 图，且出图时标注）；
- 全报告 `shape_ok` 的 metric 占比 < 30% → 报告打 `data_shape_insufficient` 标记。

### 3.3 数据模型：raw.json 补 `dim` 字段

raw row 现在有 `entity/period/metric_id`，但**没有 `dim`（这一行属于哪个分析维度：
空间/时间/对象/结构）**。补 `dim` 后，`chart_query` 才能判断"这是矩阵还是趋势"。

### 3.4 出图路径：把 `chart_query` 接成主路径

`build_sections_contract` 的图来源增加一级（优先级最高）：

```
1. 作者显式 chart（origin=panel_query 或手写）
2. panel 矩阵 → chart_query.build(rows, metric_id)   ← 新增，接主路径
3. section.refs 派生的 1D 图（现有，兜底）
```

**关键：`chart_query.build` 从"只在 synthesis 里调"改成"每个有 panel 的节都调一次"。**

---

## 4. 步骤

| 步 | 做什么 | 退出条件 |
|---|---|---|
| S0 诊断固化 | 把"130行/129指标"这类形状指标写进 manifest（每份报告都报） | 每份报告出 `data_shape` 段 |
| S1 拆卡改契约 | 卡片模板改成"同 metric ≥3 行 + cells[]" | 新卡模板通过评审 |
| S2 采集加校验 | compile 时统计同 metric 行数，标 `shape_ok/thin` | 母婴重跑能报出 129 个 thin |
| S3 出图接桥 | `chart_query.build` 接入 `build_sections_contract` 主路径 | 有 panel 的节能出 heatmap |
| S4 加形状门禁 | `shape_ok` 占比 <30% → FAIL 并给"缺哪一维" | 低形状报告不再静默出 1D |

---

## 5. 数据形状门禁（新增）

报告级指标：

```
shape_ok_ratio = 同 metric ≥3 行的指标数 / 总指标数
```

- `shape_ok_ratio ≥ 0.5` → 通过；
- `0.3 ≤ ratio < 0.5` → 告警（只允许 1D 图，出图必须标注"形状不足"）；
- `ratio < 0.3` → FAIL，报告必须写"缺哪一维、要补哪些数据"。

母婴这次：`shape_ok_ratio ≈ 1/129 ≈ 0.008` → 必然 FAIL。这正是它该 FAIL 的地方——
**它本来就没有能画高级图的数据，却画了 8 张"看着像图"的 1D 图，掩盖了缺口。**

---

## 6. DoD

- 每份报告 manifest 带 `data_shape: {rows, metrics, shape_ok, shape_ok_ratio, thin_metrics}`；
- 拆卡模板要求"同 metric ≥3 行 + cells[]"；
- `chart_query.build` 在主出图路径被调用；
- `shape_ok_ratio < 0.3` 的报告 FAIL，并写清缺哪一维；
- 母婴重跑：要么补出矩阵数据画 heatmap，要么明确 FAIL（不再"8 张 1D 图充数"）。

---

## 7. 不做

- 不做"改这份报告"——改的是模板、校验、出图路径；
- 不做"自动把 1 个点画成高级图"——形状不够就是不够，不许美化；
- 不删 `chart_query`（它是桥，只是没接上）。
