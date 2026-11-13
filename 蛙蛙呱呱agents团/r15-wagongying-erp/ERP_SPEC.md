# ERP_SPEC.md - R15 蛙供应 · ERP 与供应链运营统一规格账本 (SSOT)

> **版本**：v12.0  
> **单一信任源 (Single Source of Truth)**：本账本定义采购寻源、物料主数据、库存台账、BOM配方展开、生产发料、销售履约与财务业务接口的全局业务标准、确定性计算口径与 8 维硬门禁。

---

## 一、 北极星指标与核心准则 (North Star & KPI)

| 指标代号 | 指标名称 | 目标基准线 | 统计口径说明 |
| :--- | :--- | :--- | :--- |
| **IRA** | 库存记录准确率 (Inventory Record Accuracy) | **≥ 99.8%** | 抽盘物料账实完全一致条目数占总抽盘物料条目数的比率 |
| **OTIF** | 准时足额交付率 (On-Time In-Full Rate) | **≥ 98.0%** | 按约定日期足额完工并交付客户（或采购按时全收）的比率 |
| **BPC** | 预计量守恒准度 (Balance Projected Conservation) | **= 100.0%** | actual + ordered + planned − reserved = projected 守恒等式绝对成立 (容差 0.00) |
| **ORT** | 采购超收容差 (Over-Receipt Tolerance) | **= 0.00%** | 采购到货收货量超过 PO 数量的容差默认必须为 0，超收必须审批 |

---

## 二、 供应链计算规范与核心模型 (Supply Chain Calculation Models)

1. **库存预计可用量守恒公式 (Conservation Formula)**：
   $$\text{Projected Available} = \text{Actual In-Stock} + \text{Ordered (PO)} + \text{Planned (WO)} - \text{Reserved (SO/MO)}$$
   - 容差绝对值为 0.00，不允许任何不可解释的漂移。
2. **多阶 BOM 配方展开需求模型 (BOM Explosion Formula)**：
   $$\text{Gross Requirement} = \text{Finished Good Qty} \times \text{Unit BOM Qty} \times (1 + \text{Scrap Rate})$$
   - 损耗率 $\text{Scrap Rate} \ge 0.0$，用量 $\text{Unit BOM Qty} > 0.0$。
3. **安全库存与再订货点模型 (Safety Stock & ROP)**：
   $$\text{ROP} = (\text{Daily Usage} \times \text{Lead Time}) + \text{Safety Stock}$$
   - 保持 5~15 天安全缓冲天数。
4. **采购与发票勾稽恒等式**：
   $$\text{Total Amount} = \sum (\text{Line Quantity} \times \text{Unit Price}) + \text{Tax} - \text{Discount}$$
   - 单价与数量必须非负。

---

## 三、 供应链 8 维发布与准入门禁 (The 8-Dimension Gate Matrix)

所有 ERP 供应链工件必须通过以下 8 维硬门禁校验：

| 门禁 ID | 门禁名称 | 合格阈值 (Threshold) | 破坏后果与处置策略 |
| :--- | :--- | :--- | :--- |
| **GATE-01** | 预计量守恒门禁 (Conservation Gate) | **差额绝对值 = 0.00 (无损恒等)** | 预计量不守恒直接判定 CRITICAL，禁止出库流转 |
| **GATE-02** | 负库存刚性拦截 (Negative Stock Gate) | **actual_qty ≥ 0 (默认禁止负数)** | 无负库存开关时发生负库存直接阻断交易 |
| **GATE-03** | 采购超收容差 0 (Over-Receipt Gate) | **receipt_qty ≤ po_qty (容差 0.00)** | 超收直接拦截入库，除非具备让步接收特批凭据 |
| **GATE-04** | BOM 配方完整性 (BOM Validity Gate) | **配方行数 ≥ 1 且单件用量 > 0** | 空配方或负用量直接驳回生产请求 |
| **GATE-05** | 履约完工全交付全开票 (Full Delivery & Billing) | **Completed 单据全发货且全开票** | Completed 销售单若未全交付或未全开票判为矛盾 |
| **GATE-06** | 供应商账期上限 (Payment Terms Gate) | **账期 ≤ 180 天** | 超过 180 天账期提示隐性融资风险并驳回 |
| **GATE-07** | 付款授权刚性声明 (Payment Authorization Gate) | **必须具备显式授权 handoff** | 严禁 Agent 代付款，无授权付款直接阻断 |
| **GATE-08** | SoD 职责分离矩阵 (Separation of Duties Gate) | **不相容岗位权限冲突数 = 0** | 采购与付款、出入库与盘点角色重叠直接告警拦截 |

---

## 四、 角色红线与合规边界 (Non-Negotiable Boundaries)

1. **严禁越权代付款或发起资金划扣**：R15 仅产出付款单建议与勾稽验算，严禁直接代付款或发起打款；
2. **严禁擅自修改已过账历史凭证与反记账**：历史入库单、出库单与凭证严禁覆写或直接物理删除；
3. **严禁放行无特批的采购超收与非法负库存**：零容差严防多付货款与虚假库存；
4. **严禁在工件中输出明文凭据与密钥**：杜绝 API 密钥、密码与 Token 泄露。
