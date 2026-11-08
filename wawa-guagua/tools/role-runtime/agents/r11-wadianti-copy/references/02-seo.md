# s02 SEO/AEO 与搜索发现（keyword / audit）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`alirezarezvani__aeo-box`（answer-engine-optimization 的 ContentAnalyzer：
E-E-A-T 四维打分 + 结构 + 引用）。

## 一、方法论（什么时候用、核心口径）

AEO（Answer Engine Optimization）让内容被 AI 答案引擎选中。本角色把「AEO 就绪度」
从营销话术转成**离线可算的确定性审计**，不依赖任何 API。
两个动作：
- `keyword`：校验关键词表——primary/longtail/intent/difficulty/aeo_opportunity
  五字段齐备，intent 在枚举内（informational/commercial/transactional/navigational/comparison）。
- `audit`：对内容正文做 E-E-A-T 就绪度审计——权威域引用、一手经验、数据点、
  二级标题结构、无 hype 词、时效信息、外链数量，逐项实算。

边界：**不做外链抓取与实时排名**（需 API，如实降级）；只做离线文本审计，
权威域命中、数据点、外链数量都是「信号」而非「结论」，排名结论交 R06 蛙得清。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`seo.authoritative_domains`（12 个权威域）、`seo.intent_enum`（5 类）、
`seo.min_external_links`（默认 3）、`seo.eeat_weights`（四维各 25 权重，为后续打分预留）。

**keyword 校验规则**：
- `primary/longtail/intent/difficulty/aeo_opportunity` 任一空 → BLOCKER。
- `intent` 不在枚举内 → BLOCKER。

**audit 校验规则**（content 为空直接 BLOCKER）：
- 权威域命中：`authoritative_domains` 任一在 content 内 → 记录（不 BLOCKER，是信号）。
- 一手经验：`\b(我|我们|我们的|我的|本人)\b` 命中 → 记录。
- 数据点：`\d+(,\d{3})*(\.\d+)?%?` 计数 → 记录。
- 二级标题：`^## ` 计数 ≥2 → 否则 BLOCKER。
- hype 词：guaranteed/miracle/secret/100%有效/保证有效/永不失败 命中 → BLOCKER。
- 时效：命中「更新/最后修改/发布/20xx」→ 记录。
- 外链：Markdown `[x](http...)` 非锚点外链数 ≥ `seo.min_external_links` → 否则 BLOCKER。

**输出键**：audit → `h2_count/external_links/data_points/auth_hits`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/audit.json`：含 who.int/cdc.gov/ieee 三个权威域外链 + 第一人称「我们」+
  数据点 42/1.8 + 4 个二级标题 + 无 hype + 时效 2026-11-01 → ok=true、external_links=3、h2_count=4。
- `examples/keyword.json`：intent=informational、difficulty=medium → ok=true。
- 脏夹具 `audit_dirty.json`：hype 词「保证有效」+ 只有 1 个外链 + 无二级结构 → ok=false / exit 1。
- 脏夹具 `keyword_dirty.json`：intent=branding（不在枚举）→ ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **权威域匹配要 lower**：content 里可能是「WHO.int」或「WHO.INT」，规则统一 `content.lower()`
  后再匹配，否则大小写导致漏检。
- **数据点正则要吞千分位**：`1,234` 会被 `\d+` 切成 1 和 234 两个数，所以正则要
  加 `(,\d{3})*`，否则数据点被重复计。
- **外链要排除锚点**：`[x](#标题)` 是目录不是外链，`startswith("#")` 过滤，
  否则目录链接被误计成引用。
- **hype 词是 BLOCKER 不是警告**：E-E-A-T 的 trustworthiness 反向信号，命中即 FAIL，
  和「记录型信号」分开对待。
