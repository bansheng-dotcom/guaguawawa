# 参考层 02 —— Webhook 与事件处理（trigger-input-data-shapes）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/partner-built/zoom-plugin/skills/webhooks/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/trigger-input-data-shapes`
> 角色：R17 蛙织网 · S02 webhook 的确定性口径来源。

## 第一层 · 方法论

Webhook 触发器接收外部系统推来的 HTTP 事件，n8n 把不同触发器的输入**包成不同
形状**。集成工程师最常犯的错误是「假设所有触发器都给你同一个 body」，然后
字段映射全错位。n8n 的规则：

- **webhook 触发器** → 输入是 `body` 信封（`body` / `headers` / `query` / `params`）。
- **form 触发器** → 输入是**扁平**的键值对（无嵌套信封）。
- **chat 触发器** → 输入是 `chatInput` 字段（单条聊天消息）。
- **schedule / manual 触发器** → 无外部输入（`none`），数据只能靠上游节点或静态
  变量。

事件处理的三件套：**校验**（字段是否合法）、**路由**（按事件类型分发到对应
handler）、**重放**（失败后重投，必须幂等）。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| path | 长度 ≥ 3、不以 `/` 开头 | n8n webhook path 约定 |
| method | GET/POST/PUT/PATCH/DELETE | HTTP 动词白名单 |
| inputData 形状 | 按触发器类型匹配 body/flat/chatInput/none | trigger-input-data-shapes |
| 路由兜底 | handler 有匹配规则或 default 兜底 | intent-recognition |
| 事件类型 | created/updated/deleted/submitted/approved/... 白名单 | R17 阈值 |
| 事件时序 | ts 单调非递减（同秒合法） | 批处理排序语义 |
| 重放幂等 | replay 必须声明 idempotency_key/去重 | n8n retry/idempotency |

## 第三层 · 已验证算例

**干净 webhook**：
```
path=acme-contact-form, method=POST, trigger_type=webhook, input_shape=body
handlers=[{match: type=lead}, {default: true}]
```
门禁：path 合规 + method 白名单 + 形状匹配 body + 有默认兜底 → PASS。

**脏 webhook**：
```
path=x（长度 <3）, method=TRACE（越界）, handlers=[]（无兜底）
```
门禁：`method=TRACE 不在白名单` + `handlers 必须非空` → FAIL。

## 第四层 · 实战踩坑

1. **input_shape 别靠猜**：`formTrigger` 的输入是扁平 map，若代码按 `body.x`
   取字段会拿到 `None`。必须按触发器类型显式声明形状。
2. **`none` 形状的兼容**：schedule/manual 无输入，但为了兼容旧流程，允许
   `shape ∈ {none, body}` 都通过（有的集成把 schedule 当 body 空对象处理）。
3. **事件时序是「非递减」不是「严格递增」**：批量重放同秒事件很常见，若用
   `cur <= prev` 判倒退会误报。用 `cur < prev` 才报倒退。
4. **路由完整性要算差集**：`事件类型集合 - 路由覆盖集合` 非空且无 dead_letter
   才拦截；有 dead_letter 兜底就不拦（dead-letter 本身就是合法路由）。
