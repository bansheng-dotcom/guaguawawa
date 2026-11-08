# s02 数据库与 API（data_api）方法论

来源沉淀：`wshobson__agents` + `KarmenLoop__fullstack-web-delivery`（Schema/契约口径）。

## 一、方法论（什么时候用、核心口径）

数据库与 API 回答「数据怎么存、接口怎么调」。两个动作：
- `schema`：Schema 设计——列类型白名单、主键必须指向已有列、索引列必须存在。
- `api`：API 契约——method 枚举、path 以 / 开头且唯一、每个端点必须声明错误码。

核心红线：**列类型自由发挥 = 迁移埋雷**；**端点不声明错误码 = 调用方无法处理失败**。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

列类型、HTTP 方法、版本全部外置：`data_api.column_types`、`data_api.http_methods`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s02_data_api.schema/api`）

**schema 校验规则**：
- tables 为空 → `data_api:tables` CRITICAL。
- 列 type 不在白名单 → `data_api:column_type` HIGH。
- 主键不是已有列 → `data_api:primary_key` HIGH。
- 索引引用不存在的列 → `data_api:index` HIGH。

**api 校验规则**：
- endpoints 为空 → `data_api:endpoints` CRITICAL。
- method 不在白名单 → `data_api:method` HIGH。
- path 非 / 开头 → `data_api:path` HIGH；重复 → `data_api:path_dup` HIGH。
- 未声明错误码 → `data_api:error_codes` HIGH。

**输出键**：schema → `table_count / column_count / verdict / next`；
api → `endpoint_count / error_codes_total / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/data_api_schema.json`（2 表 5 列）：table_count=2，column_count=5，verdict=PASS。
`examples/data_api_api.json`（2 端点）：endpoint_count=2，error_codes_total=3，verdict=PASS。
脏夹具 `data_api_schema_dirty.json`：非法列类型+悬空主键 → ok=false；
`data_api_api_dirty.json`：method 非法+path 重复 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **索引列校验容易被漏掉**：索引引用了已删除的列会让建表脚本直接报错，
  必须在确定性门禁里拦，不能等运行时。
- **错误码是契约的一部分**：只校验 method/path 会放过「调用方不知道 4xx 长啥样」的契约。
