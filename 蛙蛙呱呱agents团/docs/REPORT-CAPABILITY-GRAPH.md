# 角色能力图（REPORT-CAPABILITY-GRAPH.md）

> 版本：v0.1 · 2026-11-17
> 实现：`core/capability_graph.py`　｜　问题库：`core/question_library.py`
> 产物：`workspace/report_upgrade/capability_graph.json`

---

## 1. 它回答什么

**20 个角色，到底能回答哪些问题、以什么状态回答、缺什么。**

它不是组织架构图，也不是“20 角色都能写报告”的口号；它是一张可查询的
`role × question × capability × status × evidence` 表。

---

## 2. 状态定义

| 状态 | 含义 | 对报告的含义 |
|---|---|---|
| `real` | 可产出可复核的报告证据（本地确定性计算 / 台账 / 门禁） | 可进标题、可进动作 |
| `simulated` | 可产出草案/计划/定性判断，但不能当硬证据 | 只能进观察/假设，不能进标题 |
| `blocked` | 不进报告（`enters=false`）或没有可进报告技能 | 只能写缺口，不能假装有结论 |
| `missing` | 没有任何角色能回答 | 报告必须标 INCOMPLETE |

---

## 3. 当前图（2026-11-17）

| 指标 | 值 |
|---|---|
| 角色 | 20 |
| 可进报告角色 | **16** |
| 被标记不进报告 | **4（r08 / r09 / r10 / r17）** |
| 只做草案/定性 | **2（r11 / r14）** |
| 技能很薄（eligible ≤2） | **1（r03，1/8）** |
| 问题 | **81**（r06 5 个，其余各 4 个） |
| 能力 | 81（每个问题一个能力 key，P2 粒度） |
| real | **68** |
| simulated | **4** |
| blocked | **9** |
| missing | 0 |
| 没有 v9 维度的能力 | **46 / 81** |

> 81 个问题 / 81 个能力是 P2 的刻意粒度：先把“每个问题需要一个能力”写清，
> 到 P4 再把同族能力合并成维度，而不是现在拍一个粗分类。

---

## 4. blocked 能力（9 个）

| 能力 | 提供者 | 原因 |
|---|---|---|
| `mvp.slice` / `mvp.prototype` / `mvp.learning` | r08 | `enters=false`，MVP 只做执行，不进报告 |
| `mvp.launch` | r08 + r09 | 两个都不进报告 |
| `tech.spec` / `tech.test` | r09 | 工程 0/8 可进报告技能 |
| `brand.tokens` | r10 | 设计 `enters=false` |
| `integration.contract` | r17 + r09 | 自动化与工程都不进报告 |
| `integration.webhook` | r17 | 自动化 `enters=false` |

**含义：** 今天做不了“工程/技术”“设计/品牌”“MVP/上线”“系统集成”这四类报告——
不是产线不会写，是**没有可进报告的证据提供者**。

---

## 5. simulated 能力（4 个）

| 能力 | 提供者 | 原因 |
|---|---|---|
| `brand.consistency` / `brand.production` | r11 | 内容角色可做定性判断，不能当品牌合规硬证据 |
| `content.structure` / `content.voice` | r11 | 结构与语调是定性 claim，不带数字 |

**含义：** 品牌/内容类报告只能写“建议/观察”，不能写“已合规/已达标”。

---

## 6. thin 角色（1 个）

| 角色 | 可进报告技能 | 说明 |
|---|---|---|
| r03 蛙守线 | 1/8 | 财务/合规只有 1 个可进报告技能；`finance.recon` / `finance.cash` 目前靠 r06 共同提供 |

**含义：** 财务类报告不能只靠 r03；必须有 r06 的数据口径，或补 r03 的可进报告技能。

---

## 7. 四个“不进报告”角色的处理

详见 [`REPORT-CAPABILITY-DECISIONS.md`](REPORT-CAPABILITY-DECISIONS.md)。结论：

- **r08 / r09 / r10 / r17 保持执行角色，不强行塞进报告；**
- 报告中对应的问题写 `gap`，由 coverage 判 `INCOMPLETE`；
- 要恢复，不是改产线，而是补“可进报告的证据契约”（测试报告 / diff / 令牌审计 / 重试日志）。

---

## 8. 对“任何业务”的含义

| 业务域 | 现状 | 能不能出决策级报告 |
|---|---|---|
| 市场 / 需求 / 价格 / 结构 | real（r05/r06） | **能** |
| 经营 / 成本 / TCO / 链路 | real（r15/r06） | **能** |
| 风险 / 合规 / 止损 | real（r01/r03/r04） | **能**（r03 薄，需 r06 配合） |
| 数据 / 模型 / 可靠性 | real（r18/r19/r20） | **能** |
| 客户 / 增长 / 内容 | real / simulated（r12/r13/r11） | **部分能**（内容只能定性） |
| 品牌 / 设计 | simulated / blocked（r10/r11） | **不能**（品牌硬证据缺） |
| 工程 / 技术 / MVP / 集成 | blocked（r09/r08/r17） | **不能**（证据提供者缺席） |

所以，“20 角色覆盖任何业务”在**组织层**成立，在**报告层**只对一半业务域成立。
这不是产线问题，是**证据契约问题**。

---

## 9. 复现

```bash
# 能力图
python -m core.capability_graph \
  --json workspace/report_upgrade/capability_graph.json --summary

# 或通过统一入口
python guagua.py report capabilities --graph

# 5 个水果问题
python -m core.coverage \
  --questions workspace/report_upgrade/questions_fruit.json \
  --graph workspace/report_upgrade/capability_graph.json \
  --json workspace/report_upgrade/coverage_fruit.json

# 15 个“任何业务” readiness 问题
python -m core.coverage \
  --questions workspace/report_upgrade/questions_fruit_broad.json \
  --graph workspace/report_upgrade/capability_graph.json \
  --json workspace/report_upgrade/coverage_fruit_broad.json
```

---

## 10. 维护规则

1. **新增能力 = 加问题**：在 `core/question_library.py` 的 `ROLE_QUESTIONS` 里加一行，不新开 thesis/frame/入口；
2. **改状态 = 改证据**：`real/simulated/blocked` 由 `report_roles` 的 `enters/eligible` + `SIMULATED_ROLES` 决定，不靠文案；
3. **P4 扩维度**：46 个能力没有 v9 维度，P4 在 `report_framework.DIMENSIONS` 里补组织/技术/可靠性/客户成功/交易/内容/数据模型，不另起一套报告类型；
4. **不许静默补人**：blocked 角色不能因为“报告需要”就被标成 real；缺就写 gap。
