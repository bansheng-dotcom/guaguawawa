# R05 蛙深远（战略研究官）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/product-management/synthesize-research/SKILL.md
>


> R05 只做战略研究：证据台账、行业扫描、竞品情报、商业模式、市场规模、
> 情景推演、研究自动化。**只呈现证据与选项，不替你拍板。**
> 核心红线：claims 必须挂来源（无源断言 = FAIL）；决策词（建议/应该/决定）不出现在结论文本。已引入真实执行层，不再仅仅是门禁校验。

## 运行方式

```bash
python agent.py manifest                     # 角色能力清单
python agent.py demo                         # 用真实示例跑代表性动作
python agent.py <skill> <action> --input examples/<fixture>.json
python agent.py run --task <task_id>          # workspace 协议（intent 路由）
python agent.py contract list|validate ...
python agent.py review --packet <packet.json> # T7 对抗评审
python agent.py case [<case_id>]              # 案例库
python agent.py harness materials|verdict|plan|runlog ...
python run_tests.py                           # 全量断言测试
python verify_loop.py                         # 闭环矩阵（28 行全绿）
```

技能只做确定性计算，无 LLM 调用；退出码：ok=true → 0，否则 1；
`__AGENT_RESULT__ {json}` 单行供编排器消费。

## 技能总览（7 技能 × 14 动作）

| 技能 | 动作 | 说明 |
|---|---|---|
| research 深度研究 | ledger | 证据台账：claims 挂 sources，覆盖率 1.0 才 PASS |
| research 深度研究 | report | 研究报告：章节 claim 引用核验、citation_coverage |
| industry 行业扫描 | landscape | 行业地图：players/segments/value_chain、利润池 |
| industry 行业扫描 | concentration | 集中度：HHI、CR4/CR8、市场结构定级 |
| competitor 竞品情报 | matrix | 竞品矩阵：特征白名单取值、我方覆盖、gaps |
| competitor 竞品情报 | battlecard | 战斗卡：五段齐备、威胁定级、定位重叠 |
| business 商业模式 | canvas | 商业画布：九块齐备、fit 一致性 |
| business 商业模式 | monetize | 变现：单位经济（毛利/LTV-CAC/回本） |
| sizing 市场规模 | size | TAM/SAM/SOM：双口径互证、场景化 |
| sizing 市场规模 | sensitivity | 敏感性：swing_pct 排序、key_drivers 前 3 |
| scenario 情景推演 | pestel | PESTEL：六类齐、证据全覆盖 |
| scenario 情景推演 | premortem | 事前尸检：风险评分、高风险须缓解+预警 |
| auto 研究辅助 | plan | 研究计划：问题/来源/方法白名单、覆盖矩阵 |
| auto 研究辅助 | track | 运行追踪：完成率、覆盖缺口显式列出 |

## 边界声明

- **in_scope**：行业/市场/竞品研究、市场规模测算、情景推演、证据台账与研究报告
- **out_of_scope**：数据分析结论（归 R06）、正式财务/法律判断（归 R03）、替老板决策
- **never**：无源断言（claims 必须挂来源）、替你拍板（决策权在老板）、结论文本含推测措辞

## 输入契约

每个动作的输入/输出 JSON Schema 登记在 `contracts.py`：
`python agent.py contract list` 查看；输出硬口径 `ok:boolean + checks:array + verdict`。

## 阈值外置

全部枚举/禁词/模式/评分口径在 `experience/thresholds.json`
（claim_kinds、source_types、hhi_thresholds、matrix_value_types、
battlecard_sections、monetization_types、ltv_cac_healthy、variance 阈值、
pestel_categories、risk_thresholds、method_whitelist、review 禁词等）。
改口径不改代码。

## 意图路由（run --task 的 intent 关键词 → 动作）

| 关键词示例 | 路由 |
|---|---|
| 证据台账 / evidence ledger | research/ledger |
| 研究报告 / research report | research/report |
| 行业地图 / 价值链 / landscape | industry/landscape |
| 市场集中度 / HHI / CR4 | industry/concentration |
| 竞品矩阵 / feature matrix | competitor/matrix |
| 战斗卡 / battlecard | competitor/battlecard |
| 商业画布 / business canvas | business/canvas |
| 变现 / LTV / monetize | business/monetize |
| 市场规模 / TAM / SAM / SOM | sizing/size |
| 敏感性 / sensitivity | sizing/sensitivity |
| 宏观分析 / PESTEL | scenario/pestel |
| 事前尸检 / pre-mortem | scenario/premortem |
| 研究计划 / research plan | auto/plan |
| 研究追踪 / research track | auto/track |
| （兜底） | research/ledger |

## 对抗评审（T7 五检查）

对研究产出本身再评审（`review.py`）：
1. **unsourced_gate**：verdict=PASS 却有 orphan_claims/coverage_gaps/evidence_coverage<1 → react
2. **evidence_gate**：verdict=PASS 却无任何证据字段 → react
3. **decision_gate**：结论含决策词（建议/应该/决定/recommend/must/decide）→ writer
4. **scope_boundary**：结论含越界词（回归分析/统计检验/审计意见/法律意见）→ writer（移交 R06/R03）
5. **hedge_words**：结论含推测措辞（可能/大概/预计/should/probably）→ writer

## 案例库

- `competitor-deep-dive`：竞品矩阵 → 战斗卡（威胁定级对拍）
- `market-entry`：证据台账 → 规模测算 → 失效推演 → 运行追踪（四步 expect 对拍）

## 测试

```bash
python run_tests.py     # T01-T15 全量断言
python verify_loop.py   # 28 行闭环矩阵（14 干净 + 14 脏数据）
```

## 来源

- 补充技能：`karpathy__autoresearch`（自主研究循环范式）、
  `K-Dense-AI__scientific-agent-skills`（market-research-reports 的
  TAM/SAM/SOM 计算器、competitor matrix、evidence ledger）
- 方法论：`references/s01` – `references/s07`

---

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `industry-panorama-research` · 行业全景研究（规范；消费方：r01, r12）
- `market-intelligence-radar` · 市场情报雷达（规范；消费方：r12, r01）
- `tashan-research-skills` · 学术研究与写作（规范；消费方：r11, r04）

查看：`python guagua.py capabilities --role r05`

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `industry-panorama-research` · 行业全景研究（规范；消费方：r01, r12）
- `market-intelligence-radar` · 市场情报雷达（规范；消费方：r12, r01）
- `tashan-research-skills` · 学术研究与写作（规范；消费方：r11, r04）

查看：`python guagua.py capabilities --role r05`
