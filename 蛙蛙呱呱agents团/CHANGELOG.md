# 蛙蛙呱呱专家团 · 智能体更新日志

> 只记录**专家团本体**的变化：入口、编排、拆卡与 brief、报告产线、门禁、项目边界。
> 项目资产（数据、卡、claims、报告成品、eval 结果）不进本仓库；
> 运行临时物（事件流、锁、trace）在 `workspace/`，也不入库。

版本口径：报告产线版本见 `docs/REPORT-LINES.md`；本文件按日期记录“智能体能力”的变化。

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
