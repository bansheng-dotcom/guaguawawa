# 波特五力、竞品情报与 Mom Test 访谈

> 用途：R05 研究链第 7 段 `compete` 与需求侧访谈的方法依据。目标是让“竞争格局”落到逐格有源的矩阵，让“用户需求”落到过去行为而不是礼貌性赞同。

## 方法要点

1. **五力不是五个形容词，而是五组可验证的问题：**
   - 供应商议价力：关键器件是否可多源、切换成本、成本占比；
   - 购买者议价力：比价成本、集中度、转换成本；
   - 新进入者威胁：代工成熟度、渠道门槛、认证周期；
   - 替代品威胁：传统方案的价格/体验、替代速度；
   - 同业竞争：集中度（HHI/CR4）、价格战频率、产品同质化。
   每条评分（低/中/高）必须挂来源，不能只写“竞争激烈”。
2. **竞品矩阵固定维度、逐格有源。** 5 家 × 8 维（价格带、渠道、产品线、智能化、供应链、品牌、服务、出海），每格写“事实值 + source_id”。矩阵的价值在于暴露空缺，而不是把官网话术抄一遍。
3. **Battlecard 写“怎么打”，不是写“对手简介”。** 定位（他在用户心里是谁）、威胁（他会怎么抢我）、打法（我用什么具体动作回应）。
4. **份额与规模必须同口径。** 份额是线上还是全渠道、是 GMV 还是收入、是哪一年，都要写；份额合计不能超过 100%。
5. **Mom Test 三原则（Rob Fitzpatrick）：** 问过去的具体行为，不问未来意愿；问“上次遇到这个问题时你做了什么”，不问“你会不会买”；少说自己的点子，多听对方的事实与代价。

## 来源

- Porter ME. “How Competitive Forces Shape Strategy.” *Harvard Business Review*, 1979;57(2):137–145.
- Porter ME. “The Five Competitive Forces That Shape Strategy.” *Harvard Business Review*, 2008;86(1):78–93（五力的现代修订版）。
- Fuld LM. *The New Competitor Intelligence: The Complete Resource for Finding, Analyzing, and Using Information about Your Competitors*. Wiley, 1995（竞品情报的采集与合法性边界）。
- SCIP（Strategic and Competitive Intelligence Professionals）*Code of Ethics*：竞品情报不得使用欺骗、贿赂或侵犯商业秘密的手段。
- Fitzpatrick R. *The Mom Test: How to Talk to Customers and Learn If Your Business is a Good Idea when Everyone is Lying to You*. 2013.
- Ries E. *The Lean Startup*. Crown Business, 2011（用行为验证代替意愿问卷的“经证实的认知”）。

## 适用边界

- 五力是静态结构分析，不能预测具体时点的价格战；需要与第 3 段的时间序列证据配合。
- 竞品矩阵的 8 维是管理选择，不是唯一真理；维度一旦确定，跨期比较不能随意改，否则趋势失真。
- 份额数据常来自不同口径（GMV/收入/销量），混用会制造虚假集中度；必须写口径与年份。
- Mom Test 适合发现真实痛点与现有替代方案，不适合估算市场规模；访谈样本不能外推总体比例。
- 竞品情报必须合法：公开官网、年报、电商页面、公开访谈可以；伪装客户套取报价、窃取内部文件不可以。

## 误用反例

| 反例 | 为什么错 | 本仓拦截 |
|---|---|---|
| 五力只写“竞争激烈/供应商强势”，没有来源 | 无法复核，等于主观判断 | `compete:five_forces` 要求 rationale + source_id |
| 矩阵只填 3 家、维度只有 5 个 | 覆盖不足，无法比较 | `compete:competitors_5`、`compete:dimensions_8` |
| 某一格写“领先”但没有 source_id | 结论不可追 | `compete:cell_source` |
| 5 家份额相加 120% | 口径混用或重复计算 | `compete:shares` |
| 竞品规模 120 亿元，size p50 88 亿元仍不改 | 跨段自相矛盾 | `cross:market_size_consistency`（>5% 失败） |
| 访谈问“你会买吗”，对方说“会”就写需求已验证 | 礼貌性赞同不是行为证据 | 只作为低置信度线索，需 `tri:single_source_low_confidence` |
| 伪装客户向竞品索要内部报价 | 违反商业伦理与商业秘密保护 | 方法边界拒用；SCIP 伦理准则 |

## 与本仓落点

- 生产代码：`research_chain/compete.py`（5×8 矩阵、battlecard、五力、份额、市场规模）。
- 门禁：`compete:dimensions_8`、`compete:competitors_5`、`compete:matrix_complete`、`compete:cell_source`、`compete:battlecard`、`compete:five_forces`、`compete:shares`、`compete:market_size`。
- 跨段：`cross:cell_sources_exist`、`cross:market_size_consistency`、`cross:shares_sum`。
- 黄金成品：`golden/competitor-matrix.html`（5 家 × 8 维，40 格全部附 source id）。
