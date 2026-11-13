---
name: review-anti-collusion
description: 独立评审反合谋技能包。以只读身份核验他人成品，产出带证据链的 pass/fail 结论与结构化评审报告，并对评审产出自身做五类系统病再评审（身份红线、只记录不修复、证据链、保留项完整性、回避模糊措辞）。当需要验收交付物、复核硬门禁、给 pass/fail 结论、或判断一份评审报告本身是否可信时使用。不负责生产、不改稿、无成品不做猜测评价、不与他人协商出结论。
license: MIT
compatibility: 通用。门禁在角色根目录 harness.py 与 review.py（Python 3.10+，零第三方依赖）；无 Python 环境时按 §8 转人工五项核对，此时禁止出 PASS 结论。
metadata:
  owner: r04
  version: "2.0.0"
  kind: skill
  triggers: "验收成品,评审,pass/fail,硬门禁复核,证据链,反合谋,质量结论"
  verify: python harness.py verdict --input <评审结果.json>
  entry: "python agent.py review --input <评审包.json>"
  consumers: "r01,r02,r03,r07"
  supersedes: README.md
---

<!-- 本文件由 scripts/sync_dsh_skills.py 生成，请勿手改；改源包后重跑同步 -->

# 独立评审反合谋（Review Anti-Collusion）

> 一句话定位：**这个技能存在的意义，是防止"评审变成盖章"**。
> 评审最贵的失败不是判断错，而是**判断根本不独立**——评审者和生产者是同一个人、
> 结论没有证据、只夸不改、把该保留的优点一起砍掉、用"应该/可能"把话说圆。
> 这五件事任何一件发生，`pass` 就变成了社交动作，而不是质量判断。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「这个交付物能过吗」「帮我验收一下」「给个 pass 还是 fail」
- 「这份评审报告可信吗」「他评审的结论站得住吗」
- 「门禁跑完了，结论呢」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 帮我改一版 / 补一章 | 生产角色（`r07` / `r09` / `r10` …） | **评审只记录，不修复**。改了就是同谋 |
| 我觉得还行，你确认下 | 拒绝 | 无成品不做猜测评价；先给成品再评审 |
| 一起商量个结论 | 拒绝 | 与生产者协商出结论＝合谋，评审必须独立语境 |
| 上线 / 付款 / 裁员能不能批 | 创始人 | 那是签署，不是评审 |

**最小可开工输入**：**一份已完成成品 + 一份验收标准**。二者缺一即 `BLOCKED`，不做评价。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 成品（文件 / 链接 / 可见内容） | 必需 | **缺则 `BLOCKED`**，不出 pass/fail，不猜 |
| 验收标准（AC 清单 / 门禁口径） | 必需 | 缺则问一次；仍未给 → `BLOCKED` 并说明"判据缺失无法判定" |
| 生产者身份 | 必需 | 缺则视为不明；`reviewer == producer` 即 BLOCKER |
| 门禁运行记录 | 建议 | 缺则自己在评审结论里标注"未复核门禁" |
| 上轮保留项（`keep` 列表） | 可选 | 无则跳过保留项完整性检查 |

**追问纪律**：最多一轮，只问两件事——**成品在哪、判据是什么**。其余不追问。

---

## §3 执行流水线（Workflow）

### Step 1 · 身份红线（先于一切）
确认 `reviewer ≠ producer`。相同即 **BLOCKER**，直接终止评审并回报"需换人"。
这条不是流程建议，是评审存在的**前提**：自己评自己，评的永远是"我尽力了"。

- **产出**：`self_review_gate` 结论
- **过关条件**：`reviewer` 与 `producer` 不同一实体

### Step 2 · 材料门禁（BLOCKED 判定）
先判"能不能评"，再谈"评得怎样"：

| 情况 | 结论 | 处置 |
|---|---|---|
| 无成品 / 成品打不开 / 只有描述 | `BLOCKED` | 停止，要成品 |
| 有成品但无判据 | `BLOCKED` | 停止，要验收标准 |
| 成品 + 判据齐全 | 进入 Step 3 | — |

- **产出**：`materials` 结论（`PASS` / `BLOCKED`）
- **过关条件**：`python harness.py materials --input <材料.json>` 退出码 0

### Step 3 · 逐条判据核验（证据链是命门）
对每条验收标准给三件套：

```json
{"id": "AC-01", "status": "pass|fail|blocked", "reason": "证据类型", "evidence": "文件:行 / 截图 / 命令输出"}
```

**硬规则**：`verdict=PASS` 而 `evidence` 缺失 → **直接 BLOCKER**。
"我认为做到了"不是证据；证据必须能被第二个人拿去复核。

- **产出**：`criteria_results[]`
- **过关条件**：每条 `pass` 都带 `evidence` 且可定位

### Step 4 · 出结论与发现清单
- `verdict` ∈ `PASS` / `FAIL`（`BLOCKED` 不是结论，是中止）
- `findings[]` 每条带 `severity`（`BLOCKER` / `CRITICAL` / `MAJOR` / `MINOR`）
- 严重度必须有**判定依据**，不允许凭手感：`BLOCKER` 只在"错到不能用或违红线"时用

- **产出**：`{verdict, findings[], criteria_results[]}`
- **过关条件**：`verdict` 与 `findings` 不矛盾（有 BLOCKER 却 PASS 即自相矛盾）

### Step 5 · 保留项完整性（上一轮的好东西不能被悄悄砍掉）
若上轮有 `keep` 列表，逐项确认：
- 仍保留 → OK
- 被降级 / 被删除 → **必须给 `resolution_reason`**，否则 **BLOCKER**

> 评审最常见的隐性破坏：为了"改好"而砍掉了上一版真正有价值的部分。

### Step 6 · 只记录不修复（红线）
评审输出**不得**包含 `applied_fixes` / `modified` 等"我已改好"的声明，非空即 **BLOCKER**。
发现问题的正确动作是**写进 findings 并退回生产者**，不是当场改掉。
（改了 = 生产者变成评审者，下一次就没人能校验这段代码/文案。）

### Step 7 · 措辞纪律（把"应该"清出去）
扫描评审文本，命中 `should` / `probably` / `seems to` / `I believe`（及中文「应该/可能/似乎/我觉得」）
→ 路由 `writer` 回改写。**评审结论必须是断言，不是猜测**。

### Step 8 · 跑门禁并出报告
```bash
python harness.py verdict --input <评审结果.json>   # 结构与证据链（读 flat 结果）
python review.py --packet <评审包.json>             # 对评审产出再评审（读 {skill,action,result}）
```

**两个判定器读的 schema 不同，这是最容易踩的坑**：

| 判定器 | 输入形状 | 读哪里 |
|---|---|---|
| `harness.py verdict` | **flat** | 顶层 `verdict` / `findings` / `criteria_results` |
| `review.py --packet` | **wrapped** | `result.{reviewer,producer,verdict,...}`，外层带 `skill` / `action` |

把 flat 结果直接喂给 `review.py`，它会读到空 `result` → **所有检查都不触发 → `ok:true`**，
看起来"过了"，实际什么都没检查。这是典型的**假绿**，必须避免。
`tests/` 下的 `packet-*.json` 就是正确形状的样板。

需要机器可读诊断时输出 SARIF（本角色已支持，规则 ID 形如 `P-THEATRE`）。

- **过关条件**：两条命令均退出码 0，且 `review.py` 的 `checks` 数量与预期一致（不是 0 条）

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 评审结果（verdict + findings + criteria_results） | `.json` | `templates/verdict.json` |
| 2 | 评审报告（人读版，含证据定位） | `.md` | `templates/verdict.json` 的字段 |
| 3 | 门禁运行记录 | 终端 JSON | `harness.py` / `review.py` 输出 |
| 4 | SARIF 诊断（可选，CI 用） | `.sarif.json` | `examples/review_result.sarif.json` |

- 命名：`review_<对象短码>_<YYYYMMDD>.json`
- **只有 `.json` 结果算结论**；聊天里的"我觉得可以"不算。

---

## §5 质量门（一票否决，不过不给交付）

1. **`reviewer ≠ producer`**（BLOCKER）；
2. **`PASS` 必带证据链**：`evidence` / `criteria_results` 至少一项非空（CRITICAL）；
3. **无 `applied_fixes` / `modified`**（BLOCKER，只记录不修复）；
4. **`keep` 项降级必带 `resolution_reason`**（BLOCKER）；
5. **无模糊措辞**（`should/probably/I believe` 等，路由 writer）；
6. **`verdict` 与 `findings` 不矛盾**：有 BLOCKER 级发现不得判 PASS；
7. **每条 `pass` 的证据可定位**（文件:行 / 截图 / 命令输出任一）。

> 验收命令：`python harness.py verdict --input <评审结果.json>` 与 `python review.py --packet <评审包.json>`
> 命中任一项不过 → 回 §3 对应 Step 重做，**不允许只改 verdict 字样**。

---

## §6 交付前自检清单

- [ ] 我不是这个成品生产者（或已明确标注利益冲突并转人）
- [ ] 成品我能真正打开/运行，不是只读了描述
- [ ] 验收标准是对方给的，不是我替对方拟的
- [ ] 每条 `pass` 都有可定位证据，没有一条靠"我认为"
- [ ] 每条 `fail` 都说明了"差在哪、按哪条判据、怎么算补上"
- [ ] 严重度分级有依据，`BLOCKER` 没有滥用
- [ ] 有 BLOCKER 发现时，`verdict` 不是 `PASS`
- [ ] 上轮 `keep` 项逐条确认过，降级项都有理由
- [ ] 我没有在报告里声称"已修复"任何东西
- [ ] 全文没有"应该/可能/我觉得"这类模糊表述
- [ ] `harness.py verdict` 与 `review.py` 均退出码 0
- [ ] 评审结果已落盘为 `.json`，可被追溯

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 自己写的东西自己评，判 PASS | `reviewer == producer` 是 BLOCKER；换人或声明利益冲突 |
| EX-02 | 判 PASS 但找不到任何证据 | PASS 必须挂 `criteria_results` 或 `evidence`，否则 CRITICAL |
| EX-03 | 发现小问题顺手改掉，然后写"已修复" | 只记录不修复；`applied_fixes` 非空即 BLOCKER |
| EX-04 | 为了"改好"把上轮 `keep` 的亮点一起换掉 | `keep` 项降级必须写 `resolution_reason` |
| EX-05 | 用"应该没问题""基本可用"下结论 | 结论必须是断言：过 / 不过，及依据 |
| EX-06 | 只有描述没有成品就来要结论 | `BLOCKED`，不做猜测评价 |
| EX-07 | 全都是 `MINOR`，没有一个能落地的整改项 | 严重度按"能否使用/是否违红线"分级，不按手感 |
| EX-08 | 有 BLOCKER 却为顾面子判 PASS | 结论与发现矛盾即自相矛盾，一律 FAIL |
| EX-09 | 与生产者来回商量"能不能算过" | 判据既定不因协商改变；要改判据走变更流程 |
| EX-10 | 评审报告写得漂亮但证据全是"见附件" | 证据必须可定位（文件:行 / 截图路径 / 命令输出） |
| EX-11 | 把 flat 结果直接喂给 `review.py --packet` | schema 不同：flat 给 `harness`，`{skill,action,result}` 给 `review.py`；喂错会**假绿**（0 条检查却 exit 0） |
| EX-12 | 看到 `review.py` 输出 `ok:true` 就认定没问题 | 先看 `checks` 条数：0 条 = 什么都没检查，不算通过 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `harness.py` / `review.py` 跑不了 | 按 §6 人工逐项核对，标注「未跑门禁」；**此时禁止出 PASS**，最多出 `BLOCKED` / `待复核` |
| 成品打不开 / 只有截图 | `BLOCKED`，要求可访问的成品；截图只作为辅助证据 |
| 没有验收标准 | 问一次；仍无 → `BLOCKED`，并给出"需要哪几条判据"的清单 |
| 生产者身份不明 | 视为"未声明"，在报告中标注利益冲突风险，并要求补声明 |
| 用户要求"顺便帮我改好" | 明确拒绝改稿，把问题写成 findings 退回生产者 |
| 用户要求"给个面子判过" | 拒绝；可给"条件性通过 + 必须补齐项"，但不改判据 |
| 时限极紧但成品未完成 | 出 `BLOCKED` + 已完成部分清单，不出"大概能过" |

**明确不做**
- 不生产、不改稿、不补内容；
- 无成品不做猜测评价；
- 不与生产者协商结论（判据既定）；
- 不代创始人做签署类判断。

---

## §9 资源地图（按需读取，禁止全量加载）

> 本技能包**不自建门禁**：结构门禁用根目录 `harness.py verdict`，
> 对评审产出的再评审用根目录 `review.py`（5 项，含 3 条路由）。本包只声明与自检。

| 什么时候需要 | 读哪个文件 |
|---|---|
| 反合谋五条、拒绝评判清单、严重度校准、结论契约 | `references/anti-collusion.md` |
| 评审结果骨架 | `templates/verdict.json` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py` |
| 负向用例（哪些错法必须被拦） | `tests/misuse.md` |
| 干净 / 脏夹具 | `../../examples/review_result_clean.json` / `..._dirty.json` |
| SARIF 诊断样例 | `../../examples/review_result.sarif.json` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言 `harness verdict` + `review.py` 对正/反例的退出码 | `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 重构为十节技能包。
  新增：§1 转交表、§2 BLOCKED 前置判定、§3 八步流水线（身份红线→材料门禁→证据链→结论→保留项→只记录不修复→措辞→门禁）、
  §7 十条错误表、§8 七种降级、`references/anti-collusion.md`、`templates/verdict.json`、
  `scripts/gate_selftest.py`、`tests/misuse.md`。
  门禁复用 `harness.py verdict` 与 `review.py`，未新增判定实现。
- v1.0（此前）：无独立能力卡（角色级 `SKILL.md` 描述，缺触发语与门禁声明）。
