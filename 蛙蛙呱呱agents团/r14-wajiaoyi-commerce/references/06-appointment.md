# 06 · 服务预约与日历冲突口径（appointment）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/schedule-meeting/SKILL.md
>


> 技能：`appointment` ｜ 动作：`appointment`（预约记录）、`calendar`（预约日历）
> 来源：alextselegidis__easyappointments（预约状态、customer/provider/service 三元组）

## 第一层：方法论

预约是**时间资源的独占性承诺**。与商品不同，时段不能被"超卖后补货"——
09:00-10:00 这个时段给了客户 A，就不能同时给客户 B。
因此预约层的核心判据是**重叠检测**，而重叠检测的精度取决于边界规则的定义。

三条方法论：

1. **五元组完整性**：一次合法预约必须能回答"谁（customer）在什么时候（start/end）
   由谁（provider）提供什么服务（service）"。缺任何一项，预约就无法被履行，
   也无法被排期——所以五项必填是 BLOCKER 而非建议。

2. **时长有上限**。`max_duration_min = 240`（4 小时）。超长时段通常是输入错误
   （把日期写成了时间、把结束时间写成了次日），或需要走人工排期而非自助预约。

3. **重叠需要缓冲**。两个预约首尾相接（10:00 结束、10:00 开始）在数学上不重叠，
   在现实中冲突——服务者需要切换、清理、通勤。本仓库口径：
   `overlap_buffer_min = 5`，即 `[start - 5min, end + 5min)` 视为占用区间。

**状态语义**：`booked` 是已确认占位；`pending` 待确认（**是否占位取决于策略**，
本仓库口径下未占位）；`approved` 已批准；`rejected` 被拒；`canceled` 已取消；
`no_show` 未到场。只有 `booked` 参与日历冲突检测（`bookable_status = booked`）。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 五元组 | 五个 ID/时间字段非空 | thresholds.appointment.appointment_required |
| 状态 | 转小写后 ∈ statuses | thresholds.appointment.statuses |
| 起止可解析 | `start_datetime` / `end_datetime` 可解析为时间 | 时间公理 |
| 时序 | 时长 `> 0` 分钟 | 时间公理 |
| 时长上限 | `0 < 时长 ≤ 240` 分钟 | thresholds.appointment.max_duration_min |
| 重叠检测 | 排序后相邻对：`b_start < a_end + 5min` 即冲突 | thresholds.appointment.overlap_buffer_min |

**状态归一化**：校验前状态一律 `.lower()`，所以 `Booked` / `BOOKED` / `booked` 等价；
输出字段 `status` 也是归一化后的小写值。

**重叠判定的实际口径**（`s06_appointment._validate_calendar`，代码为准）：
按 `start` 排序后**相邻两条**逐对比较，判据为
```
b_start < a_end + overlap_buffer_min   →  重叠
```
即要求相邻事件间隔 **≥ 5 分钟**。等价地说：`b_start - a_end ≥ 5min` 才算不冲突。
**注意这是单边缓冲**（只在 `a_end` 上加缓冲），不是对称的双边缓冲——
所以"10:00 结束、10:05 开始"恰好通过（差正好 5 分钟不满足 `< 5`），
"10:00 结束、10:04 开始"则判冲突。

排序后只比较相邻对，是因为对无重叠的合法序列而言相邻比较即可发现全部冲突
（区间按 start 有序时，非相邻重叠必然蕴含相邻重叠）。

**范围限制**：本实现不按 provider 分组，假定输入已是**同一服务者**的日历。
若输入混合了多个服务者的预约，并行预约（完全正常）会被误报为冲突。
接入多服务者数据时，须先按 provider 分组再逐组送入本技能。

## 第三层：已验证的算例

**算例 A（干净预约）**：`examples/appointment.json`
```
customer_id=5, provider_id=2, service_id=6
start=2026-11-10 09:00, end=2026-11-10 10:00  (60 min)
status=Booked
```
五元组齐备、时长 60 ≤ 240、时序正确、状态合法 → `ok=true`。
注意样例里状态写作 `Booked`（首字母大写），校验层做**大小写归一化**，
输出的 `status` 字段是 `booked`（小写）。

**算例 B（脏数据）**：`examples/appointment_dirty.json`
```
customer_id="" / start=10:00 / end=09:00 / status="bogus"
```
实际 4 条失败判据：`预约五要素齐备（缺 ['customer_id']）`、`预约状态='bogus' 在白名单`、
`起止时间顺序正确（时长 -60 分钟）`、`时长 -60 分钟 ≤ 240`。
（`开始时间可解析` / `结束时间可解析` 通过——时间字符串本身格式正确，只是顺序颠倒。）

**算例 C（干净日历）**：`examples/calendar.json`
```
#1 09:00–10:00   #2 11:00–12:00   #3 14:00–15:00
```
相邻间隔分别为 60min 与 120min，均 ≥ 5min → 无重叠 → `ok=true`，
`appointment_count=3`，`overlap_count=0`。

**算例 D（脏日历 —— 重叠）**：`examples/calendar_dirty.json`
```
#1 09:00–10:00   #2 09:30–10:30
```
`b_start（09:30） < a_end（10:00） + 5min = 10:05` → 判冲突 →
`日历事件无重叠（重叠 [2]）`、`overlap_count=1` → FAIL：**双重预订**。
冲突明细报出冲突事件的 `id`（此处为 `2`，即排序后靠后的那条）。

## 第四层：实战踩坑

1. **首尾相接的争议**：业务方常说"10 点结束马上接下一个怎么不行"。
   在本仓库口径下**不行**——需要 5 分钟缓冲。若业务确实允许零缓冲（如线上会议），
   应通过案例级 thresholds 覆盖为 0，而**不是**在校验代码里写特例。

2. **时区缺失**：`2026-11-10 09:00` 没有时区。跨时区服务者场景下，
   同一字符串代表不同时刻。接入真实数据时必须带时区或明确约定为本地时区。
   本仓库样例统一按本地时区解释，并在结论中提示这一约定。

3. **pending 是否占位**：不同产品策略不同。本仓库口径 `pending` **不占位**
   （只有 `booked` 参与冲突检测）。若业务要求 pending 占位，改 `bookable_status`
   会被误解为"只允许 booked"——正确做法是在案例 thresholds 里扩展
   `blocking_statuses`。这是"阈值外置"的价值所在。

4. **字符串时间比较陷阱**：`"2026-11-10 9:00"`（单位数小时）与 `"2026-11-10 09:00"`
   字符串比较会得出错误顺序。必须**解析为时间对象**再比较，禁止字符串直接比大小。

5. **同一天多服务者的日历必须按 provider 分组**：把全公司的预约放在一个池子里做重叠检测，
   会把不同服务者的并行预约（完全正常）判为冲突。口径：冲突检测必须在
   **同一 provider 内**进行。若输入未提供 provider 分组信息，需显式说明检测范围。

6. **no_show 与 canceled 不回收时段**：`no_show`（未到场）的时段在历史数据里仍被占用，
   但**未来排期**不应受其约束。口径：历史态不参与未来冲突检测。

7. **不要把预约做成排班系统**：本技能只判"某次预约是否合法/是否冲突"，
   不做"如何排最优班次"（那属 R17 自动化/R15 资源调度）。越界即 `scope_overlap`。
