# 02 · 告警与升级口径（alert）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/customer-support/skills/customer-escalation/SKILL.md
>


> 技能：`alert` ｜ 动作：`alert`（告警规则）、`escalation`（值班升级清单）
> 来源：louislam__uptime-kuma（通知渠道、阈值告警、值班升级、确认机制）

## 第一层：方法论

告警层定义**告警什么、通知谁、多久升级**。把这段做成确定性校验的价值，不在于
"通知得更响"，而在于**让发不出去的告警和跳级的升级链进不了值班**——一条
severity=`fatal` 的告警，通知系统根本处理不了；一条 3→1 的升级链，会让值班
乱成一锅粥。

三条方法论：

1. **告警策略是「约定」，不是「触达」**。本角色只校验告警策略与升级清单结构
   是否成立，不实际发送通知、不实际呼叫值班（那是运行期动作）。
2. **白名单是触达的保证**。severity 只许 critical/warning/info，channel 只许
   email/webhook/slack/sms/telegram。越界的 severity/channel 意味着这条告警
   通知系统无法正确处理，宁可拒绝重写也不放行。
3. **升级只许从低到高逐级**。level 严格单调递增（无重复、无回退）。跳级到
   CEO = 沟通事故——先让能处理的人处理，逐级确认后再升级。

**本角色只校验策略结构，不实际触达**。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| alert.rules | ≥ 1 条 | 告警规则集 |
| 每条 rule | 含 metric/condition/threshold/channel 四字段 | 阈值告警结构 |
| rule.severity | ∈ `alert.severities`（critical/warning/info） | 严重度枚举 |
| rule.channel | ∈ `alert.channels`（email/webhook/slack/sms/telegram） | 通知渠道枚举 |
| escalation.chain | ≥ 1 级 | 值班升级链 |
| 每级 chain | 含 level/role/channel/acknowledged | 升级结构 |
| chain.level | 严格单调递增（无重复、无回退） | 升级顺序 |
| chain.acknowledged | 显式 true/false | 确认机制 |

**阈值单一真源**：`alert.severities` / `alert.channels` 以
`experience/thresholds.json` 的 `alert` 段为准。

## 第三层：已验证的算例

**算例 A（干净告警）**：`examples/alert.json`
```
rules=[{metric=http_response_ms, condition=>, threshold=1000,
        channel=email, severity=critical}]
```
四字段齐、severity/channel 在白名单 → `ok=true`，`verdict=PASS`。

**算例 B（脏告警）**：`examples/alert_dirty.json`
```
severity=fatal（其余正常）
```
BLOCKER ×1：`alert.severity` 越界拦。fatal 不在三档枚举里。

**算例 C（升级链）**：`examples/escalation.json` vs `escalation_dirty.json`
```
chain=[{level=1,oncall},{level=2,sre-lead}]        → level 1→2 单调，PASS
chain=[{level=2,sre-lead},{level=1,oncall}]        → level 2→1 回退，FAIL
```
升级链 level 必须严格单调递增。`escalation_count` 字段同时回写（2 级）。

## 第四层：实战踩坑

1. **level 判据用"严格单调递增"不是"非递减"**。`len(set(levels)) == len(levels)`
   同时要求无重复。两个同 level 的值班（比如两个 oncall 并列 level=1）在 R20
   口径里是策略错误——同一级多人的场景应合并到一个 level 的 role 描述里，而非
   塞两个同 level 记录。

2. **`acknowledged` 必须显式 true/false**。很多上游序列化时把布尔值丢了或写成
   字符串 "true"。判据用 `r.get("acknowledged") not in (True, False)` 拦——只认
   真布尔。这是 R07 踩坑（JSON 序列化丢类型）在 R20 的复现点。

3. **channel 是双重白名单**。alert 的 rule.channel 和 escalation 的 chain.channel
   共用同一份 `alert.channels`，但判据写在不同动作里。改渠道清单只改
   thresholds 一处，两处判据同时生效。

4. **condition 只查非空，不查取值**。`>`/`<`/`>=`/`<=`/`==` 都合法，R20 不
   替告警引擎做语义校验（那个属于告警引擎运行时）。只保证"有比较符"。

5. **threshold 判据用 `is None` 而不是 falsy**。`threshold=0` 是合法阈值
   （比如"响应时间为 0"），不能当作缺失。判据写 `r.get("threshold") is None`，
   避开 0 的坑。
