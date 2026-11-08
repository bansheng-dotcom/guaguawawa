# 参考层 01 —— SaaS/API 集成（workflow-builder / instance-awareness）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/small-business/build-connector/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/workflow-builder` + `instance-awareness`
> 角色：R17 蛙织网 · S01 integration 的确定性口径来源。

## 第一层 · 方法论

n8n 的工作流是一个**有向图**：节点（node）通过连接（connection）串成执行管道，
每个节点要么是**触发器**（trigger，图入口），要么是**执行器**（executor，被上游
喂入数据后执行）。集成工程师的核心职责不是「画图」，而是保证这张图**可执行、
可回放、可追责**：

1. **入口唯一性**：至少一个触发器；触发器类型决定输入形状，形状错了后续全错。
2. **边完整性**：connection 引用的节点必须真实存在，否则 n8n 加载即报「悬空引用」。
3. **凭据隔离**：任何密钥/令牌都不应出现在节点 `parameters` 或 `credentials`
   的 source 里，只能用引用（`newCredential()` / `{{ $credentials.xxx }}`）。
4. **节点可命名**：每个节点 name 必须非空且唯一，审计轨迹才能定位到节点。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 触发器类型 | 以 `Trigger` 结尾或命中白名单 | n8n trigger 节点命名约定 |
| 节点必填字段 | `name` + `type` 均非空 | workflow-builder 节点结构 |
| 节点名唯一 | 同名重复即 BLOCKER | n8n 审计按 name 定位 |
| 连接引用完整 | connection 的 src/tgt 均在节点集合内 | n8n 图校验 |
| 明文密钥禁词 | `api_key/secret/token/password/bearer/private_key/access_token/client_secret` | instance-awareness |
| 节点上限 | ≤ 200（防单图失控） | R17 阈值 `max_nodes` |

## 第三层 · 已验证算例

**干净工作流**（3 节点，全部通过）：
```
Webhook(webhook) → Map Fields(set) → Create Lead(httpRequest)
connections: Webhook→Map Fields→Create Lead（无悬空）
```
门禁输出：`node_count=3, trigger_count=1, dangling_edges=0`，verdict=PASS。

**脏工作流**（引用不存在的 Ghost Node）：
```
Webhook → Map Fields，但 connection 指向 "Ghost Node"
```
门禁输出：`dangling_edges=1`，`BLOCKER: 连接引用完整（悬空 {'目标:Ghost Node'}）`，
verdict=FAIL。

## 第四层 · 实战踩坑

1. **触发器类型别用字符串前缀猜**：`scheduleTrigger` 不以 `Trigger` 结尾的判断
   会漏，必须同时匹配「以 Trigger 结尾」**和**「白名单精确命中」两路。
2. **凭据禁明文扫描要递归**：`parameters` 可能是嵌套对象，浅层 `in` 判断会漏掉
   `parameters.headers.Authorization` 里的 token。用递归 `iter_strings`。
3. **`httpRequest` 不是触发器**：它是执行器，但常被误当触发器。R17 把它放进
   白名单是为了「服务集成」场景（HTTP 轮询），但语义上是 executor，别混淆。
4. **connection 结构是 `{src: {main: [[{node, type, index}]]}}`**：src 是节点名、
   target 在 link 的 `node` 字段，解析时两层嵌套都要校验。
