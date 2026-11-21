# 工单：r07 蛙得明（产品）

- 总任务：中国小码女装市场的规模有多大，身高159厘米以下人群有多少，专属供给有多少？小码女装2025至2026年增速如何，增长来自渗透还是大盘？小码女装竞争格局如何，CR10与头部品牌份额是多少？小码女装的价格带与品类结构如何，哪个价位最赚钱？小码女装的退货率、客单价、毛利与单均贡献如何构成经营模型？小码女装的库存周转与补单模式如何影响现金流？小码女装在小红书与抖音的内容获客与转化效率如何？小码女装的进入策略与90天落地动作是什么，验收指标与停止条件是什么？
- 你负责 **2 问**（逐条答，答不了交 `unanswered`）：
  - **Q7**（清单型，必答）：小码女装品类结构如何，连衣裙裤装外套各占多少，爆品有哪些
  - **Q8**（机制型，必答）：小码女装退货率、客单价、毛利与单均贡献如何构成经营模型

## 你负责的 28 个格子（按格交，不许跳格）

| cell_id | 维度 | 度量 | grain | 期次 | 因果阶 |
|---|---|---|---|---|---|
| `Q7.对象.TOP5 品牌` | 对象 | share | G_brand_channel_year | 2026 | A |
| `Q7.对象.长尾合计` | 对象 | share | G_brand_channel_year | 2026 | A |
| `Q7.空间.全国` | 空间 | share | G_brand_channel_year | 2026 | A |
| `Q7.空间.省` | 空间 | share | G_brand_channel_year | 2026 | A |
| `Q7.空间.城市` | 空间 | share | G_brand_channel_year | 2026 | A |
| `Q7.时间.2024` | 时间 | share | G_brand_channel_year | 2024 | A |
| `Q7.时间.2025` | 时间 | share | G_brand_channel_year | 2025 | A |
| `Q7.时间.2026` | 时间 | share | G_brand_channel_year | 2026 | A |
| `Q7.结构.品类×渠道` | 结构 | category_mix | G_national_year | 2026 | A |
| `Q7.结构.价格带×渠道` | 结构 | category_mix | G_national_year | 2026 | A |
| `Q7.机制.量价拆解` | 机制 | gross_margin | G_national_year | 2026 | A |
| `Q7.机制.份额变化` | 机制 | gross_margin | G_national_year | 2026 | A |
| `Q7.边界.口径 vs 统计公报` | 边界 | share | G_brand_channel_year | 2026 | A |
| `Q7.边界.样本覆盖` | 边界 | share | G_brand_channel_year | 2026 | A |
| `Q8.对象.TOP5 品牌` | 对象 | share | G_brand_channel_year | 2026 | A |
| `Q8.对象.长尾合计` | 对象 | share | G_brand_channel_year | 2026 | A |
| `Q8.空间.全国` | 空间 | share | G_brand_channel_year | 2026 | A |
| `Q8.空间.省` | 空间 | share | G_brand_channel_year | 2026 | A |
| `Q8.空间.城市` | 空间 | share | G_brand_channel_year | 2026 | A |
| `Q8.时间.2024` | 时间 | share | G_brand_channel_year | 2024 | A |
| `Q8.时间.2025` | 时间 | share | G_brand_channel_year | 2025 | A |
| `Q8.时间.2026` | 时间 | share | G_brand_channel_year | 2026 | A |
| `Q8.结构.品类×渠道` | 结构 | category_mix | G_national_year | 2026 | A |
| `Q8.结构.价格带×渠道` | 结构 | category_mix | G_national_year | 2026 | A |
| `Q8.机制.量价拆解` | 机制 | gross_margin | G_national_year | 2026 | A |
| `Q8.机制.份额变化` | 机制 | gross_margin | G_national_year | 2026 | A |
| `Q8.边界.口径 vs 统计公报` | 边界 | share | G_brand_channel_year | 2026 | A |
| `Q8.边界.样本覆盖` | 边界 | share | G_brand_channel_year | 2026 | A |

> 每格按 `cells[]` 交：cell_id / value / unit / period / source_file / grade / quality 六维 / causal_level；填不了写 `unavailable` + tried + why。

## R02 任务契约（签发即生效）

- task_id：`T-r07-6a996c55d62e5ee1`
- 验收门禁：G1, G3, G7, G8, G13, G18
- 截止 / 升级：4h / r02
- 契约指纹：`6a996c55d62e5ee1`

## 1. 你负责回答什么

每一问都要交**三段**，缺「反例」按没深入处理：

- **事实**：数字 + 口径 + 期次（可回溯到 source）
- **机理**：为什么是这样（受什么约束、驱动是什么）
- **反例**：什么情况下不成立 / 有没有例外（找不到反例也要写"未找到"，并说明怎么找的）


## 2. 什么算答好（缺一条，这一问不算过）

1. 每问至少 **3 个可比点**（不同规格/地区/期次/主体），单点不算结论
2. 每节正文：**单段 ≤300 字（硬上限 330）**，2–4 条解读；节长不设上限（长度由判断数决定）；超过 330 字退回重写
3. 每条解读必须带 `refs`（指向本卡 numbers）——没有 refs 的数字视为编的
4. 每节必须有 `chart`（type/title/source/refs + bars 或 points）；确实画不了写 `chart_skip_reason`
5. 每问有 **事实 / 机理 / 反例** 三段，缺反例 = 没深入
6. 每条主结论带 **falsifier**（什么可观测条件下作废）
7. 必须交 **2 条计划外发现**（见第 4 段），不能是主问的复述
8. 每个 `needs` 要么被回答，要么 `declined` 写清原因

## 3. 你可以向谁要什么（卡间协商）

先想清楚"这一问缺了谁的数据就答不了"，写进 `needs.json`：

```json
{"needs": [{"id": "N1", "to": "r06", "what": "四城社零分品类",
            "why": "Q9 要判断节点城市，缺品类社零只能猜", "status": "open"}]}
```

- 发出去后跑 `python guagua.py report exchange --dir <项目>`，系统会把请求投到对方 INBOX
- 对方回 `answers.json`（带 source_file）；回不了就写 `declined` + 原因
- **open 的 need 会让整卡收不进来**——不要挂一个你其实不需要的依赖

## 4. 发散槽（硬性交付，不是建议）

交 `explore` 数组，2 条：

```json
{"explore": [{"text": "包头是唯一正号：可能与 XX 有关", "value": 9.1, "unit": "%",
              "source_file": "S2", "why_important": "如果成立，选品要按城市分"}]}
```

要求：带数字、带来源、**不是你负责问句的复述**。
业务上的关键原因常常不在这 10 个问句里，这一栏就是留给它的。

## 5. 交不了怎么办

```json
{"unanswered": [{"qid": "Q3", "tried": ["url1", "url2"],
                 "why": "内蒙品牌级零售无公开数据，省级社零不含品牌"}]}
```

`unanswered` 会进报告首页的「未答清单」，不会静默消失。


可协商的同伴：r06、r12、r05、r15

## 6. 交什么、交到哪

写到 `cards/r07/claims.json`；同目录下放 `needs.json` / `answers.json` / `explore`（可并入 claims）。
每问对应一节，节里加 `"answers": ["Q7"]` 声明这节回答的是哪一问——没有这个字段，报告对不上账。

## 7. dispatch 块（不填或填错，整卡拒收）

```json
{
  "dispatch": {
    "nonce": "98c73dd90cab57f1",
    "role": "r07",
    "by": "<你的执行者 id>",
    "questions": [
      "Q7",
      "Q8"
    ]
  }
}
```

- `by` 写真正执行这张卡的智能体 id；填 `r01` / `solo` 视为代写，直接拒收
- `questions` 必须和上面分配的一致

## 交数据的要求（决定图上能不能画出来）

- 每个判断至少 **3 个可比点**（不同规格 / 地区 / 期次 / 主体）
- 价格类：给完整阶梯（产地 → 出厂 → 批发 → 零售），不要只给一个价
- 趋势类：至少 4 期；不足 4 期就不要写趋势结论
- 2 个点画不成图，报告会退成表格——这是丢分项

## 来源要求（缺一条，整张卡拒收）

- 每条 source 必须带 `url`（http/https）、`date`（YYYY 或 YYYY-MM-DD）、`quote`（原文片段 ≥12 字）
- 每个数字必须指向本卡的某个 `source_file`；指向不存在的来源，整卡拒收
- 同一指标两个数，必须在 conflicts 里写清口径差

## 边界

- 只用公开可核来源；查不到写 `unanswered`（结构见上），不要编
- 你只对你负责的问句下结论；别人的问句不要抢，也不要写进 claims

## 维度网格（你负责的 24 个格子）

| 格子 | 维度 | 对象 | 度量 | 深度 | 匹配 |
|---|---|---|---|---|---|
| Q7.对象.TOP5 品牌 | 对象 | TOP5 品牌 | share | L3 | plan |
| Q7.对象.长尾合计 | 对象 | 长尾合计 | share | L3 | plan |
| Q7.空间.全国 | 空间 | 全国 | share | L3 | plan |
| Q7.空间.省 | 空间 | 省 | share | L3 | plan |
| Q7.空间.城市 | 空间 | 城市 | share | L3 | plan |
| Q7.时间.2024 | 时间 | 2024 | share | L3 | plan |
| Q7.时间.2025 | 时间 | 2025 | share | L3 | plan |
| Q7.时间.2026 | 时间 | 2026 | share | L3 | plan |
| Q7.机制.量价拆解 | 机制 | 量价拆解 | gross_margin | L3 | plan |
| Q7.机制.份额变化 | 机制 | 份额变化 | gross_margin | L3 | plan |
| Q7.边界.口径 vs 统计公报 | 边界 | 口径 vs 统计公报 | share | L3 | plan |
| Q7.边界.样本覆盖 | 边界 | 样本覆盖 | share | L3 | plan |
| Q8.对象.TOP5 品牌 | 对象 | TOP5 品牌 | share | L3 | plan |
| Q8.对象.长尾合计 | 对象 | 长尾合计 | share | L3 | plan |
| Q8.空间.全国 | 空间 | 全国 | share | L3 | plan |
| Q8.空间.省 | 空间 | 省 | share | L3 | plan |
| Q8.空间.城市 | 空间 | 城市 | share | L3 | plan |
| Q8.时间.2024 | 时间 | 2024 | share | L3 | plan |
| Q8.时间.2025 | 时间 | 2025 | share | L3 | plan |
| Q8.时间.2026 | 时间 | 2026 | share | L3 | plan |
| Q8.机制.量价拆解 | 机制 | 量价拆解 | gross_margin | L3 | plan |
| Q8.机制.份额变化 | 机制 | 份额变化 | gross_margin | L3 | plan |
| Q8.边界.口径 vs 统计公报 | 边界 | 口径 vs 统计公报 | share | L3 | plan |
| Q8.边界.样本覆盖 | 边界 | 样本覆盖 | share | L3 | plan |

> 填不了的格写 `unavailable` + 已试来源；**不许跳格、不许合并格**。
