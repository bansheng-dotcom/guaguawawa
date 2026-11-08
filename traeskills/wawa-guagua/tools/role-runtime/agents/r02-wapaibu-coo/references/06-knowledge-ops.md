> 蒸馏自: 补充技能/01-当前能力域/virgiliojr94__book-to-skill/SKILL.md

# 模块6 · 知识运营





>








> 整合自 virgiliojr94__book-to-skill（书籍/文档 → 技能）、


> anthropics__knowledge-work-plugins 的 productivity/memory-management、


> tobi__qmd（知识 store：BM25 + RRF + staleness）。


> 核心主张：**知识要么可检索，要么不存在**——


> 入库有指纹防重，检索有排序口径，过期有降权。





## 6.1 文档技能化门禁（s06/digest）





把书籍/长文档变成可执行技能的门禁（对齐 book-to-skill 四模式中的


analyze/generate 口径）：


- **13 种支持类型白名单**（pdf/epub/mobi/html/markdown 等）——


  不在名单的来源先转格式；


- **技能命名**：`{author}-{concept}` 风格 slug，≥2 段（kebab-case），


  单段命名被拦（已验证负例）；


- **章节结构**：`ch01-`…`chNN-` 编号连续，必含段落 Core Idea /


  Key Concepts / Key Takeaways（≥3 段）；


- **token 预算四件套**：SKILL.md ≤4000、glossary ≤1500、


  patterns ≤2000、cheatsheet ≤1200——超预算的「技能」没人读完；


- **sha256 指纹**（12 位）防重跑：已处理过的来源指纹命中即拦，


  重跑必须声明 foldin 合并模式。





## 6.2 条目登记（s06/entry）





对齐 memory-management 的幂等口径：


- **指纹 = sha256(title | sorted tags)**——同标题同标签的条目


  只存在一份，重复登记被拦走「更新合并」（已验证负例）；


- **尺寸门禁**：超存量均值 150% → `too_large`，必须拆分——


  单条巨无霸条目是检索的敌人；


- **过期检测**：>90 天未更新 → `stale` 标记。





## 6.3 检索（s06/search）





纯标准库实算 BM25 + RRF：


- **BM25**（k1=1.5, b=0.75）：中英混合分词（英文按词、


  中文按字符+二元组，保证中文可命中）；


- **RRF 融合**（k=60）：多 collection 各自排名 →


  `1/(k+rank)` 融合，跨库可比；


- **过期降权 ×0.5**：stale 条目排在新鲜内容之后。





已验证算例：查「投放口径」→ 首命中「投放口径说明 **v2**」


（新鲜版排在 v1 前），stale_count=2 条降权可见。





## 6.4 实战踩坑





- token 估算用 ≈4 字符/token 的粗口径——预算门禁看量级不看精确值，


  别拿它当 tokenizer 用。


- 中文检索靠字符二元组分词命中，**单字查询**召回偏低属正常，


  检索词至少两个汉字。


- 指纹防重跑的语义是「同来源不重复处理」，不是「同内容不重复入库」——


  不同来源的重复内容归 entry 的幂等管。


- 13 种类型、各 token 预算、BM25/RRF 参数、过期天数全部在


  `experience/thresholds.json → knowledge`，改口径不改代码。
