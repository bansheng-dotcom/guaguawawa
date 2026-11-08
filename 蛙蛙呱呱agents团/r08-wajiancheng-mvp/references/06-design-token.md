# s06 组件与设计实现（design / token）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/design-system/SKILL.md
>


来源沉淀：`makerskills`（design-system / design-token）+ `flutter`（组件库）。

## 一、方法论（什么时候用、核心口径）

「把设计稿实现为可复用的 token 与组件」。两个动作：
- `design`：校验设计系统——tokens 三类（color/typography/spacing）每类 ≥1 且每项
  name+value，components ≥1 每项 name/platform/states。
- `token`：校验单套 token——primary/secondary 主色 + scale 阶梯。

核心红线（R08 实现型身份）：**token 是「名值对」不是「描述文字」**。`value` 必须是
可被工程直接引用的具体值（`#3355FF` / `24px` / `8px`），写「品牌蓝」「大号」这类
自然语言描述会让下游无法机器消费——由 T7 review 的 no_vague 检查协同拦截。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

token 三类、scale 类型全部外置：`design.token_types`、`design.scale_types`（验证链：
`experience/thresholds.json → _common.load_thresholds() → s06_design._validate_design/
_validate_token`）。

**design 校验规则**：
- `tokens` 非 dict 或缺失 → `design.tokens` BLOCKER。
- tokens 三类（color/typography/spacing）任一缺失或为空数组 →
  `design.tokens.{tt}` BLOCKER；每项缺 name / value → `design.tokens.{tt}` BLOCKER。
- `components` 为空 → `design.components` BLOCKER；每项缺 name / platform →
  `design.component.{k}` BLOCKER；`states` 为空数组 → `design.component.states` BLOCKER。
- `token_count` = 三类 token 条目总和。

**token 校验规则**：
- `primary` / `secondary` 任一为空 → `token.primary` / `token.secondary` BLOCKER。
- `scale` 为空 → `token.scale` BLOCKER；每项缺 name / value → `token.scale.{k}` BLOCKER。

**输出键**：design → `token_count / component_count / verdict / next`；
token → `scale_count / verdict / next`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/design.json`：三类 token 各 1 项 + Button 组件（web，2 states）→
  ok=true、token_count=3、component_count=1、verdict=PASS。
- `examples/token.json`：primary+secondary+scale 1 项 → ok=true、scale_count=1、verdict=PASS。
- 脏夹具 `design_dirty.json`：color 为空数组 → ok=false / exit 1。
- 脏夹具 `token_dirty.json`：缺 primary 主色 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **三类 token 缺一不可，即使当前页面没用到**：只写 color 的设计系统在换主题时会
  全站崩——typography/spacing 是「系统」的最低完整性。空数组与缺键同罪（都是 BLOCKER）。
- **components 的 states 至少 1 个**：无状态声明的组件无法做设计评审；
  它是组件从「截图」升级为「规范」的分界线。
- **token_count 统计口径要跨三类累加**：只数 color 会低估系统规模，
  下游按 token_count 做覆盖度断言时会被误导。
- **主色是二元的（primary+secondary）**：单主色的体系在 hover/强调态会无处安放，
  secondary 缺失直接 BLOCKER——这是品牌可扩展性的最低线。
