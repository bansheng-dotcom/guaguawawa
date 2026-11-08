# 06 · 主数据与权限口径（masterdata）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/legal/compliance-check/SKILL.md
>


> 技能：`masterdata` ｜ 动作：`master_data` / `permission`
> 来源：frappe__erpnext（Item / Supplier / Warehouse / Customer / UOM / Price List + role profile）

## 第一层：方法论

权限是 ERP 的**「谁能在哪张单上做什么」的硬边界**。主数据是权限的载体：
六类主数据（item/supplier/warehouse/customer/uom/price_list）是 ERP 的外键世界，
它们的编码一旦污染（空格、中文、超长、重复），所有引用它们的下游单据都会错。

本技能坚持三条原则：
1. **编码是外键的生命线**——主数据 code 必须符合白名单字符集（`^[A-Z0-9][A-Z0-9_-]{1,31}$`），
   同类型内唯一。外键污染是「改一处、错一片」的乘数级错误。
2. **职责分离（SoD）是权限的地基**——同一角色不能对同一文档同时拥有冲突动作对
   （如 create + delete、submit + delete），防「自己录自己删」。
3. **高危动作必须有审计备注**——delete/cancel 这类不可逆动作，必须留下「为什么」。

权限矩阵的粒度是 **(role, doctype, action)** 三元组。角色白名单（buyer/warehouse_keeper/
sales/accountant/auditor/admin）与动作白名单（read/create/write/delete/submit/amend/cancel）
都必须枚举，自造角色或动作 = 绕过权限体系。

**关键立场**：本技能只做静态校验（编码合规、动作白名单、SoD 冲突识别），**不做真实授权**
——审计/税务/法务归 R03；本角色产出的是权限矩阵工件，供人工审批后落地。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| master_types | ∈ `{item, supplier, warehouse, customer, uom, price_list}` | erpnext 主数据 |
| code_pattern | `^[A-Z0-9][A-Z0-9_-]{1,31}$` | thresholds.masterdata |
| 唯一性 | 同类型内 code 不重复 | 外键公理 |
| role_types | ∈ `{buyer, warehouse_keeper, sales, accountant, auditor, admin}` | erpnext role profile |
| permission_actions | ∈ `{read, create, write, delete, submit, amend, cancel}` | erpnext DocPerm |
| SoD 冲突对 | `(create, delete)` / `(submit, delete)` | thresholds.masterdata |
| 高危动作 | delete/cancel 必须声明审计备注 note | 审计公理 |

**关键区分**：`submit`（提交入账）与 `amend`（修改）是不同权限；`cancel`（作废）是
比 `delete`（删除）更受控的动作——Cancel 留痕可追溯，Delete 直接消失。SoD 冲突对
`(submit, delete)` 拦截的是「提交入账后自己删凭证」的舞弊路径。

## 第三层：已验证的算例

**算例 A（干净·主数据）**：`examples/master_data.json`
```
records: item:RM-001 + supplier:SUP-001 + warehouse:WH-001
→ 类型合法 + 编码符合白名单 + 无重复 → PASS
```

**算例 B（脏·编码不合规）**：`examples/master_data_dirty.json`
```
records: item:"rm 001" → 含空格、小写 → 不匹配 ^[A-Z0-9][A-Z0-9_-]{1,31}$ → FAIL
```

**算例 C（干净·权限矩阵）**：`examples/permission.json`
```
buyer@Purchase Order:create + write；admin@Purchase Order:delete（有审计备注）
→ 无 SoD 冲突、高危动作有备注 → PASS
```

**算例 D（脏·SoD 冲突）**：`examples/permission_dirty.json`
```
buyer@Purchase Order:create + delete → 同一角色同文档冲突动作对 → FAIL
```
「自己录自己删」是典型的舞弊路径，SoD 门禁必须拦。

## 第四层：实战踩坑

- **编码是外键不是昵称**：编码一旦污染，改起来是「改一处错一片」。所以编码规范要在
  主数据入口做死，而不是靠下游每次校验。
- **SoD 只看 (role, doctype)**：跨角色的动作不构成 SoD 冲突（如 buyer 创建 + admin 删除
  是合规的）；SoD 只在同一角色同一文档内判定。
- **delete vs cancel**：delete 不可追溯、cancel 留痕。审计场景优先 cancel，门禁对 delete
  施加「审计备注」约束，逼出「为什么删」。
- **权限矩阵是静态工件**：真实授权落地（生效/失效）归人工或 R17 自动化，本技能不代做。
