# 03 · 考勤与休假口径（attendance）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/policy-lookup/SKILL.md
>


> 技能：`attendance` ｜ 动作：`attendance`（出勤记录）、`leave`（请假申请）
> 来源：frappe__hrms（Attendance / LeaveApplication / LeaveType 的 Select 枚举）

## 第一层：方法论

考勤与休假是**薪酬计算的输入地基**。请假天数算错 → 薪酬扣款错（下游 s05）；
请假区间重叠 → 额度被重复消耗。这两类错误在源头拦下，比在薪酬层补救便宜一个数量级。

三条方法论：

1. **状态枚举即出勤事实**。Attendance.status 是一台严格状态机，任何不在枚举内的
   状态都意味着"我们不知道这个人今天算不算出勤"——未知即危险，一律 BLOCKER。
2. **天数恒等是薪酬的地基**。`total_leave_days` 声明值必须与实算值（含半日 0.5）
   完全一致。差一天，薪酬扣款就错一天。
3. **重叠检测防额度重复消耗**。同一员工的请假区间不得重叠，否则额度会被算两次。

**本角色绝对不做的事**：不擅自审批请假、不做薪酬扣款计算、不做劳动法判定。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| attendance.status | ∈ `{Present, Absent, On Leave, Half Day, Work From Home}` | hrms Attendance.status |
| attendance.required | `employee`、`attendance_date` | hrms Attendance 必填 |
| attendance.working_hours | `0 < hours ≤ 24`（若提供） | 工作时长合理区间 |
| leave.status | ∈ `{Open, Approved, Rejected, Cancelled}` | hrms LeaveApplication.status |
| leave.required | `employee`、`leave_type`、`from_date`、`to_date` | hrms LeaveApplication 必填 |
| leave 时序 | `from_date ≤ to_date` | 起始不晚于结束 |
| leave 天数恒等 | `total_leave_days == (to − from).days + 1`；`half_day` → 0.5 | thresholds.leave.half_day_value |
| leave 额度 | `total_leave_days ≤ balance_days`（若提供） | 不超余额 |
| leave 重叠 | 与 other_leaves 的区间不得重叠 | 防额度重复消耗 |

**出勤状态速查**：
- `Present`：正常出勤。
- `Absent`：缺勤（可能扣薪，交 s05）。
- `On Leave`：休假（对应一条已批准的请假）。
- `Half Day`：半日出勤。
- `Work From Home`：居家办公（算出勤，但不算出勤地）。

## 第三层：已验证的算例

**算例 A（干净请假）**：`examples/leave.json`
```
EMP-0001 / Annual Leave / 2026-11-20 → 2026-11-22 / total=3 / balance=10 / Approved
other_leaves: LA-0007 2026-12-01 → 2026-12-03（不重叠）
```
实算天数 = (22−20)+1 = 3 = 声明值；3 ≤ 10；不重叠 → `ok=true`。

**算例 B（脏请假）**：`examples/leave_dirty.json`
```
EMP-0001 / Annual Leave / 2026-11-20 → 2026-11-22 / total=1 / balance=2 / Approved
other_leaves: LA-0007 2026-11-21 → 2026-11-25（重叠！）
```
BLOCKER ×3：天数恒等失败（声明 1 ≠ 实算 3）、超余额（3 > 2）、区间重叠。

**算例 C（脏出勤）**：`examples/attendance_dirty.json`
```
空 employee / not-a-date / Bogus / hours=30
```
BLOCKER ×4：employee 为空、日期不可解析、状态越界、工作时长 30 > 24。

## 第四层：实战踩坑

1. **半日请假的天数**。`half_day=true` 时天数固定为 0.5，不是 (to−from)+1。
   一个员工同一天请上午、另一个请下午，各自算 0.5，合计不超过 1。

2. **重叠检测的边界**。`to == other.from` 算重叠（同一员工不可能同时在两条请假里）。
   口径：`not (other.to < from or other.from > to)` 即重叠。

3. **On Leave 而无对应请假申请**。出勤记录标 `On Leave` 但请假表里查不到，属异常，
   应在考勤层提示（本技能只校验出勤记录本身，跨表勾稽交上层）。

4. **working_hours=0 的出勤**。`Present` 却 0 小时，可疑；本口径要求 `> 0`。
   但 `Absent` 可无 working_hours（不提供则跳过）。

5. **额度用的"可用余额"口径**。`balance_days` 是请假日当天的可用余额，不是年度总额。
   调用方须传入正确口径，本技能只做 `days ≤ balance` 的确定性判定。

6. **不要在结论里写"这个员工的请假我批了"**。审批是管理动作，R16 只校验。
   正确写法："请假工件 leave.json 天数恒等 3 天，额度 3 ≤ 10，无重叠，状态 Approved，
   可进入薪酬勾稽。"

7. **跨月请假的日历效应**。11-28 → 12-02 是 5 个自然日，但可能横跨两个薪酬周期。
   本技能只算自然日恒等；跨周期分摊交 s05 薪酬准备。
