# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/prd-authoring/scripts/gate_selftest.py` → 必须 `PASS 5/5`。
> 版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 标题写「做一个更好的引导」 | `prd.title` 语义空洞 | ⚠ 门禁只查非空，语义需人工判 |
| MU-02 | 产品契约写「进入后用一下 / 感受一下产品」 | `prd.contract` 四要素形式齐全但不可判定 | ⚠ 形式过、实质需人工判（见下方说明） |
| MU-03 | P0 只写名字，无 `trigger/rule/result/state` | `prd.p0.depth` BLOCKER | ✅ exit=1（`spec-fail.json`） |
| MU-04 | `source` 写「我觉得这样比较好」 | `prd.p0.source` 不在枚举内 | ✅ exit=1（同上） |
| MU-05 | `non_goals` 只 1 条 | `prd.non_goals` BLOCKER | ✅ exit=1（同上） |
| MU-06 | `edge_cases` 为空 | `prd.edge_cases` BLOCKER | ✅ exit=1（同上） |
| MU-07 | 写了 `assumptions` 但 `open_questions` 为空 | `prd.no_fabrication`（把假设当事实） | ✅ 已在 `spec-fail.json` 中覆盖 |
| MU-08 | 战略层缺字段 | `harness prd` 字段门禁 | ✅ exit=1（`prd_dirty.json`） |
| MU-09 | 把 `configs/r07.yaml` 当 PRD 喂进 `prdguard` | 非 PRD 输入必须拒绝 | ✅ exit=1（不许假绿） |

> **MU-01 / MU-02 的诚实说明**：门禁只能查"字段在不在、枚举对不对"，
> 查不出"进入后用一下"这种**形式合规但语义空洞**的填充。
> 这两条留在本节并标 ⚠，是为了明确"机器判形式、人判实质"的分工，**不是假装已覆盖**。

## 二、两层 schema 混用（最容易踩）

| # | 错误做法 | 后果 | 正确做法 |
|---|---|---|---|
| MU-10 | 用战略层 JSON 跑 `prdguard check` | 报「标题非空 / 契约四要素缺失」一堆 BLOCKER | 执行层规范走 `prdguard`，战略层走 `harness prd` |
| MU-11 | 用执行层 JSON 跑 `harness prd` | 报缺 `problem_statement` / `users` / `metrics` | 同上，两层各跑各的门禁 |

## 三、门禁抓不到，靠 §6 自检与 R04

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-12 | `after` 写「体验更好」 | 不可观测 | §6 自检 + R04 |
| MU-13 | 指标只有 target 无 baseline | 口号，无法判定成败 | §6 自检 + R04 |
| MU-14 | 把 DoD 写进 AC（"有单测、过评审"） | 混淆需求完成与团队标准 | §6 + `references/two-layer-prd.md` §二 |
| MU-15 | 写技术方案与工期 | 越界 | §6 + R04 |
| MU-16 | 让用户回答"你想要什么功能" | 需求未提炼，把设计外包给用户 | §2 追问纪律 |
| MU-17 | 手写渲染版 `.md` 不跑 `prdguard render` | 与规范脱钩 | §6 + 比对生成物 |
| MU-18 | RICE 只给分数不给算式，且 Confidence 全填 80% | 优先级不可复核 | §6 + RICE 三条纪律 |

---

## 四、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 标 ⚠ 的条目已写明"机器判不了，需人工"，没有假装覆盖
- [ ] 新增 P0 必填段时，先加 fixture 再改 `s09_prdguard.py`
- [ ] 每次改 `prdguard` 或 `harness.py prd` 后重跑 `gate_selftest.py`
- [ ] 12 项审批清单逐条打勾后才可标"可进入开发"

> **纪律**：门禁过 ≠ PRD 合格。门禁只保证"能交给开发"，不保证"做的是对的事"。
