# s04 商业模式与变现（business）方法论

来源沉淀：`market-research-reports` 价值链分析 + `scientific-brainstorming` 评估框架。

## 一、方法论（什么时候用、核心口径）

商业模式回答「怎么赚钱、赚得健康吗」。两个动作：
- `canvas`：商业画布——九块齐备 + fit 一致性。
- `monetize`：变现模式——单位经济（毛利 / LTV:CAC / 回本）。

边界：只测算健康度，不做「该不该投」的决策。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

九块清单、模式白名单、健康阈值全部外置：`business.canvas_blocks`（9 块）、
`business.monetization_types`（8 类）、`business.ltv_cac_healthy`、
`business.ltv_cac_warning`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s04_business.*`）

**canvas 校验规则**：
- 九块任一缺失或为空字符串 → 记入 fit_gaps，`business:canvas_block` HIGH。
- monetization_paths = revenue_streams/value_propositions/customer_segments 中非空块数。

**monetize 计算规则**：
- model.type 不在白名单 → `business:model_type` HIGH。
- unit_economics 必填四元组 price/cogs/cac/ltv，缺一 → `business:unit_economics` HIGH。
- gross_margin = (price − cogs) / price。
- ltv_cac_ratio = ltv / cac。
- break_even = cac / (price − cogs)（毛利为 0 或负时 break_even 为 None）。
- LTV:CAC 三档：≥ healthy 健康 / ≥ warning 预警 HIGH / < warning 不健康 CRITICAL
  （边界数值以 thresholds.json 为准）。

**输出键**：canvas → `blocks_complete / fit_gaps / monetization_paths / verdict / next`；
monetize → `gross_margin / ltv_cac_ratio / break_even / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/business_canvas.json`（九块全填）：
- blocks_complete=9，fit_gaps=[]，verdict=PASS。
`examples/business_monetize.json`（subscription，price=1200/cogs=300/cac=800/ltv=4800）：
- gross_margin = (1200−300)/1200 = **0.75**，
- ltv_cac_ratio = 4800/800 = **6.0**（≥ 3.0 健康），
- break_even = 800/(1200−300) = 800/900 = **0.8889**，verdict=PASS。
脏夹具 `business_canvas_dirty.json`：缺块 → fit_gaps 非空，ok=false。
脏夹具 `business_monetize_dirty.json`：LTV:CAC 不健康或 type 越白名单 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **break_even 除零要显式 None**：price−cogs ≤ 0 时不能算回本，返回 None 而非 0——
  0 会误导「回本 0 客户」，None 才是「无回本口径」。
- **LTV:CAC 三档边界是业务口径，不是技能逻辑**：healthy=3.0/warning=1.0 外置在
  thresholds.json，改「多健康才算健康」只改阈值，不动 `monetize` 代码。
- **canvas 只查「齐不齐」，不查「对不对」**：九块全填就 PASS，块与块之间的逻辑断裂
  （如客群是个人、收入却是企业订阅）是 LLM/人审的活，确定性门禁不越界替人判断。
- **gross_margin / ltv_cac_ratio 是证据数字**：要登记进 `review.evidence_keys`，
  否则 T7 evidence_gate 会误判 monetize 产出「无证据」。
