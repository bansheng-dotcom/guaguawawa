# s05 市场规模测算（sizing）方法论

来源沉淀：`market-research-reports` TAM/SAM/SOM 确定性计算器 + 覆盖去重守则。

## 一、方法论（什么时候用、核心口径）

市场规模回答「天花板多大、够不够吃」。两个动作：
- `size`：TAM/SAM/SOM——自上而下与自下而上双口径互证 + 场景化。
- `sensitivity`：敏感性——每个 driver 的 swing/swing_pct，排序出关键驱动。

核心口径：TAM 只用单一口径是「方法依赖」结论，两口径一致（方差小）才是「方法无关」结论。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

场景枚举、方差阈值全部外置：`sizing.scenarios`（downside/base/upside）、
`sizing.variance_warning_pct`、`sizing.variance_critical_pct`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s05_sizing.*`）

**size 计算规则**：
- TAM_top = Σ 互斥分项 value（分项互斥由输入方声明，防重复计数）。
- TAM_bottom = customer_count × addressable_fraction × annual_quantity × price_per_unit。
- 方差 variance = |top − bottom| / max(top, bottom)；≥ critical 临界 FAIL，
  ≥ warning 预警 HIGH（阈值外置）。
- TAM = 双口径均值。
- SAM = TAM × serviceable_fraction；SOM = SAM × obtainable_share（两比例均须在 [0,1]）。
- bottom_up 四字段任一缺失/负数 → `sizing:bottom_up` HIGH；addressable_fraction ∉ [0,1]
  → `sizing:fraction_range` HIGH；场景比例 ∉ [0,1] → `sizing:scenario_fraction` HIGH。

**sensitivity 计算规则**：
- 每个 driver：swing = high − low；swing_pct = swing / base_value。
- 缺 base_value/low/high → `sizing:driver_fields` HIGH；low > high → `sizing:driver_range`；
  base_value ∉ [low,high] → `sizing:driver_base` HIGH。
- key_drivers = 按 swing_pct 降序取前 3。

**输出键**：size → `tam / tam_top / tam_bottom / variance / by_scenario / verdict / next`；
sensitivity → `sensitivity_matrix / key_drivers / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/sizing_size.json`（top_down 三组分 80/30/10；bottom_up 200×0.5×1×1.2）：
- TAM_top = 80+30+10 = 120；TAM_bottom = 200×0.5×1×1.2 = 120；
  variance = 0.0，TAM = **120.0**。
- base 场景（0.4/0.1）：SAM = 120×0.4 = **48.0**，SOM = 48×0.1 = **4.8**。
`examples/sizing_sensitivity.json`（base_value=120，3 driver）：
- key_drivers[0] = **客户数**（swing_pct=0.55），sensitivity_matrix 长 3。
脏夹具 `sizing_size_dirty.json`：双口径方差 ≥0.5 → ok=false（临界 FAIL 拦下）。
脏夹具 `sizing_sensitivity_dirty.json`：driver 区间/基数破坏 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **双口径设计成同一数值才是对的**：样例 TAM_top 和 TAM_bottom 刻意都等于 120，
  证明互证通过时均值稳定；不要为了「显得有两套」故意造差异——差异该由真实数据产生。
- **variance 用 max(top,bottom) 做分母**：两者同为零时 ref=0 直接 variance=0，避免除零。
- **`by_scenario` 里 bad 场景要 continue 不产出**：比例越界时该场景跳过且记 HIGH，
  但已合法场景仍正常算——门禁拦单条，不殃及整批。
- **key_drivers 排序键是 swing_pct 不是 swing 绝对值**：swing=500 的「单价」看似摆动最大，
  但 swing_pct 只有 0.4167，反而排不进第一；「客户数」swing_pct=0.55 才是资源该押的变量。
- **`tam / by_scenario` 是证据数字**：登记进 `review.evidence_keys`，否则 T7 误杀干净产出。
