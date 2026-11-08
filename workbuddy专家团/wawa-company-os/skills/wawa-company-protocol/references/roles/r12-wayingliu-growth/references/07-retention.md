# s07 激活、留存与推荐（activation / referral）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/customer-health/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（onboarding 的激活、churn-prevention 的流失预警、
referrals 的推荐机制）+ `retieedra-profound__skills-marketing-library`（留存 playbook，去重后
不重复计数）。

## 一、方法论（什么时候用、核心口径）

激活是留存的前置，推荐是增长的复利。本角色的立场：**留存不能靠发推送，要能定 aha；
推荐不能靠口播，要能算 K 因子**。两个动作：
- `activation`：校验激活流程——aha 时刻/time_to_value/funnel 三件套齐备、流失预警天数
  ≤14、召回渠道在白名单。
- `referral`：校验推荐机制——K 因子=i×转化率 实算、K 因子≥1.0、激励类型在枚举。

边界：本角色只校验激活与推荐的口径，不真发召回触达；召回渠道必须合规（邮件/短信/
推送/站内信/人工触达），不得私信轰炸（红线）。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`retention.activation_required`（aha_moment/time_to_value/funnel）、
`retention.churn_warning_days`（14）、`retention.recall_channels`（邮件/短信/推送/站内信/
人工触达）、`retention.kfactor_min`（1.0）、`retention.incentive_types`（单边/双边/分层）。

**K 因子实算**：`K 因子 = invites_per_customer × conversion_rate`（round 4 位）。

**activation 校验规则**：
- 三件套任一为空 → BLOCKER。
- `churn_warning_days` 非数字或 >14 → BLOCKER。
- `recall_channels` 非列表或为空 → BLOCKER；任一渠道不在 `recall_channels` → BLOCKER。

**referral 校验规则**：
- `invites_per_customer/conversion_rate` 缺或非数字 → BLOCKER。
- `K 因子<1.0` → BLOCKER。
- `incentive_type` 不在 `incentive_types` → BLOCKER。

**输出键**：activation → `recall_count`；referral → `kfactor/incentive_type`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/activation.json`：三件套齐备 + churn_warning_days=14 + 召回渠道合法 → ok=true。
- `examples/referral.json`：invites=5、conversion=0.3 → K 因子=1.5、双边激励 → ok=true。
- 脏夹具 `activation_dirty.json`：三件套全空 + 30 天预警 + 渠道越界 → ok=false / exit 1。
- 脏夹具 `referral_dirty.json`：invites=2、conversion=0.1 → K 因子=0.2（<1.0）+
  激励类型「返现」越界 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **K 因子要实算不猜**：K 因子=i×转化率，必须用代码算，不能靠人工填一个「应该会涨」。
- **激励类型要枚举**：单边/双边/分层 是常见结构，「返现」「积分」这种随意措辞要拦，
  逼业务落到标准类型。
- **召回渠道是红线**：只允许邮件/短信/推送/站内信/人工触达，「电话轰炸」「私信」
  这类越界渠道必须拦，对应「不未经授权采集个人信息、不私信轰炸」红线。
