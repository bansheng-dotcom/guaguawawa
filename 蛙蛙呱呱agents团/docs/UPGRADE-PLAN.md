# 智能体系统审查与修复方案（2026-11-24）

> 文档地位：`MASTER-UPGRADE-SOP.md` 的执行分册；本轮问题、接线和验收口径以本文为准。
>
> 本轮边界：**只做静态审查与 SOP 更新，不修改业务代码、配置、测试或项目数据，不运行报告生成、门禁复现或技能同步。** 文中“应”“必须”描述未来实施要求，不表示功能已经存在。
>
> 具体业务数据修复（如甘蓝链成本闭合、Q10 质量列错填）不在本轮范围内。

---

## 0. 审查结论

系统不是“没有数据层”，也不是“采集器完全未接”。当前已有 v1 标量 claims、v2 drill/query、v3 collection→staging→mart 三条路径，且 v3 已能被桥接层和探测层局部调用。

真正的主问题是：**多条路径缺少统一的产物有效性判定、原子交接、显式降级、实际资产统计和图表血缘闭环。** 因而“文件存在”“函数存在”“测试通过”可能被误当成“本次输入已正确处理”“真实数据已落表”“报告可安全交付”。

修复顺序必须先从主链正确性入手，再修格网、图表和采集增强。只补图型、只加采集器或只把 `datasets` 字段提升到顶层，都会扩大误判。

### 0.1 对旧方案的纠偏

| 旧表述 | 源码审查结论 |
|---|---|
| “数据层代码齐但产线未接” | 不准确。`_bridge_cells_to_claims()` 已有 v3/v2/v1 条件路径，`card_probe` 也调用 `preview()` / `quality()`；问题是优先级、有效性、交接与错误收口。 |
| “`collection_spec.preview` 无调用点” | 不准确。`core/card_probe.py` 有生产调用。 |
| “`actual_rows` 现在恒为 null” | 不准确。`supply_plan.capability_of()` 能读取合并稿顶层合法的 `mart_rows` / `dataset_rows` 等；但桥内资产未提升，且表定义列表不能被当作实际行。 |
| “`dataset_query` 只差调用” | 不准确。v2 已局部使用；还缺统一主链、图表血缘、失败状态和门禁闭环。 |
| “新增 `core/fulfil.py` 即可补齐” | 不宜直接采用。现有 `from_collection()` / `from_drill()` / `dataset_query` 已覆盖主要能力，应先复用并修契约，避免第三套平行实现。 |
| “固定 104 格、22 表、15→12 图是通用验收线” | 不采用。这些只能是某个项目的结果，系统验收应使用输入无关的不变量和项目快照。 |
| “已有 `GUAGUA_PIPELINE=v2` 回滚开关” | 当前 Python 源码未核实到消费者，不得作为现存能力引用。 |

---

## 1. 证据等级与已确认决策

### 1.1 证据等级

- **本地已核实**：直接读到当前源码或测试的路径与契约；不等于已做运行时复现。
- **外部事实**：官方文档、标准或原始项目资料支持的通用做法，以后文 `[cite:N]` 标注。
- **社区经验**：工程厂商或实践文章提供的补充，不当作标准强制条款。
- **本地建议**：结合本仓库得出的设计，需要通过实现与测试验证，不能写成既成事实。

### 1.2 用户已确认的三项决策

| 决策 | 现行口径 | 禁止做法 |
|---|---|---|
| **D1：grain 不自洽** | `cell.entity` 与数据集 grain 不一致时，优先按 grain 重拆；无法可靠映射的格子标 `unavailable`，保留原因与补采条件。 | 不猜数、不补零、不把省格硬塞进渠道/品类维、不靠改名制造一致。 |
| **D2：双口径覆盖率** | 同时报告“格子交付率”和“可画切片率”，二者使用同一计划版本，分别回答“问题是否交付”和“数据是否足以成图”。 | 不用其中一个替代另一个，不把论点格混进数据格分母，不因去重改变问题覆盖率。 |
| **D3：允许去重减图** | 只删除重复、空信息或关系不成立的图；图数可下降，但问题覆盖不得下降。 | 不设图数 KPI，不为凑数保留坏图，不以表格回退冒充图成功。 |

---

## 2. 当前主链接线（静态核实）

```text
out_v3/cells_filled.json
        │ v1：cells_claims.build()
        ▼
cards/<role>/claims.json ───────────────────────┐
                                                │
plan/drill.json + datasets                      │
        │ v2：cells_claims.from_drill()          │
        ▼                                      │
dataset_query.run()/to_chart() → claims.json ───┤
                                                ▼
collection.yaml                     core/dispatch.collect()
        │ v3：from_collection()          1. _bridge_cells_to_claims()
        ▼                              2. card_probe.probe()
staging/mart → drill → claims        3. 合并 claims 内容
                                     4. 计算 capability
preview()/quality() ↑                5. 进入报告构建与渲染
        │                              │
        └──── card_probe.probe()        ▼
                              report_flow → pages/_render_svg
```

### 2.1 已接好的部分

- v1/v2/v3 都有实现，不是三条完全孤立的技术 demo。
- v3 能生成 `mart_rows={dataset_id: row_count}`，这是能力统计可复用的数据基础。
- `supply_plan.capability_of()` 已有从顶层资产行数计算实际能力级别的逻辑。
- `dataset_query.run()/to_chart()` 已能把真实表行转成查询结果与图。
- `report_flow._chart_stats()` 已能记录图错误，说明并非完全不可观测。

### 2.2 断点不在“有没有函数”，而在交接语义

1. 桥接层先用 `owners - have` 判断缺卡；若所有角色都有 claims，可能在检查 v3/v2 输入之前直接 `skipped`。
2. 仅部分角色缺卡时，v3/v2 转换未严格限制 `only_roles`，`from_drill()` 又逐角色写 claims，可能越过本次角色范围。
3. v3 在完整成功前先写 drill/mart，再逐角色写 claims；中途失败可能留下看似可用的半份产物。
4. 合并稿接收 claims 的数字、来源、节次等，但桥内 `mart_rows` 等资产仍嵌在 `cells_bridge` 下，后续能力计算不一定能看到。
5. `datasets` 在 claims 中通常是**表定义列表**，不是实际数据行；直接提升字段会把“只有结构”误报为 L2，并把表数量当行数。
6. 探测路径分别执行 `preview()` 与 `quality()`，两者各自 fetch，同一源可能重复抓取，且快照不一定一致。
7. 报告渲染可在 pro→legacy→空图/表格之间回退；错误被统计但未形成统一的交付阻断策略。

---

## 3. 问题清单与修复方向

优先级说明：P0 影响事实正确性或越权执行；P1 影响交付可信度、可解释性和协同；P2 影响治理与维护。

| ID | 级别 | 本地已核实的问题 | 主要影响 | 修复方向 |
|---|---|---|---|---|
| **A01** | P0 | 桥接层以“角色已有 claims 文件”提前跳过，未先验证本次 v3/v2 输入及产物有效性。 | 新数据可能不生效；陈旧 claims 被当作本次交付；血缘错代。 | 跳过键改为合同版本、输入快照、查询/代码版本、资产指纹与校验状态；文件存在只作为索引，不作为有效性的充分条件。 |
| **A02** | P0 | 部分缺卡时，`from_collection()` / `from_drill()` 未限定本次角色范围，drill 转换会直接写角色 claims。 | 可能覆盖非目标角色的人工卡或有效卡；重试影响面扩大。 | 转换函数显式接收角色集合；默认不覆盖范围外或已验证卡；写入前做角色归属校验。 |
| **A03** | P0 | v3 分阶段直接写 drill/mart/claims，缺少统一临时区、完成清单与原子提交。 | 失败后残留半份新产物；下次运行可能把残留物当成有效 v2 输入。 | 使用 run_id、staging 临时目录、逐项校验和完成 manifest；全部成功后一次性发布，失败产物不可被后续路径发现。 |
| **A04** | P0 | 多处异常被转成跳过、空结果或空 SVG，缺少统一的 `from/to/reason` 降级记录。 | 用户看到“成功报告”，却无法区分无数据、解析失败、执行失败和渲染失败。 | 统一结果状态与错误分类；关键契约失败阻断，非关键内容可显式降级，但必须记录原因、影响范围和实际能力级别。 |
| **A05** | P0 | 桥内实际资产未以明确契约交给能力层；`datasets` 的“定义”与“行”语义又不同。 | 实际 L2 可能被低报；简单提升字段又会把无行表定义高报为 L2。 | 定义独立资产清单：`dataset_definitions`、`physical_assets`、`actual_rows` 分开；能力只读取通过校验的物理资产。 |
| **A06** | P0 | `dataset_gates.run()` 未核实到生产调用方；现有测试允许未提供实采行数时通过并记 `unverified`。 | “存在门禁”被误认为“门禁已生效”；未验证资产可能进入高能力声明。 | 在资产发布和报告能力声明前接门禁；声明 L2 或驱动数据图时必须有实采行数，未验证不得 PASS 为 L2。 |
| **A07** | P0 | `preview()` / `quality()` / `run()` 自身不统一执行 `validate()`；compliance 仍主要是模板声明；YAML 读取异常会返回 `{}`。 | 探测路径可能绕过执行前校验；解析错误可能被当成“没有规格”并继续降级。 | 所有入口共用同一前置门；配置缺失、读取失败、解析失败、合规拒绝分别报错，默认关闭而非默认放行。 |
| **B01** | P1 | `card_probe` 的 preview 与 quality 各自触发 collector.fetch。 | 请求量、费用、频控压力增加；同一格子的预览和质量结果可能来自不同页面版本。 | 同一 run/source 使用一次抓取的不可变快照，preview/quality/run 复用；记录 fetch_id 和快照哈希。 |
| **B02** | P1 | 格网中存在 entity 与 grain 不自洽，以及论点格与数据格混放的风险。 | 全格展开膨胀、错误聚合、覆盖率失真，进而误导图表和门禁。 | 按 D1 重拆；数据格与论点格分 schema、分缓存键、分统计，映射失败者显式 unavailable。 |
| **B03** | P1 | 单一格子覆盖率无法同时表达问题交付和可画性。 | 为追覆盖率硬填格或硬画图；减图又被误读为问题覆盖下降。 | 按 D2 同时输出两种覆盖率及 unavailable 清单，固定计划版本与去重口径。 |
| **B04** | P1 | pro 图表映射未覆盖 `stacked_bar`，scatter 标签丢失，donut 未使用独立 total/rest；donut 分母取 items 之和。 | 图型回退、误读、Top-N 部分和被伪装成整体。 | 修图合同与映射；构成图必须明确总体、互斥切片、Other/rest 和可核对的分母。 |
| **B05** | P1 | 图错误只统计不阻断，SVG 失败可留空或回退本节表格。 | 图数与门禁全绿不能证明图成功；空信息图和重复图混入交付。 | 建立 `ok/empty/invalid/render_error/deduplicated/blocked` 状态；按图的重要级别决定阻断或显式降级。 |
| **B06** | P1 | 无角色图时可按 refs/chart_query/关键词/chooser 反推图，图注未始终保留完整 dataset/query 血缘。 | 图与表脱节；读者无法复核数字来自哪次查询；自动选型可能改变原意。 | 数据图优先只消费已验证 query 结果；图注和资产清单保存 dataset_id、query、rows_hash、run_id；禁止无记录猜测式补图。 |
| **C01** | P2 | 多份 SOP 对产线状态、版本号和回滚开关的描述互相漂移；docs 索引又声称历史副本已清理。 | 实施者可能按旧方案重复造模块或误以为已有门禁/开关。 | MASTER 唯一总纲、本文唯一执行分册；旧 v3/专项文档标历史或限定适用范围，索引标明现行地位。 |
| **C02** | P2 | 工作区源码与活跃技能目录是两个副本，更新 D 盘文档不等于活跃技能已更新。 | 后续智能体继续读取旧规则，形成“文档已修、行为未变”。 | 使用现有 `scripts/sync_trae_skill.py` 做 `--check` 和经授权同步；不得假定自动镜像。 |

---

## 4. 外部做法与本地适配

外部资料用于校准原则，不意味着要引入完整 dbt、Dagster、Airflow、OpenLineage 或新渲染栈。

| 外部做法 | 可借鉴的事实 | 本地适配 | 不应照搬 |
|---|---|---|---|
| dbt model contracts 与 build | 模型可定义数据合同，build 按依赖执行模型、测试等节点；失败节点与后续节点需要明确处理。[cite:1][cite:2] | 把采集合同、资产物化、质量检查、报告消费串成有状态的依赖图；失败是否继续由节点策略决定。 | 不引入 dbt 运行时，不把“写了 YAML”当成合同已执行。 |
| dbt semantic models / validation | 语义模型明确实体、度量和维度；验证应先于依赖其语义的下游使用。[cite:3][cite:4] | grain、metric、entity、query 是同一合同的一部分，不在发卡、格网和图表各写一套。 | 不为“标准化”复制一套新的语义平台。 |
| Airflow 幂等建议 | 任务应支持相同输入下可重跑，避免隐式依赖变化上下文和半提交状态。[cite:5] | run_id + 固定输入快照 + 原子发布 + 可重试；重跑不得覆盖无关角色产物。 | 不把“再跑一次”当幂等证明。 |
| Dagster assets / asset checks | 资产物化与资产检查是相关但不同的概念，检查可独立表达质量结果。[cite:6][cite:7] | `physical_assets` 与 `asset_checks` 分开；只有物化且关键检查通过的资产才能提升能力。 | 不把“检查函数存在”写成“检查已接入”。 |
| OpenLineage / Marquez | 运行、作业、数据集和 facets 可记录输入、输出与执行血缘；血缘模型本身不替代质量执法。[cite:8][cite:9][cite:10] | 在 manifest 中保存 run、input、output、query、code/version、error 与 fetch 血缘，报告读取同一记录。 | 不先部署完整血缘平台；不认为记录血缘会自动阻止坏数据。 |
| Vega-Lite spec / stack | 图形规范应显式描述数据与编码；堆叠的含义依赖可相加切片与总体关系。[cite:11][cite:12] | 图合同保存数据、query、关系和编码；Top-N 不构成总体时必须补 Other 或改图。 | 不用图型名称替代数据关系校验。 |
| ECharts pie / ARIA、Observable accessibility | 饼图用于部分—整体表达；可访问性要求文本替代与不只依赖颜色。[cite:13][cite:14][cite:15] | donut 使用独立 total/rest；保留标签、单位、来源和可读文本，图失败时给明确状态。 | 不用视觉美观掩盖分母错误或空图。 |
| robots、HTTP 条件请求/缓存/429 | robots 是爬虫协议而非完整授权；条件请求、缓存和 429/Retry-After 是降低无效请求与拥塞的重要机制。[cite:16][cite:17][cite:18][cite:19] | 合规审核同时覆盖条款、许可、署名、个人信息、频控、留存和撤销；复用快照并尊重服务端信号。 | 不把 robots 允许解释为可任意采集、转载或对外分发。 |
| Scrapy 设置与 AutoThrottle | 爬虫框架把 robots、并发、下载延迟和自动限速作为运行配置，而非报告尾部的说明。[cite:20][cite:21] | 合规和频控必须在 preview/quality/run 前及 fetch 层生效；一次抓取复用优于重复请求。 | 不为了合规名义额外引入 Scrapy。 |
| Zyte 合规实践、Google SRE overload | 社区/工程实践强调来源审查、控制请求压力、退避与过载保护。[cite:24][cite:22] | 作为频控、退避、失败预算和人工复核的辅助经验。 | 不把厂商文章当法律意见或普适数值标准。 |

---

## 5. 目标契约与分阶段修复

### 5.1 全链不变量

1. **存在不等于有效**：只有本次输入、合同、校验和指纹匹配的产物才可复用。
2. **定义不等于数据**：表结构、预期行数、实采行数、通过校验行数必须分开。
3. **降级不等于成功**：可以交付 partial/degraded，但不得保留原计划能力级别或关键事实的确定语气。
4. **血缘不等于执法**：manifest 负责记录，门禁负责阻断；二者都需要。
5. **一个运行一个快照**：同一运行中的 preview、quality、mart 和 chart 应引用可追踪的同一输入版本。
6. **角色范围不可越界**：补一张卡不能重写其他角色已经验收的卡。
7. **图数不是目标**：问题覆盖、数据关系、可复核性和可读性才是目标。

### 5.2 WP0：先冻结契约与反例测试

**要改**

- 在现有测试中先补反例：claims 存在但输入已变、半份 v3 产物、部分角色缺卡、只有表定义无物理行、YAML 解析失败、preview/quality 绕过校验、donut 分母、scatter 标签、渲染失败。
- 明确统一状态：`planned / running / materialized / verified / degraded / blocked / failed`；图另有 `ok / empty / invalid / render_error / deduplicated`。
- 明确 manifest 最小字段：run_id、contract_version、input_hash、code_version、role_scope、fetch_snapshot、physical_assets、actual_rows、checks、lineage、degradations、errors。

**退出条件**

- 旧行为会被哪些测试固定已经列清；特别是 `test_bridge_skips_when_all_roles_have_claims` 与 `test_gates_pass_without_actual_rows` 不再被误当作永久合理契约。
- 每个 P0 问题至少有一个会失败的反例，再开始改实现。

### 5.3 WP1：修桥接有效性与原子交接

**要改**

- `_bridge_cells_to_claims()` 先评估本次输入与有效产物，再决定 v3→v2→v1；提前 skip 必须给出命中指纹与校验证据。
- `from_collection()` / `from_drill()` 接收明确 role scope；目标角色之外只读。
- v3 全程写本次临时区，所有资产、claims 与检查完成后原子发布；失败临时区有状态但不被 v2/v1 自动发现。
- 异常按配置、采集、合同、转换、写入、校验分类；不得统一吞成 `skipped`。

**退出条件**

- 输入变化而旧 claims 仍存在时，不会误跳过。
- 只补一个角色时，其他角色 claims 的内容与哈希不变。
- 在 drill、mart、claims 任一阶段注入失败，下一次运行都不能读取半份产物。
- 重跑同一输入产生相同逻辑产物，或明确说明哪些时间戳字段允许变化。

### 5.4 WP2：接实际资产、能力级别与数据门禁

**要改**

- 合并阶段通过独立资产清单交接，不直接把 claims 的 `datasets` 列表提升成实际行。
- `supply_plan` 只根据通过校验的物理资产计算 actual level；无行定义最高只能证明“有结构”，不能证明 L2。
- 将 `dataset_gates` 接到资产发布和报告能力声明之前；`unverified` 与 `passed` 分开。
- 对声明 L2、数据切片和图查询设置硬要求：资产存在、actual_rows 已知、最小行数通过、grain/query 合法。

**退出条件**

- “只有 dataset 定义、0 行物理数据”的反例不会得到 L2。
- 桥内某一 mart 资产的行数，与合并稿、manifest、capability 中的行数来自同一资产记录，不多头计算。
- 未提供 actual_rows 时，可以显式交付 L1/degraded，但不得作为已验证 L2 PASS。

### 5.5 WP3：格网语义与双覆盖率

**要改**

- 数据格描述“哪个度量、哪个 grain、哪个实体、哪段时期”；论点格描述“要证明什么、引用哪些数据格”，两者不共用交付分母。
- 按 D1 对 entity/grain 做重拆；不能可靠映射者写 `unavailable + reason + tried + recovery_condition`。
- 双覆盖率建议定义：

```text
格子交付率 = 有合法值与证据的数据格数 / 计划内有效数据格数
可画切片率 = 通过行数、query 与图合同校验的去重切片数 / 计划内可画切片数
```

- `unavailable` 保留在分母与缺口清单，不补零、不从计划中悄悄删除；若计划本身修订，必须更换计划版本。
- 去重在冻结的计划切片键上进行；同一证据支持多个论点时可以复用图，但要保留所有问题到图的映射。

**退出条件**

- 所有已填数据格的 entity 都能映射到 grain，不能映射者均有 unavailable 原因。
- 论点格数量变化不改变格子交付率分母。
- 去重减图前后，问题覆盖率不下降；每个原计划问题仍能定位到图、表、文字或明确缺口。
- 两个覆盖率可从同一 manifest 独立复算。

### 5.6 WP4：图表契约、渲染状态与血缘

**要改**

- 修 `compat.py` 的 stacked_bar/scatter/donut 映射与 `spec.py` 的 donut 分母；为图型不支持、空数据、非法负值或非法构成分别返回明确状态。
- 构成图必须满足：同口径总体、切片互斥、total 独立、rest/Other 可复算；Top-N 无 Other 时不得用 donut 表示整体。
- `_render_svg()` 与 `report_flow.render()` 共用图状态；关键图 render_error/invalid 阻断交付，支持性图可 degraded，但记录 from/to/reason。
- 图注与 manifest 记录 dataset_id、query、rows_hash、run_id、source/fetch 快照；表格回退必须标“图未交付”，不能记为图成功。
- 只按 D3 删除重复、空信息或关系不成立的图，不做全自动关键词换图。

**退出条件**

- 每张已交付图都能从图注回到实际数据行和查询，而不只回到 refs 文本。
- stacked_bar、scatter、donut 的回归反例通过；donut 各项与 rest 之和等于 total。
- 任一重要图发生 pro 与 legacy 同时失败时，状态可观测，交付策略符合图的重要级别。
- 图数变化不改变问题覆盖，不作为独立 KPI。

### 5.7 WP5：采集合规前置与单快照复用

**要改**

- `validate()`、`preview()`、`quality()`、`run()` 共用 fail-closed 前置门；任何直接函数调用与 CLI 调用都不能绕过。
- YAML 不存在、读取失败、解析失败、schema 不合法、compliance 未通过分别处理，禁止统一返回 `{}` 后继续。
- 合规审核包含公开性、robots、条款、许可/署名、个人信息、频控、留存、分发范围、复核时间与撤销处理；robots 只是其中一项。
- 同一 run/source 只抓取一次，preview/quality/run 复用不可变快照；条件请求、缓存、429 与 Retry-After 在 fetch 层统一处理。
- 授权或条款撤销时，能按血缘定位受影响 staging/mart/claims/chart/report，并执行失效、删除或重建策略。

**退出条件**

- 缺合规证据、配置损坏、robots 不允许、条款未审核或发现个人信息时，三个入口均拒绝执行并给出不同错误。
- 同一快照下 preview + quality 只产生一次源请求，二者引用同一 fetch_id。
- 每行 mart 可回溯到原始 URL、抓取时间、内容哈希、quote、合规审核版本。
- 撤销一个源时，可列出全部下游资产与报告，而不是只停止下一次抓取。

---

## 6. 协同性与二阶 / 三阶影响

### 6.1 对现有协同方式的影响

| 变化 | 直接协同影响 | 必须同步的治理规则 |
|---|---|---|
| 有效性替代文件存在 | R18/采集执行者不能再以“文件已交”作为完成；R04 要审本次 run 与指纹。 | 完成定义改为“产物有效 + 校验通过 + 血缘完整”；生产者不能自签最终 PASS。 |
| 原子运行与角色范围 | 补卡、重跑、并行角色写入的边界更清楚，但需统一 run_id 和锁/发布规则。 | 一个 run 一个输入快照；每个角色只写自己的临时区，发布由主链执行。 |
| 实际资产能力统计 | R01 报告口径只能读 R04/门禁认可的实际级别，不能按计划 L2 写成实际 L2。 | 计划级别、实际级别、degraded_from、recovery_condition 同页呈现。 |
| 双覆盖率 | 拆卡者、采集者、报告作者和评审使用两种不同指标，不能再用一个“覆盖率”含混沟通。 | 每项指标带定义、计划版本、分子分母和缺口清单；论点覆盖另列映射。 |
| 图表血缘与去重 | 内容角色可复用同一图回答多个问题，但必须保留问题映射；R04 审图时同时审数据关系。 | 图不是节次装饰；删图必须给 dedup 原因与保留图 ID。 |
| 合规同门与撤销 | R03 的审核从上线前一次性动作变成带版本、复核和下游失效的持续流程。 | 无证据默认拒绝；合规变更会触发资产和报告影响分析。 |

### 6.2 二阶 / 三阶后果

| 一阶修复 | 二阶影响 | 三阶影响与应对 |
|---|---|---|
| 严格有效性、原子性和门禁 | 过去“成功”的项目会变成 partial/degraded，短期通过率下降、返工增多。 | 不能用过长期豁免架空门禁；按“关键事实失败 / 非关键增强缺失”分级，记录真实交付趋势。 |
| run_id、快照和 manifest 增多 | 存储、迁移、调试和清理成本增加，旧项目需要适配器或显式 legacy 标识。 | 采用 Expand-Contract：先双写清单、再切换读取、最后停止旧路径；不得虚构已存在的回滚开关。 |
| 角色范围限定 | 重跑更可控，但全量刷新必须显式发起，不能借补卡顺手覆盖。 | 权限与发布策略要区分“单角色重跑”和“全角色重建”。 |
| 表定义与物理资产分离 | 缓存键、能力统计、供给方案和报告字段都要改，不能只改 `_rows_of()`。 | 建立字段迁移与版本校验，防止旧清单把表数量误作行数。 |
| 双覆盖率与格网拆分 | 计划、缓存、去重键、报表和看板口径都会变化。 | 所有统计引用同一计划版本；历史项目保留旧口径快照，不做无说明横向比较。 |
| 图状态细分与去重 | 图数可能下降，部分节次只剩表格或文字，视觉上“变薄”。 | 以问题覆盖和有效切片替代图数 KPI；支持性内容可显式降级，关键图失败仍阻断。 |
| 一次抓取复用 | 请求与费用下降，快照一致性提高；同时需要快照留存、容量和访问控制。 | 快照中的敏感内容同样受合规与撤销约束，不能因“缓存”绕过删除和分发限制。 |
| 合规证据版本化 | 上线变慢，逐源审核工作量增加；源条款变化会导致旧资产需要复核。 | 保存 reviewed_at/review_due/terms_version；撤销可沿血缘使 mart、claims、图和报告失效。 |
| 显式降级成为常态 | 用户能看到更多“未答”“不可画”，不再获得表面完整报告。 | 报告应把缺口转成补采条件与决策影响，不能用形容词或猜测补满。 |

---

## 7. 最强反对意见与取舍

**反对意见：完全禁止 fallback 会让系统过于脆弱，一张非关键图失败就阻断整份报告，反而降低可用性。**

该意见成立，因此本方案不是“禁止一切降级”，而是：

- 关键事实、数据合同、角色越权、合规失败、能力虚报：必须阻断。
- 非关键图、可选增强、部分非核心切片：允许显式降级为表格、文字或缺失说明。
- 任何降级必须保存 `from / to / reason / affected_claims / actual_level / recovery_condition`。
- 表格回退只保证内容可读，不等于图交付成功；降级后的结论语气也必须随证据强度下降。

**另一个反对意见：统一契约可能变成过度设计。**

因此只统一现有路径交接所需的最小 manifest 和状态，不新建完整数据平台、不重复实现 fulfil 引擎、不统一全部渲染器、不引入外部重型服务。

---

## 8. 未来实施的文件同步矩阵

下表是**未来改码时的影响清单**，不是本轮已改文件清单。每行必须实现、接线、测试和文档同步，不得只改函数。

| 主题 | 实现/接线 | 必改或补反例的现有测试 | 文档/其他同步 |
|---|---|---|---|
| 桥接有效性、角色范围、原子发布 | `core/dispatch.py`、`core/cells_claims.py` | `tests/test_cells_claims.py`；必要时补 dispatch 集成用例 | 本文、MASTER；旧 DATA-LAYER/SYSTEM v3 的状态描述 |
| 实际资产与能力级别 | `core/dispatch.py`、`core/supply_plan.py`、`core/dataset_gates.py`、现有 dataset/drill 模块 | `tests/test_supply_plan.py`、`tests/test_dataset_layer.py` | `docs/COORDINATION-SOP.md` 的 L1/L2 口径、报告口径节规则 |
| collection 共用前置门、YAML 错误 | `core/collection_spec.py`、相关 collector 接口 | `tests/test_derivation.py`、`tests/test_collection_contract.py`、`tests/test_card_probe.py` | `docs/COLLECTION-COMPLIANCE.md`、`docs/COLLECTION-SOP.md`、模板字段说明 |
| 单快照 preview/quality/run | `core/card_probe.py`、`core/collection_spec.py`、fetch/collector 实现 | `tests/test_derivation.py`、`tests/test_card_probe.py`；增加请求次数与 fetch_id 断言 | 合规留痕、频控、留存与撤销规则 |
| 格网与双覆盖率 | `core/card_issue.py`、`core/cell_claim.py`、现有 coverage/grid 模块 | 对应 card/cell/coverage 测试；增加论点格、unavailable、同计划版本反例 | MASTER 的 D1/D2、项目口径页；不得沿用固定格数作为通用门槛 |
| 图型映射与 donut | `core/report_theme/charts_pro/compat.py`、`core/report_theme/charts_pro/spec.py` | `tests/test_chart_contract.py`、`tests/test_report_contract_v4.py` 及相关渲染测试 | `docs/CHART-UPGRADE-SOP.md`、图表可访问性说明 |
| 图状态、阻断与血缘 | `core/report_flow.py`、`core/report_theme/pages.py`、`core/dataset_query.py` | `tests/test_report_flow.py`、`tests/test_flow_renderer.py`、`tests/test_report_contract_v4.py` | MASTER 的 D3、`REPORT-STANDARD.md` 的图成功定义 |
| 合规 schema 与证据版本 | `core/collection_spec.py`、`configs/collections/_template.yaml`（未来实施时） | collection/derivation 测试 | COLLECTION-COMPLIANCE；真实源逐源规格，不得 blanket claim |
| 文档权威与历史分册 | 无业务代码 | 文档链接/引用检查（若已有） | `docs/README.md`、MASTER、本文；旧分册标历史或限定范围 |
| 活跃技能镜像 | 通常无需改同步器；使用 `scripts/sync_trae_skill.py` | `python scripts/sync_trae_skill.py --check` | 经授权后同步到 `~/.trae-cn/skills/wawaguagua-agents`，不能假定 D 盘保存即镜像更新 |

### 8.1 已明确的测试契约改写点

- `tests/test_cells_claims.py::test_bridge_skips_when_all_roles_have_claims`：当前固定了“所有角色有卡即 skip”的旧行为；未来必须改成“只有指纹和校验匹配才 skip”。
- `tests/test_dataset_layer.py::test_gates_pass_without_actual_rows`：当前允许无实采行数仍 PASS；未来需区分普通结构检查与 L2 能力验收，后者不得通过。
- `tests/test_supply_plan.py`：增加“datasets 只有定义、没有物理行”的反例，防止把列表长度当行数。
- `tests/test_derivation.py`：从“preview/quality 分别执行”扩展为“共用前置门、同一快照只 fetch 一次”。

---

## 9. 迁移、回滚与验收纪律

### 9.1 迁移顺序

1. **Contract**：先写 manifest、状态、反例测试，保留旧产物只读适配。
2. **Expand**：新路径双写资产清单和降级记录，不改变旧报告结论。
3. **Verify**：对同一输入比较旧/新 claims、资产行数、图状态和报告能力级别，差异必须可解释。
4. **Switch**：新门禁成为唯一能力来源后，再停止旧路径写入。
5. **Cleanup**：确认无消费者后删除旧字段；不得保留永久双轨和多个“唯一入口”。

### 9.2 回滚原则

- 回滚到已发布、已验证的 manifest/资产版本，不靠手动覆盖半份文件。
- 开关只有在源码有真实消费者、测试覆盖和文档登记后才能写入 SOP。
- 合规拒绝不能通过普通功能开关绕过；发现个人信息或授权撤销时不得为了出报告强制放行。

### 9.3 未来验收命令（本轮不执行）

```bash
python -m pytest tests/test_claims.py tests/test_supply_plan.py tests/test_data_layer.py -q -p no:cacheprovider
python -m pytest tests/test_data_layer.py tests/test_cards.py tests/test_collection.py -q -p no:cacheprovider
python -m pytest tests/test_charts.py tests/test_report_pipeline.py tests/test_report_render.py -q -p no:cacheprovider
python scripts/sync_trae_skill.py --check
```

命令全绿只是必要条件，还需人工核对：

- 同一输入重跑可复现，失败不发布半份产物。
- 角色范围外文件零改动。
- 双覆盖率可由 manifest 复算，问题覆盖不随去重下降。
- 每张图可回溯到实际资产与 query；每个降级都有原因和实际级别。
- 采集三入口均不能绕过合规；一次快照复用有请求次数证据。

---

## 10. 本轮不做清单

1. 不修改业务代码、配置、测试、项目数据或历史报告。
2. 不新增 `core/fulfil.py` 或另一套平行数据引擎。
3. 不引入完整 dbt/Dagster/Airflow/OpenLineage/Scrapy 技术栈。
4. 不做全自动图表选型，不合并渲染器，不以扩图型库替代数据关系修复。
5. 不把某个蔬菜项目的格数、表数、图数、源数或工期写成通用系统指标。
6. 不执行同步器，不声称活跃技能目录已经更新。
7. 不处理甘蓝链成本闭合、Q10 质量列错填等具体数据修复。

---

## Sources

### 官方文档与标准

1. [cite:1] dbt, **Model contracts** — https://docs.getdbt.com/reference/resource-configs/contract
2. [cite:2] dbt, **Build command** — https://docs.getdbt.com/reference/commands/build
3. [cite:3] dbt, **Semantic models** — https://docs.getdbt.com/docs/build/semantic-models
4. [cite:4] dbt, **Validation** — https://docs.getdbt.com/docs/build/validation
5. [cite:5] Apache Airflow, **Best Practices（含 idempotency 等建议）** — https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
6. [cite:6] Dagster, **Defining assets** — https://docs.dagster.io/guides/build/assets/defining-assets
7. [cite:7] Dagster, **Define and execute asset checks** — https://docs.dagster.io/concepts/assets/asset-checks/define-execute-asset-checks
8. [cite:8] OpenLineage, **Object model** — https://openlineage.io/docs/spec/object-model/
9. [cite:9] OpenLineage, **Facets** — https://openlineage.io/docs/guides/facets/
10. [cite:10] Marquez, **Quickstart** — https://marquezproject.ai/docs/quickstart
11. [cite:11] Vega-Lite, **Specification** — https://vega.github.io/vega-lite/docs/spec.html
12. [cite:12] Vega-Lite, **Stack** — https://vega.github.io/vega-lite/docs/stack.html
13. [cite:13] Apache ECharts, **Basic pie chart** — https://apache.github.io/echarts-handbook/en/how-to/chart-types/pie/basic-pie/
14. [cite:14] Apache ECharts, **Best practices: ARIA** — https://apache.github.io/echarts-handbook/en/best-practices/aria/
15. [cite:15] Observable Plot, **Accessibility** — https://observablehq.com/plot/features/accessibility
16. [cite:16] RFC 9309, **Robots Exclusion Protocol** — https://www.rfc-editor.org/rfc/rfc9309.html
17. [cite:17] RFC 9110, **Conditional Requests** — https://www.rfc-editor.org/rfc/rfc9110.html#name-conditional-requests
18. [cite:18] RFC 9111, **HTTP Caching** — https://httpwg.org/specs/rfc9111.html
19. [cite:19] RFC 6585 §4, **429 Too Many Requests** — https://www.rfc-editor.org/rfc/rfc6585.html#section-4
20. [cite:20] Scrapy, **Settings** — https://doc.scrapy.org/en/master/topics/settings.html
21. [cite:21] Scrapy, **AutoThrottle extension** — https://doc.scrapy.org/en/master/topics/autothrottle.html
22. [cite:22] Google SRE Book, **Handling Overload** — https://sre.google/sre-book/handling-overload/
23. [cite:23] 《中华人民共和国个人信息保护法》 — http://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html

### 工程社区 / 厂商实践（补充证据，非法律意见）

24. [cite:24] Zyte, **The science of compliance** — https://dev.zyte.com/blog/the-science-of-compliance/

> 资料用于本轮方法审查；本地问题结论仍以当前源码为准。外部资料中的工具能力不等于本仓库已经接线或验证。
