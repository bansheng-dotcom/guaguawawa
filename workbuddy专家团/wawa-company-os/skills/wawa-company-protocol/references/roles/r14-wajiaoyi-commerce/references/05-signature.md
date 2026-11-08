# 05 · 电子签与签署审计口径（signature）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/legal/signature-request/SKILL.md
>


> 技能：`signature` ｜ 动作：`document`（待签文件）、`signing`（签署状态）
> 来源：documenso__documenso（DocumentStatus、RecipientRole、SigningStatus）

## 第一层：方法论

电子签的核心问题不是"签没签"，而是**谁在什么状态下签的、可不可以被事后否认**。
一份签署完成的合同，其审计价值取决于三个要素：

```
文件状态（DocumentStatus） × 收件人角色（RecipientRole） × 签署状态（SigningStatus）
```

本技能的两条铁律：

1. **COMPLETED 必须由全员签署支撑**。文件状态标为 `COMPLETED` 而仍有收件人
   处于 `NOT_SIGNED`，是**最危险的伪造信号**——它意味着"系统说签完了，
   但有人没签"。这类不一致必须 BLOCKER，不允许"稍后补签"的模糊处理。

2. **DRAFT 状态不得存在已签署记录**。`DRAFT` 是可自由修改的草稿态，
   若草稿里已有 `SIGNED` 收件人，说明签署记录被绕过或数据被篡改，
   属最高级别告警。

**本角色绝对不做的事**：不代签、不伪造签署状态、不代客户确认合同内容。
签署动作只能由真实的人在其设备上完成。R14 只核验"签署状态是否自洽"。

**角色语义**（决定谁必须签）：
- `SIGNER`：必须签署，未签则文件不可 COMPLETED。
- `APPROVER`：审批角色，本仓库口径下计入必须签署集合。
- `CC`：抄送，**不需要**签署，未签不影响 COMPLETED。
- `VIEWER`：只读，不签。
- `ASSISTANT`：代操作助手，不构成独立签署方。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| document_status | ∈ `{DRAFT, PENDING, COMPLETED}` | documenso DocumentStatus |
| recipient_roles | ∈ `{SIGNER, CC, VIEWER, APPROVER, ASSISTANT}` | documenso RecipientRole |
| signing_status | ∈ `{NOT_SIGNED, SIGNED}` | documenso SigningStatus |
| document_required | `title`、`status` | thresholds.signature.document_required |
| recipient_required | `email`、`role` | thresholds.signature.recipient_required |
| signed_roles | `{SIGNER, APPROVER}` | thresholds.signature.signed_roles |
| completed_status | `"COMPLETED"` | thresholds.signature.completed_status |
| 全签前置 | `status == COMPLETED` → **所有** `signed_roles` 收件人必须 `SIGNED` | 审计自洽性 |
| DRAFT 无签 | `status == DRAFT` → 不得存在 `SIGNED` 收件人 | 防伪造 |
| email 非空 | 去空格后长度 > 0 且含 `@` | 送达可行性 |

**签署时间线语义**：`DRAFT`（起草，可改）→ `PENDING`（发出待签，不可改内容）→
`COMPLETED`（全员签署完成）。这个顺序不可逆：从 `PENDING` 回到 `DRAFT` 属撤回，
需重新走发送流程；从 `COMPLETED` 回退意味着合同失效，属重大操作，必须人工介入。

## 第三层：已验证的算例

**算例 A（干净文件）**：`examples/document.json`
```
title=服务合作协议 / status=PENDING
recipients: zhang@example.com (SIGNER), li@example.com (APPROVER), wang@example.com (CC)
```
三个收件人角色均合法、邮箱非空、状态 `PENDING` 且无签署记录（合理）→ `ok=true`，
`recipient_count=3`。

**算例 B（脏数据）**：`examples/document_dirty.json`
```
title="" / status=SIGNED / recipients: ["" (bogus)]
```
实际 4 条失败判据：`文件标题非空`、`文件状态='SIGNED' 在白名单`（`SIGNED` 不在
`{DRAFT, PENDING, COMPLETED}` 内）、`签署人角色在白名单（越界 ['']）`、
`签署人均有邮箱（缺 ['bogus']）`。注意 `SIGNED` 是**签署状态**值，
不是**文件状态**值——混淆这两个枚举是签核数据的经典错误。

**算例 C（干净签署）**：`examples/signing.json`
```
status=COMPLETED
zhang (SIGNER, SIGNED) + li (APPROVER, SIGNED)   → signed_count=2 / must_sign_count=2
```
所有 `signed_roles` 均 `SIGNED` → 全签前置满足 → `ok=true`。

**算例 D（脏签署 —— 伪造信号）**：`examples/signing_dirty.json`
```
status=COMPLETED
zhang (SIGNER, NOT_SIGNED)   → 0/1 已签
```
判据：`COMPLETED 前置：必须签署人全签 （0/1）` → FAIL。这是最需要拦截的一类：
如果放行，下游会把一份实际未生效的合同当成已生效合同去执行，
进而产生订单、账单、付款义务——错误一路传播到底。

## 第四层：实战踩坑

1. **CC 未签被误判为"未完成"**：CC 是抄送，不需要签署。若把 CC 纳入"必须签"集合，
   大量正常合同会被判未完成。口径：只有 `SIGNER` 与 `APPROVER` 计入 `signed_roles`。

2. **`PENDING` 与 `NOT_SIGNED` 混淆**：一个是文件状态，一个是签署状态，分属两个枚举。
   校验时必须先确认读到的是哪个字段的值。

3. **全员签署但状态未同步**：所有收件人已 `SIGNED`，文件却仍是 `PENDING`。
   这不是错误，是**同步延迟**（事件尚未回写）。口径：判 WARN 并提示"等待状态同步"，
   不要判 BLOCKER——强制要求立即 COMPLETED 会导致正常的异步流程报错。

4. **签署顺序被忽略**：真实场景里存在"甲方先签、乙方后签"的顺序约束。
   本技能的样例未含顺序字段；接入真实数据时若存在 `signing_order`，
   需额外校验实际签署顺序与声明一致，否则会出现"越序签署"的审计漏洞。

5. **邮箱大小写与别名校验**：`Zhang@Example.com` 与 `zhang@example.com` 是同一人。
   比对前应做规范化，否则会把同一签署方当成两个人，误报"有人未签"。

6. **不要在结论里写"我已代客户签署"**：属 `unauthorized_exec`。
   正确写法："文件 X 的 SIGNER 全签、APPROVER 待签，不能标记 COMPLETED，
   需 li@example.com 完成签署后才能推进。"

7. **审计包要留证据**：一份好的签署结论应包含：文件 status、每个收件人的 role +
   signing_status、结论（是否可标记完成）、欠缺项（谁还没签）。缺了"谁还没签"，
   使用者无法知道下一步找谁。
