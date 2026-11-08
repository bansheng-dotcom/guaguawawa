# s06 宏观与情景推演（scenario）方法论

来源沉淀：`what-if-oracle` 六分支情景 + `hypothesis-generation` 可证伪口径。

## 一、方法论（什么时候用、核心口径）

情景推演回答「什么会杀死这个项目、怎么提前看见」。两个动作：
- `pestel`：PESTEL 宏观分析——六类因子齐全 + 证据覆盖。
- `premortem`：事前尸检——假设「一年后项目已死」倒推死因，风险评分排序。

核心口径：找不到缓解的死因本身就是最大的死因——高风险场景必须带缓解与预警。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

类别、评分、风险阈值全部外置：`scenario.pestel_categories`（6 类）、
`scenario.impact_scale`、`scenario.probability_scale`（各 1/2/3 档）、
`scenario.risk_thresholds`（low/medium/high 边界）。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s06_scenario.*`）

**pestel 校验规则**：
- factor.category 不在白名单 → `scenario:category` HIGH。
- 六类任一为空 → `scenario:category_coverage` HIGH。
- factor 无 evidence（须来源或「待核实」标记）→ `scenario:factor_evidence` HIGH。
- factor.impact 不在分级白名单 → `scenario:factor_impact` HIGH。
- evidence_coverage = 有证据因子数 / 总因子数。

**premortem 计算规则**：
- risk_score = probability × impact（各取 1/2/3，乘积 1–9）。
- 分层：< low / < medium / < high / ≥ high 四档（阈值外置）。
- 声明 risk_level 与计算不一致 → `scenario:risk_level_consistency` HIGH。
- high/critical 却无 mitigation → `scenario:mitigation_required` HIGH；
  无 early_warning → `scenario:early_warning_required` HIGH。
- risk_ranking 按 risk_score 降序（同分按名称），highest_risk 取首。

**输出键**：pestel → `categories_checked / total_factors / evidence_coverage /
impact_summary / verdict / next`；premortem → `scenario_count / risk_ranking /
highest_risk / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/scenario_pestel.json`（6 类各 1 因子，全带证据）：
- categories_checked=6，total_factors=6，evidence_coverage=1.0，
  impact_summary = {high:3, medium:2, low:1}，verdict=PASS。
`examples/scenario_premortem.json`（3 场景）：
- 「巨头碾压」high×high = 3×3 = **9** → risk_tier=**critical**，highest_risk 即它；
  「预算冻结」medium×medium = 2×2 = **4** → medium；
  「合规收紧」low×medium = 1×2 = **2** → low。
脏夹具 `scenario_pestel_dirty.json`：缺类/无证据 → categories_checked<6 且 evidence_coverage<1，ok=false。
脏夹具 `scenario_premortem_dirty.json`：声明风险等级与计算不一致 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **风险分层边界是乘积不是分档加和**：score=3 是 low（< medium 边界），score=4 就 medium，
  score=9 直接 critical——边界数值以 `scenario.risk_thresholds` 为准，勿手抄。
- **声明等级与计算等级必须对拍**：输入自己写 risk_level 是「拍脑袋」，
  与 probability×impact 算出来的不一致就要 FAIL，不许让输入方自证。
- **high/critical 无缓解必 FAIL 是硬门禁**：mitigation 与 early_warning 缺一不可，
  这是「失效推演」区别于「危险清单」的关键——没有预警信号的死因等于没提前看见。
- **`impact_summary / evidence_coverage / risk_ranking` 是证据数字**：登记进
  `review.evidence_keys`，否则 T7 evidence_gate 误杀干净产出。
