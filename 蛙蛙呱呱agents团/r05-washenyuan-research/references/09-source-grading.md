# 源分级：一手 / 二手 / 三手与可访问性

> 用途：R05 研究链第 2 段 `source` 的方法依据。目标不是“找很多链接”，而是让每个子问题都能落到可复核的原始口径，并知道哪些源只是转述。

## 方法要点

1. **按“离原始事实的距离”分级，而不是按机构名气分级。**
   - 一手（primary）：统计机构原始表、政府公告/法规、企业年报与招股书、官网价格页、一线访谈逐字稿、自有实验数据。
   - 二手（secondary）：券商/咨询/媒体在原始数据基础上加工的图表与结论，必须能看到它引用了谁。
   - 三手（tertiary）：概览、榜单、聚合站、百科式转述，通常已经丢失采样方法与口径。
   - 数据库（database）：付费终端（如零售监测、海关库），介于一手与二手之间；要记录抽取日期、字段定义与许可范围。
2. **载体与可访问性要同时记录。** 载体是“官网页/行业报告/新闻/访谈/电商/数据库/年报”；可访问性是 `open / paid / restricted / offline`。`offline` 的源不能作为唯一证据。
3. **每个子问题至少一个一手候选。** 只有二手转述时，结论必须降级，并写明缺哪一类原始源。
4. **源地图先于采集。** 先列候选（≥10 个、≥3 类），再决定抓哪几条；否则容易“抓到什么写什么”。

## 来源

- OECD, *Quality Framework and Guidelines for OECD Statistical Activities*, 2012：统计数据的相关性、准确性、及时性、可获取性等质量维度。
- ISO 20252:2019, *Market, opinion and social research — Vocabulary and service requirements*：市场研究中对数据来源、访问方式与记录的要求。
- ESOMAR & ICC, *International Code on Market, Opinion and Social Research and Data Analytics*, 2016：区分原始数据与二手资料、保护受访者与客户信息。
- 国家统计局《政府信息公开条例》配套的数据发布与解读制度（官网“数据发布”栏目）：官方统计的发布口径、修订与说明机制。
- 美国《Data Quality Act》(2001) 及 OMB 信息质量指南：联邦机构传播信息时对“影响、透明、可复现”的要求，可迁移为源分级检查表。

## 适用边界

- 本分级衡量的是“可复核性”，不是“真理性”。一手源也可能口径错误（如样本偏差、统计修订），仍需第 4 段 `verify` 复算与时效检查。
- 对快速变化的行业（如 AI 硬件），二手报告可能比官方统计更新；此时允许二手源承担“时效”，但关键数字仍要回到一手或数据库核对。
- 付费数据库的字段定义常随供应商版本变化，必须记录版本/抽取日；跨年比较要先确认口径一致。
- 访谈属于一手，但单次访谈不是统计代表样本；只能用于解释机制或发现假设，不能单独外推总体比例。

## 误用反例

| 反例 | 为什么错 | 本仓拦截 |
|---|---|---|
| 全篇引用同一篇公众号转述，把它当“行业数据” | 转述可能已丢失样本、口径与年份，无法复核 | `source:type_diversity`、`source:tier_coverage` |
| 10 个链接全是“二手报告”，没有官网/统计/访谈 | 无法判断原始口径，结论不可追 | `source:type_diversity` 失败 |
| 把付费数据库截图当一手，不记字段与抽取日 | 字段定义可能变化，跨期不可比 | `source:candidate_fields` 要求 url/date/carrier/accessibility |
| 某个子问题没有候选源也继续写结论 | 结论没有证据入口 | `source:subquestion_coverage` |
| 收录 `offline` 的内部资料作为唯一证据 | 外部审计无法回抓 | `verify:refetch` 判 unverified，报告必须披露 |

## 与本仓落点

- 生产代码：`research_chain/source.py`（候选源、层级、载体、可访问性、逐子问题覆盖）。
- 门禁：`source:candidate_count`、`source:type_diversity`、`source:tier_coverage`、`source:candidate_fields`、`source:subquestion_coverage`、`source:unique_ids`、`source:accessibility_enum`。
- 夹具示例：`fixtures/pet_smart_hardware.json` 的 23 个源覆盖一手 14、二手 7、三手 1、数据库 1。
