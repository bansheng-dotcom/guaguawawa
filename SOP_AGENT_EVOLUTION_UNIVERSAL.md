# 人机协作·智能体十轮渐进式演进标准作业程序 (Universal Agent 10-Stage Evolution SOP v13.0)

> **核心哲学**：拒绝“一蹴而就的脆弱重构”，拒绝“只有判断题的假 Agent”，更严禁**“削足适履、生搬硬套的模板八股文”**。  
> **核心演进法则 (Audit-First, Metamodel Law & Workflow Automation)**：  
> 1. **十轮演进的本质是「演进元模型 (The 10-Stage Metamodel)」**——它代表一个智能体从“脚本玩具”走向“工业级自主交付实体”必须翻越的 **10 座工程与认知大山**，而非某一个角色的具体功能名字；  
> 2. **实战体检与 Engines 模块化解耦**——升级绝非套模板或死记硬背，每轮必须**先穿透体检当前智能体的代码现状与真实断点病灶**，对标高星开源标杆，并将核心能力沉淀在独立解耦的 `engines/` 目录中；  
> 3. **零破坏双轨回归法则 (Dual Zero-Regression Gate)**——每一轮升级必须是旧系统的严格超集。既要运行**原有基准回归测试套件 (100% PASS)**，也要通过新构建的**十维演进集成测试套件 (100% PASS)**，破坏原有契约或只有口头汇报均判为升级失败；  
> 4. **Workflow 外循环自动化编排法则**——支持以多阶段自动化 Workflow (`auto_evolve_runner.py` 调度器 + `agent()` 编排钩子) 驱动持续自升级，自动化闭环完成体检、对标、代码跃迁、工件验收与双轨回归，状态机精准落盘至 `workspace/evolution_state.json`。  
> **通用范围**：适用于「蛙蛙呱呱 agents 团」全角色矩阵（R01 全局决策/CEO、R02 运营编排/COO、R03 财务合规/CFO、R04 独立评审/Reviewer、R05 战略研究/CSO、R06 数据分析、R07 产品管理/PM、R08 原型架构/MVP、R09 生产研发、R10 视觉设计、R11 文案运营、R12 增长运营/Growth、R13 客户成功/CSM、R14 交易履约/Commerce、R20 运维安全等）。

---

## 一、 为什么不能生搬硬套？病根溯源与“求同存异”

### 1. 历史教条主义病根
早期的 SOP 演进表直接沿用了 **R10 视觉设计官（蛙成美）** 的成功经验。在视觉生成场景下，“画廊看板”、“去塑料感/去反光”、“局部遮罩重绘 (Inpainting)”、“留白坐标计算”是自然的核心技术点；  
但如果直接硬搬到 **R04 (独立评审/Reviewer)**、**R02 (运营/COO)**、**R03 (财务合规/CFO)**、**R06 (数据分析)**、**R08 (原型实现/MVP)**、**R01 (战略决策)** 等角色身上，就会出现**“让评审去调反光”、“让运营去画遮罩”、“让财务去降噪”、“让架构去调饱和度”**的荒谬现象，导致工程变成为了交差而写假文件的“伪 Agent”。

### 2. 求同存异：十座必须翻越的“工程与认知大山”
十轮演进的“**同**”在于：任何专业智能体走向工业级成熟度，必须依次构建出以下 **10 层核心能力**；  
十轮演进的“**异**”在于：面对每一层，不同职能智能体的**体检病灶不同、对标项目不同、落地的技术方案与物理工件截然不同**！

---

## 二、 十维演进元模型：通用本质思维 vs 全角色特化落地方案

| 阶梯层级 | 这一层的通用本质思维 (The "Why") | ❌ 错误的死记硬背 (生搬硬套) | ✅ 正确的因地制宜 (先体检现状，再对标升级) |
| :---: | :--- | :--- | :--- |
| **L01<br>工具实体层** | **它有真实的手和脚吗？**<br>还是只有字符串 print 或写死 Mock？ | 无论什么 Agent，都强行抄一个生图驱动或空引擎接口 | **R15 体检**：库存预计量计算、BOM配方多阶展开与超收校验缺乏独立确定性沙箱，对标 `Frappe ERPNext / Odoo / Apache OFBiz` 构建真实物料守恒沙箱 (actual+ordered+planned-reserved=projected，容差 0.00)、多阶 BOM 展开与采购超收容差 0 探针；<br>**R14 体检**：商品阶梯价格、税费计算、用量计量聚合与退款限额缺乏真实确定性沙箱，对标 `Stripe API / Medusa / Lago / Kill Bill` 构建真实勾稽平衡沙箱 (容差 0.00)、阶梯定价、用量聚合与电子签哈希探针；<br>**R13 体检**：客户健康度、NPS与流失概率缺少确定性沙箱，对标 `Gainsight / Vitally / Planhat` 构建真实 NPS 三桶与四维健康加权计算沙箱 (30/25/25/20)、管道 HHI 与流失预测模型；<br>**R12 体检**：增长指标复算依赖手写或静态 Mock，无漏斗瓶颈与统计显著性检测，对标 `PostHog / GrowthBook` 构建真实增长指标精算沙箱 (LTV/CAC/K-factor) 与 Z-Score / p-value 假设检验引擎；<br>**R11 体检**：基础字数排版依靠简单正则或 print，无 AST 解析与格式 Lint，对标 `textlint/vale` 构建真实AST解析与确定性排版Lint引擎；<br>**R10 体检**：外部生图缺少设备层健康探测与物理工件属性审查，对标 `SDWebUI / ComfyUI / Stable-Diffusion` 构建多路生图引擎池接管、硬件探针与物理图像头/尺寸判定；<br>**R07 体检**：优先级打分与产品需求校验缺乏真实 AST 与确定性计算引擎，对标 `Productboard / Aha! / OpenHands` 构建 AST 语法校验、RICE/Opportunity 优先级算子与健康探测探针；<br>**R05 体检**：研究台账缺少代码与文档 AST 审计驱动，对标 `PyCQA/radon / ast-grep` 构建 AST 复杂度与反模式静态审查引擎；<br>**R04 体检**：审查缺少真实代码度量驱动，对标 `PyCQA/radon / ast-grep` 构建圈复杂度与可维护性评分引擎；<br>**R02 体检**：排期日历缺少跨进程调度，对标 `Temporal/Celery` 构建任务探针与运行池；<br>**R03 体检**：财务算子零散且缺合规探针，对标 `DuckDB/FinOps` 构建精算引擎与合规健康探针；<br>**R06 体检**：SQL 没有真实查询引擎，对标 `DuckDB-Wasm` 接入嵌入式本地分析驱动；<br>**R08 体检**：代码只吐 Markdown，对标 `WebContainer / E2B / Playwright` 接入真实 HTML/AST 语法沙箱、表单提交端点安全探针与 A11y 可达性树审查；<br>**R09 体检**：代码未真正编译，对标 `esbuild / tsc / PyTest` 接入真实轻量构建与语法自测沙箱。 |
| **L02<br>意图解构层** | **它听得懂复杂人话吗？**<br>还是只有静态正则/硬编码字典匹配？ | 无论什么场景，都硬套视觉 Prompt 摄影词扩写器 | **R15 体检**：复合供应链与排产需求无法结构化解构，对标 `DSPy / Ray DAG` 编译包含【审计 / 寻源 / PO签发 / 生产调拨 / 收货入库】5 阶段标准的 Kahn 拓扑 DAG 与工时估算；<br>**R14 体检**：复合交易/订阅/签约/履约意图无法结构化解构，对标 `DSPy / Ray DAG` 编译包含【商品选品核价 / 购物车订单 / 订阅计费 / 支付签约 / 履约状态机】5 阶段标准的 Kahn 拓扑 DAG 与工时估算；<br>**R13 体检**：复合客户运营意图无法结构化编排，对标 `DSPy / Ray DAG` 编译包含【审计/诊断/归因/挽留/自动化】5 阶段标准的 Kahn 交付 DAG 与工时估算；<br>**R12 体检**：复合增长需求无法解构为全生命周期闭环，对标 `DSPy / Ray DAG` 编译包含【现状诊断 / 假设发现 / 飞轮构建 / 渠道投放 / 归因复盘】5 步标准的 Kahn 交付 DAG 与工时估算；<br>**R11 体检**：复合运营意图无法结构化拆解与编排，对标 `DSPy / Ray DAG` 编译【选题/受众/钩子提纲/正文/分发】5步 Kahn DAG 与工时估算；<br>**R10 体检**：商业设计诉求缺乏阶段解构，对标 `DSPy / Ray DAG` 将自然语言需求解构编译为包含【解析/扩写/渲染/精修/质检】5 阶段标准的 Kahn 交付 DAG 与工时估算；<br>**R07 体检**：复合产品需求缺乏阶段解构，对标 `DSPy / Ray DAG` 提取实体并编译为包含【JTBD发现 / OST机会树 / PRD用户故事 / 优先级排序 / 路线图发版】5 步标准的 Kahn 交付 DAG 与工时估算；<br>**R05 体检**：复合战略诉求依赖手工分步，对标 `DSPy / Ray DAG` 编译为声明式 Research DAG 与 Kahn 拓扑执行序；<br>**R04 体检**：复合审查需求需多次调用，对标 `DSPy / Ray DAG` 编译为声明式 Review DAG 与 Kahn 拓扑序；<br>**R02 体检**：面对“双11大促抢跑，研发紧缺，预计需15人天”，对标 `DSPy` 编译为工时、人天、依赖拓扑；<br>**R03 体检**：面对“账上有200万刀，月烧15万，查AML与跑道”，对标 `Vanna/DSPy` 提取资金量与窗口并结构化归一到24项动作；<br>**R06 体检**：用户说“看一下上周转化跌了没”，对标 `Text-to-SQL / Vanna` 编译为结构化度量指标与时间窗口；<br>**R08 体检**：复杂 PRD 需求无法拆解，对标 `DSPy / Ray DAG` 提取形态、栈、端点并编译为包含【切片/脚手架/页面/设计/QA】5步标准的 Kahn 交付 DAG 与工时估算；<br>**R01 体检**：复杂战略提议，对标 `Meta-Prompting` 提取不可逆性、牵头 DRI 与治理时间盒。 |
| **L03<br>自愈反思层** | **它犯了错会自己改吗？**<br>还是错误直接报错崩溃或把垃圾丢给人类？ | 强行给非视觉 Agent 写一个“画面留白或高光打分器” | **R15 体检**：供应链合规红线缺乏刚性审判，对标 `Reflexion / Critic-Agent` 硬拦截越权代付款（移交 R03）、负库存超发、无授权超收与擅自篡改历史账单，并自愈反思补齐预计量守恒与财务授权 handoff 声明；<br>**R14 体检**：交易安全红线缺乏刚性拦截，对标 `Reflexion / Critic-Agent` 硬拦截篡改已结历史财务账目（强制移交 R03）、非法负数洗账、超额退款无授权，并自愈补齐缺失幂等键、规范币种（RMB->CNY）与勾稽差额反思自纠；<br>**R13 体检**：客户运营红线缺乏硬审判，对标 `Reflexion / Critic-Agent` 硬拦截越界处理退款（移交 R14）、私自违规承诺免单、双门槛不达标放行续约，并自愈客户档案与承诺三件套；<br>**R12 体检**：遭遇无源刷量、纯烧钱补贴未算ROI或越界接管销售CRM时缺乏防线，对标 `Reflexion / Critic-Agent` 硬拦截四大违规红线，自愈平衡LTV/CAC与健康回收期；<br>**R11 体检**：遇到广告法极限词、未授权发布或缺失核心 CTA 时直接报错，对标 `Reflexion / Critic-Agent` 硬拦截未授权发布与极限词，自愈补齐黄金3秒钩子与行动号召；<br>**R10 体检**：缺少自动补齐残缺提示词机制，对标 `Reflexion / Critic-Agent / OpenHands` 自愈补齐负向提示词、风格锁与安全留白，并硬拦截“越界做后台分布式高可用微服务”与“替老板直接拍板商业定价”红线；<br>**R07 体检**：PRD 验收标准非 Gherkin 或缺漏核心板块时直接阻断报错，对标 `Reflexion / Critic-Agent` 闭环反思自愈补齐 Given/When/Then 与成功指标，并强力拦截“越界写工程代码”与“替老板直接拍板决策”红线；<br>**R05 体检**：市场份额未归一或无源推测直接报错，对标 `Reflexion / OpenHands` 自愈映射并强拦截“替老板拍板”红线；<br>**R04 体检**：输入字段别名、判据缺少状态时崩溃，对标 `Reflexion` 闭环反思自愈字段映射并强拦截自评红线；<br>**R02 体检**：排期产生循环依赖或工时超标时崩掉，对标 `Reflexion` 自动检测缺陷并重新平衡负载；<br>**R03 体检**：勾稽破损或触犯保本保收益，对标 `Reflexion/Critic-Agent` 闭环反思并注入平衡分录与免责声明；<br>**R06 体检**：SQL 执行语法错误或除以零，对标 `Self-Debug` 捕获异常，自愈重写查询语句重试；<br>**R08 体检**：原型缺漏成败指标或佐证不足时瘫痪，对标 `Reflexion / Critic-Agent` 自愈补齐 criteria 与 handoff，并硬拦截“越界做生产级工程（K8s/微服务）未声明交接”及“充斥 TODO/待定占位”红线；<br>**R01 体检**：决策卡缺杀死标准或不可逆无回滚，对标 `Critic-Agent` 闭环重写补齐安全防线。 |
| **L04<br>领域账本层** | **它有全局行业专业基准吗？**<br>还是换个任务/多轮对话后口径严重漂移？ | 不管是什么职能，都在根目录硬塞一个 DESIGN.md | **R15 体检**：库存准确率、准时交付率与 8 维门禁散落代码，建立 `ERP_SPEC.md`（定义统一北极星 IRA≥99.8%、OTIF≥98.0%、预计量守恒准度 BPC=100%、采购超收容差 ORT=0.00% 与 8 维发布硬门禁）；<br>**R14 体检**：交易业务规范、税率口径与 8 维门禁散落代码，建立 `COMMERCE_SPEC.md`（定义统一结算成功率 SRR≥99.5%、勾稽容差 BTA=0.00、电子签合规率 SCL=100% 与 8 维发布硬门禁）；<br>**R13 体检**：健康分权重与门禁散落代码，建立 `CSM_SPEC.md`（定义北极星指标 GRR/NRR/NPS、四维加权 30/25/25/20 与 8 维发布门禁）；<br>**R12 体检**：北极星指标、8维门禁与显著性量纲散落，建立 `GROWTH_SPEC.md`（定义统一 WAU 北极星、8 维发布门禁与 p<0.05 容差标准）；<br>**R11 体检**：全平台字数、标题爆款公式与反作弊规则分散在各 skill，建立 `COPY_SPEC.md`（定义 8 维发布硬门禁与平台字数矩阵校验）；<br>**R10 体检**：色彩与排版规范分散，建立 `DESIGN.md`（定义统一色彩 Token、安全留白与字阶规范，提供 `spec_ledger.py` 动态加载并一键导出 CSS Variables 与 Flutter ThemeData）；<br>**R07 体检**：JTBD 准则、RICE 量纲与 PRD 8 门禁散落硬编码，建立 `PM_SPEC.md`（定义统一 Job Story 三段式、RICE 权重与发布门禁 SLA，并提供 `pm_spec_ledger.py` 动态加载）；<br>**R05 体检**：TAM口径容差、三级证据链硬指标硬编码分散，建立 `RESEARCH_SPEC.md`（定义 0.3 方差上限、PESTEL 完整性）；<br>**R04 体检**：证据链等级、门禁扣分散落，建立 `REVIEW_SPEC.md`（定义三级证据链、7维门禁扣分）；<br>**R02 体检**：排期阈值写死在代码，建立 `OPERATIONS_SPEC.md`（定义 8h 上限/红线）；<br>**R03 体检**：跑道告警线、留存年限散落，建立 `FINANCIAL_SPEC.md`（定义容差 0.00、6个月跑道底线、7年WORM）；<br>**R06 体检**：指标口径定义分散，建立 `METRICS_SPEC.md`（定义 GMV/LTV 口径与置信区间）；<br>**R08 体检**：组件规范与样式混乱，建立 `TECH_SPEC.md`（对标 `Style Dictionary / DTCG` 统一定义色彩阶梯、排版网格、响应式断点与 A11y 对比度底线，并一键编译 CSS/Flutter 映射）。 |
| **L05<br>质感去劣化** | **输出物有专业深度吗？**<br>还是充斥着 AI 常见废话/塑料感/逻辑伪影？ | 对非图片任务强行用 OpenCV 调饱和度或降噪 | **R15 体检**：供应链报告充斥“整体良好”、“按需采购”、“视情况而定”、“细节待定”套话，对标 `reviewdog / Vale` 构建 `SupplySlopGuard` 物理清洗，强制注入账实 IRA、ROP 再订货模型与责任人 DRI（蛙供应）；<br>**R14 体检**：交易交付报告充斥“整体正常”、“交易平稳”、“退款合规”、“细节待定”套话，对标 `reviewdog / Vale` 构建 `SlopGuard` 物理清洗假大空，强制注入订单流水凭证、不可篡改审计哈希与责任人 DRI（蛙交易）；<br>**R13 体检**：报告充斥“整体良好”、“持续关注”、“服务体验提升”套话，对标 `reviewdog / Vale` 构建 `SlopGuard` 物理清洗并置换为四维量化分值与确切 DRI（蛙客成）；<br>**R12 体检**：方案充斥“显著提升”、“大幅增长”等伪增长套话，对标 `reviewdog / Vale` 构建 `GrowthSlopGuard` 物理清洗并强制注入 p-value、95% 置信区间与量化行动力；<br>**R11 体检**：文案充斥“总而言之”、“毋庸置疑”等套话，对标 `reviewdog / Vale` 构建 `SlopGuard` 物理级拦截假大空词库，计算 Actionability 行动力分值并置换事实论据；<br>**R10 体检**：AI 生图有塑料反光和高光畸变、充斥占位废话，对标 `pbakaus/impeccable / Vale` 构建 `SlopGuard` 物理级高光抑制、微反差锐化与假大空占位递归清洗；<br>**R07 体检**：PRD 充斥“全面提升体验”、“持续优化性能”、“移动端功能待定”等套话，对标 `reviewdog / StyleGuide / Vale` 构建 `PMSlopGuard` 物理清洗并替换为量化判据（如 P99<200ms、流失率下降>=15%）；<br>**R05 体检**：报告充斥“值得重点关注”套话，对标 `reviewdog / StyleGuide` 建立 `SlopGuard` 强制可检验性与量化指标绑定；<br>**R04 体检**：评审充斥“整体良好”废话，对标 `reviewdog / StyleGuide` 建立 `SlopGuard` 强制可行动性与确切行号绑定；<br>**R02 体检**：方案全是“高度重视”空话，对标 `Anti-Slop` 审计并强制替换为明确 DRI 与交付时间；<br>**R03 体检**：财务建议充斥“加强合规”套话，落地 `FinancialSlopGuard` 绑定 DRI、控制金额与截止期；<br>**R06 体检**：数据解读只有复述没有归因，建立数据幻觉审计器，强制输出置信度与相关性检验；<br>**R08 体检**：原型充满“此处待定”、“TODO: 实现业务逻辑”、“href='#'”等假按钮与塑料感，对标 `reviewdog / Biome` 构建 `PrototypeSlopGuard` 物理清洗替换并计算行动力得分。 |
| **L06<br>横向决策层** | **它能给人类提供选择吗？**<br>还是一锤子买卖逼人类无脑接受？ | 无论任务是什么，都强行拼一张九宫格生图看板 | **R15 体检**：补货决策单一缺乏权衡，对标 `Scenario Planning / MCDA` 自动裂变【极速敏捷版 (JIT Rush) / 稳健经济批量版 (EOQ Balanced，推荐) / 战略安全缓冲版 (Buffer Maximized)】三维决策看板与多维 ROI 权衡矩阵；<br>**R14 体检**：结算方案单一，对标 `Scenario Planning / MCDA` 自动裂变【极简现结版 (0.1d/全额单次付/极速履约) / 稳健阶段版 (0.5d/首付30%+电子签SLA+尾款70%，推荐) / 弹性用量版 (1.5d/底座月费+阶梯用量月结)】三维决策看板与多维 ROI 权衡矩阵；<br>**R13 体检**：续约挽留方案单一，对标 `Scenario Planning / MCDA` 自动裂变【极简防御型 / 稳健运营型 / 深度战略型】三维方案看板与多维 ROI 矩阵；<br>**R12 体检**：增长方案一锤子买卖，缺乏不同风险偏好的权衡空间，自动裂变【极速轻量试错版 (Minimal Rapid) / 稳健精益留存版 (Steady Lean) / 全域ROI平衡版 (Omnichannel Balanced)】三维策略看板与 ROI 矩阵；<br>**R11 体检**：文案交付一锤子买卖，人类缺乏多风格横向权衡对比机制，自动裂变【极简数据流 / 故事共鸣流 / 爆款转化流】三维方案与 ROI 矩阵；<br>**R10 体检**：视觉方案单一一锤子买卖，对标 `huashu-design / Stylescapes` 自动裂变【扁平现代版 / 商业大片版 / 赛博科技版】三维交付方案与 ROI 权衡矩阵；<br>**R07 体检**：需求输出单一一锤子买卖，对标 `MCDA / Scenario Planning` 自动裂变【极简试错版 (Lean MVP) / 基准商业版 (Commercial Standard) / 全功能旗舰版 (Enterprise Flagship)】三维交付方案与 ROI 权衡矩阵；<br>**R05 体检**：单一预测与策略，对标 `Scenario Planning` 自动裂变【保守紧缩 / 基准稳健 / 进取扩张】三维决策看板；<br>**R04 体检**：一刀切放行/驳回，对标 `Backstage / SonarQube` 自动裂变【激进突击 / 稳健基准 / 严苛防御】三维决策看板；<br>**R02 体检**：排期只吐一种方案，对标 `Stylescapes` 裂变出【突击激进 / 稳健基准 / 弹性精益】对比看板；<br>**R03 体检**：资金预测单一，对标 `Scenario Planning` 裂变【保守紧缩 / 基准稳健 / 进取扩张】看板；<br>**R06 体检**：单一指标视图无法归因，自动裂变出【环比同周期 / 渠道下钻 / 用户分层】对比看板；<br>**R08 体检**：原型交付一锤子买卖，对标 `Stylescapes / Scenario Planning` 自动裂变【极简切片版 (0.5d) / 标准组件版 (1.5d) / 生产就绪版 (3d)】三维方案与 ROI 权衡矩阵。 |
| **L07<br>伴生消费层** | **输出物下游系统能直接消费吗？**<br>还是必须让人类肉眼阅读并人肉二次录入？ | 强行给纯文本或纯逻辑计算计算 CSS 坐标留白 | **R15 体检**：供应链工件纯文本下游 ERP/MES 无法机器消费，对标 `OASIS SARIF / Vega-Lite` 伴随导出 `erp_bundle.json`、`erp_audit.sarif.json` (OASIS SARIF v2.1.0) 与 `erp_inventory_chart.vega.json`；<br>**R14 体检**：交易结果纯文本下游 ERP/对账无法机器消费，对标 `OASIS SARIF / Vega-Lite` 伴随导出 `commerce_bundle.json`、`commerce_audit.sarif.json` 与 `commerce_chart.vega.json`；<br>**R13 体检**：产物仅纯文本无法被系统消费，对标 `OASIS SARIF / Vega-Lite` 伴随导出 `csm_bundle.json`、`csm_audit.sarif.json` 与 `csm_health_chart.vega.json`；<br>**R12 体检**：增长策略仅纯文本无法被 CI/CD 或看板引擎消费，对标 `OASIS SARIF / Vega-Lite` 伴随导出 `growth_bundle.json`、`growth_audit.sarif.json` 与 `vega_charts.json`；<br>**R11 体检**：产物仅纯 Markdown，CMS、多平台发布流水线与 CI/CD 无法机器解析，对标 `OASIS SARIF` 伴随导出 `content_bundle.json`、`copy_audit.sarif.json` 与分发元数据；<br>**R10 体检**：仅输出图片下游无法装配，对标 `microsoft/sarif-tools / Figma-Context-MCP` 伴随导出 `design_bundle.json`、物理级 `design_layer_ast.json` 与标准 `design_audit.sarif.json` (OASIS SARIF v2.1.0)；<br>**R07 体检**：PRD 纯 Markdown 无法被 R08/R09 编译器解析，对标 `microsoft/sarif-tools` 导出结构化 `prd_bundle.json` 与 `prd_audit.sarif.json`；<br>**R05 体检**：报告纯 Markdown 无法集成，对标 `microsoft/sarif-tools` 导出 `research_result.sarif.json` 与 `bundle.json`；<br>**R04 体检**：CI/CD 无法直接消费报告，对标 `microsoft/sarif-tools` 伴随导出标准 `review_result.sarif.json`（OASIS SARIF v2.1.0）；<br>**R02 体检**：只输出文本下游无法消费，对标 `Design-to-Code` 伴随导出 `operations_spec.json`（任务 AST 树）；<br>**R03 体检**：报告仅人类可读，对标 `FinAST` 导出 `financial_spec.json` 与标准 `vega_spec.json` 供系统消费；<br>**R06 体检**：图表无法集成，伴随导出标准的 `vega_spec.json` 供前端图表引擎直接渲染；<br>**R08 体检**：原型仅人类浏览，对标 `microsoft/sarif-tools / Component-AST` 伴随导出标准 `component_ast.json`、`prototype_audit.sarif.json` 与 `prototype_bundle.json`，供前端编译器直接解析装配。 |
| **L08<br>局部差量层** | **改一小处需要全盘推倒重来吗？**<br>原有的满意部分会被冲掉吗？ | 强行在无像素场景下调用二值 Mask 羽化涂抹 | **R15 体检**：调整单一物料明细全量推倒重来，对标 `RFC 6902 (JSON Patch)` 实现条目级差量热修无损置换与增量物料守恒重算；<br>**R14 体检**：订单或购物车微调需全量撤单重做破坏已锁定状态，对标 `RFC 6902 (JSON Patch)` 实现条目级差量热修无损置换与增量重算总额勾稽平衡；<br>**R13 体检**：微调单一客户参数需全量重构，对标 `RFC 6902 (JSON Patch)` 实现条目级差量热修与无损增量评分；<br>**R12 体检**：微调某一渠道预算导致全量策略洗牌，对标 `RFC 6902 (JSON Patch)` 实现条目级差量热修无损置换与弹性差量重算；<br>**R11 体检**：微调单段需全量重写全文，破坏原有满意文案，对标 `RFC 6902 (JSON Patch)` 实现字段级与段落级增量补丁与无损局部应用；<br>**R10 体检**：改背景全量重绘导致主体变形，对标 `RFC 6902 / IOPaint` 实现属性级 JSON Patch 与语义遮罩局部无损增量重绘；<br>**R07 体检**：调整单一 AC 或字段重新生成全量 PRD，对标 `RFC 6902 (JSON Patch)` 实现条目级差量热修；<br>**R05 体检**：调单一竞品导致全量重算，对标 `RFC 6902 (JSON Patch)` 实现局部差量置换；<br>**R04 体检**：改一行触发全量重审导致旧告警误伤，对标 `diff-match-patch / reviewdog` 实现 Unified Diff 增量切片审查；<br>**R02 体检**：改一任务工时全局洗牌，对标 `RFC 6902` 实现局部差量节点置换；<br>**R03 体检**：微调租金全量重算，实现 `FinancialPatchEditor` 局部差量调节且保证勾稽不变；<br>**R06 体检**：重切时间段全量重算，实现局部切片下钻差量重算引擎；<br>**R08 体检**：改动单处组件或颜色全量重新生成原型，对标 `RFC 6902 (JSON Patch)` 实现属性及组件级差量补丁与无损局部应用，降低 75% 重复消耗。 |
| **L09<br>会话记忆层** | **它记得前因后果吗？**<br>第二轮对话是不是就彻底“失忆”了？ | 强行把图片路径写死存在内存临时变量里 | **全角色通用进阶（含 R10/R11/R12/R13/R14/R15 落地）**：对标 `MemGPT (Letta) / LangGraph State Store`：<br>1. 建立持久化会话记忆池 `session_state.json`；<br>2. 支持自然语言代词消歧（“按刚才第二套方案调整”、“把上次的落地页加上移动端适配”、“切换到小红书投放渠道”）；<br>3. 具备历史版本快照树与一键回滚 (Rollback) 能力。 |
| **L10<br>工业容灾层** | **它能上生产环境打硬仗吗？**<br>遇到网络抖动、死锁、超时会不会直接瘫痪？ | 随便写一段空的 `except: pass` 伪装容灾 | **全角色通用进阶（含 R10/R11/R12/R13/R14/R15 落地）**：对标 `Temporal / Celery / OpenTelemetry / Tenacity`：<br>1. 部署长任务看门狗 (`Watchdog`)，具备超时硬熔断（CLOSED/OPEN/HALF_OPEN 三态）与进程级隔离；<br>2. 外部 API 或依赖服务具备指数退避带抖动重试 (Exponential Backoff with Full Jitter)；<br>3. 全链路遥测追踪 `telemetry.jsonl`，记录 TraceID、SpanID、SHA256、耗时与健康状态。 |

---

## 三、 标准单轮演进五步操作法 (The 5-Step Execution Workflow)

每一轮演进必须杜绝直接“凭感觉写代码”，必须严格执行以下闭环：

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│ 步骤 1: 穿透体检 (Audit)│ ──►  │ 步骤 2: 标杆对齐 (Bench)│ ──►  │ 步骤 3: 架构跃迁 (Code) │
│ 扫描当前 Agent 代码与   │      │ 检索 Stars>1k 开源项目 │      │ 落实当前阶梯最低 3 项  │
│ 寻找当前层级断点真实病灶│      │ 吸收其核心设计模式     │      │ 架构升级，拒绝假代码   │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
                                                                            │
                                                                            ▼
┌────────────────────────┐                                      ┌────────────────────────┐
│ 步骤 5: 契约零破坏回归 │ ◄────────────────────────────────────│ 步骤 4: 物理工件验收   │
│ 运行原基准测试套件，   │                                      │ 终端执行 CLI 实跑，    │
│ 确保 100% PASS 零衰退  │                                      │ 真实物理工件落盘查验   │
└────────────────────────┘                                      └────────────────────────┘
```

### 1. 穿透体检 (Reality Audit)
- 严禁死记硬背！必须阅读当前智能体的代码，寻找当前阶梯维度的具体病灶：
  - *是根本没有实体驱动？还是只有 Mock 假数据？*
  - *是无法处理非预设自然语言？还是没有自愈修正机制？*
  - *是输出物下游无法机器解析？还是改动一处就会全盘推倒重来？*

### 2. 标杆对齐 (Benchmark Sourcing)
- 准入硬红线：启动该轮前必须列出检索到的 **GitHub 高星标杆（Stars > 1k）**；
- 明确吸收该标杆的什么机制（例如：学习 DSPy 的签名编译模式、学习 RFC 6902 的 Patch 算子规范、学习 Reflexion 的短时记忆反思流）。

### 3. 架构跃迁 (Architectural Upgrade)
- 每一轮必须落地**最低 3 项具体架构升级点**；
- 代码必须组织在 `engines/` 模块下，保持核心主流程解耦可测。

### 4. 物理工件验收 (Physical Artifact Validation)
- 拒绝文字汇报，必须在终端执行 CLI 命令；
- 真实物理产物落盘（如 Spec JSON、AST、看板 Markdown、遥测日志 `telemetry.jsonl` 等）。

### 5. 契约零破坏回归 (Zero-Regression Gate)
- 新功能的引入必须是旧系统的严格超集；
- 运行原有的单元测试和基准套件，必须 **ALL GREEN (100% 通过)**，任何破坏原有基础功能的操作直接判为升级失败。

---

## 四、 智能体分轮次自升级工作流推荐划分 (Recommended 3-Round Batching)

在自动化任务与 Workflow 编排场景中，十维演进元模型推荐划分为**三大渐进式升级阶段**：

```
                ┌──────────────────────────────────────────────┐
                │             十维演进三轮自升级路线             │
                └──────────────────────┬───────────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│   【第 1 轮】    │          │   【第 2 轮】    │          │   【第 3 轮】    │
│   执行基石阶段   │          │   专业深度阶段   │          │   工业交付阶段   │
│   (L01 ~ L03)    │ ───────► │   (L04 ~ L06)    │ ───────► │   (L07 ~ L10)    │
│                  │          │                  │          │                  │
│ • L01 工具实体   │          │ • L04 领域账本   │          │ • L07 伴生消费   │
│ • L02 意图解构   │          │ • L05 质感去劣化 │          │ • L08 局部差量   │
│ • L03 自愈反思   │          │ • L06 横向决策   │          │ • L09 会话记忆   │
│                  │          │                  │          │ • L10 工业容灾   │
└──────────────────┘          └──────────────────┘          └──────────────────┘
```

1. **第 1 轮：执行基石 (L01~L03)**
   - 目标：让 Agent “长出真实手脚、听得懂复杂需求、犯错能够就地自愈”；
   - 核心工件：`engines/runtime_engine.py`、`engines/intent_compiler.py`、`engines/reflexive_healer.py`；
   - 调度指令：`python auto_evolve_runner.py --stage 1`。
2. **第 2 轮：专业深度 (L04~L06)**
   - 目标：让 Agent “拥有行业统一基准账本、消除 AI 塑料感与假大空套话、为决策者提供多维方案权衡”；
   - 核心工件：`<ROLE>_SPEC.md`（如 `DESIGN.md`）、`engines/slop_guard.py`、`engines/scenario_matrix.py`；
   - 调度指令：`python auto_evolve_runner.py --stage 2`。
3. **第 3 轮：工业交付 (L07~L10)**
   - 目标：让 Agent “产物能直接被机器与下游解析消费、局部微调无需推倒重来、跨轮多会话不失忆、高并发容灾与全链路可观测”；
   - 核心工件：`engines/asset_bundle.py` (含 SARIF/AST)、`engines/diff_patch_engine.py`、`engines/session_memory.py`、`engines/telemetry_watchdog.py`；
   - 调度指令：`python auto_evolve_runner.py --stage 3`。

状态机调度器通用 CLI 规范：
- `python auto_evolve_runner.py --status`：查看当前十轮与三大阶段演进完成看板；
- `python auto_evolve_runner.py --stage <1|2|3>`：执行指定阶段演进批次；
- `python auto_evolve_runner.py --round <1..10>`：执行指定单层演进；
- `python auto_evolve_runner.py --run-all`：自动连续推进未完成的全部演进阶段。

---

## 五、 跨平台与沙箱工业级避坑指南 (Production Hardening)

1. **运行时异构路径引导 (Runtime Bootstrap)**：
   - 跨目录执行 `python agent.py` 时严禁依赖外部环境 `PYTHONPATH`；在 `agent.py` 与执行器顶部使用动态安全引导，将自身目录、agents 根目录、代码仓根目录统一注入 `sys.path`。
2. **Windows 终端编码与 Unicode 字符崩溃**：
   - 控制台子进程调用必须显式注入 `PYTHONIOENCODING=utf-8`，并在脚本内显式声明 `sys.stdout.reconfigure(encoding='utf-8')` 与 `sys.stderr.reconfigure(encoding='utf-8')`，防止 GBK 编码下特殊字符抛出 `UnicodeEncodeError` / `UnicodeDecodeError`。
3. **跨进程文件锁死锁与目录读写权限**：
   - 基于文件锁的机制必须配备强制生存时间（TTL 自动剔除）；
   - 在 Windows 沙箱环境下，若遇到跨子目录权限拒绝，应确保拥有上级目录的有效 DACL，或将临时文件约束在当前 Agent 的 `workspace/` 目录内部，严禁直接依赖系统全局不可写临时目录。
4. **沙箱权限与临时文件隔离**：
   - 跨系统执行时，临时文件统一约束在当前 Agent 的 `workspace/tmp` 或 `artifacts/` 目录内，避免使用系统全局 `tempfile` 触发沙箱权限拒绝。
5. **单元测试 loader 同名包遮蔽防御**：
   - 各 Agent 的测试目录 `tests/` 下必须显式放置 `__init__.py`，防止 Python `unittest` 动态索引时优先加载全局 site-packages 中的同名包产生 `AttributeError` 或 `ModuleNotFoundError`。
6. **自动化 Workflow 嵌套与上下文隔离**：
   - 使用自动化 `workflow` 编排工具调度多轮升级时，每一轮子 agent 调用必须遵循独立工作目录与环境解耦；
   - 调度脚本需捕获每一轮演进返回的工件与测试状态，严禁前序阶段未通过强行启动后续阶段。
7. **Windows 下 Python `tempfile.mkdtemp` 死循环挂起陷阱**：
   - 在 Windows 系统下，当临时目录或上级目录存在权限缺失时，Python 标准库 `tempfile.mkdtemp()` 捕获 `PermissionError` 会误以为“Windows 随机名称已被占用”，若 `_os.access(dir, _os.W_OK)` 为真，会执行 `continue` 进入无限重试死循环导致测试直接挂起 120s+ 超时。
   - **防御策略**：严禁盲目依赖隐式系统全局临时目录，必须在执行测试前由工作区显式创建带有效用户写入权限的 `workspace/tmp`，并在生成临时子目录时指定 `dir=tmp_dir`。
8. **Windows ACL 继承与 AppContainer 权限断裂自愈**：
   - 当在 Windows 沙箱环境下创建子目录或执行子进程时，若父目录的完全控制条目未配置容器继承 (`ContainerInherit, ObjectInherit`)，子目录将丢失当前用户的有效 `WRITE_DAC` / `WRITE_OWNER`，触发 `PermissionError: [WinError 5] 拒绝访问` 或 DSH 沙箱拒绝。
   - **修复策略**：必须通过 `diagnose-windows-sandbox-acl` 脚本排查并赋予用户完全控制权限（同时需确保 `$env:SystemRoot\System32` 在 `$env:PATH` 中以供调用 `icacls`）。
9. **异构 cwd 下模块导入路径断裂 (Import Traversal Defensive)**：
   - 在各子 Agent 的 `agent.py`、`run_tests.py` 与 `auto_evolve_runner.py` 顶部，若计算 `_REPO_ROOT` 时多写或少写一层 `dirname`，在异构工作目录（跨 Agent 或工作区根目录）下执行时将引发 `ModuleNotFoundError: No module named 'agents'` 或 `ModuleNotFoundError: No module named 'core'`。
   - **防御策略**：统一采用动态防爆探测法，将 `_HERE`、其上一级（`agents` 集合目录）以及上两级（仓库根目录）同时加入 `sys.path`，避免硬编码层级导致的路径断裂。
10. **案例库动态扩展与历史测试契约超集兼容 (Case Library Hardcoding Antipattern)**：
    - 在新引入真实业务案例（例如从 2 个扩展至 3 个，引入 `channel-attribution` 等深度用例）时，若历史测试套件硬编码断言 `len(cases.list_cases()) == 2`，会导致历史基准测试直接挂红。
    - **防御策略**：既有测试契约应使用严格超集判据（`>= 2`），并对新案例做结构与语义的存在性校验，既杜绝案例丢失，又支持业务用例库平滑扩容。
11. **时间锚点漂移与动态日期断言陷阱 (Time-Anchored Date Drift Pitfall)**：
    - 在包含截止时间、逾期计算 (`due_date`, `overdue_grace_days`) 等确定性算子时，若静态测试样例硬编码了绝对日期（如测试样例写死 `2026-11-08`，系统日期随时间推移至 `2026-11-10`），会导致原为“未逾期”的干净样例被动态判定为逾期从而引发测试崩溃。
    - **防御策略**：测试样例应采用动态相对时间锚点（如 `datetime.date.today() + datetime.timedelta(...)`）或时钟 Mock 注入基准时间，测试数据中静态基准日期必须预留充分未来时间窗口。
12. **交易与金融类智能体的确定性浮点勾稽与零容差沙箱 (Zero-Tolerance Balance Guard)**：
    - 金融、订单与交易金额核算严禁使用未加控制的隐式浮点数累加，防止 IEEE 754 精度丢失产生微量误差；必须使用四舍五入或最小货币分位 (`cents`) 核算，实现 $\text{Total} = \sum (\text{Price} \times \text{Qty}) + \text{Tax} - \text{Discount} + \text{Shipping}$ 的绝对零容差 ($|\text{tolerance}| \le 0.001$) 勾稽平衡，破损直接阻断。
13. **跨角色硬红线移交与协作契约闭环 (Cross-Role Redline Hand-off)**：
    - 智能体必须具备严格的角色权责防线：如 R13 严禁越权处理退款打款并强制移交 R14 (蛙交易)；R14 严禁越权修改历史账目并强制移交 R03 (蛙守线·财务)；R15 (蛙供应) 严禁越权代付款或擅自修改已结历史库存台账，涉及资金拨付必须移交 R03 并强制要求授权声明；任何跨界越权操作必须触发 `[REDLINE BLOCKED]` 阻断抛错，杜绝无边界乱伸手。
14. **会话记忆槽位与顶层活跃实体的双向同步 (Memory Slot Bi-directional Sync)**：
    - 在 `session_memory.py` 中更新槽位（如 `update_slot("current_order_id", ...)`）时，必须同时持久化至 `slots` 字典和顶层实体字段，防止代词消歧读取旧值造成状态漂移。
15. **供应链物料预计可用量守恒等式绝对闭合 (Projected Conservation Equation)**：
    - 在 ERP 供应链场景下，预计量必须严格满足 $\text{Projected} = \text{Actual} + \text{Ordered} + \text{Planned} - \text{Reserved}$，容差绝对值为 0.00；任何出入库、局部 Patch 或订单状态流转均需触发守恒重算，不守恒即判为 CRITICAL 门禁破损。
16. **采购超收零容差与让步接收凭据约束 (Strict Zero-Tolerance Over-Receipt)**：
    - 采购入库超收容差默认必须为 0.00%（$\text{Receipt} \le \text{PO}$），严防多付货款；超收发生时必须触发自愈机制生成让步接收申请 (Concession Ticket) 并阻断自动流转，直至人工或财务特批凭据闭环。

---

## 六、 升级验收六大交付红线 (Six Non-Negotiable Rules)

1. ❌ **无体检报告不准开工**：严禁无脑套模板，每轮前必须明确指出该 Agent 在当前阶梯上的真实代码断点；
2. ❌ **无开源标杆不准开工**：必须明确列出 Stars > 1k 的参考项目及吸收的具体架构模式；
3. ❌ **无物理工件验证不准汇报**：必须有 CLI 实战跑出来的文件（JSON/Markdown/Log），拒绝纯文本汇报；
4. ❌ **回归失败不准算升级成功**：双轨回归测试套件未达到 100% GREEN (All Tests Passed) 的一切汇报均为无效；
5. ❌ **严禁把 10 轮演进在单轮里合并“伪造”打卡**：各 Agent 目录下必须配备标准化自动化演进执行器 `auto_evolve_runner.py`，必须由外循环状态机逐轮分步驱动、每轮产生独立的物理工件验收、每轮严守双轨回归门禁，并将轮次打卡轨迹落盘至 `workspace/evolution_state.json`，确保每一次演进均真实、独立、可追溯、可审计；
6. ❌ **严禁破坏原有测试契约与偷懒删除判据**：在扩展技能入口（如添加全功能 pipeline 或新动作）时，严禁简化、注释或删除已有动作的判据字段（如 `lock_count`, `tests_passed` 等），扩展代码必须是历史契约的严格超集，破坏原有契约直接判为升级失败。

---

## 七、 升级交付件标准结构参考 (Golden Standard Repository Structure)

经过三轮演进升级后，一个工业级智能体的标准工程目录结构如下：

```
rXX-<role-name>/
├── agent.py                        # 主入口：提供 manifest/demo/run/evolve(子命令探针)
├── auto_evolve_runner.py           # 自动化十轮演进调度状态机执行器 (支持 --stage 1/2/3, --round 1..10, --run-all)
├── run_tests.py                    # 双轨零破坏回归总入口 (既有门禁 + 演进集成门禁)
├── <ROLE>_SPEC.md                  # [L04] 领域业务或技术规格账本 (SSOT，如 PM_SPEC.md / TECH_SPEC.md)
├── EVOLUTION_REPORT.md             # 演进终验综合报告
├── engines/                        # 十维演进解耦核心引擎包
│   ├── __init__.py
│   ├── runtime_engine.py           # [L01] 工具实体层 (真实沙箱/AST解析/确定性算子)
│   ├── intent_compiler.py          # [L02] 意图解构层 (DAG拓扑编译/工时预算)
│   ├── reflexive_healer.py         # [L03] 自愈反思层 (Reflexion自纠/红线边界拦截)
│   ├── spec_ledger.py              # [L04] 领域账本层 (账本编译与跨端规则导出)
│   ├── slop_guard.py               # [L05] 质感去劣化 (Anti-Slop去塑料感/占位与假大空驱除)
│   ├── scenario_matrix.py          # [L06] 横向决策层 (三维方案裂变与多维ROI权衡矩阵)
│   ├── asset_bundle.py             # [L07] 伴生消费层 (AST/SARIF/Bundle跨系统导出)
│   ├── diff_patch_engine.py        # [L08] 局部差量层 (RFC 6902 JSON Patch增量热修)
│   ├── session_memory.py           # [L09] 会话记忆层 (记忆池/代词消歧/快照回滚)
│   └── telemetry_watchdog.py       # [L10] 工业容灾层 (三态熔断/抖动重试/遥测日志)
├── tests/
│   ├── __init__.py
│   └── test_evolution_l01_l10.py   # 十维元模型配套双轨集成测试套件 (100% PASS)
└── workspace/
    ├── evolution_state.json        # 状态机打卡持久化轨迹 (10/10 PASS)
    ├── telemetry.jsonl             # 全链路遥测追踪日志
    ├── session_state.json          # 多轮交互快照记忆池
    └── bundles/                    # 伴生消费导出的标准资产包 (含 SARIF / AST / Spec)
```

---

## 八、 全角色演进落地映射速查表 (Cross-Role Mapping Matrix)

| 智能体代号 | 智能体名称 | 核心职能定位 | L04 领域账本命名 | L05 质感去劣化核心切入点 | L06 横向决策矩阵变体 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R01** | 蛙全局 (CEO) | 全局战略与决策治理 | `EXECUTIVE_GOVERNANCE_SPEC.md` | 拦截空泛愿景、无回滚路径建议与不可逆动作伪装 | 激进扩张 / 基准稳健 / 极致防御 |
| **R02** | 蛙排步 (COO) | 运营规划与跨流程调度 | `OPERATIONS_SPEC.md` | 拦截无工时评估、无明确 DRI 的“口头推进” | 突击激进 / 稳健基准 / 弹性精益 |
| **R03** | 蛙守线 (CFO) | 财务精算与合规审计 | `FINANCIAL_SPEC.md` | 拦截“保本保收益”违规承诺与虚假无源毛利预估 | 保守紧缩 / 基准稳健 / 进取扩张 |
| **R04** | 蛙挑刺 (Reviewer) | 独立审查与对抗门禁 | `REVIEW_SPEC.md` | 拦截“整体良好”、“基本合格”无代码/无行号套话 | 严苛防御 / 稳健基准 / 激进放行 |
| **R05** | 蛙深远 (CSO) | 行业洞察与战略研究 | `RESEARCH_SPEC.md` | 拦截“值得重点关注”空泛研报，强制三级证据链绑定 | 保守紧缩 / 基准稳健 / 进取扩张 |
| **R06** | 蛙得清 (Analyst) | 数据分析与因果归因 | `METRICS_SPEC.md` | 拦截数据表面复述，强制输出相关性与置信区间 | 环比同周期 / 渠道下钻 / 用户分层 |
| **R07** | 蛙得明 (PM) | 产品规划与需求矩阵 | `PM_SPEC.md` | 拦截“提升用户体验”、“持续优化性能”、“功能待定” | 极简试错版 / 基准商业版 / 全功能旗舰版 |
| **R08** | 蛙建成 (MVP) | 原型构建与敏捷交付 | `TECH_SPEC.md` | 拦截“TODO:待定”、“href='#'”、假按钮与空页面 | 极简切片版 / 标准组件版 / 生产就绪版 |
| **R10** | 蛙成美 (Designer) | 视觉生成与设计工程 | `DESIGN.md` | 拦截 AI 生成塑料反光、高光畸变、占位废话，微反差精修 | 扁平现代 / 商业大片 / 赛博科技 |
| **R11** | 蛙点题 (Copywriter) | 内容主笔与文案运营 | `COPY_SPEC.md` | 拦截“毋庸置疑”、“总而言之”等 AI 味空泛套话，置换为事实与量化指标 | 极简数据流 / 故事共鸣流 / 爆款转化流 |
| **R12** | 蛙引流 (Growth) | 增长运营与归因精算 | `GROWTH_SPEC.md` | 拦截“显著提升”、“大幅增长”等伪增长套话，强制绑定 p-value、95% CI与量化指标 | 极速轻量试错 / 稳健精益留存 / 全域ROI平衡 |
| **R13** | 蛙客成 (CSM) | 客户成功与销售运营 | `CSM_SPEC.md` | 拦截“整体良好”、“持续关注”、“服务体验提升”套话，强制绑定四维健康分、流失哨兵与确切 DRI | 极简防御 / 稳健运营 (推荐) / 深度战略 |
| **R14** | 蛙交易 (Commerce) | 交易与收入履约 | `COMMERCE_SPEC.md` | 拦截“整体正常”、“交易平稳”、“退款合规”、“相关细节待定”套话，强制注入订单流水、退款比例与 DRI 蛙交易 | 极简现结 / 稳健阶段 (推荐) / 弹性用量 |
| **R15** | 蛙供应 (ERP) | ERP 与供应链运营 | `ERP_SPEC.md` | 拦截“整体良好”、“按需采购”、“视情况而定”、“相关细节待定”套话，强制绑定账实准确率 IRA、ROP再订货点与 DRI 蛙供应 | 极速敏捷 / 稳健经济批量 (推荐) / 战略安全缓冲 |
