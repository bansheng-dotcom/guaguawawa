# R16 蛙人事 · 人员与组织运营官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/human-resources/org-planning/SKILL.md
>


把「从招聘到薪酬准备的人事运营链」做成**本地可运行、可确定性校验**的角色 Agent。
不真发 Offer / 不真解聘 / 不真发薪 / 不收集过量个人信息，而是把「该定什么口径、
什么约束、什么证据」落成白名单 + 确定性算术 + 门禁。

来源仓库：`frappe__hrms`（JobOpening / JobApplicant / JobOffer / Attendance /
LeaveApplication / Appraisal / Goal / SalaryStructure / SalaryComponent /
ExpenseClaim 的 Select 枚举与勾稽）、`frappe__erpnext`（Employee doctype 在
`setup/doctype`、HolidayList）、`frappe-ui`（前端子模块，UI 来源登记）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 招聘与入职 | `recruit` | `opening` / `applicant` / `offer` | JobOpening status∈{Open,Closed} + job_title/designation 必填 + vacancies≥1；Applicant status 6 枚举 + 邮箱正则；Offer status 6 枚举 + 必填 + **接受前置**（prior_status∈{Shortlisted,Accepted}） |
| 人员与合同档案 | `people` | `employee` / `profile` / `contract` | Employee status 4 枚举 + 四必填 + dob<doj + **PII 最小化**（禁身份证/银行卡/住址等）；紧急联系人≥1 + 附件≥1；合同 start<end + 到期窗口 30 天 |
| 考勤与休假 | `attendance` | `attendance` / `leave` | Attendance status 5 枚举 + 日期必填 + 工时∈(0,24]；LeaveApplication status 4 枚举 + from≤to + **天数恒等**（含 half_day=0.5）+ 额度≤余额 + **重叠检测** |
| 绩效与目标 | `performance` | `appraisal` / `goal` | 周期非空 + cycle_status 3 枚举 + 总分/KRA 分∈[0,5] + 打分完整；Goal status 5 枚举 + progress∈[0,100] + KRA 引用完整 + Completed 须满进度 |
| 薪酬准备 | `payroll` | `input` / `calc` | 频率 5 枚举 + 组成项类型 3 枚举 + 每项 source；**净额恒等**（gross−Σdeduction=net，容差 0.01）+ 毛额恒等 + 计薪天数勾稽 + **L4 制度性字段可溯源** |
| 费用与福利 | `expense` | `claim` / `benefit` | 报销双轨状态（approval_status 4 枚举 / status 7 枚举）+ 明细≥1 且金额>0 + **总额恒等**；福利绑周期 + 额度≤上限 |
| 组织运营报表 | `report` | `headcount` / `report` | 分组恒等（Σ分组=总数）+ 维度非空；指标字段白名单 + 非负 + **流动率实算**（离职/期初） |

共 **7 技能 / 16 动作**（16 个门禁）。

## 协作契约

- **inputs**：`org_decision` + `roles`
- **outputs**：`roster` + `payroll_input`
- 意图路由（`agent.py run --task`）：招聘/职位/候选人/录用/入职 → recruit；
  合同/档案/联系人 → people；考勤/出勤/打卡 → attendance/attendance；
  请假/休假/年假 → attendance/leave；绩效/评估/考核 → performance/appraisal；
  目标/OKR/KRA → performance/goal；薪酬/工资/核算/净额 → payroll/calc；
  报销/费用/发票 → expense/claim；福利/补贴 → expense/benefit；
  报表/花名册/人数/流动率 → report/headcount；兜底 → `report/headcount`。

## 运行

```bash
python agent.py manifest                                    # 契约 + 7 技能清单
python agent.py demo                                        # 生成示例人事工件
python agent.py recruit offer      --input examples/offer.json
python agent.py people employee    --input examples/employee.json
python agent.py attendance leave   --input examples/leave.json
python agent.py performance goal   --input examples/goal.json
python agent.py payroll calc       --input examples/payroll_calc.json
python agent.py expense claim      --input examples/claim.json
python agent.py report headcount   --input examples/headcount.json
python agent.py harness leave --input examples/leave.json   # 确定性门禁
python agent.py contract list
python agent.py case list
python verify_loop.py                                       # 32 行闭环矩阵
python run_tests.py                                         # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **劳动关系 / 税务 / 正式薪酬复核结论**归 R03 + 外部专业人士。
- **组织决策（裁/招/调薪）**归 R01；**数据分析与趋势归因**归 R06；
  **隐私/合规约束**归 R03。
- 本角色只产出**人事工件**（职位、候选人、录用、档案、合同、考勤、请假、绩效、
  目标、薪酬输入、薪酬核算草稿、报销凭证、福利申领、花名册、运营指标），
  不产出法律结论、不做税务判断、不做组织决策。
- **红线（不可越）**：
  1. **不擅自招聘 / 解聘 / 发薪**：任何录用、解雇、发薪、打款动作一律产出
     **请求工件 + handoff 声明**，由人工授权后执行。
  2. **不收集过量个人信息**：身份证号/银行卡号/家庭住址/体检报告/宗教民族等
     超必要字段不得出现，PII 最小化是硬红线。
  3. **不做劳动关系 / 税务 / 薪酬复核结论**：劳动仲裁、竞业协议效力、个税申报、
     社保合规结论一律移交 R03 + 外部专业人士。

## Honest capability status and safe local execution

`manifest` marks local PII/payroll validation `real` and payroll disbursement `blocked`. `python agent.py local --input <record.json>` redacts email/phone and validates sourced, nonnegative gross input; it never pays wages. Unavailable external payroll remains blocked.


- 干净数据 → `ok=true` / exit 0；脏数据（枚举越界 / 恒等式不闭合 / 前置状态非法 /
  天数不恒等 / 区间重叠 / 额度超额 / **凭空制度字段**）→ `ok=false` / exit 1。
- 对抗评审五检查：`contract` / `unauthorized_hr_action` / `pii_overreach` /
  `scope_boundary` / `concrete_artifact`；失败按类别 route 回 writer
  （越权招聘发薪 / 过度 PII / 越界税务法律）或 controller（无工件 / 无价值），
  类别为 `unauthorized_hr_action` / `pii_overreach` / `scope_overlap` /
  `artifact_not_concrete` / `no_report_value`。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `hiring-pipeline` 补充录用前置集合、`payroll-preparation` 补充制度字段词表）。
- Windows GBK 控制台：所有输出经 UTF-8 重配置，verify_loop 使用 `[OK]` / `[XX]` ASCII 标记。

## L4 制度性幻觉防护（本角色的新经验）

薪酬技能是本角色风险最高处：LLM 很容易"顺手"写上"按 3% 税率""免税额度 5000"
这类**看起来完全合理**的制度性字段。本角色对此的核心设计：

1. **字段必须可溯源**：任何制度性字段（lance/免税额度/税率/社保基数…）必须带
   `source`，无来源 = 凭空 = BLOCKER。
2. **数量必须恒等**：`net_pay = gross_pay − ΣDeduction`，容差 0.01。
3. **宁可拦错，不可放过**：制度性幻觉的危害远大于一次误报——误报只是多一步人工复核，
   幻觉是**编造制度**并可能流入真实薪酬。
