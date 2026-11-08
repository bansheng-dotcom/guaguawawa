# s09 自媒体运营（daily / probe）方法论
> 蒸馏自: 补充技能/01-当前能力域/bzwh321__self-media-data-console-bzwh/SKILL.md
>


来源沉淀：`bzwh321__self-media-data-console-bzwh`（self-media-console-workflow 的多平台数据
看板、self-media-attribution 的自媒体归因）+ `自媒体工作台-trae`（与 bzwh321 同源，去重后
不重复计数）。

## 一、方法论（什么时候用、核心口径）

自媒体运营是自然获客的内容阵地。本角色的立场：**日报不能靠感想，要能定结论；数据不能
靠假装，要能如实降级**。两个动作：
- `daily`：校验一份运营日报——date/platform_summary/conclusion 三件套齐备、平台在
  白名单、指标字段在白名单。
- `probe`：探测数据接入——恒 ok=true，缺数据只反映在 status=blocked（如实降级）。

边界：本角色只产出看板与日报口径，不真拉取平台数据（真实数据接入需用户配置）；
数据探测是「如实降级」而非门禁，缺数据不判 FAIL。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`selfmedia.daily_required`（date/platform_summary/conclusion）、
`selfmedia.platforms`（公众号/B站/小红书/抖音/知乎/微博）、`selfmedia.metric_fields`
（month_net_followers/month_net_revenue/month_content_count/month_views）。

**daily 校验规则**：
- 三件套任一为空 → BLOCKER。
- `platform_summary` 非列表或为空 → BLOCKER。
- 任一行 `platform` 不在 `platforms` → BLOCKER。
- 任一行指标字段不在 `metric_fields`（platform 自身除外）→ BLOCKER。

**probe 规则**：
- 恒 `ok=true`、`verdict=PASS`。
- 探测数据根是否存在 demo → `status=ready`，否则 `status=blocked`。
- 输出键 `detected` 记录是否检测到数据。

**输出键**：daily → `platform_count`；probe → `status/detected`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/daily.json`：三件套齐备 + 3 平台（公众号/B站/小红书）+ 指标字段合法 → ok=true。
- `examples/daily_dirty.json`：date 空 + platform=抖音国际版（不在白名单）→ ok=false / exit 1。
- `probe`：本机未检测到数据源时 `status=blocked`、`detected=false`，但 `ok=true`（如实降级）。

## 四、实战踩坑（真拦下来的教训）

- **probe 是降级不是门禁**：数据探测恒 ok=true，缺数据只反映在 status=blocked，这是
  「如实降级」——不能因为本机没接数据就判 FAIL，否则 probe 失去了探测本意。
- **指标字段白名单要放行 platform**：platform_summary 每行除了指标还有 platform 标识键，
  判指标字段白名单时必须跳过 platform/platform_name，否则会把合法行误判为越界。
- **平台白名单外置**：平台会随业务扩展（比如加「视频号」「X」），外置到 thresholds 后
  只改 JSON，不改代码。
