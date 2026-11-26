# 蛙蛙呱呱专家团 · 智能体更新日志

> 只记录**专家团本体**的变化：入口、编排、拆卡与 brief、报告产线、门禁、项目边界。
> 项目资产（数据、卡、claims、报告成品、eval 结果）不进本仓库；
> 运行临时物（事件流、锁、trace）在 `workspace/`，也不入库。

版本口径：报告产线版本见 `docs/REPORT-LINES.md`；本文件按日期记录“智能体能力”的变化。

---

## 2026-11-26（第十二轮）· P4 第一阶段：core/base 分包

一句话：**先搬地基，五个模块一个包；旧路径全部保留 shim，行为不变。**

| 件 | 落点 | 说明 |
|---|---|---|
| 物理迁移 | `core/base/{paths,workspace,project,registry,protocol}.py` | `git mv`，不改逻辑、不改名 |
| 命名修正 | 包名用 `base` 而非 `platform` | `core/platform/` 会遮蔽标准库 `platform`：r06 把 `core/` 加入 `sys.path` 后，pandas 导入即崩（AttributeError: python_implementation） |
| 兼容层 | 旧 `core/<name>.py` 保留 shim | 全量转发实现模块的 globals（含私有符号），117 处 import 不用改 |
| 根目录修正 | `base/paths.py` · `base/workspace.py` | 文件深了一层，`__file__` 上溯层数 +1，`TEAM_ROOT` / 工作区根仍指向正确位置 |
| 白名单 | `configs/core_files.json` | 重生成：160 → 166（5 实现 + 5 shim + base/\_\_init\_\_） |
| 边界复发修复 | `r01-waquanju-ceo/agent.py` | `dispatch_results.jsonl` 从团内 `workspace/` 改写到 `paths.runtime_root()/artifacts/r01`（该文件无读取方，仅留调试台账） |
| 边界 | `core/base/__init__.py` | 空包，不在 import 时加载子模块，避免循环依赖 |

验收：`pytest` 630 passed / 3 skipped；`ci_report_checks` ALL PASS；`wiring_truth --check` PASS；`check_dead_code --check` PASS；`gen_agent_packs --check` 无漂移；`check_role_packs` 20/20；`guagua.py roles` 正常（20 角色）。

未做：其余 7 个包（data/sources/charts/claims/cards/report/prose）尚未迁移；shim 全部保留，等全部包搬完再单独删。

---

## 2026-11-26（第十一轮）· 断舍离：12 个未接线模块下线（-1,807 行）

一句话：**把「文档里有、测试在测、产线不用」的模块全部删掉，并保留真实需求的替代判据。**

### 归属决策（先处理最大的 512 行）

`claim_card` + `claim_gate` 删除，不接回。依据：

- 它们接的是 `report_compose`，该模块 11-18 已删除；
- 现产线头条是自动生成的「X/Y 个决策问题有证据」覆盖率句，**不存在自由写作头条**，三条规则的适用对象已消失；
- 来源等级仍由 `claim_consistency` C3 检查，证伪/深度仍由 `report_quality` 与 F10/F12 检查；
- 文档 `REPORT-CLAIM-GATE.md` 标 ARCHIVED，不再声称“已接入”。

### 删除清单（12 文件 / 1,807 行）

| 模块 | 行数 | 理由 |
|---|---:|---|
| `analysis_lab` | 557 | 与 `shared/methods` + r06/r19 技能重复，未接任何产线 |
| `claim_card` + `claim_gate` | 512 | 见上 |
| `coverage_cli` + `task_frame` + `task_research` | 263 | 无外部入口；`coverage_plan/confirm/policy` 保留（仍被 dispatch/report_flow/r04_audit 使用） |
| `gate_chain` | 131 | 四层门禁已由 `check_report_flow` F1–F12 取代 |
| `chart_fit` | 96 | `report_flow.chart_fitness_errors` 已有同判据 |
| `evidence_graph` / `argument_plan` / `spec_extract` | 180 | 11-19 的实验层，只有测试引用 |
| `prose_critic` | 68 | `prose_style` + F10/F12 已覆盖 |

### 连带修复

- `core/__init__.py` 分组导出移除 12 个名字；`configs/core_files.json` 172 → 160；
- `scripts/audit_dod.py` 第 8/10 条改查 `report_flow` 与 `check_report_flow`（不再读 `gate_chain.py` 文本）；
- `core/domain_pack.py` 去掉 `python -m core.analysis_lab` 的广告；
- 6 份文档归档或标注：`REPORT-CLAIM-GATE`、`REPORT-COVERAGE-UPGRADE-SOP`、`REPORT-SYSTEM-UPGRADE-SOP`、`REPORT-DECISION-GRADE`、`REPORT-PRODUCTION-LINE-SPEC`、`DOMAIN-EXPERT-LAYER`；
- `CORE-MAP.md` / `REPORT-LINES.md` 删除已下线模块的行；
- `wiring-debt.json` 清空为 `{}`；
- 测试同步删除 43 条（全部只测已删模块）：673 → **630 passed / 3 skipped**；`test_collection` 的 TaskFrame 夹具改为静态结构，`coverage_plan.pre_gate` 仍被覆盖。

### 验收

`pytest` 630 passed / 3 skipped；`ci_report_checks` ALL PASS；`audit_dod` 15/15；`wiring_truth --check` PASS（0 UNWIRED / 0 DOC_DEAD）；`check_dead_code --check` PASS；`check_project_boundary` PASS；`guagua.py check` 20/20；r06 / r19 端到端全绿。

---

## 2026-11-26（第十轮）· 接线真相 + 两类假绿修复（P0/P1）

一句话：**先证明“哪些模块真的在产线上”，再修会让门禁永远 PASS 的两处漏洞。**

| 件 | 落点 | 判据 |
|---|---|---|
| 接线真相表 | `scripts/wiring_truth.py` · `docs/_migration/wiring-truth.md` | AST 真实 import + 从非测试入口回溯可达；输出 LIVE / TEST_ONLY / DOC_ONLY / UNWIRED |
| 债务登记 | `docs/_migration/wiring-debt.json` | 未接线模块必须显式登记理由（接回还是删除）；接线后不删登记 → 门禁报「债务过期」 |
| 文档死链 | 同上 `--check` | 文档里的 `core/X.py`、`python -m core.X` 必须存在；`已删除/不新增` 的历史说明行除外 |
| 隔离门禁修复 | `scripts/check_report_isolation.py` | 扫描范围从 `report_*.py` 扩到 `report*/**/*.py`；文件挪进子包后不再「扫不到 = 永远 PASS」 |
| 隔离证伪测试 | `tests/test_gates.py` | 故意写 `import shared.knowledge` 必须 FAIL；正常文件必须 PASS |
| 死代码判据收紧 | `scripts/check_dead_code.py` | 文档不再算“有人用”；新增 TEST_ONLY / DOC_ONLY；`core/__init__.py` 与 `core_files.json` 不再充当使用证据 |
| 首个 A 类删除 | `core/report_theme/table_backend.py`（66 行） | 无任何产线引用；表格渲染由 `report_flow._table` 承担；测试同步删除 |
| 边界复发修复 | `r10-wachengmei-design/skills/s01_imagegen.py` | 默认输出目录从团内 `workspace/prompts` 改为 `role_workspace()`（团外）；角色自测不再把产物留进仓库 |
| CI 新步骤 | `scripts/ci_report_checks.py [18c]` | `wiring_truth --check`：未登记未接线 / 文档死链直接红 |

验收：`wiring_truth --check` PASS（112 LIVE / 11 TEST_ONLY / 1 DOC_ONLY / 0 UNWIRED / 0 DOC_DEAD）；`check_dead_code --check` PASS；文档死链 9 → 0；`pytest tests/test_charts.py tests/test_gates.py` 58 passed。

未做（需拍板）：11 个 TEST_ONLY 模块的去留（claim_gate 接回还是归档、coverage 集群是否收成命令）；core 物理分包（P4）尚未开始。

---

## 2026-11-26（第九轮）· 经验层收口 + 表达候选器 + 三角色补齐

一句话：**把上一轮「有规则没库、有提示没执行器」的两处半成品补成可验收的闭环。**

### 一、经验层收口（从「能读」到「能管、能审」）

| 能力 | 落点 | 判据 |
|---|---|---|
| 任务卡可见 | `shared/knowledge/brief.py` | brief 新增 `experience_refs`（只记 tier + 卡 id，不内联卡片正文）；`validate_brief` 拒收内联 `wrong_once/do_instead` |
| 冲突检测 | `shared/experience_cards.py#conflicts` | 同 trigger 但 `do_instead` 不一致 → 列出并提示「只能按各自 boundary 择一」 |
| 项目上限 | 同上 `MAX_PER_PROJECT=30` | 超出只保留最新 30 张，并写错误说明（不静默丢） |
| 写入门 | 同上 `add_card` | `source` + `reviewed_by` 必填（谁写谁签）；同 id 不许静默覆盖 |
| 注入预算 | 同上 `BRIEF_MAX_CHARS=600` | 超长按行截断并标 `truncated`；prompt_pack 用截断后的文本 |
| 验收指标 | 同上 `stats()` · CLI `--stats` | 载入量 / 过期占比 / 注入字数 / 冲突数 |
| 接缝记账 | 同上 `to_knowledge_items()` | 卡片 → 带 hash 的注入条目；说明为何不默认走向量 |

### 二、表达候选器（波 2）

| 件 | 落点 | 说明 |
|---|---|---|
| 候选器 | `core/prose_candidates.py` | 数字多重集一致（硬判据）+ trigram Jaccard + 七项权重（20/20/15/15/10/10/10）+ <85 淘汰 + ≤3 轮 + 固定种子 |
| 双模如实标注 | 同上 | 无模型 → `mode=rule`，只出确定性单稿并标 `no_model_single_variant`（实测三份相似度 0.9，不假装是 3 个候选）；有模型 → `mode=llm`，diversity ≥0.6 的候选硬淘汰 |
| 接入 | `core/report_prose_gen.generate()` | `compose()` 行为不变；`candidates` 可传 dict 覆盖配置，`record_path` 落盘候选集便于逐字复跑 |
| 配置 | `configs/report_prose.yaml#candidates` | enabled / n / max_rounds / pass / diversity_max / budget_ms_per_section |

### 三、三角色补齐（波 3，按角色类型分法）

| 角色 | 类型 | 变化 |
|---|---|---|
| r05 蛙深远 | A 生成型 | 新增 L2 三块：假设-证伪台账 / 来源饱和 / 三角验证；新增 `references/08-evidence-saturation.md`（独立源判定、三类互证、两份台账、常见反例） |
| r06 蛙得清 | B 计算型 | 不加任何写作提示块；在 `references/05-visualization-report.md` 补「图点可回溯 / 基线同口径 / 构成图合计」三条机器判据与交付自检 |
| r07 蛙得明 | A 生成型 | 新增 L2「需求成立门槛」：三类证据缺一不出 PRD；验收可判定（对象/阈值/判定人）；非目标至少一条 |

### 四、登记与门禁

- `configs/core_files.json` 登记 `prose_candidates.py`；
- `boundary_allowlist.yaml` 登记 5 个角色级 `experience/cards/`（角色通用经验，不含项目资产）；
- 顺手修掉两个真 bug（r06 端到端验收暴露）：`chart_renderers_ext.py` 四处 `len)(items)` 语法错误（dumbbell / dot / 分组 / 任务图都渲染即崩）；`r06/run_tests.py` 未自建产物目录，workspace 被清理后误红；
- 回归：`pytest` **673 passed / 3 skipped**；`ci_report_checks` **ALL PASS**；`check_prompt_system` PASS；`check_role_packs` 20/20；`guagua.py check` 20/20；`gen_agent_packs --check` 无漂移；`check_project_boundary` PASS；`check_report_isolation` PASS；`check_convergence` 违规 0；`check_gate_lock` PASS；`check_doc_consistency` PASS。

已知边界（不掩盖）：规则模式下多样性达不到 0.6，这是「无模型只能换措辞」的物理上限；候选器的差异度判据只在接入模型后生效。

---

## 2026-11-26（第八轮）· 四项硬门禁：结构同构 / 图表契约 / 回抓硬化 / 报告隐私

一句话：**把「人看得出来但机器没拦」的四类问题变成确定性门禁，并用金样例（nm-vegetable）验证它们真的会红。**

| 能力 | 落点 | 判据 |
|---|---|---|
| 结构同构门禁 F12 | `core/structure_guard.py` · `scripts/check_report_flow.py` · `scripts/compile_agent_report.py` | 连续 ≥3 节「标签序列 + 段数」完全一致 → FAIL；阈值唯一出处 `configs/report_prose.yaml#structure_gate` |
| 写作结构轮换 | `core/report_prose_gen.py` | 4 套论证顺序按节 id 稳定轮换，连续两节同序自动换序，避免自动生成的稿子被 F12 判死 |
| 图表收卡契约 | `core/dispatch.py#_chart_contract` | 图上的点必须能由本卡数字/派生量解释；`chart.refs` 必须在本卡命名空间；构成图合计 95–105% 或显式 `partial` |
| 来源回抓硬化 | `core/source_verify.py` | 浏览器级请求头 + 3 次退避重试；`GUAGUA_FETCH_FALLBACK=1` 时才启用 Playwright 兜底 |
| 来源时效度量 | `core/source_freshness.py` | 18 个月窗口统计 stale_ratio；>60% 旧源时写降级标记与边界，不硬拦年报口径 |
| 报告隐私扫描 | `scripts/check_report_privacy.py` | 只扫报告资产（claims/报告/manifest），密钥前缀/键值对/手机号/身份证；占位符放行 |

二阶处理：F12 会拦「自动生成的同构稿」，所以同步改了 `report_prose_gen` 的结构轮换；新 core 模块须登记 `configs/core_files.json`（已加 2 个）；门禁脚本变更已 `check_gate_lock --write` 留痕。

### 第二轮：角色层与共享层（同一天）

| 层 | 落点 | 变化 |
|---|---|---|
| 共享硬规则 | `shared/gate_digest.json` · `shared/prompt_pack.py` | 6 条跨角色硬规则（证据可回溯/结构不重复/图有出处/经验带边界/隐私不入稿/来源有时效），按角色适用性注入每个角色的提示词 |
| L0 宪法 | `shared/prompt_constitutions.json` | r04/r06/r07/r10/r11 各加一条边界（评审三类问题、图必须有出处、经验必须写边界、图不缺口径、不连续同构） |
| L2 方法块 | `r11-wadianti-copy/prompt_profile.json` | 候选写作、结构轮换、去 AI 味自检 |
| L2 方法块 | `r07-wademing-pm/prompt_profile.json` | 经验卡（触发场景/上次错法/正确做法/适用边界/最近核验） |
| L2 方法块 | `r10-wachengmei-design/prompt_profile.json` | 图表标注规范（先定关系再选型、结论式标题、不用 3D/彩虹色） |

边界：r06 属计算型角色，`validate_profiles` 明确禁止其携带写作提示块，所以图表规则走共享层注入，不写进 r06 的 `l2_prompt_blocks`。

### 第三轮：项目级经验卡（库 + 检索 + 注入）

| 件 | 落点 | 说明 |
|---|---|---|
| 经验卡模块 | `shared/experience_cards.py` | 卡片校验（缺 boundary / last_verified 拒收）、加载（角色级 + 项目级，同 id 项目覆盖）、检索（触发词/标题/正文，TTL 与置信度衰减）、分档 L0/L1/L2 |
| 提示词注入 | `shared/prompt_pack.build(..., project=...)` | 传项目目录才检索经验卡，不传保持旧行为；返回体新增 `experience: {tier, ids, errors}` 便于审计 |
| CLI | `python -m shared.experience_cards --role r07 --query "..." --project <项目>` | 排障与人工核对用 |
| 种子卡 | r05 / r06 / r07 / r12 / r13 各 1 张 + nm-vegetable 项目级 2 张 | 均为真实复盘结论，带适用边界与核验日期 |

治理：`last_verified` 超 180 天降权；同 trigger 冲突卡必须写边界；经验卡不得替代本期证据（提示词里明文约束）。

门禁：`pytest` 659 passed / 3 skipped；`ci_report_checks` ALL PASS；`check_prompt_system` PASS；`check_role_packs` 20/20；`gen_agent_packs --check` 无漂移。

门禁：`pytest` 653 passed / 3 skipped；`ci_report_checks` ALL PASS；`check_prompt_system` PASS；`check_role_packs` 20/20；`gen_agent_packs --check` 无漂移；`check_doc_consistency` PASS。金样例验证：nm-vegetable 旧报告在新 F12 下 FAIL（第 4–7 节同构），证明门禁生效。

---

## 2026-11-25（第七轮）· 清理 0 引用死资产（36 文件 / 约 850KB）

一句话：**只删有「零引用」证据的资产，活跃的 pipelines / samples / knowledge / docs 一律不动。**

| 删除 | 证据 |
|---|---|
| 根 `fixtures/`（2 文件） | 全仓 0 引用；测试实际读 `tests/fixtures` |
| `samples/dataset.py` | 0 引用；其余 samples 模块被 `charts_pro` 与测试 import |
| `baselines/` 4 个目录 + `report.html`（605KB） | `_fruit_demo`/`_ir_panel_demo`/`_ir_shadow_facts`/`_kaggle_demo` 0 引用；corpus 只读 `report.md` |
| `scripts/_archive/`（11 文件） | 均为已废弃的一次性迁移脚本；删除后暴露的 2 个真死脚本（`analyze_agent_skills`、`gen_method_packs`）一并删除 |
| `examples/`（5 文件） | 代码不执行；`golden_corpus` 改指 `baselines/_golden_flow_specfruit` 产物 |
| `evals/results` 历史文件 | `run_consult_eval` 运行时自建目录；`evals/answers`（评测输入）保留 |
| `scripts/notify.py` | mock 演示残留 |

核查后保留：`run_pipeline.py`（pipelines 单条入口）、`grade_report_level.py`（手动分级工具）；`make_package.py` 登记进 `check_dead_code` ALLOW（发布打包入口）。

门禁：`pytest` 629 passed / 3 skipped；`ci_report_checks` ALL PASS；`audit` 15/15。

---

## 2026-11-25（第六轮）· 测试目录按域合并 + 5 个失效自测转正

一句话：**测试文件从 96 个降到 22 个，用例不减；CI 从「假绿」变真跑。**

| 问题 | 处理 |
|---|---|
| 5 个 `check()` 脚本被 pytest 收集为 0，CI 从不执行，已有 3 个坏掉 | 改写为 pytest 用例（+13 例）；修掉过时断言（geo_tokens 已中性化 / panel 需 metric_id / chart_contracts 需 dim） |
| 88 个薄测试文件（多数 ≤2 例） | 按域合并为 14 个域文件（charts / cards / claims / report / data / collection / methods / research / gates / agents / orchestration / consulting / platform），断言与用例数不变 |
| 本机 HTTP fixture 被系统代理劫持（Windows 上 urllib 忽略 no_proxy） | `tests/test_collection.py` 加 autouse no-proxy fixture，127.0.0.1 直连 |
| CI 与 Move 卡片指向旧文件名 | `ci_report_checks.py`、`ci_upgrade_checks.py`、`knowledge/moves/*.json` 同步到新域文件 |

门禁：`pytest tests -q` 629 passed / 3 skipped；`ci_report_checks` ALL PASS；`audit` 15/15。

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
| 数据驱动选型 | `core/chart_fit.py`（2026-11-26 已删除，判据由 report_flow 内联） | 画像 → 候选图型 + 前置条件 + fallback；空态/常数值拒绝出图 |
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
