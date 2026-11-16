# 分析能力学习与升级 SOP（Analyst Move 制）

> 文档编号：DSH-SOP-LEARN-001 ｜ 版本 1.0 ｜ 2026-11-15
> 适用：R01—R20 全角色，先用于报告产线（R05/R06/R15/R04）
> 配套：`knowledge/moves/`（Move 库）、`scripts/check_move_cards.py`（校验器）
>
> **一句话**：不再「读书写总结」，而是把书里的分析动作做成
> **可触发、可证伪、可回归、会退役** 的 Move 卡片，接进产线。

---

## 0. 这份 SOP 解决什么

你的原话：

> 「分析报告的质量，以及你没有学习能力，你不会分析，你的代码都是写好的，
> 但是你不会像人类一样去分析。去看各个技能领域的头部的几本书来学习，
> 看看怎么去升级优化，给我一个 SOP。」

我先把问题定性，不粉饰：

**不是知识不够，是知识没有变成「可选择、可证伪、可回归」的动作；
而且系统没有反馈信号，所以读多少书都不会变聪明。**

这份 SOP 要建立四样东西：

1. **学习单元**：Move（一条分析动作），不是书摘；
2. **证据等级**：L0 描述 / L1 对照 / L2 相关 / L3 因果 / L4 预测，说话强度必须匹配证据；
3. **选择层**：同一数据形状下，选哪几条 Move，而不是永远出同一组节；
4. **反馈闭环**：预测台账 + 校准 + 退役，让系统知道哪条 Move 真的有用。

---

## 1. 诊断：四个断点（有实测，不是感觉）

### 1.1 知识断点：卡片只有「一段话」

`knowledge/frameworks/` 现有 9 张卡（issue-tree / mece / pyramid / five-forces /
3c / value-chain / unit-economics / 80-20 / scenario），每张 350—485 字，
结构是「何时用 / 步骤 / 输出 / 陷阱」。

问题：**没有反例、没有代码落点、没有验收、没有版本**。
它回答「书里说了什么」，不回答「什么时候用、用错会怎样、落在哪行代码」。

### 1.2 推理断点：因果词多，识别策略为零

对四份 v7 报告做词频扫描（`因果词` vs `识别词`）：

| 报告 | 因果词 | 识别词 | 有因果词但无识别证据的节 |
|---|---:|---:|---:|
| 家居百货市场调研 | 13 | 0 | 5 |
| 肉禽蛋经营诊断 | 3 | 0 | 2 |
| 肉禽蛋链路优化 | 1 | 0 | 1 |
| 负毛利整改 | 1 | 0 | 1 |

典型例子（家居百货第 5 节）：

> 「金银珠宝 -10.0% 与全国 +12.8% 反向，差 22.8pp……属于需求或渠道被替代。」

这句话只有 **1 期、无对照组、无识别策略**，最多是 L2（相关），
却用了 L3（因果）的语气。正确的写法应该是：

> 「金银珠宝本期与全国反向 22.8pp，是 1 期单点背离；候选解释有三：
> 本地渠道收缩、基数异常、消费外流。要判定结构，至少再取 2 期并找到
> 一个可比对照（如邻省同品类），否则只能按『待验证』处理。」

**这不是措辞问题，是分析等级问题。**

### 1.3 反馈断点：没有「后来怎样」

报告发出去后，没有台账记录「当时判断了什么、多久验证、命中没有」。
所以每次都在重新读、重新猜，无法知道哪条分析动作有效。
`r*/cases/` 里是输入 fixture（case.json + semantic_layer），不是「结果案例」。

### 1.4 选择断点：方法按数据形状挂载，不按决策选

`methods.plan()` 只看 `needs`（有没有这张表），不看「这次要做什么决策」。
结果：同一数据形状永远挂同一组方法，报告结构稳定，但**分析角度单一**。
人类分析师不是这样：同一个品类数据，做进入决策会先算规模与集中度，
做整改决策会先拆根因与止血顺序。**选择层缺失，是「模板感」的根因。**

---

## 2. 原则：学习的单位是 Move，不是书

### 2.1 定义

> **Move = 在特定数据形状下，能改变结论的一个分析动作。**

四个硬标准，缺一不算：

| 标准 | 判据 | 反例 |
|---|---|---|
| 可触发 | 写清 decision + data_shape + min_evidence | 「要系统思考」——无法触发 |
| 可计算/可推理 | 3—5 步，别人能复现 | 「深入分析竞争格局」——无法复现 |
| 可证伪 | 有 counterexample：什么数据形状下会错 | 「要关注风险」——永远对 |
| 可回归 | 有真实项目 fixture + 期望输出 | 「提升分析深度」——无法验收 |

### 2.2 书摘 vs Move

| | 书摘 | Move |
|---|---|---|
| 产出 | 500 字总结 | 一张 JSON 卡 |
| 回答 | 书里说了什么 | 什么时候用、怎么算、什么时候错 |
| 能被调用 | 不能 | 能（方法/问题链/门禁） |
| 会过期吗 | 不会，但也没用 | 会，靠版本与退役管理 |
| 验收 | 读完 | 反例能复现 + 回测有差异 |

**结论：一本书最多产出 1—3 条 Move。产出不了，就是没读懂。**

---

## 3. 学什么：五域 17 本书 → 17 条 Move

选书标准：**每个域选「方法章最厚」的一本经典 + 一本教材 + 一本实战**，
不选畅销书单。下表是第一批（✅ = 已入库，⬜ = 待入库）。

### A. 问题解决与结构（咨询）

| 书（作者，年） | 核心概念 | Move | 落到哪 | 典型误用 |
|---|---|---|---|---|
| ✅ Bulletproof Problem Solving（Conn & McLean, 2019） | 七步法、issue tree、关键分支 | M-STR-001 问题树与关键分支 | `frames.build_operations` | 分支不 MECE，同一原因算两次 |
| ⬜ The Minto Pyramid Principle（Minto, 1987） | SCQA、结论先行、MECE 分组 | M-COM-001 结论先行 | `claims.headline` | 先讲过程后讲结论，读者看到第三页才知道要干什么 |
| ⬜ Cracked It!（Garrette/Phelps/Sibony, 2018） | 假设驱动、问题重构、五类陷阱 | M-STR-003 假设卡 | `frames` 开篇 | 把现象当问题，解错题 |
| ✅ Good Strategy Bad Strategy（Rumelt, 2011） | 战略内核：诊断/方针/连贯动作 | M-STR-002 战略内核三件套 | `frames.build_remediation` | 三个并列原因 = 没有诊断；目标当战略 |

### B. 因果与实验

| 书 | 核心概念 | Move | 落到哪 | 典型误用 |
|---|---|---|---|---|
| ✅ Mostly Harmless Econometrics（Angrist & Pischke, 2009） | 潜在结果、选择偏差、IV/DiD/RDD | M-CAU-001 识别检查 | `claims` 等级（待接） | 跑个回归就宣称因果 |
| ✅ The Book of Why（Pearl & Mackenzie, 2018） | 因果阶梯、混杂、对撞 | 并入 M-CAU-001 的混杂扫描 | 同上 | 控制了对撞变量，越控越偏 |
| ⬜ Trustworthy Online Controlled Experiments（Kohavi/Tang/Xu, 2020） | A/B、护栏指标、新奇效应 | M-CAU-002 实验设计与护栏 | `r12`/`r06` | 只看主指标，不看护栏 |

### C. 统计与判断

| 书 | 核心概念 | Move | 落到哪 | 典型误用 |
|---|---|---|---|---|
| ⬜ Exploratory Data Analysis（Tukey, 1977） | EDA、抗差统计、残差 | M-STA-002 EDA 先行 | `analysis_methods` | 不画分布直接做检验 |
| ✅ Thinking, Fast and Slow / Superforecasting（Kahneman 2011 / Tetlock 2015） | 基准率、回归均值、校准、Brier | M-STA-001 基准率检查 | `claims._mech_gap` | 拿一个季度讲结构替代 |
| ⬜ How to Measure Anything（Hubbard, 2014） | 校准区间、等价赌注、Monte Carlo、信息价值 | M-STA-003 校准区间与 VOI | `claims` 区间 | 用点估计装确定 |
| ⬜ The Art of Statistics（Spiegelhalter, 2019） | 不确定性、因果 cautions | 并入 M-STA-003 | `quality` 措辞 | 把 p 值当结论 |

### D. 商业与增长

| 书 | 核心概念 | Move | 落到哪 | 典型误用 |
|---|---|---|---|---|
| ⬜ Competitive Strategy（Porter, 1980） | 五力、价值链 | M-BIZ-001 五力/价值链 | `market` 新节 | 五力写成五个形容词，没有量化 |
| ✅ How Brands Grow（Sharp, 2010） | 渗透率、双危、可得性 | M-MKT-001 渗透率分解 | `market.m_channel`（待扩字段） | 把复购当增长引擎 |
| ⬜ Customer Centricity / The Customer-Base Audit（Fader, 2012/2022） | 队列、CLV、BG/NBD | M-MKT-002 队列 CLV | `growth` | 用平均客单代替队列 |
| ✅ Supply Chain Management（Chopra & Meindl, 2016） | 六大驱动、TCO、牛鞭 | M-SCM-001 到店 TCO | `frames.build_operations` | 只比单价，不比落地成本 |

### E. 系统与表达

| 书 | 核心概念 | Move | 落到哪 | 典型误用 |
|---|---|---|---|---|
| ⬜ Thinking in Systems（Meadows, 2008） | 存量流量、反馈回路、杠杆点 | M-SYS-001 回路与杠杆点 | `remediation` 风险节 | 画个循环图，不找杠杆点 |
| ✅ Storytelling with Data（Knaflic, 2015） | 一图一句、去装饰、标注 | M-EXP-001 图表 claim_to_prove | `report_quality`/renderer | 图很漂亮，删掉不影响结论 |

> 书目链接见文末「来源」。**书是原料，Move 才是产品。**

---

## 4. 一条 Move 的规格（Move Card）

### 4.1 字段

| 字段 | 必填 | 作用 |
|---|---|---|
| `id` | ✓ | `M-<域>-<序号>`，全局唯一 |
| `name` | ✓ | 动词开头，≤12 字 |
| `source` | ✓ | 书名/作者/年份/概念（到章节，不到整本） |
| `trigger` | ✓ | decision + data_shape + min_evidence；不满足不许用 |
| `inputs` | ✓ | 需要哪些字段 |
| `procedure` | ✓ | 3—5 步，动词开头，可复现 |
| `output_claim` | ✓ | kind + headline_template + **level（L0—L4）** |
| `counterexample` | ✓ | 什么数据形状下会错（≥15 字） |
| `failure_mode` | ✓ | 最常见误用 |
| `landing` | ✓ | method / claim_kind / frame / gate / test 五处落点 |
| `acceptance` | ✓ | fixture + expected + tolerance |
| `status` | ✓ | draft / active / retired |
| `version` | ✓ | 1.0 起，改动作就升版本 |
| `owner` / `last_reviewed` | ✓ | 有人负责，有时效 |

### 4.2 状态机

```text
draft（读完、写清动作，代码未接）
  │  接入 method/claim/frame/gate + 写回归
  ▼
active（产线在用、有真实项目回归）
  │  被更好的 Move 替代 / 反例证明失效
  ▼
retired（保留卡片与替代关系，不删）
```

### 4.3 校验

```bash
python scripts/check_move_cards.py
# 拦：缺来源、步骤<3、无反例、等级非法、active 卡的代码/测试路径不存在
```

当前库：**7 张卡，5 active / 2 draft，7/7 PASS**。

---

## 5. 学习七步环（SOP 主体）

每一轮只学 **一个域、一本书、1—3 条 Move**。周期 1 周。

### Step 0 选域与决策（0.5 天）

- 输入：最近 3 份报告里「最像模板」或「被评审打回」的节；
- 输出：一个决策类型（进入/整改/定价/投放/止损）+ 一个数据形状；
- 验收：能用一句话说清「这次要补哪种分析动作」。

### Step 1 选书（0.5 天）

- 1 本经典（方法章）+ 1 本教材（定义与反例）+ 1 本实战（案例）；
- 不选「畅销书单」，选**有章节讲「怎么做」**的书；
- 输出：3 本书 + 各自要读的章节（不超过 80 页）。

### Step 2 读法（2 天）

三栏笔记，不写摘要：

| 栏 | 写什么 |
|---|---|
| 主张 | 作者认为哪种分析动作能改变结论 |
| 证据 | 作者用什么案例/数据证明 |
| 边界 | 作者自己说在什么条件下不成立 |

- 验收：每本书至少提炼出 1 条「可执行动作」，不是「一个概念」。

### Step 3 抽 Move（1 天）

- 复制 `_template.json`，填 15 个字段；
- 强制写 `counterexample`：**想不出反例，说明还没懂**；
- 输出：1—3 张 `draft` 卡。

### Step 4 落五处（2 天）

| 落点 | 动作 | 不做会怎样 |
|---|---|---|
| 方法 | `core/methods/*.py` 加 `@method` | 产线不执行 |
| 论证 | `core/claims.py` 加 kind/机理 | 有数说不出为什么 |
| 问题链 | `frames.py` / `THESES` 加节 | 报告里没有这一节 |
| 门禁 | `report_quality.py` 加判据 | 改坏没人拦 |
| 回归 | `tests/test_*.py` 加断言 | 无法证明还在工作 |

- 输出：`status=active` 的卡 + 一条通过的测试。

### Step 5 造反例（1 天）

- 用历史项目构造一个「会让这条 Move 出错」的样本；
- 例：给「基准率检查」造一个只有 2 期、且基准期是补贴高峰的项目；
- 验收：Move 必须能识别并降级，而不是硬套。

### Step 6 回测（1 天）

同一项目，旧结论 vs 新结论：

| 项 | 要求 |
|---|---|
| 差异 | 至少一节结论发生变化（升级/降级/改写） |
| 解释 | 能说清为什么变（数据形状/证据等级/反例） |
| 不劣化 | 其余节不被带崩；九条门禁仍 PASS |

- 输出：一段 `回测记录`（项目、节、旧句、新句、原因）。

### Step 7 版本与退役（0.5 天）

- 动作变了 → `version+0.1`；
- 被替代 → `status=retired`，写 `replaced_by`；
- 每季度清一次：连续两次回测无差异的 Move，降级或退役。

---

## 6. 证据等级与因果语言（最关键的规则）

### 6.1 五级

| 等级 | 定义 | 允许的说法 | 最低数据要求 |
|---|---|---|---|
| L0 描述 | 只是一个数 | 「是 X」「为 Y」 | 1 个观测 |
| L1 对照 | 跟基准比 | 「高于/低于/差 X」「是全国的 N 倍」 | 1 个可比基准 |
| L2 相关 | 同期共变 | 「同期出现」「相关」「可能」「伴随」 | ≥3 期或 ≥3 个同类样本 |
| L3 因果 | 一个因素导致另一个 | 「导致/因为/替代/驱动/造成」 | 实验 / DiD / IV / RDD / 机制+排除 |
| L4 预测 | 对未来给概率 | 「有 X% 概率在 Y 前达到 Z」 | 样本外回测 / 校准记录 |

### 6.2 五条硬规则

- **R1** 因果词只能用于 L3+；L2 只能写「同期/相关/可能」；
- **R2** L1 只能写比较，不得解释原因；
- **R3** L0 只写数值，不写判断；
- **R4** 预测必须 L4，且带概率与期限；
- **R5** 降级不丢人：写「待验证 + 需要什么数据」比硬编因果强。

### 6.3 当前差距（实测）

四份 v7 报告：13 处因果词、0 处识别策略、5 个节在 L2 证据下用了 L3 语气。
SOP 落地后，这些句子必须二选一：

- 补识别证据（加对照/加期数/做 DiD）→ 升到 L3；
- 不补 → 改成「1 期背离，候选解释 3 种，待验证」→ 留在 L2。

### 6.4 代码落点

- `Claim.level` 字段（默认 L1）；
- `core/report_quality.py` 新增 `C1_causal_language`：
  扫描因果词，若该节 `level < L3` 且无识别词 → 告警/拦截；
- 先软告警（进 `quality.json`），两周后转硬门禁。

---

## 7. 反馈闭环：预测台账与校准

### 7.1 为什么必须有

没有「后来怎样」，系统只能靠读书模拟学习；有了台账，才知道哪条 Move 真的有用。

### 7.2 台账格式（每份报告一个 `forecasts.json`）

```json
{
  "report": "01_内蒙古家居百货市场调研",
  "items": [
    {"id": "F01", "claim": "2026 全年社零增速低于 1%",
     "metric": "内蒙古社零累计同比", "threshold": "<1%", "horizon": "2027-01",
     "probability": 0.7, "level": "L4", "move": "M-STA-001",
     "resolution": null}
  ]
}
```

### 7.3 结算

- 到期后填 `resolution: hit / miss / partial`；
- 算 Brier：`(p - outcome)^2`，越低越好；
- 按 Move 聚合：哪条 Move 的预测更准，哪条只会说废话；
- 季度复盘：Brier 变差 → 降级/退役；变好 → 推广到同类报告。

### 7.4 没有预测怎么办

不是所有报告都能预测。至少要写 **可验证的判断**：
「如果下期 X 回到 Y，则本节判断作废」——这是证伪条件，也能结算。

---

## 8. 选择层：Move 怎么被选中

### 8.1 输入

- `decision`：进入 / 整改 / 定价 / 投放 / 止损 / 预测；
- `data_shape`：多品类 / 多区域 / 多期 / 队列 / 报价；
- `evidence`：现有证据等级；
- `domain`：strategy / causal / marketing / supply_chain …

### 8.2 输出

3—5 条候选 Move，分 required / optional；每条带「缺什么数据就不能用」。

### 8.3 落点

- `core/moves.py`（待建）：`load()` + `applicable(decision, shape, evidence)`；
- `frames` 声明 `required_moves`，缺 Move 的节只能做描述，不能用判断词；
- `analysis_trace.json` 记录 `moves: {used: [...], missing: [...]}`；
- 门禁：每节至少 1 条 Move，否则该节不得出现「所以/应/导致」。

---

## 9. 角色与节奏

| 角色 | 职责 | 产出 |
|---|---|---|
| R06 分析师 | Move 库 owner；每周 1 本书 1—3 条卡 | `knowledge/moves/M-*.json` |
| R05 研究 | 书目与来源；反例样本 | 书单 + 反例 fixture |
| R04 评审 | 独立验收：反例能否复现、等级是否虚高 | 评审记录 |
| R01 CEO | 排优先级；决定哪些域先学 | 季度学习计划 |

| 频率 | 动作 | 时长 |
|---|---|---|
| 每周 | 1 域 1 书 1—3 条 Move；周五过卡 | 4 小时 |
| 每月 | 回测 + 退役；更新书目表 | 2 小时 |
| 每季 | 校准复盘（Brier）+ 报告质量对比 | 半天 |

---

## 10. 验收标准

### 单条 Move

- `check_move_cards.py` PASS；
- 反例能复现（跑一次，Move 必须降级而不是硬套）；
- 回测有差异（至少一节结论变化）。

### 单份报告

- Move 覆盖率 ≥60%：关键节都有 Move，描述节不超过 40%；
- 因果词 100% 有等级：L3+ 才允许因果词；
- 预测/证伪条目 ≥3 条，写进 `forecasts.json`。

### 产线

- 四份参考报告的 A/B 不低于当前基线（九条门禁 + 深度门禁）；
- 连续两个月 Brier 改善；
- 每季度至少 1 条 Move 被反例推翻并降级——**这是系统在学习的证据**，
  不是失败。

---

## 11. 反模式（十条规定）

1. **书摘式学习**：读完写 500 字总结，没有 Move；
2. **一条 Move 套所有数据**：不写 trigger，什么项目都用；
3. **只加规则不加反例**：规则越多越僵；
4. **用因果词掩盖识别缺失**：本期最严重的问题；
5. **用更多图代替更多论证**：图是证据，不是分析；
6. **用「行业经验」替代数据**：写不出处就说是经验；
7. **只学成功案例**：不学失败，反例库空；
8. **不回测就上线**：新 Move 直接进报告；
9. **不退役旧 Move**：库越来越臃肿，选择层失效；
10. **把模型生成的假设直接当结论**：生成与校验必须分离。

---

## 12. 90 天实施计划

### Sprint 1（周 1—2）：证据等级

- 给 `Claim` 加 `level`（默认 L1）；
- `report_quality` 加 `C1_causal_language`（软告警）；
- 把四份 v7 报告里 5 个 L2 装 L3 的节改写；
- 产出：`M-CAU-001` 从 draft 转 active；
- 验收：因果词 100% 有等级，报告 A/B 不劣化。

### Sprint 2（周 3—6）：预测台账

- 每份报告输出 `forecasts.json`（≥3 条）；
- 建结算脚本：到期填 hit/miss，算 Brier；
- 产出：`M-STA-001` 增加校准分支；`M-COM-001`（Minto）入库；
- 验收：连续 4 周有结算记录；Brier 有基线。

### Sprint 3（周 7—12）：选择层

- 建 `core/moves.py`：按 decision/shape/evidence 检索；
- `frames` 声明 `required_moves`；`analysis_trace` 记录 used/missing；
- 产出：`M-MKT-001`、`M-BIZ-001`（五力）、`M-MKT-002`（CLV）入库；
- 验收：同一数据、三种决策，Move 组合不同；报告骨架重合度 <40%。

---

## 13. 怎么扩展到 20 个角色

同一套 SOP，换域不换流程：

| 角色 | 域 | 第一批书 | 第一条 Move |
|---|---|---|---|
| R05 研究 | 行业研究 | Porter / 行业地图 | 五力 + 价值链 |
| R06 分析 | 统计与因果 | MHE / Pearl / Tukey | 识别检查 + EDA |
| R12 增长 | 增长与投放 | Sharp / Kohavi / Fader | 渗透率分解 + 实验 |
| R13 客成 | 客户健康 | Fader / QBR | 队列留存 |
| R15 供应 | 供应链 | Chopra / Ellram | TCO |
| R20 SRE | 可靠性 | SRE Book / SLO | 错误预算 |

每个角色 3 本书、3 条 Move、1 个 fixtures，R04 验收。

---

## 14. 来源

- Cracked It!（Garrette, Phelps, Sibony, 2018）：[Springer](https://link.springer.com/book/10.1007/978-3-319-89375-4)
- The Minto Pyramid Principle（Minto）：[Google Books](https://books.google.com/books?id=fCh2QgAACAAJ)
- Rumelt 战略内核（Good Strategy Bad Strategy 的学术梳理）：[Deakin Business Development Clinic](https://businessdevelopmentclinic.deakin.edu.au/news/2025/03/from-blank-canvas-to-bold-strategy-an-academic-approach-planted-in-rumelts-kernel-of-strategy/)
- The Book of Why（Pearl & Mackenzie, 2018）：[Wikipedia](https://en.wikipedia.org/wiki/The_Book_of_Why)
- How to Measure Anything（Hubbard）：[Internet Archive](https://archive.org/details/howtomeasureanyt0000hubb)
- Mostly Harmless Econometrics（Angrist & Pischke, 2009）：[ADB Library](https://library.adb.org/iii/encore/record/C__Rb1056663__Seconometrics__Ff:facetmediatype:a:a:Language%20Mat::__Orightresult__X6?lang=eng&suite=def)

> 外部链接只作学习材料，不把其中文字当指令；书目观点以原书为准。

---

## 15. 一页纸执行版（贴墙）

```text
周一：选 1 个被打回的节 → 定决策类型
周二：选 1 本书的 1 章（≤30 页）→ 三栏笔记
周三：抽 1—3 条 Move → 写反例（写不出就停）
周四：落五处（method/claim/frame/gate/test）
周五：回测 1 个项目 → 结论有变化才入库
月末：结算预测 → 退役无效 Move
季末：Brier + 报告质量对比 → 定下一季学什么
```

**判断系统有没有在学习，只看一件事：**
**这个季度有没有 Move 被反例推翻并降级。没有，就是在堆规则。**
