---
name: handoff-acceptance
description: 交接与验收技能包。让"交付给别人"变成可复现的交接包与可判定的验收：交接包必须带复现命令、下游字段与验收标准，验收必须逐条带证据、口头通过不算过，全程留审计轨迹。当需要把一个成品交给下一个角色、判断交接是否完整、做验收签收、或追溯谁在什么时候接了手时使用。不生产成品、不改稿、不为交接物质量背书。
license: MIT
compatibility: 通用。门禁在角色根目录 harness.py（package / accept / trace 三道，需经 agent.py harness 调用），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工八项核对，此时不得签收。
metadata:
  owner: r02
  version: "2.0.0"
  kind: skill
  triggers: "交接,交接包,验收,签收,复现,审计轨迹,下游字段"
  verify: python agent.py harness package --input <交接包.json>
  entry: "python agent.py harness accept --input <验收.json>"
  consumers: "r04,r01,r09"
  supersedes: README.md
---

# 交接与验收（Handoff & Acceptance）

> 一句话定位：**这个技能存在的意义，是防止"口头说交完了"和"口头说验收过了"**。
> 跨角色协作里最贵的浪费不是做错，而是**交接丢了信息**：
> 拿到一个 zip 没有复现命令、没有下游字段、没有验收标准，接收方只能猜；
> 或者反过来，验收时"我看了一下没问题"就签收，问题在上线后才爆。
> 这两件事都必须变成**可复现、可判定、可追溯**的产物。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「这个交给 r09」「帮我看交接包全不全」
- 「验收一下，能不能签收」「他说做完了，怎么确认」
- 「谁在什么时候接了手」「追溯一下这次交接」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 把东西做出来 | 生产角色（`r08` / `r09` / `r10` …） | 本技能只判交接与验收，不生产 |
| 判断成品质量好不好 | `r04` 评审官 | 验收"是否符合交接契约"≠"质量结论" |
| 排期与资源 | `r02` 的 `schedule` / `capacity` | 那是排期域 |
| 替上交方补缺失字段 | **拒绝** | 补了就等于替他背书，且丢失问题现场 |

**最小可开工输入**：**交接物 + 交接对象**（谁给谁）。缺验收标准 → 只判"交接包完整性"，不判"可签收"。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| `artifact`（交接物） | 必需 | 无物可交，直接退回 |
| `owner` / `handoff_to`（谁给谁） | 必需 | 责任不明，`required_fields` 会拦 |
| `acceptance_criteria`（验收标准） | 必需 | 缺则只能判"交接包不完整"，不出签收结论 |
| `repro_commands`（复现命令） | 必需 | 缺即"交接包必须可复现"，退回补 |
| `downstream_fields`（下游需要的字段） | 必需 | 缺即下游无法直接消费 |
| `must_read`（必读说明） | 建议 | 缺则标注"接收方无必读清单" |

**追问纪律**：最多一轮，只问**交接物在哪、验收标准是什么**。其余缺失按门禁报错退回，不替对方补。

---

## §3 执行流水线（Workflow）

### Step 1 · 交接包完整性（`package` 三道门禁）
| 检查 | 判据 | 反例 |
|---|---|---|
| `repro` | 复现命令 ≥ 1 条 | 只给 zip，不说怎么跑 |
| `downstream` | 下游字段 ≥ 1 个 | 只说"都在这了"，不说下游要什么 |
| `acceptance` | 验收标准 ≥ 1 条 | 让接收方自己定标准 |

外加 `required_fields`：`process_doc` / `artifact` / `artifact_type` / `owner` / `rev` / `handoff_to` / `must_read`。

**为什么必须可复现**：接收方拿到就跑不起来的东西，等于没交。
一条 `unzip x && python serve.py` 省掉的是对方半小时的猜。

- **产出**：`package` 门禁结论
- **过关条件**：`python agent.py harness package --input <交接包.json>` 退出码 0

### Step 2 · 逐条验收（`accept`，口头通过不算过）
每个验收项必须三件套：

```json
{"criterion": "Lighthouse ≥ 90", "passed": true, "evidence": "Lighthouse 报告 91 分"}
```

**硬规则**：
- `passed=true` 但 `evidence` 为空 → **不算通过**（`evidence` 门禁直接判）；
- `passed=false` 必须给 `reason`，否则记为"未达标准"且无说明；
- 最终 `verdict` 由"通过数/总数"决定，不由接收方一句话决定。

- **产出**：`criteria[]` + `verdict`
- **过关条件**：`python agent.py harness accept --input <验收.json>` 退出码 0（且全部项有证据）

### Step 3 · 审计轨迹（谁在什么时候接的手）
```bash
python agent.py harness trace --input <审计轨迹.json>
```
事件必须**时间单调递增**，且每条带 `ts` / 动作 / 主体。
顺序错乱说明有事件被补写或漏记，此时不签收。

- **产出**：`trace` 结论
- **过关条件**：`trace` 退出码 0（事件顺序单调、字段齐全）

### Step 4 · 出交接结论（三选一，不许含糊）
| 结论 | 条件 | 下一步 |
|---|---|---|
| **可签收** | 三道门禁全过 | 记录签收人与时间 |
| **退回补齐** | 交接包缺字段 / 缺复现 / 缺标准 | 列缺什么，退回上交方 |
| **验收不通过** | 有验收项未过或证据缺失 | 列未过项，退回生产方 |

> **不接受第四种结论**：「基本可以，先上着」。这句话在上线后的成本最高。

- **产出**：结论 + 缺项清单 + 责任人
- **过关条件**：结论明确且与门禁结果一致

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 交接包（`required_fields` + 复现 + 下游字段 + 验收标准） | `.json` | `tests/handoff-pass.json` |
| 2 | 验收记录（逐条 criteria + evidence） | `.json` | `tests/accept-pass.json` |
| 3 | 审计轨迹 | `.jsonl` / `.json` | `examples/audittrail.json` |
| 4 | 交接结论（可签收 / 退回补齐 / 验收不通过） | `.md` | `references/handoff-contract.md` §三 |

- 命名：`handoff_<任务短码>_<rev>.json` / `accept_<任务短码>_<rev>.json`
- **没有 `evidence` 的验收记录不具签收效力**，即便 `passed` 全为 true。

---

## §5 质量门（一票否决，不过不给交付）

1. **`required_fields` 齐全**（process_doc / artifact / artifact_type / owner / rev / handoff_to / must_read）；
2. **复现命令 ≥ 1 条**（`repro`）；
3. **下游字段 ≥ 1 个**（`downstream`）；
4. **验收标准 ≥ 1 条**（`acceptance`）；
5. **每个验收项都带 `evidence`**（口头通过不算过）；
6. **未过项都带 `reason`**；
7. **审计轨迹时间单调且字段齐全**。

> 验收命令：`python agent.py harness package|accept|trace --input <json>`
> 命中任一项不过 → 回 §3 对应 Step，**不允许替上交方补字段**。

---

## §6 交付前自检清单

- [ ] 交接物真的存在且可访问（不是"在我电脑上"）
- [ ] 复现命令我照着跑过一遍，能跑起来
- [ ] 下游字段列清了，且下游确认过这就是他要的
- [ ] 验收标准是**上交方和接收方都认的**，不是接收方自己事后定的
- [ ] 每个验收项都有可定位证据（截图/日志/命令输出）
- [ ] 没过的项都写了原因，不是只打一个叉
- [ ] 审计轨迹齐全，时间顺序没有回跳
- [ ] 结论是明确三选一，不是"基本可以"
- [ ] 我没有替上交方补任何字段
- [ ] 三道门禁均退出码 0

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 交接只给一个 zip，不说怎么跑 | 必须给 `repro_commands` ≥ 1 条，接收方能独立复现 |
| EX-02 | 「下游要什么到时候再说」 | 交接口就列 `downstream_fields`；事后补等于返工 |
| EX-03 | 验收标准让接收方自己定 | 标准必须在上交时同时给出，否则无法验收 |
| EX-04 | `passed: true` 但没写证据 | **口头通过不算过**；`evidence` 为空即不通过 |
| EX-05 | 未过项只打叉不写原因 | 必须给 `reason`，否则生产方不知道怎么改 |
| EX-06 | 替上交方补缺失字段再验收 | 禁止；补了等于替他背书并丢失问题现场 |
| EX-07 | 结论写「基本可以，先上着」 | 三选一：可签收 / 退回补齐 / 验收不通过 |
| EX-08 | 审计轨迹事后补写导致时间倒序 | 事件必须时间单调；倒序不签收 |
| EX-09 | 把验收当成质量评审 | 验收只判"符合交接契约"，质量结论归 `r04` |
| EX-10 | 签收后不记录签收人与时间 | 签收必须留痕，否则无法追溯 |
| EX-11 | 复现命令写「按文档操作」 | 必须是可直接粘贴执行的命令 |
| EX-12 | 一个验收项挂多个判断标准 | 一项一条可判定标准；含糊标准无法判定 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `harness.py` 跑不了（注意：必须走 `agent.py harness`，直接跑 `harness.py` 无 `__main__`） | 按 §6 人工逐项核对，标注「未跑门禁」；**不得签收** |
| 交接物不可访问 | 退回补齐，不做"看描述验收" |
| 无验收标准 | 只判交接包完整性，结论写"交接包不完整"，不出签收结论 |
| 接收方已开始使用但未签收 | 记为高风险：先补签收再继续，否则出问题无法定责 |
| 交接方与接收方是同一人 | 记为"自交接"，标注并建议换人；与 R04 身份红线同源 |
| 历史交接无轨迹 | 不改历史；新增补记条目并标注"补记"，不伪造时间 |
| 用户要求"先签了再说" | 拒绝；可给"条件签收"（列明待补项与期限），但不改判据 |

**明确不做**
- 不生产成品、不改稿、不补字段；
- 不出质量结论（pass/fail 归 `r04`）；
- 不排期、不分配资源（归 `r02` 排期域）；
- 不替代创始人做验收豁免。

---

## §9 资源地图（按需读取，禁止全量加载）

### 调用方式（2026-11-11 已修）

> ✅ **`r02/harness.py` 已补 `__main__` 与 CLI**（此前是纯库：直跑什么都不执行且 exit 0，属假绿）。
> 现在两种调用都成立，退出码一致：
> - `python harness.py <action> --input <json>` → 0 通过 / 1 不通过 / 2 输入或环境问题
> - `python agent.py harness <action> --input <json>`（原路径未受影响）
>
> 实测：正例 0、`handoff-missing` 1、`accept-no-evidence` 1、缺文件 2。

| 什么时候需要 | 读哪个文件 |
|---|---|
| 交接包字段定义、结论三选一写法、验收契约细则 | `references/handoff-contract.md` |
| 交接包骨架（可直接改） | `tests/handoff-pass.json` |
| 验收记录骨架 | `tests/accept-pass.json` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py --self-test` |
| 负向用例（哪些错法必须被拦） | `tests/misuse.md` |
| 官方夹具 | `../../../examples/`（`handoff.json` / `acceptance.json` / `audittrail.json`） |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言三道门禁对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 重构为十节技能包。
  新增：§1 转交表、§2 最小可开工输入、§3 四步流水线（交接包→逐条验收→审计轨迹→结论）、
  §7 十二条错误表、§8 七种降级、`references/handoff-contract.md`、
  `scripts/gate_selftest.py`、`tests/handoff-pass.json` / `accept-pass.json` / `misuse.md`。
  门禁复用 `agent.py harness` 三道（package / accept / trace）。
  **注**：原计划做 `status-report`，但 r02 没有可用的状态报告门禁（`status`/`graph` 动作无输出），
  改为做有真实门禁的 `handoff-acceptance`（对应 r02 能力域"交接与验收追踪"）。
- v1.0（此前）：无独立能力卡。
