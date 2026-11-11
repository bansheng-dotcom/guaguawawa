# 专业数据集 Professional Dataset — TRAE Plugin

火山引擎面向 AI Agent 场景的专业搜索基础设施。通过聚合多个垂直专业领域的数据源，为 Agent 提供结构化、高质量、高可信度的专业领域数据检索能力，有效降低 Agent 执行过程中出现幻觉、数据来源不明确等风险。

- 官网：https://console.volcengine.com/high-quality-dataset/data-application/pro-dataset

## 一、能力概览

本插件把火山引擎线上「专业数据集」检索服务（一个 HTTP Remote MCP Server）接入 TRAE。核心能力：

- **一个 MCP 工具 `dataPro_search(query)`**：以自然语言检索，服务端自动路由到对应垂直数据集并返回结构化结果。
- 覆盖领域：学术文献、企业工商、企业风险、股票金融、汽车配置、汽车销量、宏观经济，以及新闻资讯等其他综合数据。

## 二、Skill / MCP / Connector 的关系

| 组件 | 文件 | 作用 |
|-|-|-|
| Skill | `skills/pro-dataset/SKILL.md` | 告诉 Agent「何时用、怎么写 query」的路由与提问规范，提升命中率。 |
| MCP | `.mcp.json` | 声明一个 HTTP Remote MCP Server，`url` 指向线上服务，工具 `dataPro_search` 由服务端提供。 |
| Connector | `connector.json` | 声明 `manual_token` 授权方式；用户填写的 API Key 通过占位符注入到 MCP 请求头。 |

> 本插件**不包含任何后端源码或本地命令**：数据检索逻辑全部运行在火山引擎线上服务，插件包只是一个指向该服务的远程 MCP + 鉴权壳。因此无第三方运行时依赖，可支持 Universal。

## 三、认证方式与凭据消费

采用 **Manual Token** Connector（Provider 名：`pro-dataset`）：

1. 用户在 TRAE 授权弹窗中填写自己的专业数据集 API Key（形如 `hqd_sk_xxx`）。
2. 该 Key 作为 `ACCESS_TOKEN` 保存在 Connector 中。
3. `.mcp.json` 通过占位符 `${connector.pro-dataset.ACCESS_TOKEN}` 将其注入 `X-Hqd-Api-Key` 请求头，服务端据此鉴权与后付费计费。

平台侧完整授权表单（弹窗文案、字段、多语言、帮助链接）见 `examples/connector-provider-template.json`，该文件仅用于提交给 TRAE 配置，不会由 `plugin.json` 自动加载。

**安全说明**：本包内不含任何真实 API Key、token 或凭据；所有凭据由用户在运行时自行填写，运行时解析后注入请求头，不会写回插件包。

## 四、配置与验证

- MCP 地址：`https://datapro.hqd.cn-beijing.volces.com/mcp`（生产环境）
- 验证方式：安装并完成授权后，向 Agent 提出任一专业数据问题（例如「查询北京字节跳动科技有限公司的工商信息」「五粮液 股票基础信息」），Agent 应调用 `dataPro_search` 并返回结构化结果。

## 五、已知限制

- 每次调用建议只表达一个明确意图。
- 计费为后付费模式，账号无权限或额度不足时工具会返回对应错误提示。
- 详细提问规范见 `skills/pro-dataset/SKILL.md`。

## 六、外部服务与许可证

- 外部服务：火山引擎「高质量数据集-专业数据集」线上 API。
- 许可证：见 `LICENSE`。
