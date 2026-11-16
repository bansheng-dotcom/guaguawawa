# 报告产线 v3 升级方案：从「模板填数」到「技能编排 + 证据推理」

> 2026-11-15 · 基于现有 v2 产线（`report pack` + 章节稿 + 逐节过账）
> 目标：一份报告里，**每个章节都由真实角色技能跑出来的证据支撑**，20 个角色的能力不再闲置，
> 报告能落到「单店/毛利/SKU/阈值」这一档业务决策。
>
> **执行状态（2026-11-15 17:00）**
> - P0 技能编排：**已完成**。`report produce` 跑通，家居百货实测 5 技能 / 2 角色 / 25 claim。
> - P1 证据图 + 评测：**已完成（基础版）**。`claims.json` / `skill_trace.json` / `judge.json` 落盘；
>   冲突检测、缺口标记、rubric 100 分制已接入；LLM judge 与基线回归留到有基线样本后接。
> - P2 落地业务数据：**阻塞**。缺门店 POS / 商品毛利 / 库存，单店模型、SKU 结构、补货规则只能先建接口。
> - 测试：`tests/test_report_produce.py`（4 条）＋全仓 137 条全绿。

---

## 一、先说诊断：为什么现在还是模板

上一版（`workspace/reports/home_research_2026-11`）被判定为模板，根因不是措辞，是三层断点：

| 断点 | 表现 | 后果 |
|---|---|---|
| **没有技能调用** | 全篇数字来自 `evidence_pack`，而 pack 只是把 JSON 摊平 | 20 个角色的技能一个都没跑，报告不可能有新判断 |
| **没有证据图** | 结论 → 数字，中间没有「哪个技能算的、用什么公式、和谁冲突」 | 数字对了也只是复述，错了查不出来 |
| **没有评测** | 只查「标题带数、数字可解释」 | 结构合规但业务价值为零，也能 PASS |

v2 补了「公式可复算」（26 个派生量逐条验算），但**仍然是"我算"，不是"角色算"**。
真正的差别在于：市场规模该由 r05 的 `sizing` 跑，结构该由 r06 的 `explore` 跑，
成本该由 r15 的 `tco` 跑——报告只是这些技能结果的编排。

---

## 二、借鉴：GitHub 上已经跑通的做法

| 来源 | 核心做法 | 落到我们哪 |
|---|---|---|
| [stanford-oval/storm](https://github.com/stanford-oval/storm) | 写长文分两段：**先研究出提纲，再按提纲写**；提纲靠「多视角提问」而不是直接让模型想；正文每句挂引用 | `section_plan`：章节由不同角色视角提问生成，不是我拍脑袋定 9 节 |
| [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) | **supervisor → 并行 researcher → compression → 终稿**；同一任务多研究员并行，最后压缩合并；评测用 Deep Research Bench 的 LLM judge | 章节并行调度多个角色技能；`report_judge` 用 rubric + 基线回归 |
| [hwfengcs/SDYJ_Multi_Agents](https://github.com/hwfengcs/SDYJ_Multi_Agents) | 任务规划 + human-in-the-loop + 多源检索 + **evidence-grounded 报告** + 全链路 tracing | `claim_graph`：结论必须挂证据，trace 可回放 |
| [qinyu8028/sage-research](https://github.com/qinyu8028/sage-research) | **quality-gated retrieval**（检索先过质量门，再进写作）+ 结构化报告 | 技能结果先进门禁（`ok` / 口径 / 覆盖），不合格的不进报告 |
| [vis-nlp/DSAgentBench](https://github.com/vis-nlp/DSAgentBench) | 数据科学任务按**产物**评分（artifact-level），不是按文字 | 评测看「报告里有没有可执行的业务表」，不看字数 |
| [dzhng/deep-research](https://github.com/dzhng/deep-research) | 递归「问题 → 子问题 → 检索 → 反思」的深度优先研究 | 每节的追问链：答不上就列为缺口，不硬写 |

一句话总结借鉴：**提纲先行（STORM）+ 并行研究（Open Deep Research）+ 证据落地（SDYJ/Sage）+ 产物评分（DSAgentBench）**。

---

## 二·五、已实测：技能调用长什么样

不是纸面设计。刚跑了一次真实技能：

```bash
python r06-wadeqing-analyst/agent.py describe \
  --input 家居百货内蒙调研_2026-11-15/data/category_long2.csv --col growth
```

返回：

```json
{"describe": {"growth": {"count": 22, "mean": 0.0745, "median": 0.047,
                         "std": 0.1516, "min": -0.1, "max": 0.695,
                         "p5": -0.0506, "p95": 0.2055, "skew": 3.0121}},
 "conclusion": "均值 0.0745，中位数 0.047，偏度 3.0121。",
 "provenance": {"skill": "describe", "input_hash": "5acb4e1824cd"}}
```

三个结论：

1. **技能自带 provenance 与 input_hash** —— 报告里的数字天然可回放，不用我另建一套。
2. **技能会自己给结论**（`mean 0.0745 / median 0.047 / skew 3.01`），但它不知道这段结论该放在第几节——
   这正是 `section_plan` 要解决的。
3. **每个 action 的输入契约不同**（`describe` 要 `--col`，`explore` 要 `--date/--value`）。
   全仓 20 角色 / 201 个技能，不能一把梭；P0 的第一件事就是把「输入契约」标出来。

---

## 三、目标架构（v3）

```
意图
 │
R01 选报告画像 profile（市场调研 / 经营诊断 / 链路优化 / 营销方案 / 负毛利整改 / 趋势预测）
 │
R01 出「章节计划」section_plan.json
 │   每节 = { 问题, 需要的技能能力, 验收判据, 缺什么就写缺口 }
 │
技能调度 skill_dispatch（并行）
 │   ├─ r05 sizing / sensitivity / ledger      市场规模与证据台账
 │   ├─ r06 explore / groupby / correlate       结构与量价
 │   ├─ r13 health / qbr / churn                客户与续约
 │   ├─ r15 tco / quote / inventory             成本、毛利、供应链
 │   ├─ r14 order / refund                      交易与履约
 │   ├─ r19 abtest / power / eval               实验与显著性
 │   └─ r03 healthcheck / tax                   财务红线
 │
证据图 claim_graph.json
 │   claim（一句话判断）← computation（公式 + 技能结果 id）← observation（原始观测 id）
 │   跨来源冲突单独成节
 │
章节写作（模型）
 │   只能引用 claim 里的数字，不能自己再算
 │
渲染 core/report_renderer → 一份报告
 │
评测 report_judge（rubric + 基线回归）→ 不达标不进交付
```

关键改变：**报告里出现的每一个数字，都能回答「哪个角色、哪个技能、哪次运行、什么公式」**。

---

## 四、20 角色能力矩阵（报告章节 ← 角色技能）

> 实测盘点：**20 个角色 / 201 个技能**（`workspace/_skills_inventory.tsv`）。
> 下表只列与报告直接相关的动作，括号里是真实技能名。

| 报告章节 | 主责角色 | 该跑的技能/动作（真实名） | 产出 |
|---|---|---|---|
| 市场规模与测算 | r05 | `sizing` / `scenario` / `tam-mc` | 三条路径 + 敏感性区间 |
| 结构与量价 | r06 | `describe` / `explore`(trend/groupby/segment) / `correlate` | 增速分解、价量拆分 |
| 根因与贡献 | r06 | `rootcause`(decompose/drilldown) / `regression` / `chi2` | 贡献度、显著性 |
| 客户与留存 | r13 | `health`(health/risk) / `voc` / `pipeline` | 健康分、续约风险 |
| 成本与毛利 | r15 | `tco`(compare/lifecycle) / `safety-stock` / `fulfill-sim` | 单件成本、安全库存 |
| 品类与选品 | r14 | `selection`(score/profit) / `elasticity` | 上架淘汰评分 |
| 交易与履约 | r14 | `order` / `payment`(refund) / `workflow` | 订单三态、退款合规 |
| 促销与投放 | r12 | `diagnose` / `roi` / `activation` | 投放 ROI、漏斗 |
| 内容与转化 | r11 | `brief` / `longform` / `xhs` | 内容策略与稿件 |
| 产品与需求 | r07 | `prd` / `rice` / `northstar` | 需求优先级 |
| 组织与人效 | r16 | `hiring` / `attendance` / `perf` | 人效、编制 |
| 财务红线 | r03 | `cfo` / `tax` / `audit` | 现金流、合规 |
| 数据可信度 | r18 | `quality` / `profile` / `catalog` | 数据质量六维 |
| 实验与显著性 | r19 | `evaluation` / `eval-ci` / `trace` | p 值、MDE、样本量 |
| 可靠性与恢复 | r20 | `slo` / `backup` / `drill` | SLO、RTO/RPO |
| 自动化与集成 | r17 | `webhook` / `retry` / `mapping` | 集成契约 |
| 工程与实现 | r08/r09 | `slice` / `tdd` / `arch` | 技术方案 |
| 视觉与物料 | r10 | `vi` / `ui` / `imgops` | 版式与素材 |
| 决策与反方 | r01 | `decide` / `redteam` / `ev` | 决策卡、反方挑战 |
| 独立评审 | r04 | `criteria` / `quality` / `facts` | PASS/FAIL 与缺陷 |
| 排期与交接 | r02 | `schedule` / `handoff` / `process` | 排期与验收 |

**规则**：一份报告不要求 20 个角色全上，但必须满足
「引用的技能结果 ≥ 6 个、覆盖角色 ≥ 4 个、每个业务章节至少挂 1 个技能结果」。
跑不到的章节写「缺口」，不许用文字补。

---

## 五、改造清单

### P0 · 让技能真的跑起来（1 周）

| # | 交付 | 文件 | 验收 |
|---|---|---|---|
| 1 | 技能注册表：角色 → 能力 → action → **输入契约**（201 个技能先标与报告相关的 40 个） | `core/skill_graph.py`（新） | `python guagua.py skills --graph` 列出 action 与必填参数；调度器能按契约拼参数 |
| 2 | 章节计划：profile → 章节问题 + 需要的能力 | `core/section_plan.py`（新） | 每个 profile 出 6—9 节，每节声明 `needs: [r05.sizing, r06.explore]` |
| 3 | 调度器：按节并行调角色，收 result，失败标缺口 | `core/skill_dispatch.py`（新） | 一份报告实际调用 ≥ 6 个 action，可复现（带 seed/输入哈希） |
| 4 | 章节草稿只能引用技能结果 | 扩 `s09_interpret` | 无 skill 结果的节 → 拒绝渲染 |

**验证样例**：用家居百货数据，跑 `r05.sizing + r06.explore + r15.tco`，产出一份「市场规模 + 结构 + 成本」三节报告，
每节挂真实技能结果 id。

### P1 · 证据图与冲突（1—2 周）

| # | 交付 | 文件 | 验收 |
|---|---|---|---|
| 5 | claim / computation / observation 三层图 | `core/claim_graph.py`（新） | 100% 的 claim 可回放到 observation |
| 6 | 冲突检测：同一指标跨来源差异 > 5% 必须单列 | 同上 | 家居百货的牛肉两口径 37.28/35.03 自动成节 |
| 7 | 评测：rubric（结构/证据/推理/落地/边界）+ LLM judge + 基线 | `core/report_judge.py`（新） | 每类报告录一次基线，低于基线不进交付 |

### P2 · 落地业务数据（2—4 周，依赖数据）

| # | 交付 | 依赖 | 验收 |
|---|---|---|---|
| 8 | 单店模型：面积 × 坪效 × 客流 → 年销 / 回本周期 | POS + 租约 | 一家店的投资回收期可算 |
| 9 | SKU 结构：价格带 × 毛利 × 周转 → 上架/淘汰清单 | 商品主数据 + 毛利 | 给出「上 30 个、下 20 个」的具体清单 |
| 10 | 补货规则：安全库存 = f(周销, 提前期, 波动) | 库存 + 到货 | 断货率与滞销率双降的阈值 |

> P2 不是写不写的问题，是**有没有数据**的问题。没有 POS/毛利，就只能写缺口——
> 这也是上一份报告里「单店/毛利」只给了天花板、没给模型的原因。

---

## 六、门禁（G1—G5，新增，进 CI）

| # | 判据 | 阈值 |
|---|---|---|
| G1 | 技能覆盖 | 技能结果 ≥ 6 个、角色 ≥ 4 个 |
| G2 | 证据链完整 | claim → observation 回溯率 100% |
| G3 | 冲突显式 | 同指标跨来源差异 > 5% 时必须有冲突节 |
| G4 | 落地性 | 至少 1 节含阈值/停止条件/责任人 |
| G5 | 评测 | rubric 分 ≥ 该类报告基线 |

---

## 七、风险与回滚

| 风险 | 处理 |
|---|---|
| 技能调用慢（20 角色 × 1.3s） | 按节并行；缓存 result（输入哈希） |
| 技能输出口径不一致 | 进报告前必须过 `data_contract` 检查，不合格标缺口 |
| 模型写作退化成模板 | G2/G4 拦：没有 claim 不许写、没有阈值不许收尾 |
| 旧产线回滚 | v2 的 `report run` 保留，profile=sections 与 profile=skills 并存 |

---

## 八、需要你拍板的三件事

1. **优先级**：先做 P0（技能编排跑通）还是先做 P1（证据图 + 评测）？我建议 P0，因为它直接回答「20 个角色有没有被用到」。
2. **评测基线**：rubric 用 LLM judge 还是先用人评 5 份定基线？后者稳，前者快。
3. **P2 数据**：门店 POS / 商品毛利 / 库存，哪一份能拿到？拿不到，落地那一档就只能标缺口。

---

## 附：与 v2 的关系

- v2 已有：证据包（`report pack`）、章节稿、逐节过账（公式 + refs + 假设参数）、9 条门禁。
- v3 在其上加三件：**技能调度**、**证据图**、**评测**。
- v2 的产物不作废：`draft_sections` 变成「章节计划 + 技能结果」的下游，写作接口不变。
