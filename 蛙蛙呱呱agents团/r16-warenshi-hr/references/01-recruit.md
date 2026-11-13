# 01 · 招聘与入职口径（recruit）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/recruiting-pipeline/SKILL.md
>


> 技能：`recruit` ｜ 动作：`opening`（职位空缺）、`applicant`（候选人）、`offer`（录用通知）
> 来源：frappe__hrms（JobOpening / JobApplicant / JobOffer / Employee Onboarding 的 Select 枚举）

## 第一层：方法论

招聘管道是**状态机驱动的跃迁链**，每一个跃迁都有前置条件。职位空缺（Opening）
→ 候选人投递（Applicant）→ 筛选（Shortlisted）→ 录用（Offer/Accepted）→ 入职
（Onboarding）。把这条链做成确定性校验的价值，不在于"更快招到人"，而在于
**让不该发生的跳步发生不了**。

三条方法论：

1. **状态枚举即管道边界**。JobApplicant.status 是一台严格状态机，任何不在枚举内
   的状态都意味着"我们不知道这个人走到哪一步了"——未知即危险，一律 BLOCKER。
2. **录用前置是头号红线**。没有把候选人标记为 Shortlisted 就发 Offer，等于跳过
   筛选直接录用。这是招聘事故的头号来源。R16 只产出录用工件，**不擅自发 Offer、
   不替人入职**。
3. **邮箱是身份锚点**。候选人邮箱格式非法，后续所有通知都发不出去，而且可能是
   PII 泄露的入口。邮箱格式校验（正则）是管道的第一道门。

**本角色绝对不做的事**：不擅自发 Offer、不替人入职、不对外发出录用通知书。
所有对外动作都产出**请求工件 + handoff 声明**，由人工执行。R16 的价值在于
"把该不该录、录到哪一步算对"，不在于"按下发送键"。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| opening.status | ∈ `{Open, Closed}` | hrms JobOpening.status |
| opening.required | `job_title`、`designation` | hrms JobOpening 必填 |
| opening.vacancies | `≥ 1` | 招聘人数必须为正 |
| applicant.status | ∈ `{Open, Replied, Shortlisted, Rejected, Hold, Accepted}` | hrms JobApplicant.status |
| applicant.required | `applicant_name`、`email_id` | hrms JobApplicant 必填 |
| applicant.email | 正则 `^[^@\s]+@[^@\s]+\.[^@\s]+$` | 邮箱格式 |
| offer.status | ∈ `{Draft, Ready to Send, Awaiting Response, Accepted, Rejected, Cancelled}` | hrms JobOffer.status |
| offer.required | `applicant_name`、`applicant_email`、`offer_date`、`designation` | hrms JobOffer 必填 |
| offer.accept_prior | `status==Accepted` → `prior_status ∈ {Shortlisted, Accepted}` | R16 录用前置口径 |

**录用前置状态机速查**：
- `Open` → `Replied` → `Shortlisted` → 发 Offer 是合法管道。
- `Accepted` 只能来自 `Shortlisted`（刚通过筛选）或 `Accepted`（重复确认）。
- `Rejected` / `Hold` 是不可直接录用的终止/暂停态，发 Offer 前须先核对原因。

## 第三层：已验证的算例

**算例 A（干净录用）**：`examples/offer.json`
```
张三 / zhangsan@example.com / 2026-11-05 / R9 代码工程官 / Accepted / prior=Shortlisted
```
必填齐备、邮箱合法、状态白名单、前置合法 → `ok=true`。

**算例 B（脏录用）**：`examples/offer_dirty.json`
```
李四 / lisi@example.com / 2026-11-05 / R9 代码工程官 / Accepted / prior=Open
```
BLOCKER：`接受前置状态='Open' ∈ [Shortlisted, Accepted]` 不成立——跳过筛选直接录用。

**算例 C（脏候选人）**：`examples/applicant_dirty.json`
```
李四 / not-an-email / Bogus
```
BLOCKER ×2：邮箱格式非法、状态 `Bogus` 不在白名单。

## 第四层：实战踩坑

1. **"候选人很优秀"不能替代 prior_status**。录用前置是事实校验，不是主观判断。
   任何"虽然没筛选但这个人很熟/很强"的说辞都不能跳过 G1。

2. **Replied ≠ Shortlisted**。`Replied` 只是"候选人回复了"，可能回复的是"不考虑"。
   把 Replied 当成已筛选是常见误判。

3. **Accepted 的重复确认**。候选人已 Accepted，再发一次 Offer 确认，prior_status
   仍是 Accepted，属合法（重复确认），不是流程错误。

4. **邮箱格式的"隐性"泄露**。不只是明显非法邮箱。形如 `zhangsan@@example.com`、
   带空格、带中文全角 `＠` 都算非法，正则必须覆盖。

5. **不要在结论里写"我已录用 XXX"**。这是越权（`unauthorized_hr_action`）。
   正确写法："产出录用工件 offer.json（prior=Shortlisted），标注需人工授权，
   由人工对外发出。"

6. **职位空缺的 vacancies=0**。招聘人数为 0 的职位空缺是脏数据（已关闭却标 Open），
   口径：`vacancies ≥ 1`。

7. **offer_date 缺失**。录用日期是合同与薪资的锚点，缺了会导致下游 s02 合同、
   s05 薪酬无法对齐，必须在录用层拦下。
