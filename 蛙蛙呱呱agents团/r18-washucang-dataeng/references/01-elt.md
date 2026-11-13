# 01 · 数据连接与 ELT 口径（elt）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/architecture/SKILL.md
>


> 技能：`elt` ｜ 动作：`connection`（连接配置）、`sync`（同步任务）
> 来源：airbytehq__airbyte（`airbyte-integrations/connectors/` 的 `source-*` / `destination-*` 命名约定、`metadata.yaml` 的 connectorType、sync mode 口径）

## 第一层：方法论

ELT 管道的第一段是**「来源 → 目的地」的连接与同步**。连接器名字、同步模式、
stream 集合——这三样构成「数据能不能稳定到达」的地基。把这段做成确定性校验的
价值，不在于"连得更快"，而在于**让不成立的连接在配置层就发不出来**。

三条方法论：

1. **连接器命名约定即路由边界**。Airbyte 的连接器目录严格以 `source-`（来源）
   与 `destination-`（目的地）命名。名字不符合约定的配置，编排器无法识别、无法
   路由——未知即危险，一律 BLOCKER。
2. **sync mode 是口径漂移的头号来源**。`full_refresh` 每次全量覆盖，
   `incremental_append` 只追加、`incremental_dedup` 追加去重——选错模式直接导致
   多算或重算。sync mode 必须落在白名单内。
3. **增量必须有 cursor 字段**。选 `incremental_*` 却不声明 `cursor_field`，
   下次同步就找不到「从哪续」，要么重复拉全量、要么丢数。cursor 字段是增量模式的
   必需伴随项。

**本角色绝对不做的事**：**绝不在产出里携带任何连接凭据**。api_key / secret /
password / token 一律不落工件（凭据走环境变量 / 密钥管理）。R18 的价值在于
"把该不该连、连对没连对"，不在于"保存密码"。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| connection.connection_id | 非空 | R18 连接口径 |
| connection.source_connector | 以 `source-` 开头（`elt.source_prefix`） | airbyte connector 命名约定 |
| connection.destination_connector | 以 `destination-` 开头（`elt.destination_prefix`） | airbyte connector 命名约定 |
| connection.distinct | 来源 ≠ 目的地 | 自己同步给自己是配置错误 |
| connection.no_credential | 顶层字段名不含凭据词 | R18 红线 1 |
| sync.sync_mode | ∈ `elt.sync_modes` = `[full_refresh, incremental_append, incremental_dedup]` | airbyte sync mode |
| sync.streams | ≥ 1 个 stream | 空同步无意义 |
| sync.cursor | 增量的每个 stream 声明 `cursor_field` | airbyte incremental cursor |
| sync.schedule | 非空 | 同步频率必填 |
| sync.no_credential | 顶层字段名不含凭据词 | R18 红线 1 |

**阈值单一真源**：`elt.source_prefix` / `elt.destination_prefix` / `elt.sync_modes`
以 `experience/thresholds.json` 的 `elt` 段为准。凭据词表见 `review.credential_words`。

## 第三层：已验证的算例

**算例 A（干净连接）**：`examples/connection.json`
```
conn-001 / source-postgres / destination-snowflake
```
命名约定成立、来源≠目的地、无凭据字段 → `ok=true`，`verdict=PASS`。

**算例 B（脏连接）**：`examples/connection_dirty.json`
```
conn-002 / postgres / destination-snowflake / password=s3cr3t
```
BLOCKER ×2：`source_connector='postgres'` 不以 `source-` 开头；
顶层含 `password` 字段（红线 1 凭据入工件）。

**算例 C（脏同步）**：`examples/sync_dirty.json`
```
sync_mode=incremental_dedup / streams=[{name:orders}]（无 cursor_field）
```
BLOCKER ×1：增量模式未声明 `cursor_field`。对照 `sync.json`（full_refresh + 两
stream 各带 cursor）→ `ok=true`。

## 第四层：实战踩坑

1. **凭据是扫描「字段名」不是「值」**。`_has_credential()` 检查的是配置里有没有
   名为 password / api_key 的**键**，不是值里有没有一串像密码的字符串。理由是：
   键名不定 → 值必然是明文；键名在，无论值是否已脱敏都违规。

2. **`source-` 前缀大小写敏感**。`Source-postgres` ≠ `source-postgres`。命名约定
   是精确字符串匹配（`startswith`），不做归一化——归一化会掩盖命名漂移。

3. **full_refresh 不需要 cursor**。README 常写"每个 stream 都要 cursor"是误读——
   只有增量模式需要。对 full_refresh 强制 cursor 会把合法配置误拦（对照
   `sync.json`，full_refresh 的两 stream 也带了 cursor，属超配不是必需）。

4. **来源 = 目的地是隐蔽错误**。`source-x → destination-x` 看着工整，其实是把
   数据源同步回自己，通常在批量复制配置时误粘贴产生，必须显式拦。

5. **不要在结论里写"我已连上 XXX 库"**。这是越权动作的措辞。正确写法：
   "产出连接工件 connection.json（source-postgres → destination-snowflake），
   凭据走密钥管理，未落工件。"这样 review 的 `credential_gate` 不会被误触发。

6. **stream 为空 ≠ 同步全量**。`streams: []` 不是"同步所有表"的简写，而是没有
   目标的空任务。口径：`streams ≥ 1`。

7. **schedule 的口径是字符串非空**。cron 表达式（`0 2 * * *`）或频率词
   （`hourly`）皆可，但空串或缺失一律 BLOCKER——没有频率的同步是"看心情同步"。
