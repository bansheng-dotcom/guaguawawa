# s01 内容策略与选题（brief / plan）方法论
> 蒸馏自: TBD: 待关联补充技能源文件
>


来源沉淀：`bzwh321__article-director-public`（topic-architect 的选题规划、content-planner
的选题卡与内容日历）+ `渭河科普文写作agent`（与 article-director 同源，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

选题是内容流水线最便宜的纠错点。本角色的立场：**选题不能靠灵感，要能校验**。
两个动作：
- `brief`：校验一张选题卡是否可执行——受众（audience）、痛点（pain_point）、
  渠道（channel）、差异点（differentiator）四字段齐备，渠道在平台白名单内，
  差异点必须具体可陈述，不能是「更好/更强/更多」这类空泛措辞。
- `plan`：校验一份内容规划——条目列表（items），每条含 topic/owner/due/status，
  status 在 `idea → briefed → drafting → editing → ready → published` 枚举内。

边界：本角色不做市场数据统计（交 R05 蛙深远），选题卡只要求差异点可陈述，
不要求市场规模数字；不替读者拍板（差异点也要落到「不同答案」而非「绝对正确」）。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`topic.channels`（10 个渠道）、`topic.status_enum`（6 态）。

**brief 校验规则**：
- `audience/pain_point/channel/differentiator` 任一为空串 → BLOCKER。
- `channel` 不在 `topic.channels` → BLOCKER（短路返回，topic_count=1）。
- `differentiator` 命中「更好/更强/更多/不一样/差异化/有特色/提升」且长度 <4 → BLOCKER。
- `audience` 为空 → BLOCKER。

**plan 校验规则**：
- `items` 非列表或为空 → BLOCKER（item_count=0）。
- 任一条目缺 `topic/owner/due/status` → BLOCKER。
- 任一条目 `status` 不在枚举内 → BLOCKER。

**输出键**：brief → `channel/topic_count`；plan → `item_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/brief.json`：audience=一人公司创始人、pain_point=没有稳定内容节奏、
  channel=公众号、differentiator=用确定性流水线替代灵感驱动 → ok=true、verdict=PASS。
- `examples/plan.json`：2 条（idea/briefed），owner=r11，due 具体 → ok=true、item_count=2。
- 脏夹具 `brief_dirty.json`：channel=论坛（不在白名单）+ differentiator=更好（空泛）→ ok=false / exit 1。
- 脏夹具 `plan_dirty.json`：status=todo（不在枚举）→ ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **渠道白名单要短路**：channel 非法时直接返回，别继续判差异点，否则脏数据会在
  差异点校验里「碰巧通过」，掩盖渠道问题。
- **差异点空泛判定要卡长度**：「更好」单看是空泛词，但「用确定性门禁替代灵感驱动」
  这类长句也含「更」字——所以规则是「命中空泛词 且 长度 <4」才拦，避免误杀。
- **status 枚举要外置**：内容日历的 status 会被业务反复加（比如加 `archived`），
  硬编码在技能里就要改代码；外置到 thresholds 后只改 JSON。
