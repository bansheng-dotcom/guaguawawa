# s03 公司与竞品情报（competitor）方法论

来源沉淀：`market-research-reports` competitor matrix + SEC EDGAR/USPTO 情报口径。

## 一、方法论（什么时候用、核心口径）

竞品情报回答「对手强在哪、我方差在哪、威胁多大」。两个动作：
- `matrix`：竞品特征矩阵——competitors × features 对照，识别我方 gaps。
- `battlecard`：单竞品战斗卡——五段齐备 + 威胁定级 + 定位重叠度。

边界：矩阵只陈述事实，「哪个功能要不要做」不在此拍板。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

取值白名单、五段清单、威胁枚举全部外置：`competitor.matrix_value_types`
（yes/no/partial/unknown）、`competitor.battlecard_sections`（5 段）、
`competitor.threat_levels`（4 级）。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s03_competitor.*`）

**matrix 校验规则**：
- competitor 缺某 feature → `competitor:missing_feature` HIGH。
- 取值（小写化后）不在白名单 → `competitor:value_type` HIGH。
- gaps = 我方（our_product.features）为 no 或 unknown 的 feature 清单。
- our_coverage = 我方 yes 数 / 总 feature 数。

**battlecard 计算规则**：
- 五段（positioning/strengths/weaknesses/strategy/pricing）任一缺失或为空 →
  `competitor:battlecard_section` HIGH。
- threat_level 按 strengths 占比分级：≥0.75 critical / ≥0.5 high / ≥0.25 medium / 否则 low
  （占比 = strengths / (strengths+weaknesses)，两者之和为 0 时计 0）。
- positioning_overlap = 我方与竞品 positioning 的词集 Jaccard 相似度（0–1）。

**输出键**：matrix → `competitor_count / feature_count / gaps / our_coverage / verdict / next`；
battlecard → `threat_level / battlecard_sections / positioning_overlap / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/competitor_matrix.json`（2 竞品 × 4 特征）：
- competitor_count=2，feature_count=4，gaps=[]，our_coverage=1.0，verdict=PASS。
`examples/competitor_battlecard.json`（厂商A：2 strengths / 2 weaknesses）：
- strengths 占比 = 2/(2+2) = 0.5 → threat_level = **high**，
  positioning_overlap = **0.0**（「个人开发者」vs「企业研发团队」词面无交集），
  battlecard_sections 长 5，verdict=PASS。
脏夹具 `competitor_matrix_dirty.json`：缺格或越白名单取值 → ok=false（门禁拦下）。
脏夹具 `competitor_battlecard_dirty.json`：缺段 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **威胁定级不是拍脑袋**：threat_level 只由 strengths/weaknesses 数量对比算出，
  案例里厂商A 2:2 正好 0.5 落在 high 档（≥0.5），不是 critical——两个强项两个弱项不构成碾压。
- **取值要先 `.lower().strip()` 再对白名单**：输入写 `"Yes"` 或 `" yes "` 都是合法 yes，
  不清洗会误报「越白名单」。
- **matrix 与 battlecard 是两套 competitor schema**：matrix 的 competitor 用
  `{name, features}`，battlecard 的用 `{name, positioning, strengths, …}`，
  contracts.py 里是两份独立 item schema（`_MATRIX_COMPETITOR` vs `_BATTLECARD_COMPETITOR`），
  不能复用同一个。
- **gaps 空 ≠ 没问题**：gaps=[] 只说明「特征都覆盖」，真正的差距可能在
  positioning_overlap 高（正面撞车）或威胁 high/critical，需要 battlecard 接着深挖。
