# OpenAPI 3.1、RFC 7807 与契约测试：让接口先可校验再可联调

> 适用角色：R09 工程官；对应工程链第 2 段 `api` 与第 4 段 `testing` 的契约部分。

## 1. 来源

- OpenAPI Specification 3.1.0（2021-02-15）：正式对齐 JSON Schema 2020-12，
  允许在 Schema 中使用 `type: ["string", "null"]` 等写法。
- RFC 7807 *Problem Details for HTTP APIs*（2016）：定义
  `application/problem+json` 与 `type/title/status/detail/instance` 字段。
- RFC 9457（2023）：替代 RFC 7807，语义基本一致，新增 `code` 等扩展建议。
- JSON Schema 2020-12：OpenAPI 3.1 的 Schema 方言基础。
- Pact 官方文档：消费者驱动契约测试（consumer-driven contract testing）的
  交互记录与验证流程。

## 2. 适用边界

适合：

- HTTP + JSON 的服务间契约，尤其是前后端分离、跨团队、跨版本并行开发；
- 需要生成客户端、Mock、文档或网关校验的场景；
- 需要把「错误码」当作对外承诺管理的服务。

不适合：

- 二进制流、WebSocket 私有帧、gRPC（应使用 protobuf/IDL）；
- 纯内部函数调用（用类型标注与单元测试即可）；
- 一次性脚本或没有外部消费者的内部工具。

## 3. 方法：四步

1. **数据模型先行**：先写实体字段、类型、必填性，再写端点。Schema 是单一事实源，
   OpenAPI 只引用它，不再复制一份字段列表。
2. **OpenAPI 3.1 片段**：每个操作必须有成功响应与至少一个 4xx 响应；
   `POST` 返回 201，`DELETE` 返回 204，其余 200。请求体只引用 Schema。
3. **RFC 7807 错误响应**：所有 4xx/5xx 的 `content` 使用
   `application/problem+json`，Schema 引用统一的 `Problem` 对象；错误码列表
   必须唯一、状态码在 400–599。
4. **契约测试**：每个端点至少一条契约测试，校验状态码、Content-Type 与必填字段；
   消费者侧记录交互，提供者侧在 CI 中回放。契约变更必须先改 Schema 再改实现。

## 4. 仓内落点

`eng_chain/api.py` 生成 `schemas`、`openapi`、`error_codes`、`migration` 四块：

| 门禁 | 检查内容 | 失败级别 |
|---|---|---|
| `api:schemas` | 实体已转成带 type 的 JSON Schema | CRITICAL |
| `api:openapi31` | `openapi` 以 3.1 开头，≥3 个操作且都有 responses | CRITICAL |
| `api:rfc7807` | 4xx/5xx 均为 problem+json，错误码唯一且状态合法 | CRITICAL |
| `api:contract_refs` | 请求/响应引用不悬空 | CRITICAL |
| `api:migration_reversible` | 迁移默认可回滚；不可逆须审批 + 备份计划 | CRITICAL |
| `testing:contract` | 每个端点至少一条契约测试 | CRITICAL |
| `testing:acceptance_mapping` | E2E 覆盖场景与验收 ID 一一对应 | CRITICAL |

跨段一致性由 `runner.py` 再查一次：`api.error_codes` 必须等于
`security.handled_error_codes`，避免「接口有码、安全清单不认」。

## 5. 误用反例

| 反例 | 后果 | 拦截门禁 |
|---|---|---|
| 所有错误都返回 200 + `{code, msg}` 包装 | 网关/监控无法按状态码告警 | `api:rfc7807` |
| 错误码只写在文档里，实现随手返回字符串 | 客户端无法分支处理 | `api:rfc7807` |
| OpenAPI 里再抄一份字段，和 Schema 漂移 | 生成客户端与实现不一致 | `api:contract_refs` |
| 204 响应仍返回 problem+json body | HTTP 语义错误，部分客户端解析失败 | `api:openapi31` |
| 不可逆迁移「先上线再说」 | 出问题无法回滚，只能停服修数据 | `api:migration_reversible` |
| 契约测试只测 200，不测 4xx | 错误路径回归无人发现 | `testing:contract` |
| 安全清单漏掉 `forbidden` | 越权错误被当成未知异常 | `security:error_codes` |

## 6. 检查清单

- [ ] 实体字段的必填性与数据库 NOT NULL 一致；
- [ ] 每个 4xx/5xx 状态码都有对应的 problem+json 描述；
- [ ] 错误码命名稳定（小写下划线），不随实现细节改名；
- [ ] 迁移步骤 ≥2，回滚步骤 ≥2，且回滚演练过；
- [ ] 每个端点有契约测试，主路径与失败态都覆盖；
- [ ] 版本号与 `release.publish.version` 一致；
- [ ] 契约变更进入 PR 审查清单，而不是口头同步。
