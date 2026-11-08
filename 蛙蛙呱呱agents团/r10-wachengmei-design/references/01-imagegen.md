# s01 AI 生图与插画（imagegen / prompt·style）方法论
> 蒸馏自: 补充技能/01-当前能力域/nlr-2007__illustrations/SKILL.md
>


来源沉淀：`mae616__design-skills`（creative-coder）+ `nlr-2007__illustrations`（illustration/diagram/hybrid 三技能的 style locks 纪律）。

## 一、方法论（什么时候用、核心口径）

「把生图提示词从口头模板变成可审计的规格包」。两个动作：
- `prompt`：校验生图提示词包——media/style 枚举合法、正/负向提示词均非空、
  style_locks ≥1 且不被负向提示词自我推翻。
- `style`：校验风格探索——style 枚举合法、composition ≥1 且每项非空字符串、
  palette 为 hex 色列表。

核心红线（R10 视觉身份）：**提示词是资产不是草稿**。负向提示词若命中风格锁
（锁原文或其否定式「不X/无X」），说明自相矛盾，直接 BLOCKER。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

枚举全部外置：`imagegen.output_media`、`imagegen.style_types`（验证链：
`experience/thresholds.json → _common.load_thresholds() → s01_imagegen`）。

**prompt 校验规则**：
- `media` 不在 `output_media`（image/illustration/icon/poster/banner）→ BLOCKER 且短路返回。
- `style` 不在 `style_types`（line-art/flat/gradient/3d/watercolor/pixel/isometric/duotone）→ BLOCKER。
- `prompt` / `negative_prompt` 空 → BLOCKER。
- `style_locks` 空或非数组 → BLOCKER。
- 锁自洽：任一 lock 满足 `lock in negative` 或 `不{lock} in negative` 或 `无{lock} in negative` → BLOCKER。

**style 校验规则**：
- `style` 枚举 + `composition` ≥1 且每项非空 + `palette` 每项 `is_hex_color`。

**输出键**：prompt → `media/style/lock_count`；style → `style/comp_count/palette`。
`verdict` 只有 PASS/FAIL。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/prompt.json`：media=illustration、style=line-art、正负向非空、3 条 style_locks
  且负向不含锁 → ok=true、lock_count=3、verdict=PASS。
- `examples/style.json`：style=flat、composition 3 项、palette 3 个 hex → ok=true、verdict=PASS。
- 脏夹具 `prompt_dirty.json`：prompt/negative/style_locks 全空 → ok=false / exit 1。
- 脏夹具 `style_dirty.json`：composition=[] + palette=["red"]（非法 hex）→ ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **media 非法要短路**：media 一旦不在白名单，后面的 style/prompt 校验无意义，
  直接 return FAIL，避免对坏输入继续做无谓断言。
- **锁自洽是核心，别只查「存在」**：`不{lock}` 与 `无{lock}` 的否定式也要查，
  否则「负向写『非黑白黄三色』、锁写『#111111/#FFC21A 双色』」这种隐性矛盾会漏。
- **palette 每个都要 `is_hex_color`**：`#red`、`red`、`"blue"` 都不是合法 hex，
  别用「以 # 开头」的弱判断。
- **负向提示词 ≥1 是门禁**：生图质量靠负向约束兜底，空负向提示词直接 BLOCKER，
  不是「建议项」。
