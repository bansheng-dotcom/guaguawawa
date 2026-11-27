# R07 蛙得明 · 厚度自述（T5 工作流）

> 按升级方案 §5「五层可验收」与 §16「厚度包」逐项自述。只写能被命令复核的事实。
> 本轮把「10 个校验模块」升级为「5 条工作流 + 1 个经验门」，落点全部在 `r07-wademing-pm/`。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 14 篇 / 约 50.8KB；本轮新增 3 篇（09–11，约 8KB） |
| 新增来源 | `09-workflow-discovery.md`（JTBD/Opportunity Tree/Mom Test，升级方案 §10.3 迁移表）；`10-workflow-prd-redteam.md`（Cagan 四风险、Klein premortem、Gherkin、PM_SPEC §4）；`11-experience-rag-rules.md`（RAG 三段、冲突消解、写回状态机） |
| 适用边界 | 每篇单列「适用边界」 |
| 误用反例 | 每篇单列「误用反例」表，并写明本仓哪个门禁拦截 |

## 2. 生产层

`pm_workflows` 一条链串起 5 条工作流 + 1 个经验门：

| # | 模块 | 输入 | 产出 | 门禁 |
|---|---|---|---|---|
| W1 | `pm_workflows/discovery.py` | 访谈记录 + job story + 机会树 + 假设 + POC | `discovery_pack.json` | 问题真实（≥3 原话、≥2 行为证据）、假设可证伪、不是「用户想要」 |
| W2 | `pm_workflows/prd.py` | 上下文 + 八段 PRD + 故事 + 非目标 + premortem | `prd_pack.json` | 八门禁 8/8 + 非目标 + premortem ≥5 条且每条有缓解/责任人 |
| W3 | `pm_workflows/priority.py` | 机会分/RICE/ICE + backlog + 路线图 + 发布说明 | `priority_pack.json` | 每项有分值与来源、排序可复算、路线图结果导向、发布五分类 |
| W4 | `pm_workflows/acceptance.py` | Given/When/Then + 测试 + 发布检查 | `acceptance_pack.json` | 主路径 + 边界 + 失败态 + 场景全覆盖 + go/no-go |
| W5 | `pm_workflows/briefing.py` | 项目理解 + 选项/利弊 + 建议 + 回链 | `briefing_pack.json` | 不代决策（决策人非 r07）+ ≥2 选项 + 回链 |
| G | `pm_workflows/experience.py` | 档位 + 索引/卡片 + 写回 | `experience_brief.json` | L0/L1/L2、3~5 卡上限、五查、冲突优先级、写回状态机 |
| — | `pm_workflows/runner.py` | 束 JSON 或单段输入 | 各包 + `workflow_manifest.json` | 每段 sha256 + 门禁 + 交接回链；失败即停 |
| — | `skills/s11_workflows.py` | CLI | discovery/prd/priority/acceptance/briefing/experience/run/audit | 与上面同源 |

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 真实夹具 1 | `pm_workflows/fixtures/bundle_new_product.json` | 0→1 新品：自由职业者发票管家（3 访谈 + 机会树 + 2 假设 + POC + 八段 PRD + 5 条 premortem） |
| 真实夹具 2 | `pm_workflows/fixtures/bundle_feature.json` | 存量优化：分步新手引导（PRD + 3 项排序 + 路线图 + 发布说明 + 验收） |
| 真实夹具 3 | `pm_workflows/fixtures/bundle_briefing.json` | 项目决策汇报（3 选项 + 利弊 + 决策人 + 2 条回链） |
| 经验夹具 | `pm_workflows/fixtures/experience_cards.json` | L2 4 张卡 + 1 条合法写回 |
| 黄金样本 | `golden/*.html` | 3 份，均由链真实跑夹具后渲染 |
| 运行账本 | `workflow_manifest.json` | 每段 sha256 + gate + handoffs |

## 4. 门禁层

| 门禁 | 落点 | 失败后果 |
|---|---|---|
| 问题真实 / 假设可证伪 / 非「用户想要」 | `discovery.build` | BLOCKER（不出 POC） |
| 八门禁 + 非目标 + premortem | `prd.build`（复用 `s03_prd._validate_prd`） | BLOCKER |
| 排序可解释 + 路线图结果导向 | `priority.build`（复用 `s04` 算子） | BLOCKER |
| 主路径/边界/失败态 + 发布门禁 | `acceptance.build` | BLOCKER |
| 不代决策 + 回链 | `briefing.build` | BLOCKER |
| 卡片数/五查/冲突/写回 | `experience.build` | BLOCKER |
| 交接回链哈希 | `runner.run` / `runner.audit` | BLOCKER |
| profile 语义字段 | `scripts/validate_profiles.py --role r07` | 退出码 1 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 单工作流门禁 | `tests/test_pm_workflows.py` | 29 条（含经验门 9 条） |
| 端到端 | 同上 `TestEndToEnd` | 4 条（新品/存量/汇报/确定性） |
| 误用拦截 | 同上 `TestMisuseIntercepted` + `misuse/*.json` | 3 条 |
| 黄金/误用存在性 | 同上 `TestGoldenSamples` | 2 条 |
| 角色验收 | `run_tests.py` T11 | 57 项检查全绿 |
| 全量 pytest | `python -m pytest r07-wademing-pm/tests -q` | 89 passed |

## 6. 最近真实运行

- 时间：2026-11-27
- `python r07-wademing-pm/run_tests.py` → 通过 57 / 57（含 verify_loop 58 行矩阵与 T11 工作流 38 条）
- `python -m pytest r07-wademing-pm/tests -q -p no:cacheprovider` → 89 passed
- `python scripts/validate_profiles.py --role r07` → PASS（actions=10 declared=30）
- `python scripts/check_role_thickness.py --check` → 问题 0（golden=3、misuse=3）
- 黄金链路：new-product（discovery+prd）PASS；feature（prd+priority+acceptance）PASS；briefing（W5）PASS；`workflows audit` 哈希与回链一致

已知边界：

- 工作流只交产品工件，不写对外报告（报告归 R01）；
- 经验卡时效以输入 `as_of` 为准（默认 2026-11-27），不读系统时钟；
- 优先级算子复用 `skills/s04_priority.PriorityCalculator`，与本模块退化实现同公式；
- 本轮未新增第三方依赖，未联网。
