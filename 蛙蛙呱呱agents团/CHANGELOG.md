# 蛙蛙呱呱专家团 · 智能体更新日志

> 只记录**专家团本体**的变化：入口、编排、拆卡与 brief、报告产线、门禁、项目边界。
> 项目资产（数据、卡、claims、报告成品、eval 结果）不进本仓库；
> 运行临时物（事件流、锁、trace）在 `workspace/`，也不入库。

版本口径：报告产线版本见 `docs/REPORT-LINES.md`；本文件按日期记录“智能体能力”的变化。

---

## 2026-11-25（第五轮）· ECharts 交互后端 + cells_claims 三套收敛

一句话：**图能交互了，但离线/PDF 仍有静态兜底；同一格不再出三个数。**

### ECharts 交互后端（P5-4，可选）

| 能力 | 位置 | 说明 |
|---|---|---|
| 交互后端 | `charts_pro/interactive.py` | hbar/vbar/line/area/pie/donut/scatter/heatmap/funnel/treemap 等映射为 ECharts option；tooltip、图例开关、类别多时 dataZoom、热力 visualMap |
| 开关 | `GUAGUA_CHART_BACKEND=echarts` | 默认仍走静态 SVG；**零破坏** |
| 兜底 | 同上 | 每张图内嵌静态 SVG fallback，JS 未执行（PDF/断网/打印）时读者仍看到原图；不支持的类型直接回退 SVG |
| 依赖边界 | CDN `echarts@5` | 核心链路仍不 import 任何第三方包；只有浏览器端加载 |

### cells_claims 三套收敛（P5-5）

| 能力 | 位置 | 说明 |
|---|---|---|
| 统一读数 | `core/cells_unified.py` | `observations()` 优先 `out/raw.json`，其次 `plan/mart.json`，按 (measure, entity, period) 归一 |
| 双写对账 | 同上 `compare()` | v1 已填格子 vs 统一读数逐键比对，写 `out/cells_claims_diff.json` |
| 切换 | `cells_claims.build(unified=True)` | 数字改读统一读数，标 `value_from=observation`；与格子值不一致的标 `needs_human`，不静默改数 |
| CLI | `scripts/cells_diff.py --project` | 对账入口，差异非 0 退出 1 |

### 门禁

`pytest 618 passed / 3 skipped`；`check_business_terms` 0/0/0；
`check_charts_pro` contract OK + tokens OK；`check_chart_edges` 8/8；
`check_project_boundary` PASS；`check_convergence` 违规 0；`guagua.py audit` 15/15。

---

## 2026-11-25（第四轮）· 业务词清零 + Layout 全量接管 + 两个缺口补齐

一句话：**核心代码里不再有任何行业口径词；70 型图在渲染前走同一层 Layout。**

### 业务词清零（P1-7 收尾）

| 改动 | 位置 | 说明 |
|---|---|---|
| 中性术语替换 | `core/` `shared/` `scripts/` | 终端/集散/上游/网点/面积效率/单品 取代行业口径词；23 个文件 |
| 研究类方法去业务化 | `core/methods/research.py` | 指标 id 全部改 `metric_roles` 映射（项目 `method_params.yaml`）；无角色**不挂载**，不退回业务线默认 |
| 渠道词项目化 | `core/analysis_desk.py` + `method_params.channel_hints` | 团内只留中性默认词；项目自己的列名口径写在项目配置 |
| 门禁收紧 | `scripts/check_business_terms.py` | 三层全部要求 **0**；`configs/industries/*` 作为显式行业库豁免 warn |

### Layout 层接管 70 型（P4-3）

- 新增 `charts_pro/layout.py`：`prepare()` 在 `render()` 入口统一处理
  空态（70 型一致的「无数据」卡）、值域（含 0 + 5% padding）、nice 刻度、decimals、标签像素。
- `spec.render()` 先过 Layout 再校验/渲染；渲染函数可读 `spec["_layout"]`，不改绘图数学。
- 新增 `tests/test_chart_layout.py`：70/70 有 layout、70/70 可渲染、≥60 型走统一空态。

### 缺口补齐

| 项 | 位置 | 说明 |
|---|---|---|
| P2-5 `collect schema` | `core/collect_schema.py` + `guagua.py collect` | 抓一页 → 推断 JSON/表格结构 → 生成源画像 + 采集规格草稿 → 试采 20 行过质量门；产物只写项目侧 |
| P3-4 quote 判据合并 | `core/research_intake.py` | `verify()` 降级为 URL 可达性预检（`reachability.json`）；quote 命中**只**由 `source_verify` 判定；门禁支持项目 `raw/` 离线缓存 |

### 门禁

`pytest 607 passed / 3 skipped`；`check_business_terms` **0/0/0**；
`check_charts_pro` contract OK + tokens OK；`check_chart_edges` 8/8；
`check_project_boundary` PASS；`check_convergence` 违规 0（删除旧基线文件后）；
`guagua.py audit` 15/15。

---

## 2026-11-25（第三轮）· 数据标准 + 采集六层 + 业务词出团

一句话：**给全链路一条数据标准，把行业口径搬出核心模块。**

### 新增（契约与数据标准，P1）

| 能力 | 位置 | 说明 |
|---|---|---|
| 四份数据契约 | `core/data_standard.py` | Record（原始不可变）/ Observation（唯一可比较单元）/ Dataset（含 manifest+dq+profile）/ ChartSpec（数据引用，不内嵌数字）；`Row` 双向适配 |
| 语义层拒绝臆造 | `core/card_upgrade.neutral_semantics` | 缺语义层只给中性占位，**不写盘**；四段（entities/grain/measures/boundaries）缺一不发卡 |
| 两段式接线 | `core/card_issue.prepare_probe_cards` + `merge_grid` | 探源卡 = `bundle.json`（`task_type=探源型`）；语义层指纹不变时网格**合并**，探测结论不被冲掉 |
| 单位显式化 | `core/data_model.normalize_unit` | 返回 `(base, scale, verified)`；coverage 增 `unit_unverified` |
| 冲突裁决 | `core/data_model._arbitrate` | 按来源 grade 取值；同级保留第一条并标 `needs_human`；导出 `out/conflicts.json` |

### 新增（采集现代化，P2/P3）

| 能力 | 位置 | 说明 |
|---|---|---|
| 采集六层 | `core/ingest/` | Policy（robots/rps/timeout/max_bytes/retries）/ Fetcher / Extractor / Validator / Store / Runner |
| staging + DQ | `core/ingest/store.py` | `data/staging/<source>/<batch>/{rows.jsonl,_state.json,dq_report.json}`，统一走 `paths.write_artifact` |
| 失败隔离 | `core/ingest/runner.run_many` | 单源失败不拖垮整批；每个 URL 留 `kind`（robots/http_404/timeout/too_large…） |
| 规格前置校验 | `core/collection_spec._guard` | `preview / quality / run` 先校验；`validate()` 拆 raw/metric（只要数据的规格合法） |

### 新增（选型与主题，P4）

| 能力 | 位置 | 说明 |
|---|---|---|
| 数据驱动选型 | `core/chart_fit.py` | 画像 → 候选图型 + 前置条件 + fallback；空态/常数值拒绝出图 |
| 字段契约同源审计 | `core/chart_field_contract.py` | REQUIRED vs SAMPLE 逐型比对，进 `check_charts_pro`（治 V-1） |
| 表格降级后端 | `core/report_theme/table_backend.py` | 可访问表格 + `fallback_note`（缺什么、改用哪型） |
| 设计 token | `core/report_theme/tokens.py` | 默认值=现状；门禁比对渲染常量，防静默改产出 |

### 变更（业务词隔离，P1-7）

- `core/domain_pack.INDUSTRIES` → `configs/industries/*.yaml`（7 个行业包；项目目录同名覆盖）。
- `analysis_methods`：品类表 / 损耗 / 物流成本 / 价格单位全部来自项目 `method_params.yaml`；
  缺参数走中性默认并写脚注，**不再用某条业务线的默认值顶上**。
- `analysis_desk`：单位换算参数化；渠道词去掉具体市场名与品类名。
- 新增 `scripts/check_business_terms.py`（三层词表：project_block / line_block / warn 棘轮），
  接入 `ci_report_checks` 的 `[0c]`；`configs/business_terms_warn_baseline.json` 冻结既有 warn 债。
- `shared/knowledge/brief.py`：新增任务类型 `探源型`（L0/L1/L2）。

### 门禁

`pytest 589 passed / 3 skipped`；`check_business_terms` project_block 0 / line_block 0；
`check_charts_pro` contract OK + tokens OK；`check_chart_edges` 8/8；`check_project_boundary` PASS；
`check_convergence` 违规 0。

### 未做（需拍板或另开一轮）

- ECharts 交互后端：需第三方 JS，破坏"核心链路零第三方依赖"。
- `cells_claims` 三套收敛：需要双写比对期，爆炸半径大。
- `core/methods/research.py` 的乳业/区域 metric id 迁项目方法包（不在 block 词表内）。

---

## 2026-11-25（第二轮）· 图型止血 + 边界门禁加固

一句话：**先让图不撒谎，再让边界查得出来。**

### 修复（作图边界，P0）

| 问题 | 位置 | 修法 |
|---|---|---|
| 空数据崩 `max() arg is empty` | `charts_pro/spec.py` `_hbar`、`spec_families.py` `_vbar` | 返回"无数据"说明卡（`prokit_helpers.empty_chart`） |
| 单点/全零崩 `ZeroDivisionError` | `prokit_helpers.sx/sy` | 零域映射到画布中线；`line`/`pie` 单点与全零不再除零 |
| 全负值条形向右、轴向反转 | `_hbar` | 0 基线居中，负值向左；轴域含 0 并取整 |
| 热力图负值与 0 同色 | `_heatmap` + `prokit_helpers.blend` | 新增 `diverging()`（负蓝 / 0 白 / 正红），`_heatmap` 改用它 |
| 18 字中文标签压到条上 | `_hbar` / `_vbar` / `_heatmap` | 新增 `text_width` / `fit_text`，超宽换 2 行、仍超加省略号 |
| 数值格式混用（`364824.0`） | 同上 | 新增 `fmt_num()`：整数不带 `.0`，小数去尾零 |
| 饼/环/华夫全零崩 | `_pie` / `_donut` / `_waffle` / `_rose` | 空态或 0 总额守卫 |

### 新增

| 能力 | 位置 | 说明 |
|---|---|---|
| 图型边界门禁 | `scripts/check_chart_edges.py` | 8 例：空态/零域/负值方向/发散色阶/长标签/200 项；已接入 `ci_report_checks` 的 `[18b]` |
| 产物落盘唯一入口 | `core/paths.write_artifact()` | 解析路径 → 过守卫 → 建父目录；`data_model.export` 已改走它 |
| 边界允许清单 | `boundary_allowlist.yaml` | 登记"团队自身证据"（r01/r04/r05 的演进留证、`交付/generic_semantics_v1.yaml`），每条写 kind/note/since |

### 变更

- `scripts/check_project_boundary.py`：**任意层级**匹配过程目录（新增 `workspace/out/plan/coverage/data/artifacts`），
  并对命中项标注**是否已提交**（gitignore 对已跟踪文件无效）；读取 `boundary_allowlist.yaml`。
- `.gitignore`：补 `*/tests/workspace/`、`*/_test_*/`，并注明由边界门禁兜底。

### 清理（运行残留，均未入库）

`workspace/`（含 5 个 `_test_*`）、`pipelines/out/`、`r10-wachengmei-design/workspace/`、
`r04-watiaoci-reviewer/tests/workspace/`、`r05-washenyuan-research/tests/workspace/`，共 83 个文件。

**根因修复**：`tests/test_card_default_gate.py`、`tests/test_user_in_the_loop.py` 用的是相对路径
`Path("workspace/_test_*")`，跑测试就落在团内——这正是残留反复出现的源头。
已改为系统临时目录（`tempfile.gettempdir()`），跑完不再在团内留任何东西。

> 保留不动：`r01/r04/r05` 的 `artifacts/` 是已登记的方法演进留证（含 SHA256 清单），
> 不按项目资产处理，但已纳入 allowlist 可审计。

### 门禁结果

`pytest 547 passed / 3 skipped`；`check_charts_pro`、`check_chart_edges 8/8`、
`check_project_boundary PASS`、`check_convergence 违规 0`、`ci_report_checks ALL PASS`。

### 本轮未做（按方案 P1–P5 排期）

采集六层（Policy/Staging）、四份契约（Record/Observation/Dataset/ChartSpec）、
`normalize` 规则外置、`chart_fit` 选型、Theme token 与 ECharts 后端、`cells_claims` 收敛。

---

## 2026-11-25 · 项目边界落地 + expert_brief v2

一句话：**专家团是工具，项目是资产；工具不带项目走，项目不写进工具。**

### 新增

| 能力 | 位置 | 说明 |
|---|---|---|
| 三个根与写入守卫 | `core/paths.py` | `TEAM_ROOT`（工具）/ `PROJECT_ROOT`（资产）/ `RUNTIME_ROOT`（事件·锁·trace）；写团内抛 `BoundaryError`，CLI 退出码 2 |
| 项目资产根 | `core/project.py` | `Project` / `load` / `init` / `ensure`；10 个标准子目录；`project.yaml` 不覆盖已存在 |
| expert_brief v2 | `shared/knowledge/brief.py` | 七层（决策语境→定义口径→结构分解→机制归因→判断情景→行动可逆→反证不确定）；每条五门槛（answerable_by / evidence / owner / failure_impact / check）；单卡上限 18 条，超出进 `parking_lot` |
| CardBundle 组装 | `core/card_bundle.py` | 卡是信封、brief 是内容；让报告拆卡线在不 import 知识库的前提下拿到 bundle |
| 三道新门禁 | `scripts/check_project_boundary.py`、`check_brief_contract.py`、`check_report_isolation.py` | 依次守：团内无项目资产、brief 契约不回退、报告层不读知识库/brief |
| 新入口 | `guagua.py project init/show`、`guagua.py prompt` | `prompt` 是接入大模型的唯一提示词入口 |

### 变更

- **卡不再写验收明细**：`protocol.Task` 增 `brief_ref` / `brief_version` / `knowledge_scope`；`acceptance` 降为遗留字段，新卡恒为空，验收只由 `brief.acceptance_checks` 派生。
- **拆卡下发 bundle**：`dispatch.write_cards(project=)` 写 `cards/<role>/bundle.json`，brief 落 `<项目>/briefs/<task_id>.yaml`；`TASK.md` 带上 `must_answer` 与验收清单。
- **收卡校验契约**：`dispatch.collect()` 校验 bundle 版本一致、卡无 acceptance，结果进 `merged["brief_contract"]`；报告拆卡线 `report_dispatch.issue()` 把 brief 问题写进 `issued.json.brief_issues`，不静默。
- **任务账本进项目**：`Workspace(root, project=)` 把任务与产物写到 `<项目>/runs/tasks` 与 `<项目>/artifacts`，事件流仍留运行根。
- **R01 拆卡带 brief**：`r01 plan --project` 为每张卡生成 brief，任务日志记录 brief 问题。
- **报告 CLI 加边界**：`report brief/collect/run-line/research/plan-report/clarify/intake/flow` 支持 `--project` 并在写盘前做边界守卫。
- **`chat.py` 标废弃**：`guagua.py chat` 只保留一个版本的兼容壳，下一版本删除。

### 项目迁出

- `蛙蛙呱呱agents团/projects/consulting` → `<仓库根>/projects/consulting`；
  `shared/consulting/workbook.py` 与 README 同步改指团外。
- 仓库根的小码女装/showcase/宣传图等历史项目产物一并移出工具仓库；
  根 `.gitignore` 与团 `.gitignore` 增加项目资产兜底规则。

### 门禁

- `guagua.py audit` 快检 **12 → 15 项**（新增 project-boundary、brief-contract、report-isolation）。
- 新增测试：`tests/test_paths_project.py`、`test_brief_contract.py`、`test_card_bundle_flow.py`。
- 本轮复验：`audit` 15/15 通过；`pytest` 547 passed / 3 skipped；`ci_report_checks` 全通过；生成物与 Trae/DSH 镜像漂移 0。

### 不兼容与迁移

1. 写专家团目录的命令一律被拒（退出码 2）：把 `--out` 改到项目根，或先 `guagua.py project init`。
2. 项目资产写进 `GUAGUA_WORKSPACE`（运行根）也被拒：运行根只放事件/锁/trace。
3. 未带 `--project` 的 `plan` 仍可运行，但会提示迁移；下一版本项目根必填。
4. 老的纯 `TASK.md` 卡仍可收（`--allow-legacy`），但不再享受 brief 契约校验。

### 已知遗留

- M5 知识自举（从证据沉淀知识快照）未做；
- `chat.py` 壳保留一个版本；
- 行业示例夹具的中性化清理分批进行。

---

## 2026-11-24 · 统一入口与报告取数收敛（D+）

- 新增 `guagua.py run` 路由器：默认只打印建议命令，`--execute` 才转发；按 `--role / --dir+--out / --intent` 选单角色、报告线或拆卡线。
- `report run-line --source data|cards`：明确“报告层算”还是“收卡编译”。
- `call --as-task` 只写 `workspace/traces`，产物标 `trace_only`，不混入项目账本。
- 修复 r06 文档与死命令。

## 2026-11-24 · 体检入口与历史归档（P2）

- 新增 `guagua.py audit`（快检 + `--full`）。
- 历史文档归档到 `docs/archive/`；`.gitignore` 补齐运行产物与基线输出。

## 2026-11-24 · 报告线收口（P1 / P0）

- P0：报告线门禁修复，清理生成物，输入显式拒绝缺样本。
- P1：依赖声明、死接线、孤立模块、文档漂移、废弃入口、CI SKIP 标注。
- 报告产线统一到 v14，新增文档一致性门禁。

## 更早

- 数据供给方案 v7.x：先定“能采到什么”，再谈降级；探源交给 R18。
- 降级三层与收卡前探测；证据层（数字+来源）不算无数据。
- 图表选型（relation → chart）与单段字数硬上限进入拆卡契约。

---

维护约定：

1. 每条变更必须能指向文件或命令，不写“优化了体验”这类空话；
2. 改 schema/路径/入口时，同时更新本文件、`AGENTS.md`（由生成器产出）与对应门禁；
3. 门禁结果只写实际跑过的命令与数字，没跑的写“未验证”。
