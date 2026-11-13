# HR_SPEC.md - R16 蛙人事 · 人力资源与组织运营统一规格账本 (SSOT)

> **版本**：v13.0  
> **单一信任源 (Single Source of Truth)**：本账本定义招聘寻源、候选人流转、员工主数据档案、考勤工时与休假守恒、绩效评估、薪酬预计算与个税五险一金扣减、费用报销与组织运营报表的全局业务标准、确定性计算口径与 8 维硬门禁。
> **对标标杆**：`dbt Semantic Layer` / `Frappe HRMS DocType` / `Workday HCM Spec` (Stars > 15k)

---

## 一、 北极星指标与核心准则 (North Star & KPI)

| 指标代号 | 指标名称 | 目标基准线 | 统计口径说明 |
| :--- | :--- | :--- | :--- |
| **PRA** | 薪酬记录准度 (Payroll Record Accuracy) | **>= 100.0%** | 实发净额必须与应发总额扣除社保、公积金、个税及其它扣款完全恒等，净额容差绝对值 = 0.00 |
| **OTA** | 录用接受前置率 (Offer-to-Acceptance Rate) | **= 100.0%** | 发放 Offer 的候选人必须前置通过筛选与面试流程，状态必须来源于 Shortlisted 或 Accepted |
| **PMR** | 敏感个人信息泄露率 (PII Minimization Rate) | **= 0.00%** | 物理级拦截明文居民身份证号、银行卡账号、详细家庭住址等超范围高敏数据收录 |
| **LBR** | 休假天数与余额恒等率 (Leave Balance Recalculation) | **= 100.0%** | 申请休假天数必须与周期严格匹配，不得大于可用额度，且同一员工假期区间恒不重叠 |
| **TOR** | 流动率实算率 (Turnover Rate Grounding) | **= 100.0%** | 组织月度/年度离职率基于实际在册人数与离职人数精准精算，严禁任何主观臆测与拍脑袋 |

---

## 二、 人力资源计算规范与核心模型 (HR Calculation Models)

1. **薪酬实发净额守恒公式 (Payroll Net Pay Conservation)**：
   $$\text{Net Pay} = \text{Gross Pay} - \sum \text{Statutory Deductions} - \text{IIT Tax} - \sum \text{Other Deductions}$$
   - 容差绝对值为 0.00，不允许任何不可解释的分位漂移。
2. **休假扣减与可用余额守恒模型 (Leave Balance Conservation)**：
   $$\text{Remaining Balance} = \text{Initial Balance} - \text{Requested Leave Days}$$
   - 约束：$\text{Requested Leave Days} \le \text{Initial Balance}$ 且同一员工假期区间严禁重叠。
3. **费用报销总额与明细勾稽公式 (Expense Claim Integrity)**：
   $$\text{Total Claimed Amount} = \sum_{i=1}^{n} \text{Item Amount}_i \quad (n \ge 1, \text{Item Amount}_i > 0)$$
   - 报销总额必须严格等于明细金额代数和，且明细条目数至少为 1，单项金额必须大于 0。
4. **组织人员离职流动率模型 (Turnover Rate Model)**：
   $$\text{TOR} = \frac{\text{Leavers Count}}{\frac{\text{Headcount}_{\text{start}} + \text{Headcount}_{\text{end}}}{2}} \times 100\%$$
   - 严禁空泛汇报“人员相对稳定”，必须依此公式输出量化数据。
5. **招聘漏斗前置转换模型 (Hiring Pipeline Funnel)**：
   $$\text{Applicants} \ge \text{Screened} \ge \text{Interviewed} \ge \text{Offered} \ge \text{Accepted}$$
   - 各阶段候选人数量必须单调非增，严禁跳过前置面试直接进入发 Offer 状态。

---

## 三、 人事八维硬门禁矩阵 (The 8-Dimension HR Gate Matrix)

所有 R16 人力资源业务工件必须通过以下 8 维硬门禁刚性审查：

| 门禁 ID | 门禁名称 | 刚性校验标准 (Threshold) | 破坏后果与处置策略 |
| :--- | :--- | :--- | :--- |
| **GATE-01** | 净额恒等门禁 (Net Balance Gate) | **gross - Σdeduction = net (容差 0.00)** | 净额不恒等直接判定 CRITICAL，禁止生成待发薪清单 |
| **GATE-02** | PII 最小化刚性拦截 (PII Minimization Gate) | **身份证号/银行卡号/私密住址泄露数 = 0** | 检出敏感未脱敏 PII 直接阻断工件流转并触发合规告警 |
| **GATE-03** | 录用前置门禁 (Offer Pre-requisite Gate) | **Offer 状态必须来自 Shortlisted/Accepted** | 跳过初筛/面试直接发放 Offer 判为违规，强制驳回补齐流转记录 |
| **GATE-04** | 休假天数与余额守恒 (Leave Balance Gate) | **申请天数 ≤ 可用余额 且 天数 > 0** | 超额休假或负数休假直接拦截，判定审批前置无效 |
| **GATE-05** | 休假重叠检测 (Leave Overlap Gate) | **同一员工请假日期区间重叠数 = 0** | 同一员工历史重叠假期直接拦截，防止重复请假套取工时 |
| **GATE-06** | 薪酬制度溯源 (Statutory Policy Trace Gate) | **社保公积金免税额必须附带 source 制度溯源行** | 缺失合规政策引用行 (如 local_policy/statutory_source) 直接驳回 |
| **GATE-07** | 报销总额与明细恒等 (Expense Consistency Gate) | **总额 = Σ明细 且 明细行数 ≥ 1 且 明细金额 > 0** | 报销单明细缺失、单项为负或总和不符判定作弊驳回 |
| **GATE-08** | 人事红线授权与移交 (HR Redline & Handoff Gate) | **发薪/解聘/税务等关键动作必须具备明确 handoff** | 严禁 Agent 越权打款或单方解聘，无授权声明直接阻断 |

---

## 四、 角色红线与合规边界 (Non-Negotiable Boundaries)

1. **严禁擅自代发薪资与发起银行划扣**：R16 仅负责薪酬核算、工时盘点与凭据生成，资金调拨与实际代扣发必须移交 R03 财务执行；
2. **严禁擅自下达员工解聘或辞退决定**：解聘解除劳动合同属于重大法律行为，必须完成合规调查并附带 HRBP/法务主管的双签 Hand-off；
3. **严禁非脱敏采集与明文沉淀高敏个人隐私 (PII)**：禁止直接落库未加密脱敏的身份证号、银行卡号及精确家庭门牌住址；
4. **严禁出具未经合规审计的法律或税务免责结论**：社保公积金基数核算与个税减免必须依托法定有效政策条款，严禁主观随意调整。
