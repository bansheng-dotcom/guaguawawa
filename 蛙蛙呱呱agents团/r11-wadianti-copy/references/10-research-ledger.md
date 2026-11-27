# 10 证据台账：来源分级与 claim 挂靠

## 方法

证据台账不是参考文献列表，而是“结论—来源”的对照表。最小结构：
- `sources`：id、标题、URL、日期、原文引用（≥12 字）、档位；
- `claims`：claim_id、章节、结论句、数字、source_ids、示例；
- `quotes`：可直接进正文的原文；
- `gaps`：已知但未回答的问题。

来源分三档：
- 一手 primary：原始数据、官方文档、作者自述实验；
- 二手 secondary：媒体转述、行业报告、他人总结；
- 三手 tertiary：二手再转述，只能当线索，不能单独支撑结论。

挂靠规则：每个 claim 至少一条已登记来源；正文出现的每个数字必须能在某条 claim 的 `numbers` 里找到。
一手来源可单独支撑；二手需两条互证；三手只用于提示“存在争议”。

## 来源

- 公开方法：claim–evidence–warrant（图尔敏论证模型）、来源三角验证。
- 本角色实现：`content_chain/research.py` 的 `build()` / `check()`。
- 既有参考：`r11-wadianti-copy/references/02-seo.md` 的 E-E-A-T 段落。

## 适用边界

- 只做“可用性登记”，不做事实真伪裁决；真伪由人工复核；
- 不联网抓取，URL 与日期由输入提供；
- 三手来源不得单独支撑任何数字结论；
- 法规、医疗、金融等强监管主题需额外人工审签，不在本链自动放行。

## 误用反例

- 只列 7 条来源：`research.sources` 门禁要求 ≥8，直接 FAIL。
- 来源只有标题没有原文：`research.source_fields` 会指出缺失项。
- claim 写“数据表明增长很快”但不挂 source_ids：`research.claim_sources` 判 FAIL。
- 正文写“提升了 300%”，claims 里只有 30%：`final.fact_check` 报出多余数字并阻断。
