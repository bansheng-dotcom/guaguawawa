# s02 行业与市场扫描（industry）方法论

来源沉淀：`market-research-reports` 竞争者与集中度分析 + `database-lookup`（80 个公共数据库）。

## 一、方法论（什么时候用、核心口径）

行业扫描回答「市场长什么样、钱在哪」。两个动作：
- `landscape`：行业格局地图——players 归属 role/segment、value_chain 利润池。
- `concentration`：市场集中度——HHI、CR4/CR8、市场结构定级。

利润池逻辑：`value_chain` 各环节按 margin_pct 呈现——钱在哪个环节，进入策略就偏向哪里。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

角色白名单、集中度阈值全部外置：`industry.player_roles`（5 类）、`industry.hhi_thresholds`
（competitive/moderate/oligopoly 三档边界）、`industry.cr_n`（[4,8]）、`industry.min_players`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s02_industry.*`）

**landscape 校验规则**：
- player.role 不在白名单 → `industry:player_role` HIGH。
- player.segment 引用了不存在的 segment → `industry:player_segment` HIGH。
- value_chain 为空 → `industry:value_chain` CRITICAL。
- profit_structure 按环节输出 stage/players/margin_pct。

**concentration 计算规则**：
- HHI = Σ(share²)，份额为**百分数口径**（42² + 25² + …，不是 0.42²）。
- CR4 / CR8 = 前 4 / 前 8 名份额合计（cr_n 外置）。
- 份额合法性：每项正数（`industry:share_positive`）、总和在 100±5 容差内（`industry:share_sum`）。
- 市场结构四档 competitive/moderate/oligopoly/monopoly 由 `industry.hhi_thresholds` 判定，
  边界数值以 thresholds.json 为准。

**输出键**：landscape → `player_count / segment_count / value_chain_stages /
profit_structure / role_distribution / verdict / next`；concentration → `hhi / cr4 / cr8 /
market_structure / total_share / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/industry_landscape.json`（4 player / 3 segment / 3 环节）：
- player_count=4，segment_count=3，value_chain_stages=3，profit_structure 长 3，verdict=PASS。
`examples/industry_concentration.json`（份额 42/25/15/10/8）：
- HHI = 1764+625+225+100+64 = **2778**，CR4 = **92**，CR8 = **100**，
  market_structure = **oligopoly**，total_share = 100，verdict=PASS。
脏夹具 `industry_concentration_dirty.json`：份额总和/正数破坏 → ok=false（门禁拦下）。

## 四、实战踩坑（真拦下来的教训）

- **份额口径必须是百分数**：HHI 用 42² 不是 0.42²，两套口径差 10000 倍，直接改变市场结构定级。
- **`hhi` / `market_structure` 是证据不是描述**：这两个是集中度的核心结论数字，
  必须登记进 `review.evidence_keys`，否则 T7 evidence_gate 会把干净产出误判成「无证据」。
- **总和容差 100±5 是防手抄错份额**：份额漏填、多填一个玩家都会破总和，先验正数再验总和，
  顺序不能反（负份额会让总和假性通过）。
- **min_players 与 CR4 口径不要混**：min_players 是「至少几个玩家才有集中度可算」，
  CR4 是「前四名合计」，前者不足直接 HIGH，后者永远可算。
