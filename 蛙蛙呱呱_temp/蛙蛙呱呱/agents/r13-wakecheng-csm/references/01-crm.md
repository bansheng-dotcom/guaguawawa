# s01 客户与联系人管理（person / company）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/crm-hygiene-check/SKILL.md
>


来源沉淀：`twentyhq__twenty` —— `person.workspace-entity.ts`（姓名/联系方式/时间线）、
`company.workspace-entity.ts`（公司名/域名/年收入 + people 与 opportunities 关系）、
`note`/`timeline` 的互动记录。只取标准对象与字段语义，不取前端实现。

## 一、方法论（什么时候用、核心口径）

客户档案不是「一堆字段填满就算完」。真正的判据是三条：**能不能找到人、能不能看出
关系走到哪一步、互动记录是否可信**。所以本能力域只做两件事：

- `person`：校验单个人的档案——必填、生命周期、联系方式渠道、时间线时序。
- `company`：校验公司档案——必填、关联人员、关联商机引用完整。

立场：**档案的时间线必须单调递增**。时间线倒挂意味着有人在事后补记录、或者从别处
导入时字段错位；这时所有「上次联系是什么时候」的判断都会失真，因此直接判 BLOCKER，
不给「大致对」的余地。

边界：本角色只管档案口径，不替 R12 判定线索质量、不替 R07 判断谁是理想客户画像。

## 二、可执行口径（与实现逐字对齐）

阈值外置在 `experience/thresholds.json` 的 `crm` 节：

- `person_required`：`["name"]`
- `company_required`：`["name"]`
- `contact_channels`：`email / phone / linkedin / wechat / other`
- `lifecycle_stages`：`lead / qualified / customer / churned`
- `record_types`：`person / company / opportunity / activity`

**person 校验规则**：
- `person` 不是对象 → BLOCKER；必填缺项 → BLOCKER。
- `lifecycle` 不在四阶段枚举 → BLOCKER（不接受「潜在客户」「老客户」这类自造词）。
- `channels` 非列表或为空 → BLOCKER；任一 `type` 越界 → BLOCKER；任一 `value` 为空 → BLOCKER。
- `timeline` 非列表 → BLOCKER；`ts` 序列必须等于其排序结果 → 否则 BLOCKER。

**company 校验规则**：
- `people` 必须非空且每个都有 `name`；`opportunities` 必须是列表且每条都有 `name`。

**输出键**：person → `record_count / channel_count / timeline_count`；
company → `record_count / person_count / opp_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿）

- `examples/person.json`：张伟，qualified，email+wechat 双渠道，时间线 3 条单调 →
  `channel_count=2`、`timeline_count=3`、ok=true / exit 0。
- `examples/company.json`：云启科技，2 名人员 + 1 个商机 → `person_count=2`、`opp_count=1`。
- `examples/person_dirty.json`：name 为空 + 时间线倒挂（10-08 在 10-01 之前）→
  同时命中 `crm.person_required` 与 `crm.timeline_order`，ok=false / exit 1。
- `examples/company_dirty.json`：people 为空 + 商机无 name → 两条 BLOCKER。
- 附加断言：渠道 `fax` 越界 → FAIL（run_tests 内联用例）。

## 四、实战踩坑（真拦下来的教训）

- **时间线倒挂比字段缺失更危险**：字段缺了看得出来，时间线倒挂看起来「有记录」，
  但会让人误判客户最近一次接触时间。所以做成硬门禁而非警告。
- **生命周期要逼到枚举**：团队习惯写「意向客户」「重点客户」，这些都不是状态而是标签；
  强行映射成四阶段后，才能算漏斗流转率。
- **渠道值要非空**：只写「微信」不写微信号，等于没有联系方式——这是档案最常见的假完整。
- **公司必须有至少一个人**：没有联系人的公司档案在实际协作里完全不可用。
