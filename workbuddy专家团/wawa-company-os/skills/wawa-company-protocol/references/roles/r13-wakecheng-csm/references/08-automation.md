# s08 客户运营自动化接口（automation / probe）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/customer-support/customer-escalation/SKILL.md
>


来源沉淀：`twentyhq__twenty`（对象字段与变更事件）、`chatwoot__chatwoot`（会话状态流转）、
`formbricks__formbricks`（问卷与响应事件），以及 R17 蛙织网（n8n）的自动化实现能力边界。
本能力域**不实现自动化**，只产出「自动化需求卡」。

## 一、方法论（什么时候用、核心口径）

R13 的职责边界是：**定义「该自动什么」，不定义「怎么自动」**。需求卡必须回答六件事：
触发（trigger）、条件（condition）、动作（action）、负责人（owner）、人工审批点
（approval_point）、审计（audit）。少了任何一件，R17 都无法安全实现。

三条硬立场：

1. **高危动作必须挂人工审批点**——退款、折扣、合同变更、数据导出、删除记录、群发邮件，
   自动化只能是「准备好待批」，不能直接执行。
2. **敏感字段禁入字段映射**——`password / api_key / secret / token / credit_card /
   id_number` 不出现在任何 `fields[].name` 里，这是把「不把凭据写进工作流」变成机器判据。
3. **探测是如实降级不是门禁**——`probe` 恒 `ok=true`，R17 未落地时 `status=blocked`。

边界：自动化实现交 R17；审批政策交 R03；不放宽任何一条红线。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `automation` 节：

- `trigger_types`：`record_created / field_changed / schedule / webhook / manual`
- `approval_actions`：`refund / discount / contract_change / data_export /
  delete_record / send_bulk_email`
- `required_fields`：`trigger / condition / action / owner / approval_point / audit`
- `field_types`：`string / number / boolean / date / enum / relation / currency`
- `forbidden_fields`：`password / api_key / secret / token / credit_card / id_number`

**automation 校验规则**：
- 六要素任一为空 → BLOCKER。
- `trigger` 不在白名单 → BLOCKER。
- 任一 `fields[].type` 越界 → BLOCKER。
- 任一 `fields[].name`（小写）包含禁用词 → BLOCKER。
- `action` 含高危词（refund/discount/...）且 `approval_point` 为空 → BLOCKER。

**probe**：检测 sibling 目录 `r17-wazhiwang-automation` 是否存在，输出
`status=ready|blocked`，恒 `ok=true`。

**输出键**：automation → `automation_count / field_count / trigger / high_risk`；
probe → `status / r17_present`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

- `examples/automation.json`：`field_changed` 触发、WON 后创建续约任务、
  `approval_point` 写明「续约折扣 > 10% 需人工审批」、字段 `opportunity_stage(string)` 与
  `renewal_discount(number)` → `field_count=2`、`high_risk=false`、ok=true。
- `examples/automation_dirty.json`：字段 `customer_api_key` → 命中 `automation.forbidden`，
  ok=false / exit 1。
- 内联用例：`action="automatic refund"` 且 `approval_point=""` → `automation.approval` FAIL。
- 内联用例：`trigger="manual"` 但动作是退款，仍判高危——审批不因触发方式而豁免。

## 四、实战踩坑（真拦下来的教训）

- **禁止字段要按「名字包含」匹配，不按相等**：`customer_api_key`、`stripe_token` 都是变体，
  精确匹配会全部漏掉。
- **高危判断看动作文本**：团队常把动作写成英文（`auto refund`）或中英混写，
  白名单词表要覆盖实际写法，宁可误判为高危也不要漏判。
- **审批点不能写「按需」**：`approval_point` 非空很容易通过，但「按需审批」等于没有
  审批；这是门禁挡不住、必须靠对抗评审与案例规则补的地方。
- **probe 不要做失败门禁**：R17 没落地是常态，探测失败不该让整份需求卡验收失败，
  否则团队会倾向于关掉探测。
- **审计字段不是摆设**：写清「记录变更前后值与操作人」，否则事后无法追责也无法回滚。
