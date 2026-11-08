# s04 品牌 VI 与设计令牌（brand / vi·token）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/design-system/SKILL.md
>


来源沉淀：`jgerton__brand-toolkit`（brand-visual-identity / brand-audit / brand-voice）
+ `mae616__design-skills` 的 token 纪律。

## 一、方法论（什么时候用、核心口径）

「视觉身份必须策略驱动」。两个动作：
- `vi`：校验品牌视觉身份——directions ≥3（Stylescape 三方向，每方向 name/palette/
  typography/imagery/narrative 五要素齐）、反陈词滥调、voice 四维齐备。
- `token`：校验设计令牌——tokens.color/typography/spacing 三类均 ≥1（name+value）、primary 为合法 hex。

核心红线：**narrative 不许出现「因为蓝色代表信任」「看起来专业」「显得高端」这类
无信息量的通用空话**；voice 四维（tone/word_choice/cadence/forbidden）是「可以做什么」
与「不许做什么」的边界，缺一不可。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`brand.stylescape_dirs_min`（3）、`brand.voice_dimensions`（4 维）。

**vi 校验规则**：
- `directions` <3 → BLOCKER。
- 每方向缺 name/palette/typography/imagery/narrative 任一 → BLOCKER。
- narrative 含陈词滥调（「因为蓝色代表信任」「看起来专业」「显得高端」「lorem」）→ BLOCKER。
- `voice` 四维任一空 → BLOCKER。

**token 校验规则**：
- `tokens.color` / `tokens.typography` / `tokens.spacing` 任一缺失或空 → BLOCKER。
- 每个 token 缺 name/value → BLOCKER。
- `primary` 非合法 hex → BLOCKER。

**输出键**：vi → `direction_count`；token → `token_count/primary`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/vi.json`：3 个方向（各五要素齐）、narrative 无陈词滥调、voice 四维齐 → ok=true、direction_count=3。
- `examples/token.json`：三类 token 各 1 条（name+value）+ primary=#1E3A5F → ok=true、token_count=3。
- 脏夹具 `vi_dirty.json`：1 个方向且 narrative="因为蓝色代表信任"、voice 四维空 → ok=false / exit 1。
- 脏夹具 `token_dirty.json`：只有 color 空数组 + primary="blue" → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **陈词滥调是子串匹配但要精确**：直接 `if cliche in narrative`，用「因为蓝色代表信任」
  这种带因果的完整短句当锚点，比单查「信任」更准，避免误伤「建立用户信任」这类正常叙事。
- **五要素用字符串判**：palette/typography/imagery 在 Stylescape 阶段是「方向描述」不是
  结构化对象，`str(d.get(key, "")).strip()` 判非空即可，别要求它们是 hex 或数组。
- **voice.forbidden 也是必填**：四维里 forbidden（禁用词/禁区）最容易漏，它承载
  「不许写什么」的边界，缺了就等于品牌没有约束。
- **token 三类平权**：color 有值但 typography 空，照样 BLOCKER——三类令牌缺一类，
  设计系统就是残的。
