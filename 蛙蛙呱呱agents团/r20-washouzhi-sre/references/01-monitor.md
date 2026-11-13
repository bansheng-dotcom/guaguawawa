# 01 · 可用性监控口径（monitor）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/skills/status-report/SKILL.md
>


> 技能：`monitor` ｜ 动作：`monitor`（监控项结构）、`uptime`（可用性记录）
> 来源：louislam__uptime-kuma（监控类型 http/tcp/ping/dns/port、心跳间隔、重试、请求方法）

## 第一层：方法论

监控层定义**监控什么、多久查一次、怎么判不可用**。把这段做成确定性校验的价值，
不在于"查得更快"，而在于**让结构不成立的监控项进不了调度**——一个 target 为空
的监控项，会让调度器白跑一辈子；一个 interval=1 秒的监控项，会打爆被监控方。

三条方法论：

1. **监控项是「探测定义」，不是「探测结果」**。本角色只校验监控项结构能否被
   调度器稳定探测，不代 Uptime Kuma 实际发起探测、不判"现在通不通"。运行期
   事实由状态页（s03）承载。
2. **类型决定必需字段**。http/https 必须有合法 method（GET/HEAD/POST）；
   tcp/port 必须有合法端口（1-65535）；ping/dns 只需 target。类型与字段
   错配 = 探测定义不成立。
3. **间隔是「可探测性」约束**。interval 太短（<30s）会打爆目标，太长
   （>86400s）等于没监控。这是对目标方的基本尊重，不是性能调优。

**本角色只校验结构，不实际探测**。实际探测与"现在通不通"是运行期事实。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| monitor_id | 非空字符串 | 监控项唯一标识 |
| type | ∈ `monitor.monitor_types`（http/tcp/ping/dns/port） | uptime-kuma 类型枚举 |
| target | 非空（URL/主机/端口） | 探测目标 |
| interval | ∈ `[monitor.interval_min, monitor.interval_max]`（默认 30~86400 秒） | 心跳间隔 |
| retries | ≥ 0 | 失败重试次数 |
| method（http/https） | ∈ `monitor.methods`（GET/HEAD/POST） | HTTP 请求方法 |
| port（tcp/port） | ∈ [1, 65535] | TCP 端口 |

**阈值单一真源**：`monitor.monitor_types` / `monitor.methods` /
`monitor.interval_min` / `monitor.interval_max` 以 `experience/thresholds.json`
的 `monitor` 段为准。

## 第三层：已验证的算例

**算例 A（干净监控项）**：`examples/monitor.json`
```
mon-http-api / type=http / target=https://api.example.com/health /
interval=60 / retries=3 / method=GET
```
http 类型带合法 method、interval 在区间内 → `ok=true`，`verdict=PASS`。

**算例 B（脏监控项）**：`examples/monitor_dirty.json`
```
monitor_id="" / type=http / 其余正常
```
BLOCKER ×1：`monitor.id` 空 ID 拦。ID 是调度器定位监控项的唯一依据。

**算例 C（可用率）**：`examples/uptime.json` vs `examples/uptime_dirty.json`
```
checks_total=1000 / up_count=999 / uptime_ratio=0.999   → 实算 0.999，PASS
checks_total=1000 / up_count=1200 / uptime_ratio=0.999  → up>total，FAIL
```
可用率必须由 up/total **实算**，声明值与实算值容差 0.001 内才算一致。
`up_count > checks_total` 直接拦——成功次数不可能超过探测次数。

## 第四层：实战踩坑

1. **`_num()` 对缺失字段返回 0.0，会误伤 interval=0**。interval 未填时
   `c._num(None)=0`，落入 `[30,86400]` 之外，恰好被 interval 判据拦住——
   这是"缺字段"借"区间"判据显形的典型。但 retries 未填也归 0，而 0 ≥ 0
   恰好合法（重试 0 次合理），所以 retries 缺字段不拦。这是**有意为之**：
   重试可选，间隔必填。

2. **method 白名单别乱扩**。uptime-kuma 实际支持 HEAD，但监控语义里 HEAD
   常用于"只测连通不拉 body"。若扩成 PUT/DELETE，等于让监控项能改生产数据，
   违背"探测定义"立场。白名单只增不减。

3. **port 判据只在 tcp/port 类型触发**。http 类型带个 port 字段不应触发端口
   校验（http 的端口在 URL 里）。同理 method 只在 http/https 触发。类型驱动的
   条件判据要写在 `if mtype in (...)` 里，否则会误报。

4. **uptime 的 ratio 用 `safe_div` 实算**，分母为 0 返回 0.0。checks_total=0
   时 ratio=0，但此时 total 判据已 BLOCKER，ratio 判据不额外添乱——两判据
   各自独立，不互相依赖。

5. **uptime_ratio 声明缺失不拦**。只有"声明了却和实算不一致"才拦。这是为了
   兼容"上游只给 up/total 不给 ratio"的协作场景——ratio 由 R20 补算，不因
   上游少给一个字段就拒收。
