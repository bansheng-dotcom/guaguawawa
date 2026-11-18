# 报告产线（REPORT-LINES.md）

> **v10.2 单入口（2026-11-18）**：`report build` 与 `report decide` 现在是**同一个实现**：
> 决策契约（3–5 问）→ 逐问作答 → 图由对照选型 → binding/图/质量门禁。
> **lens 已退役**：`--lens` 保留只为兼容，传了会被忽略并打 deprecation。
> 旧的三环（数据定题 / 答案定考题 / lens 砍方法）在 CLI 路径上已不存在；
> `core/report_compose.py` 的 lens 参数仅内部遗留，下一版删除。
> 单环定义与收口过程见 [`交付/报告质量与图表系统-根因与修复-2026-11-18.md`](../../交付/报告质量与图表系统-根因与修复-2026-11-18.md) §八·补三。

> **P5 已收敛（2026-11-17）**：22 个业务纲领 → **1 个 `analysis` + `lens`**；
> `run / pack / produce / research` 已删除，统一入口是 **`python guagua.py report build`**；
> `core/frames.py` / `core/frames_cheese.py` 已删除，只留 `frames_framework.py`。
> 以下内容是收敛前的历史地图，保留作对照；新写法见 `docs/REPORT-DECISION-GRADE.md` 与 `交付/报告产线P5-Gate-2026-11-17.md`。
>
> **升级冻结（2026-11-17 起）**：本文件描述的 22 纲领 / 3 走法 / 2 分支进入改造期，
> 执行计划见 [`报告产线升级SOP-2026-11-17.md`](../../交付/报告产线升级SOP-2026-11-17.md)。
> 升级期间**不得新增** thesis / frame / 入口；新能力先进 `core/report_framework.py` 的维度库，
> 等 P4 统一后再放开。
>
> 2026-11-15 收敛结果：**12 条产线 → 1 条产线、2 个分支、1 份报告**。
> 本文是产线的唯一地图；写报告的标准见 `REPORT-STANDARD.md`，
> 接入方式见 `REPORT-BRIDGE-GUIDE.md`。

---

## 一、唯一产线

```
意图
  │
R01 s01（意图识别）→ s02（路由 / 拆卡 / 波次）
  │
  ├─ 分支 A：单角色 ──────────────┐
  └─ 分支 B：跨角色（≥2 角色）────┤
                                   │
              执行角色只跑技能 → result.json（role_runtime.emit）
                                   │
                      R01 s09 解读（带数字的判断）
                                   │
        core/report_flow.py → core/report_bridge.py → core/report_renderer.py
                                   │
                     一份报告：HTML + MD + manifest（署名 R01）
```

入口命令（以本表为准）：

| 命令 | 作用 |
|---|---|
| `python guagua.py report produce --intent … --dir … --out …` | **主线**：数据台 → 方法库 → 纲领 → 章节稿 → 报告 |
| `python guagua.py report produce --profile … --dir … --out …` | v3 兼容入口：章节计划 → 技能调度 → 证据图 → 评测 |
| `python guagua.py report run --intent … --results … --out …` | 出一份报告（A/B 分支） |
| `python guagua.py report pack --dir … --out …` | 证据打包 → 可寻址数字索引 + 写作简报 |
| `python guagua.py report run --evidence pack.json --draft sections.json --out …` | 调研级：章节稿逐节过账后出一份报告 |
| `python guagua.py report check --html …` | 验一份成品（CI 同款） |
| `python guagua.py report charts` | 48 型图表能力盘点 |

### 开工前契约（`produce --intent`）

动笔前先立契约，落在 `out/report_ship.json`（判定规则见 `core/report_kernel/contract.py`）：

```
给谁看 audience / 支持哪个决定 decision / 必答 3—5 问 questions
数据截止 data_cutoff / 档位 target_level / 签字 owner-reviewer
+ 实算字段：来源数、期数、时间跨度、是否跨市、期次是否对齐
```

`--require-contract` 时契约不成立就中止、不出报告；不带该参数只记录不拦截，
结果写进 `manifest.json`、`analysis_trace.json` 与命令返回值。

注意：`out/contract.json` 是**渲染契约**（report_flow 写），与 `report_ship.json` 语义不同，不要混用。

### v3：技能编排（2026-11 新增）

```
profile → section_plan.json（每节声明要跑哪个角色的哪个技能）
        → skill_trace.json（并行跑技能，带 input_hash / 缺口）
        → claims.json（claim ← computation ← observation；跨来源冲突单列）
        → draft（模型写，或按 claim 自动编排）
        → report_flow 逐节过账 → report.html
        → judge.json（rubric 100 分制，低于基线不交付）
```

实测：`market_research` 画像在家居百货数据上跑了 **5 个技能 / 2 个角色 / 25 个 claim**，
其中 `r05.sizing.sensitivity` 因输入缺 drivers 未产出，报告按「缺口」处理而不是补文字。

---

## 二、两个分支的差别

| | 分支 A | 分支 B |
|---|---|---|
| 触发 | 路由只命中 1 个角色 | 路由 ≥2 角色，或实际收到 ≥2 份 result |
| 任务卡 | 1 张 | N 张（带依赖与波次） |
| 报告 | 1 份，署名 R01 | 1 份，署名 R01 |
| 交叉验证 | 无第二来源，报告里显式写明 | 同一指标跨来源冲突会进结论 |
| 代码 | `core/report_flow.route()` → `"A"` | 同函数 → `"B"`；以 `--results` 里实际 role 为准 |

两条分支共用：收集器 `collect()`、解读 `s09_interpret`、契约
`build_contract()`、渲染 `report_bridge.render_html`、门禁 `check_report_flow.py`。

---

## 三、被删除的 11 条产线

| 旧产线 | 去向 |
|---|---|
| `report one`（core L1 单角色） | 删除；角色改为只交 result |
| `--path single`（REP-001 五段式） | 删除 |
| `r03/r06/r07 deep`（深度稿） | 删除；CLI 保留下线提示 |
| `report project`（项目级单份） | 删除 |
| `report build/audit/seal/diff`（L1→L2→L3） | 删除 |
| `report analysis`（Q/A/E/R/D 包） | 删除 |
| `report modules / write / blueprint` | 删除 |
| 20 角色批量脚本 ×3 套 | 删除 |
| 真实数据专项脚本 ×10 | 删除 |
| 角色交付包 `build_rNN_*_pack/proof` ×18 | 删除 |
| `run_heavy_*` 手写 HTML、`enhanced_report_renderer` | 删除 |

连带删除：`report_specs/`（20 份角色 spec + frame + writing + archetypes）、
`core/report_pipeline|project|analysis|modules|writer|blueprint|corpus_analysis`、
`shared/report_engine|report_generator|report_writer|kernel_report_adapter|business_frame`、
`core/report_kernel/{spec,layers,aggregate,guard}`、角色侧 `report_contract.py`、
7 类报告门禁脚本（合并为 `check_report_flow.py`）、21 份历史 SOP 文档。

归档说明：收敛时的 77 个代码文件与 21 份文档**未随本仓提供**
（`workspace/_archive/` 已不存在，2026-11-17 体检确认）。需要恢复时从 git 历史
（2026-11-15 前后的提交）取，不要再引用 tar.gz 路径。

---

## 四、保留的零件（不是产线）

| 模块 | 职责 |
|---|---|
| `core/report_renderer.py` | 唯一渲染器：contract → HTML（48 型图 + 8 套主题） |
| `core/report_bridge.py` | 渲染薄层：`render_html / write_markdown / render_pdf` |
| `core/report_kernel/structure.py` | 版式四规则 + 写作四判据（被门禁复用） |
| `core/charts/`（含 `v2/`） | 图表引擎，v2 默认、v1 兜底，48/48 |
| `core/report_flow.py` | 产线本体：路由 / 收集 / 解读 / 契约 / 渲染 / manifest |
| `r01-.../skills/s09_interpret.py` | 解读技能：result → 带数字的判断 |

---

## 五、验收

```bash
python scripts/ci_report_checks.py       # [1] 角色入口 [2] A [3] B [3b] manifest [4] 无第二引擎 [5] 图型
python scripts/check_report_flow.py --dir <输出目录>
python guagua.py report check --html <report.html>
```

判据（任一不过即 FAIL）：F1 版式四规则、F2 标题带数字、F3 结论段带数字、
F4 每节带数字、F5 边界节、F6 末节口径与分数、F7 图有来源、F8 无 JSON 回显、
F9 重复句 ≤10% + 数字密度 ≥25/千字 + 禁用词 0。

---

## 六、历史文档

删除的 21 份 SOP（V3 产线、L3 升级、A+B Plus、fused、咨询级、业务报告 v1—v3 等）
已打包在 `workspace/_archive/report-docs-2026-11-15.tar.gz`。
仍然有效的文档：`REPORT-STANDARD.md`、`REPORT-BRIDGE-GUIDE.md`、本文件、
`docs/SOP_CHART_ENGINE_V2_UPGRADE.md`、`docs/CHART_CRAFT_STUDY.md`。

---

## 七、v7 论证链（2026-11-15）

v7 不新增产线，只给唯一产线加两层：**论证层**（`core/claims.py`）与
**问题链帧**（`core/frames.py`），并加一条**深度门禁**（`core/report_quality.py`）。
详细说明见 `docs/REPORT-LINE-V7.md`。

| 新增模块 | 职责 |
|---|---|
| `core/fact_table.py` | 把 `data/obs_*.json / facts.json / derived_metrics.json` 归一成带来源的事实表 |
| `core/claims.py` | 一条判断 = 观察 + 对照 + 机理 + 落点 + 证伪；机理按 kind 生成 |
| `core/methods/market.py` | 区域消费市场 11 个方法（规模/需求/大盘/结构/量价/渠道/区域/供给/补贴/口径/缺口） |
| `core/frames.py` | 经营 / 链路 / 整改三套问题链（章节结构不同，不是同一模板换序） |
| `core/report_quality.py` | 反模板门禁：对照率、落点率、本节边界覆盖、跨节复读、深度下限、跨报告骨架比对 |

新增命令：

```bash
python guagua.py report produce --intent "内蒙古家居百货市场调研" --dir <项目> --out <目录>
python -m core.report_quality <report.html>              # 单份深度门禁
python -m core.report_quality --compare a.html b.html    # 两份是不是同一个模板
```

每份 v7 报告额外产出 `quality.json`；`manifest.json` 的 `ok` 同时受
九条门禁、逐节过账、R04 清点、深度门禁四方约束。
