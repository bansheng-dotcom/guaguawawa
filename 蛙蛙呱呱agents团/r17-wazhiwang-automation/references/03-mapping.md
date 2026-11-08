# 参考层 03 —— 字段与身份映射（data-table-manager）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/data/skills/data-visualization/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/data-table-manager`
> 角色：R17 蛙织网 · S03 mapping 的确定性口径来源。

## 第一层 · 方法论

不同系统用不同的字段名、主键、枚举和类型。集成的第一步是**建一张映射表**：把
源系统的字段映射到目标系统的字段，并**显式声明主键**（身份）。n8n 的 Data Table
是跨 run 的持久表，它的列命名与类型有硬规则：

- **列名必须 snake_case**：小写字母开头，仅小写字母/数字/下划线。
- **类型只有四种**：`string` / `number` / `boolean` / `date`。智能推断时**保守**
  ——ID、电话、货币金额一律当 `string`，不猜数字（避免丢精度）。
- **系统保留名禁用**：`id` / `created_at` / `updated_at`（含 camelCase 变体）由
  Data Table 自动维护，用户列不得占用。

主键是「身份映射」的核心：两套系统要对话，必须有一个稳定的、非系统保留的主键，
且主键字段必须真实存在于映射表中。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 字段名格式 | 匹配 `^[a-z][a-z0-9_]*$` | data-table-manager snake_case |
| 列类型 | string/number/boolean/date 四选一 | data-table-manager 类型推断 |
| 系统保留名 | 拒收 id/created_at/updated_at 等 | data-table-manager 保留列 |
| 主键引用完整 | key_field 必须 ∈ 映射的 target 集合 | 身份映射要求 |
| 主键非保留名 | key_field ∉ reserved_columns | 同上 |
| target 去重 | 同一 target_field 不得重复映射 | 映射一致性 |

## 第三层 · 已验证算例

**干净映射**：
```
mappings: first_name→first_name(string), total_amount→total_amount(number)
primary_key: {entity: lead, key_field: first_name}
```
门禁：字段名 snake_case + 类型白名单 + 主键 `first_name` 存在且非保留名 → PASS。

**干净表**：
```
table_name=leads, columns=[lead_id(string), deal_amount(number), is_qualified(boolean)]
```
门禁：3 列全 snake_case + 类型合法 + 无保留名 → PASS，`column_count=3`。

**脏表**：
```
columns=[{name: id}, {name: CreatedAt}]
```
门禁：`id` 命中保留列 + `CreatedAt` 不符 snake_case → FAIL。

## 第四层 · 实战踩坑

1. **snake_case 正则要锚定首字符**：`^[a-z]` 而非 `[a-z]`，否则 `_x` 或数字开头
   会漏过。下划线连续也需在模式里排除。
2. **保留名要覆盖 camelCase**：Data Table 内部 `createdAt` 与 `created_at` 都算
   系统列，保留集合必须两套都列。
3. **主键值类型宽松**：主键 `key_field` 在 JSON 里可能来自 DB（int）或 API
   （string），契约用 `["string","integer"]` 双类型，别只写 string。
4. **类型推断不猜**：宁可把金额当 string 也不要当 number 丢小数精度——这是
   data-table-manager 明确的「保守推断」立场，R17 只校验「已声明类型是否合法」，
   不做智能推断。
