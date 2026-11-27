# 13 审稿五维：AI 味、文风、逻辑、结构、简化

## 方法

每个维度只留一条主 finding，避免“什么都提一句”导致无法修改。每条 finding 三件套：

1. 维度：ai_flavor / voice / logic / structure / simplification；
2. 原文片段：必须在选中稿里逐字存在，否则视为凭空点评；
3. 改法：动词开头，能直接执行。

五维关注点：
- AI 味：套话、转场腔、无对象的总结；
- 文风：书面讲台腔、术语堆叠、称呼不一致；
- 逻辑：结论与证据之间缺过渡、因果倒置；
- 结构：单段承载过多判断、层级混乱；
- 简化：句子过长、修饰词过多、一个句子两个主语。

审稿只做否决与建议，不直接改稿；改稿归 rewrite 段。

## 来源

- 公开方法：BLUF、plain language、George Orwell 的六条写作规则。
- 本角色实现：`content_chain/review.py` 的 `build()`、`check()`、`verify_quotes()`。
- 既有参考：`r11-wadianti-copy/references/05-voice.md`。

## 适用边界

- 原文片段来自选中稿，不来自候选稿；
- 五维是“最低覆盖”，不是评分模型；不输出百分制总分；
- AI 味词表是兜底，不能替代人工判断；
- 引文必须逐字匹配，标点差异也会被判为不可回溯。

## 误用反例

- 只写“这段有点 AI 味”但不引原文：`review.quote` 判 FAIL。
- 五维只写四维：`review.dims` 判 FAIL。
- finding 引用的句子在选中稿里找不到：`verify_quotes()` 判 FAIL。
- 改法写“优化一下表达”：长度不足 6 字，`review.fix` 判 FAIL。
