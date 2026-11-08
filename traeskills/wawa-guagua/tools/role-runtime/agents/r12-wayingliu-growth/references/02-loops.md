# s02 增长循环与自然获客（flywheel / content）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/content-creation/SKILL.md
>


来源沉淀：`coreyhaines31__marketingskills`（marketing-loops 的增长飞轮、content-strategy
的内容获客）+ `retieedra-profound__skills-marketing-library`（自然获客 playbook，去重后不重复计数）。

## 一、方法论（什么时候用、核心口径）

增长循环是自然获客的骨架。本角色的立场：**循环不能只画箭头，要能校验闭环**。两个动作：
- `flywheel`：校验增长飞轮是否五环闭环——获客→激活→留存→推荐→营收 五环缺一不可，
  且循环定义（loop）六要素齐备。
- `content`：校验内容获客方案——渠道在白名单内，且声明与飞轮衔接。

边界：本角色产出获客循环与渠道清单，不产出具体内容正文（内容改写归 R11 蛙点题）；
循环只要求要素齐备与闭环，不替读者判断内容质量。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`loops.flywheel_rings`（五环）、`loops.content_channels`（公众号/知乎/小红书/
SEO/播客/视频号/B站/邮件）、`loops.loop_parts`（trigger/acts_when/purpose/self_check/
stop_condition/output）。

**flywheel 校验规则**：
- `rings` 非列表或长度≠5 → BLOCKER；五环任一缺失 → BLOCKER。
- `loop` 非对象 → BLOCKER；`loop_parts` 任一为空 → BLOCKER。

**content 校验规则**：
- `channels` 非列表或为空 → BLOCKER；任一渠道不在 `content_channels` → BLOCKER。
- `flywheel_link` 为空 → BLOCKER（必须声明内容如何接入飞轮）。

**输出键**：flywheel → `ring_count`；content → `channel_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/flywheel.json`：五环齐备 + loop 六要素齐备 → ok=true、ring_count=5。
- `examples/content.json`：渠道=公众号/知乎/小红书/SEO/播客 + flywheel_link 声明 → ok=true。
- 脏夹具 `flywheel_dirty.json`：rings 只有三环 + loop 缺要素 → ok=false / exit 1。
- 脏夹具 `content_dirty.json`：渠道=贴吧/论坛（不在白名单）+ 无衔接声明 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **闭环判定要数长度**：五环必须 `len(rings)==5` 且集合覆盖，只写「获客/激活/留存」
  三环时 `len` 判定先拦下，避免漏掉推荐与营收两环。
- **loop 要素要逐项判空**：六要素任一空串即 BLOCKER，不能用「loop 存在」替代「要素齐备」，
  否则空循环定义会混过去。
- **内容与飞轮要强制衔接**：光有渠道没有 flywheel_link 说明内容是孤岛，必须声明
  如何把内容流量导入留存/推荐环。
