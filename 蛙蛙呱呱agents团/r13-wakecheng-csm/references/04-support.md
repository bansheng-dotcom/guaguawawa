# s04 全渠道客服（inbox / ticket）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/customer-support/ticket-triage/SKILL.md
>


来源沉淀：`chatwoot__chatwoot` —— `conversation.rb`（status: open/resolved/pending/
snoozed、first_reply_created_at、waiting_since、assignee、team）、`inbox.rb`
（channel_type 白名单）、`message.rb`（message_type: incoming/outgoing/activity/template、
private 内部备注）、`csat_survey_response.rb`（rating 1-5）、`app/builders/v2/reports`
（conversations_count / avg_first_response_time / avg_resolution_time 指标口径）。

## 一、方法论（什么时候用、核心口径）

客服不是「回复了就完事」，而是四个可量化的事实：**多快回、多久解决、会不会重开、
客户满不满意**。所以本能力域做两件事：

- `inbox`：校验整批会话的 SLA——渠道/状态白名单、首响、解决时长、重开率、CSAT 均值。
- `ticket`：校验单张会话——状态/渠道/消息方向、私有备注隔离、至少一条入站。

立场：**首响与解决时长分别对「已响应」和「已解决」的会话生效**，未响应的会话不该
因为「还没有首响」被判超时，也不该因为「还没解决」被判超时——这是最常见的误报来源。
另一个关键判据是**私有备注隔离**：内部讨论（如「这个客户要特殊处理」）一旦变成对外
outgoing 且 `private != true`，就是真实的客诉事故。

边界：不替 R07 决定产品缺陷归属、不替 R03 判定退款资格；只给客服事实与 SLA 结论。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `support` 节：

- `conversation_status`：`open / pending / snoozed / resolved`
- `channel_types`：`web_widget / email / whatsapp / facebook / instagram / api / sms / telegram / twitter`
- `message_types`：`incoming / outgoing / activity / template`
- `first_response_minutes_max`：240；`resolution_hours_max`：48
- `reopen_ratio_max`：0.15；`csat_min`：4.0；`csat_scale`：[1..5]

**inbox 校验规则**：
- 渠道或状态越界 → BLOCKER。
- 有 `first_response_minutes` 且 > 240 → BLOCKER。
- `status=resolved` 且有 `resolution_hours` 且 > 48 → BLOCKER。
- `reopened` 占比 > 0.15 → BLOCKER。
- 任一 `csat` 不在 1-5 → BLOCKER；已有评分的均值 < 4.0 → BLOCKER。

**ticket 校验规则**：状态/渠道白名单；`messages` 非空；`message_type` 白名单；
`message_type=outgoing`、`private != true` 且内容含「内部」→ 判泄漏；
至少一条 `incoming`。

**输出键**：inbox → `ticket_count / channel_count / open_count / avg_csat / reopen_count`；
ticket → `ticket_count / message_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

- `examples/inbox.json`：4 条会话、3 个渠道，首响 15-60 分钟、解决 20-30 小时、
  CSAT 5 与 4 → `avg_csat=4.5`、`ticket_count=4`、ok=true。
- `examples/ticket.json`：incoming + outgoing(private=false) + activity，无「内部」泄漏 →
  `message_count=3`、ok=true。
- `examples/inbox_dirty.json`：channel=`fax` 越界、首响 600 分钟、解决 100 小时、
  CSAT 1、含重开 → 5 条 BLOCKER，ok=false / exit 1。
- `examples/ticket_dirty.json`：状态 `closed_illegal`、channel `fax`、内部备注未隔离、
  无入站消息 → 4 条 BLOCKER。

## 四、实战踩坑（真拦下来的教训）

- **未响应的会话被判首响超时**：只对「有 first_response_minutes 字段」的会话判；
  没这个字段表示还没响应，属于积压问题而非 SLA 违约，应单独统计。
- **private 字段缺省不等于 true**：许多系统缺省是 false，一旦内容含内部讨论即泄漏。
  判据必须是 `private is True`，不是「没写就当他私有」。
- **重开率高不一定是客服差**：也可能是修复不彻底；所以重开率只做门禁，不做归因，
  归因交 R07/R09。
- **CSAT 均值要有样本**：没有评分时不判达标，只报告；用 0 分代替缺失会系统性拉低均值。
- **渠道枚举要贴近真实接入**：`fax`、`line` 这类未接入渠道出现在数据里，说明导出或
  映射出了问题。
