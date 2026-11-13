# 02 · 人员与合同档案口径（people）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/onboarding/SKILL.md
>


> 技能：`people` ｜ 动作：`employee`（人员档案）、`profile`（联系人与附件）、`contract`（合同期限）
> 来源：frappe__erpnext（Employee doctype 在 setup/doctype）、frappe__hrms（合同/附件口径）

## 第一层：方法论

人员档案是**敏感个人信息的最小必要集**。这里的设计哲学与常规数据管理相反：

> **档案不是"越多越好"，而是"够用即可"。**

三条方法论：

1. **PII 最小化是硬红线**。身份证号/银行卡号/家庭住址/体检报告/宗教民族等超必要
   字段不得进入档案。这不是"隐私偏好"，是**红线 2**——收集过量个人信息本身就是风险。
2. **合同到期是主动治理**。合同到期提醒的窗口（默认 30 天）让续签从"事后救火"变成
   "事前安排"。到期日临近却无动作，是劳动关系的中断风险。
3. **紧急联系人与附件齐备是员工可服务性的底线**。没有紧急联系人，出事时无法联系
   家属；没有合同扫描件，劳动关系无凭证。

**本角色绝对不做的事**：不收集超必要个人信息、不做劳动关系法律判断、不做税务结论。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| employee.status | ∈ `{Active, Inactive, Suspended, Left}` | erpnext Employee.status |
| employee.required | `first_name`、`gender`、`date_of_birth`、`date_of_joining` | erpnext Employee 必填 |
| employee.salary_mode | ∈ `{Bank, Cash, Cheque}` | erpnext Employee.salary_mode |
| employee 时序 | `date_of_birth < date_of_joining` | 出生早于入职 |
| employee.pii | 不得含 `id_card/id_number/bank_account/bank_card/home_address/religion/ethnicity/medical_report` | R16 红线 2 |
| profile.emergency_contacts | `≥ 1`，且每条含 `name`、`phone` | 可服务性底线 |
| profile.attachments | `≥ 1`（身份/合同扫描件） | 劳动关系凭证 |
| contract 时序 | `start_date < end_date` | 合同起止顺序 |
| contract.expiry | `0 ≤ (end_date − as_of).days ≤ 30` → 触发到期提醒 | thresholds.contract.expiry_window_days |

**在职状态速查**：
- `Active`：在职，正常。
- `Inactive`：已停用但未离职（如长假），仍在名册。
- `Suspended`：停职，需附原因。
- `Left`：已离职，应从在编花名册剔除（影响 s07 headcount）。

## 第三层：已验证的算例

**算例 A（干净档案）**：`examples/employee.json`
```
王五 / Male / 1995-04-12 / 2026-11-10 / Active / Bank
```
必填齐备、状态合法、出生早于入职、无 PII 越界字段 → `ok=true`。

**算例 B（脏档案）**：`examples/employee_dirty.json`
```
赵六 / Male / 2027-01-01 / 2026-11-10 / Bogus / id_card=110101199501011234
```
BLOCKER ×3：出生（2027）晚于入职（2026）、状态 `Bogus` 越界、含 `id_card` 超必要 PII。

**算例 D（干净合同）**：`examples/contract.json`
```
EMP-0001 / 2026-11-10 → 2027-11-09 / as_of=2027-10-20
```
距到期 = (2027-11-09 − 2027-10-20).days = 20 天 ∈ [0,30] → 触发到期提醒，`ok=true`。

**算例 C（脏合同）**：`examples/contract_dirty.json`
```
EMP-0003 / 2027-11-09 → 2026-11-10
```
BLOCKER：合同起止顺序错误（起始晚于到期）。

## 第四层：实战踩坑

1. **PII 字段的"看起来合理"陷阱**。很多 HR 系统默认收集身份证号做社保，但 R16 的
   档案层**不存**这些——社保/税务所需的敏感字段在 R03 的合规通道处理，不在人员档案。
   档案只维护劳动关系所需的最小字段。

2. **date_of_birth = date_of_joining 是边界**。严格 `<` 还是 `≤`？口径取严格 `<`，
   因为同日出生+入职是不可能的（除非数据错误），标为异常。

3. **合同到期窗口的 as_of 缺失**。没有 as_of 时跳过到期提醒，不报错——因为"现在几点"
   应由调用方明确给出，而不是技能自己取系统时间（不可复现）。

4. **在职但无紧急联系人**。`Active` 员工必须至少有 1 名紧急联系人，这是可服务性底线。
   `Left` 员工可豁免，但本口径统一要求，简化处理。

5. **附件名称的"隐性"缺失**。attachments 为空数组 = 无凭证，属 BLOCKER；不能因为
   "附件在别的系统"就放过——本角色要求附件清单落地。

6. **不要在结论里写"这个员工的劳动合同效力没问题"**。这是越界到 R03 的劳动法律关系。
   正确写法："档案字段齐备，合同期限 2026-11-10 → 2027-11-09，距到期 20 天，
   触发续签提醒；劳动关系法律效力移交 R03。"
