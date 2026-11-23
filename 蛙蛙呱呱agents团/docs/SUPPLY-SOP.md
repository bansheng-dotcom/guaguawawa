# 数据供给 SOP（v7.1）：两段发卡 + 供给方案是生成物

> 起因（2026-11-23）：用户问「降级应该在什么时候做」。
> 本文不直接回答执行细节，而是先做一次**需求诊断**——因为我认为问题定义偏了一层。
>
> 依据：[Zyte《Build or Buy》三步框架](https://www.zyte.com/blog/build-or-buy-solving-the-dilemma/)、
> [Lean Data](https://futurumgroup.com/insights/bigger-isnt-always-better-its-all-about-lean-data-collection/)、
> [MIT Sloan《The Data Problem Stalling AI》](https://sloanreview.mit.edu/article/the-data-problem-stalling-ai/)。

---

## 0. 诊断：问题定义偏了一层

### 你说的问题

> "数据补全不严格的时候要降级，降级应该在什么时候做？"

### 我的判断：**这是症状，不是原因**

| | 内容 |
|---|---|
| **症状** | 数据补全不严格 → 需要降级 |
| **原因** | **每个业务没有先定"数据供给方案"**，所以到采集时才发现采不到 |
| **后果** | 降级变成**常态**，不是例外 |

**证据（本会话实测）：**

| 项目 | 数据从哪来 | 能给到几级 |
|---|---|---|
| 汽车内饰 | **合成**（`random.seed(23)`） | 假 L2 |
| 咖啡 | Open Food Facts（真实） | 真 L1（无价格） |
| 母婴（老） | 网页 + quote（真实） | 真 L1（130 个数字） |

**三个项目，没有一个拿到真 L2。** 如果现在把降级做完美，结果只是**每份报告都诚实地写着"我是点证据"**——读者会认为系统没用。

### 更值得解决的问题

> **不是"采不到怎么降级"，是"这个业务到底能采到什么、成本多少、值不值得采"。**
>
> 降级是**兜底**；供给方案是**前提**。没有前提的兜底，会变成常态。

---

## 1. 业界依据

### 1.1 电商价格是全网最难采的（这不是 bug）

[Zyte 的行业观察](https://www.zyte.com/blog/sowa-hardest-sites-to-scrape/)：

> 「只有一小片网页需要最重的机器去读。这片网页被商店、房产、订票占据——
> **每一个公开的价格都是某人的市场情报**。」

**对我们的含义**：京东/天猫被反爬拦截，**是行业常态，不是我们代码不行**。
想要品牌级价格/销量，只有三条路：买、爬（重机器）、手工。

### 1.2 三步决策框架（Zyte）

> ① 先定优先级：**成本 / 时间 / 质量**（三者不可兼得）
> ② 做一个 POC/MVP 的范围
> ③ 决定 **自建 / 购买 / 混合**

**对我们的含义**：每个业务都该先过这三步，而不是直接开拆卡。

### 1.3 Lean Data：只采需要的

> 「更大不总是更好，关键是**精简的数据采集**。」

**对我们的含义**：84 格不需要 84 张表；先只采"决策必需"的那几个。

---

## 2. 数据供给的三层可得性

| 层 | 典型源 | 可得性 | 能给什么 | 能到几级 |
|---|---|---|---|---|
| **A 开放** | 统计局、政府公报、开放 API（Open Food Facts）、百科 | **高**（直接抓） | 宏观数、点证据、品类清单 | **L1** |
| **B 半开放** | 行业报告 PDF、公开榜单、新闻 | **中**（能读，但要解析） | 品类级规模/增速 | **L1**（品类级） |
| **C 封闭** | 电商价格/销量、第三方数据（生意参谋/魔镜） | **低**（要买 / 要重机器） | 品牌级、**序列** | **L2** |

**关键结论：L2 几乎只能从 C 层拿；而 C 层要么花钱，要么重工程。**

**所以"能不能到 L2"不是技术问题，是采购决策。**

---

## 3. 每个业务必须先交一份「数据供给方案」

**在拆卡之前**（不是之后），回答五件事：

```yaml
# 供给方案（业务级，一页纸）
business: <业务>
decision: <这份报告要支持什么决定>

sources:
  - layer: A
    name: 国家统计局
    gives: [品类规模, 增速, 保有量]
    cost: 0
    access: 直接抓
  - layer: B
    name: <行业白皮书>
    gives: [品类结构, 价格带分布]
    cost: 0
    access: PDF 解析
  - layer: C
    name: <第三方数据>
    gives: [品牌份额, 月度价格]
    cost: <报价>
    access: 购买

levels:
  L1_possible: true       # A+B 就能出点证据报告
  L2_possible: false      # 没有 C 层，做不了序列
  L2_condition: 需采购 <第三方>，约 X 元/年
```

**这份方案定了，后面才有意义：**

- 拆卡知道"哪些格子只能到 L1"
- 探测字段知道"预期行数是多少"
- 收卡降级知道"降到的基准是哪一级"

---

## 3.1 两段发卡：探源卡 → 采集卡（2026-11-23 修正）

**第一次发卡不是给执行层的，是给探测层的。**

| 发卡 | 给谁 | 目的 | 卡里写什么 | 回填 |
|---|---|---|---|---|
| **探源卡** | **探测层** | 查清有哪些源 | 要查哪些度量/维度、每个源要报什么 | `cards/probe/sources.json` |
| **采集卡** | 执行层 | 按已知源去采 | 每格能到 L1 还是 L2、缺什么 | `cards/<role>/claims.json` |

**为什么必须先探源**：
不先查清源，采集卡只能写"去采品牌价格"，执行层要么采不到、要么自己造。
探源卡把"有哪些源、各给什么字段、多少钱"先问清楚，采集卡才能写"这格采不到，标缺口"。

**探源卡由 `card_issue.prepare_probe_cards(project)` 生成**，落在 `cards/probe/TASK.md`，
回填 `cards/probe/sources.json`。

## 3.2 供给方案是**生成物**，不是手写输入

**v7.0 的错**：把 `supply.yaml` 当手写输入。结果只能写出"国家统计局""行业报告"
这种口号——因为写的时候既不知道要采什么，也不知道源里有什么。

**v7.1 的做法**：

```
拆卡 → 探源卡 → 探测层回填 sources.json
                        ↓
              card_probe.probe()
              需求(demand_of) × 源(load_sources) → 匹配
                        ↓
              supply_plan.from_probe()  →  plan/supply.json（生成物）
                        ↓
              采集卡（带 supply.json 的结论）→ 执行层
```

**生成物长这样**（汽车实测）：

```json
{"generated": true,
 "demands": [
   {"measure": "asp", "grain": ["brand","month"], "cell_count": 3,
    "matched_source": "manual_csv",
    "matched_via": {"brand": "split:brands:,:0"},
    "level": "L1", "missing": [], "why": ""},
   {"measure": "channel_share", "grain": ["brand","channel"],
    "cell_count": 5, "level": "L0", "missing": ["channel"],
    "why": "源里没有 channel 字段"}],
 "summary": {"demands": 6, "L2": 0, "L1": 1, "L0": 5,
             "planned_level": "L1", "planned_rows": null}}
```

**每一条都有命中源、覆盖格数、缺口原因。** 手写写不出这个。

**读取顺序**：`supply_plan.load_or_generate()` 优先读 `plan/supply.json`（生成物），
退回 `supply.yaml`（legacy 手写）。

## 3.3 `planned_rows` 由探测层申报

生成物里 `planned_rows` 可能是 `null`——因为"6 个品牌 × 24 个月"这种基数
只有探测层查过源才知道。

**申报方式**：在 `cards/probe/sources.json` 里写 `answers.planned_rows`。

没申报时 `collection_contract` 退回 `len(cells)`（格子数，下界），并标
`rows_expected_source: "cell_count(fallback)"`——**不假装知道行数**。

## 4. 降级的位置（**你说对了**）

```
拆卡 → 发卡 → 供给方案 → 探测字段 → 采集 → 收卡（不足→降级成基准）→ 报告 → 门禁
```

**降级在「收卡」时做**，理由：

| 步骤 | 这时知道什么 | 能降级吗 |
|---|---|---|
| 拆卡 | 想要什么 | ❌ |
| 发卡 | 派给谁 | ❌ |
| **供给方案** | **这个业务最多能到几级** | ❌（但定基准线） |
| 探测字段 | 预测能采到什么 | 🟡 预测 |
| 采集 | 正在采 | ❌ |
| **收卡** | **实际采到多少** | ✅ **这里判、这里降** |
| 报告 | 读结论 | ❌ 只读 |
| 门禁 | 验结论 | ❌ 只查 |

**"基准"由供给方案定**：方案说 L2 可达，采不到就降 L1；方案说只能 L1，那就不是降级，是**按计划交付**。

**这个区别很重要**：
- **计划内 L1** → 正常交付，不叫降级。
- **计划 L2 实际 L1** → 降级，必须写 `degraded_from`。

---

## 5. 二阶影响：9 个模块

| 模块 | 现在 | 改后 |
|---|---|---|
| **供给方案**（新） | 无 | 业务级一页纸，定 L1/L2 基准 |
| **拆卡** | 84 格，不看供给 | 格子标 `planned_level`（来自供给方案） |
| **探测字段** | `rows_expected = len(cells)`（错） | `rows_expected` = 供给方案预估的真实行数 |
| **发卡** | 不变 | 卡里带 `planned_level` |
| **采集** | collectors | 按供给方案选源（A/B/C） |
| **收卡** | 合并 | 比 `planned_level` vs 实际 → 降级 |
| **报告** | 按节渲染 | 首页写"计划 Lx / 实际 Ly" |
| **门禁** | G1'–G5' | 加 G-CAPABILITY（计划 vs 实际要一致或有理由） |
| **验收** | 13 项 | 加"供给方案存在且被引用" |

### 最痛的二阶后果

**拆卡会被供给方案约束**——这是好事（不再拆采不到的格子），但**用户会感觉"分析变少了"**。

**对策**：拆卡照旧穷尽，只给格子标 `planned_level`，不砍。**采不到的格子进"计划外缺口"，不是"删掉"。**

---

## 6. 三阶影响：四个

### 6.1 用户行为：从"要报告"变成"先定供给"

用户要先回答"这个业务我愿意花多少钱买数据"。

**这是好事**——它把"数据要不要花钱"从隐性变成显性。

**代价**：启动变慢。

### 6.2 复杂度迁移：从"代码"迁移到"采购决策"

代码复杂度不会再涨（供给方案是一页 YAML）。

**但决策复杂度涨了**：每个业务要评估"买不买数据"。

### 6.3 长期维护：供给方案会过期

源会改版、报价会变。

**对策**：供给方案带 `reviewed_at`，超过 6 个月提示复核。

### 6.4 危险：供给方案变成"免责声明"

写"只能 L1"然后就不采了。

**对策**：`L2_possible: false` 必须写 **`L2_condition`**（要多少钱/多少时间才能到 L2）。

---

## 7. 接线图（全系统）

```
⓪ 供给方案   projects/<业务>/supply.yaml        ★ 新，业务级
                   ↓ planned_level / planned_rows
① 拆卡       card_upgrade.build_grid            格子标 planned_level
                   ↓
② 发卡       card_issue.prepare                 卡里带 planned_level
                   ↓
③ 探测字段   collection_contract.build          rows_expected = planned_rows（真实行数）
                   ↓
④ 采集       core/collectors/*                  按 supply.yaml 选源
                   ↓
⑤ 收卡       dispatch.collect                   比 planned vs actual → 降级
                   ↓ merged["capability"] = {planned, actual, level, degraded_from}
⑥ 报告       report_flow                        首页写"计划 Lx / 实际 Ly"
                   ↓
⑦ 门禁       dataset_gates                      G-CAPABILITY：降到哪级必须有理由
```

### 文件级接线清单

| 文件 | 改什么 | 类型 |
|---|---|---|
| `core/supply_plan.py` | **新增**：读/校验 `supply.yaml`；算 `planned_level` / `planned_rows` | 新 |
| `core/card_upgrade.py` | 格子加 `planned_level`（默认从 supply 取） | 改 |
| `core/collection_contract.py` | `rows_expected` 改成 `planned_rows`；加 `capability` | **改（修 bug）** |
| `core/card_probe.py` | 判定对齐 `planned_level`（不是硬编码 full/partial/none） | 改 |
| `core/dispatch.py` | 收卡时算 `capability`（planned vs actual） | 改 |
| `core/report_flow.py` | 首页"计划 Lx / 实际 Ly"；缺口写补采条件 | 改 |
| `core/dataset_gates.py` | 加 G-CAPABILITY（软） | 改 |
| `core/card_issue.py` | 卡里带 `planned_level` | 改 |
| `scripts/compile_agent_report.py` | 透传 `capability` | 改 |
| `scripts/audit_dod.py` | 加"供给方案存在"一项 | 改 |
| `docs/REPORT-LINES.md` / `REPORT-STANDARD.md` | 补供给方案与能力级别 | 改 |
| `README.md` / `SKILL.md` | 同上 | 改 |
| `AGENTS.md` | 重新生成 | 生成 |

**新增 1 个文件，改 12 个。**

---

## 8. 验收（一阶/二阶/三阶）

### 一阶
- [ ] `supply.yaml` 能声明三层源 + `planned_level` + `L2_condition`
- [ ] `rows_expected` 等于真实预估行数（不再等于格子数）
- [ ] 收卡能算 `planned vs actual`

### 二阶
- [ ] 12 个文件接线
- [ ] 报告首页显示"计划 Lx / 实际 Ly"
- [ ] G-CAPABILITY 生效（软）
- [ ] **全系统 grep：`planned_level` / `capability` 每个字段都有读写方**

### 三阶
- [ ] **三个真实项目都能生成供给方案**（汽车/咖啡/母婴）
- [ ] 老产物读时按 `point_evidence` 处理，不报错
- [ ] `L2_possible: false` 必带 `L2_condition`
- [ ] 拆卡不缩水（`planned_level` 只标不砍）
- [ ] 全量测试零回归

---

## 9. 不做清单

1. **不在没有供给方案时开拆卡**（否则拆的是"想要的"，不是"能采的"）。
2. **不把"计划内 L1"叫降级**（那是按计划交付）。
3. **不把 `rows_expected` 写成格子数**。
4. **不砍格子**（只标 `planned_level`）。
5. **不让降级没有理由**（`degraded_from` + `L2_condition` 必填）。
6. **不假设电商价格能免费采到**（行业最难，要么买要么重工程）。

---

## 10. 一句话

> **降级是兜底，供给是前提。**
> **先答"这个业务能采到什么、值多少钱"，再谈"采不到怎么降"。**
> **计划内 L1 不叫降级；计划 L2 实际 L1 才叫降级。**
