# 报告产线 v7 · 论证链（2026-11-15）

> 目标：把「算得对但写得薄」的产线，升级成能产出**咨询级论证报告**的产线。
> 参照标准是 6 份既有报告：
> `家居百货 302 亿元存量替换`、`肉禽蛋市场调研与数据分析`、`经营报告`、
> `链路优化`、`牛肉与鸡蛋负毛利整改`、`营销调研与内容增长方案`。
>
> 本版不新开产线：仍是 `report produce` 一条入口、`report_compose` 装配、
> `report_renderer` 唯一渲染器、`check_report_flow` 九条门禁。
> 新增的是**论证层**与**问题链帧**，以及一条会拦住模板稿的**深度门禁**。

---

## 一、v4/v5 的问题（先承认）

v4 已经能算：品类涨跌、单位经济、批零加价、跨市套利、贡献分解都算对了。
但它出的是「数据说明书」：

| 症状 | 代码层原因 |
|---|---|
| 每节都是「3 条 bullet + 一张表 + 本节边界」 | 章节由 finding 按固定顺序平铺，`_section_from` 只有一种装配方式 |
| 标题是标签不是判断（「结构：2 涨 5 跌」） | 标题由方法直接给，没有「命题」层 |
| 只报数，不解释为什么、不说什么情况下错 | Finding 只有 `reading`，没有机理/落点/证伪字段 |
| 五类报告只换顺序，不换问题链 | 纲领（THESES）只有 order + ask，没有节级问题 |
| 深度靠形容词补 | 没有可判定的「深度」门禁 |

结论：**缺的不是计算，是论证结构**。

---

## 二、v7 加了什么（四个模块）

```text
data/obs_*.json  data/facts.json  data/derived_metrics.json
        │
   fact_table.py        带来源事实表：id/指标/值/单位/期/地区/等级/url/quote
        │
   methods/market.py    区域消费市场方法族（11 个方法）
   analysis_methods.py  价格/成本方法（沿用，不动口径）
        │
   claims.py            论证层：观察 → 对照 → 机理 → 落点 → 证伪
   frames.py            问题链帧：经营 / 链路 / 整改（各一套节序列）
        │
   report_compose.py    装配（Claim → section / Frame → section）
        │
   report_renderer.py   唯一渲染器（48 型图，未改）
        │
   check_report_flow.py 九条门禁（能不能发）
   report_quality.py    反模板门禁（是不是模板）
```

### 1. `core/fact_table.py`：带来源的事实表

把项目里三种数据形态归一成一张可查的表：

- `data/obs_*.json`：`{id, indicator, value, unit, period, region, source_org,
  source_title, url, quote, grade}`（家居百货的 249 条观测就是这个形态）；
- `data/facts.json`：列表（奶酪项目的 `metric/name/value/source_id`）或扁平 dict；
- `data/derived_metrics.json`：带 `formula/inputs` 的派生量。

关键 API：`one/series/find/latest/value/pct`，按**指标语义 + 地区 + 期**取数，
不写死 id。期次统一排序（`2026Q1-3` 晚于 `2026H1`），百分数统一成比例
（`0.043` 与 `4.3` 都按 4.3% 处理），同一指标多来源时优先 A 级 + 有 url + 最新期。

### 2. `core/claims.py`：论证层

一条判断不是一句话，是一个结构：

```python
Claim(kind="gap", headline="结构：通讯器材 +69.5% 比全国 +20.9% 高 48.6pp；…",
      detail=[观察句…], refs=[E001…], tags={items, same_dir, …},
      mechanism=…, implication=…, falsifier=…)
```

`finalize()` 按 `kind` 调用机理函数，用 `tags` 里的量化标签生成：

- **机理**：为什么会这样，或至少给两种解释 + 判别方法（不把相关说成因果）；
- **落点**：所以该做什么/不该做什么，可执行或可验收；
- **证伪**：什么条件下这个判断作废，给可观测阈值。

标签不全就不硬编（`REQUIRED_TAGS`），门禁据此判「深度不足」。
节内强标签按 `kind` 变化（口径差 / 背离清单 / 成本栈 / 位次 / 缺口清单…），
避免每节都长成「判断/机理/落点/证伪」同一个壳。

### 3. `core/methods/market.py`：区域消费市场方法族

11 个方法，全部吃事实表、全部只认指标语义：

| key | 回答的问题 | 关键算法 |
|---|---|---|
| `size` | 市场多大 | 居民支出法/社零占比法/家庭户数法/全口径法，给区间+收敛+敏感性 |
| `demand` | 需求来自新增还是替换 | 新增家庭/存量家庭、老龄化、小家庭化 |
| `trend` | 大盘还增不增 | 多年序列、CAGR、最新累计、与全国的同向/反向 |
| `mix` | 结构怎么变 | 逐品类本地 vs 全国，pp 差、同向/反向、最大向上/向下背离 |
| `volume` | 增长靠量还是靠价 | 名义 = 价格 + 量 + 交叉 |
| `channel` | 钱从哪流走 | 业态增速对照 + 线上渗透 |
| `region` | 区域集中度 | 盟市份额、CR3、HHI 上下界、县域样本 |
| `supply` | 供给够不够 | 卖场/超市/县域商业网点密度 |
| `policy` | 补贴改变哪个价格带 | 补贴比例 ÷ 单件上限 → 锁价区间 |
| `consistency` | 同一指标两套数 | 公报增速 vs 绝对值反推，识别口径修订 |
| `coverage` | 哪些结论不能下 | 缺盟市/缺品类/缺期，逐条写影响与补数动作 |

### 4. `core/frames.py`：问题链帧

同一批 finding，三类报告的问题链不同，章节结构就必须不同：

```text
经营诊断：矩阵 → 单位经济 → 采购三档 → 跨市场配额 → 周转损耗 → 定价组合 → 风险 → KPI
链路优化：分段加价 → 可重构段 → 单位经济 → 跨市场 → 风险
负毛利整改：根因拆解 → 三段目标 → 分品类动作 → 整改后账 → 里程碑 → 拍板 → 不做清单
```

每节的数字仍来自 finding 里已登记的 `Num`；新增的推导值（KPI 目标、每千斤改善）
用 `cite.n` 登记，阈值写进 `section.assumptions`，正文不出现无出处的数。

---

## 三、深度门禁（`core/report_quality.py`）

九条门禁管「能不能发」，本模块管「是不是模板」：

| 判据 | 硬/软 | 阈值 | 拦什么 |
|---|---|---|---|
| Q2 有对照 | 硬 | ≥50% 的节含对照词 | 只报数、不跟任何对象比 |
| Q3 有落点 | 硬 | ≥50% 的节含落点词 | 读完不知道要做什么 |
| Q5 不套壳 | 硬 | 「本节边界」覆盖 <30% | 每节尾巴都挂同一句话 |
| Q6 不复读 | 硬 | 12 字片段 <15%，重复句 ≤10% | 跨节复制粘贴 |
| Q7 深度下限 | 硬 | 节≥6、字≥4000、数≥100、图表≥4 | 三段式薄报告 |
| Q1 标题即判断 | 软 | ≥85% | 标题只是标签 |
| Q4 有机理 | 软 | ≥40% | 只报现象、不解释 |

**阈值是拿 6 份参考报告校准过的**：参考稿全部 PASS；
v4 的肉禽蛋报告因「本节边界」覆盖 83% 被判 FAIL —— 这正是要拦的模板稿。

`compare(paths)` 再做一层：把多份报告的章节前缀与解读条数分布放在一起，
若两类报告骨架重合 ≥60% 且条数分布相同，判「同一模板换数据」。
当前 4 份 v7 报告两两重合度 8%—33%，不构成同模板。

---

## 四、数据契约（写新项目时照这个填）

```text
项目/
  data/
    obs_*.json      必填：带 url/quote/grade 的观测（一个指标一条）
    facts.json      可选：老项目的扁平事实
    derived_metrics.json 可选：带公式的派生量
    assumptions.json     可选：{key: {value, note}} 项目假设
    meta.json       可选：{"title": "报告标题"}（不从目录名硬拼）
  raw/              可选：原文（quote 回抓用）
```

`obs` 一条的最小字段：`id / indicator / value / unit / period / region / grade`；
有 `url + quote` 才能进「A 级证据」，没有就只能当 B/C 级并写进缺口。

---

## 五、加一类新报告，只动三处

1. **数据**：按上面的契约补观测（不用改代码）；
2. **方法**：在 `core/methods/` 加 `@method(key, family, needs, produces)`，
   返回 `Finding`，把量化标签放 `meta["claim"]`；
3. **问题链**：在 `core/report_thesis.py` 加 `THESES[key]`（order + ask + PRIMARY），
   需要专门章节结构就在 `core/frames.py` 加一个 `build_*`。

渲染器、门禁、CLI、R04 清点都不用动。

---

## 六、复现（4 份 v7 报告）

```powershell
cd "D:\蛙蛙呱呱\蛙蛙呱呱agents团"
$out = "D:\蛙蛙呱呱\workspace\reports\v7"

python guagua.py report produce --intent "内蒙古家居百货市场调研" `
  --dir "D:\蛙蛙呱呱\家居百货内蒙调研_2026-11-15" --out "$out\household"

python guagua.py report produce --intent "内蒙古肉禽蛋经营诊断" `
  --dir "D:\蛙蛙呱呱\内蒙古肉禽蛋调研_2026-11-12" --out "$out\meat_ops"

python guagua.py report produce --intent "内蒙古肉禽蛋链路优化" `
  --dir "D:\蛙蛙呱呱\内蒙古肉禽蛋调研_2026-11-12" --out "$out\meat_chain"

python guagua.py report produce --intent "牛肉与鸡蛋负毛利整改方案" `
  --dir "D:\蛙蛙呱呱\内蒙古肉禽蛋调研_2026-11-12" --out "$out\meat_fix"

# 双门禁
python scripts/check_report_flow.py --dir "$out\household"
python -m core.report_quality "$out\household\report.html"
python -m core.report_quality --compare `
  "$out\household\report.html" "$out\meat_ops\report.html" `
  "$out\meat_chain\report.html" "$out\meat_fix\report.html"
```

每份报告的 `quality.json` 保留全部判据与取值，`manifest.json` 里
`quality.ok / score` 与 R04 清点、逐节过账并列。

---

## 七、边界（这一版没做的）

1. **采集仍由 agent 完成**：找哪些来源、摘哪句 quote 是判断；产线只做回抓校验、
   台账、计算、成稿。它不会自己发现「哪个行业值得做」。
2. **区域市场方法族绑定「消费市场」语义**：指标名对不上（例如没有社零、
   没有分品类增速）时会整节跳过并写缺口，不会拿别的数硬凑。
3. **价格类帧仍依赖羊肉/鸡蛋这种「品类×价格」长表**：没有批发价或没有产地价，
   采购三档 / 链路分段会降级为单档，并在边界里写明。
4. **软指标还不是硬门禁**：Q1/Q4 只记分不拦，因为参考稿本身在这两项上也不高；
   等更多样本后再收紧。
5. **PDF 仍受本机 Chrome 限制**：交付以单文件 HTML 为准。
