# s07 服务知识与升级（faq / escalation）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/customer-support/kb-article/SKILL.md
>


来源沉淀：`chatwoot__chatwoot` —— `canned_response.rb`（short_code + content 复用问答）、
`kbase.rb`（知识库）、`article.rb`（帮助文章）。只取「可复用问答 + 知识库条目」语义。

## 一、方法论（什么时候用、核心口径）

客服知识有两个失效模式：**重复**（同一个问题三个版本，答复口径不一致）和
**无证据升级**（把「客户说有问题」原样转给研发）。所以本能力域做两件事：

- `faq`：校验知识库条目——三件套、答案长度下限、语义重复检测。
- `escalation`：校验升级单——四要素、路由白名单、问题证据（source + quote）。

立场：**升级必须有证据**。没有 source（数据/工单来源）和 quote（可追溯原文）的升级单，
研发无法复现，只会把皮球踢回来。所以证据双要素做成硬门禁。

边界：升级路由只到 R07（产品）、R09（工程）、R03（合规）、R02（流程）；
不直接承诺修复时间，不替 R07 决定排期。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `knowledge` 节：

- `faq_required`：`question / answer / owner`
- `min_answer_chars`：40
- `duplicate_similarity`：0.8（字符二元组 Jaccard > 0.8 判重复）
- `escalation_routes`：`r07 / r09 / r03 / r02`
- `escalation_required`：`symptom / repro / impact / owner_route`
- `evidence_required`：`source / quote`

**faq 校验规则**：三件套缺项 → BLOCKER；答案 < 40 字 → BLOCKER；
任意两条问题 Jaccard > 0.8 → BLOCKER。

**escalation 校验规则**：四要素缺项 → BLOCKER；`owner_route` 不在四个路由 →
BLOCKER；`evidence` 缺 `source` 或 `quote` → BLOCKER。

**输出键**：faq → `faq_count`；escalation → `escalation_count / route`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

- `examples/faq.json`：续约/导出/升级三条问答，答案均 ≥ 40 字，两两 Jaccard 远低于 0.8
  → `faq_count=3`、ok=true。
- `examples/escalation.json`：403 报错，repro 可复现，impact 明确，route=`r07`，
  evidence 有 source（chatwoot__chatwoot）与 quote → ok=true。
- `examples/faq_dirty.json`：两条完全重复的「如何续约？」+ 一条 owner 空、答案「略。」→
  同时命中 `knowledge.faq_fields`、`knowledge.answer_len`、`knowledge.duplicate`。
- `examples/escalation_dirty.json`：route=`r99` 越界 + quote 为空 →
  `knowledge.route` 与 `knowledge.evidence` 双 BLOCKER。

## 四、实战踩坑（真拦下来的教训）

- **重复检测要看问题不看答案**：两条答案不同但问的是同一件事，照样是重复；本实现
  对 question 做 Jaccard，正是为了抓「换个说法再写一条」。
- **答案 40 字下限拦的是「略」「见文档」**：这类条目在知识库里毫无价值，却会让
  搜索命中率看起来不错。
- **升级单路由要白名单**：`r99`、`研发`、`技术` 这类模糊路由等于没有路由；
  四个路由对应四类阻塞（产品缺陷/工程故障/合规风险/流程卡点）。
- **evidence.quote 不能为空串**：只写来源不写原文，复现时仍然要回问客户。
- **symptom 要写「现象」不写「判断」**：「接口挂了」是现象，「他们代码写错了」是判断，
  后者会把研发带偏。
