# s04 红人与合作增长（influencer / comarketing）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/competitive-brief/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（influencer-marketing 的达人分级、co-marketing
的联合营销五要素）+ `retieedra-profound__skills-marketing-library`（红人合规清单，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

红人合作是撬动外部流量的杠杆。本角色的立场：**合作不能只追粉丝量，要能反刷量**。两个动作：
- `influencer`：校验红人合作是否合规——达人分级在枚举内、披露合规（#ad 必含）、
  反刷量检查通过。
- `comarketing`：校验联合营销方案——partner/audience/offer/channel/measure 五要素齐备。

边界：本角色只校验合作方案与合规，不真联系达人、不代投放；反刷量是本角色红线，
粉丝突变/泛评论/机器人/买粉/刷量信号命中即拦截。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`partner.tiers`（nano/micro/mid/macro/thought_leader）、
`partner.disclosure_tokens`（#ad/#sponsored/广告/赞助）、`partner.fraud_signals`
（粉丝突变/泛评论/机器人/买粉/刷量）、`partner.comarketing_required`（五要素）。

**influencer 校验规则**：
- `tier` 不在 `tiers` → BLOCKER（短路返回）。
- `disclosure` 不含任一 `disclosure_tokens` → BLOCKER。
- `fraud_signals` 命中任一 `fraud_signals` → BLOCKER（反刷量检查）。

**comarketing 校验规则**：
- 五要素任一为空 → BLOCKER。

**输出键**：influencer → `tier/partner_count`；comarketing → `element_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/influencer.json`：tier=micro + disclosure=#ad + 无刷量信号 → ok=true。
- `examples/comarketing.json`：五要素齐备 → ok=true、element_count=5。
- 脏夹具 `influencer_dirty.json`：tier=mega（不在枚举）+ 无披露 + 刷量信号 → ok=false / exit 1。
- 脏夹具 `comarketing_dirty.json`：offer 为空 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **tier 枚举要短路**：tier 非法时直接返回，别继续判披露，否则脏数据会在披露校验里
  碰巧通过，掩盖分级问题。
- **披露 tokens 要兼容多写法**：中英都有（#ad/#sponsored/广告/赞助），只认 #ad 会漏掉
  中文「广告」标注的合规内容。
- **反刷量信号是红线**：粉丝突变/泛评论/机器人/买粉/刷量 这些词出现在 fraud_signals
  里必须拦，这是本角色「不刷单、不伪造评价」红线的直接落地。
