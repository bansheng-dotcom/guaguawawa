# s03 冷启动与外联（coldemail / sequence）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/email-sequence/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（cold-email 的冷邮件四要素、prospecting 的外联
序列）+ `retieedra-profound__skills-marketing-library`（外联合规清单，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

冷外联是零预算获客的起点。本角色的立场：**外联不能靠套话，要能过合规**。两个动作：
- `coldemail`：校验一封冷邮件是否可发——四要素（观察→问题→证明→请求）齐备、
  无 AI 腔禁词、发送前合规三件套齐备。
- `sequence`：校验一个外联序列——3-5 封、逐封新增价值、末封 breakup 收尾。

边界：本角色只校验外联邮件结构与合规，不真发邮件；外联对象必须是公开可触达的
商业联系，不爬取个人信息（红线）。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`outreach.email_required`（observation/problem/proof/ask）、
`outreach.ai_tells`（AI 腔禁词，含中英）、`outreach.compliance_required`
（secondary_domain/opt_out/postal_address）、`outreach.sequence_min/max`（3/5）、
`outreach.breakup_keywords`（最后/不再打扰/breakup/final）。

**coldemail 校验规则**：
- 四要素任一为空 → BLOCKER。
- 四要素拼接文本命中任一 `ai_tells`（不区分大小写）→ BLOCKER。
- `compliance` 非对象或三件套任一为空 → BLOCKER。

**sequence 校验规则**：
- `emails` 非列表 → BLOCKER；封数不在 [3,5] → BLOCKER。
- 任一封 body 为空，或任意两封 body 完全相同 → BLOCKER（逐封新增价值）。
- 末封 body 不含 `breakup_keywords` → BLOCKER。

**输出键**：coldemail → `ai_tell_count`；sequence → `email_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/coldemail.json`：四要素齐备 + 无禁词 + 合规三件套齐备 → ok=true。
- `examples/sequence.json`：3 封、body 两两不同、末封含「不再打扰」→ ok=true。
- 脏夹具 `coldemail_dirty.json`：含 "I hope this email finds you well"、"leverage"、
  "冒昧打扰" + 合规三件套全空 → ok=false / exit 1。
- 脏夹具 `sequence_dirty.json`：2 封（<3）+ body 完全相同 + 无 breakup → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **AI 腔禁词要中英都覆盖**：只拦中文「冒昧打扰」会漏掉英文套话 "I hope this email
  finds you well"，所以禁词表必须双语，且匹配不区分大小写。
- **逐封新增价值要判 body 集合去重**：只判封数会漏掉「复制粘贴三封」的情况，必须
  用 `len(set(bodies))==n` 保证每封都不一样。
- **合规三件套是发送前硬闸**：退订链接、次要域名、邮政地址缺一不可，这是外联
  合法性的底线，不能靠「差不多」。
