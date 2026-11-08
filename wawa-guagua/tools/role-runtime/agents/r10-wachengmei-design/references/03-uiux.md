# s03 产品与 UI/UX（uiux / screen·ux）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/design-handoff/SKILL.md
>


来源沉淀：`mae616__design-skills`（ui-designer / frontend-implementation /
accessibility-engineer / usability-psychologist）。

## 一、方法论（什么时候用、核心口径）

「UI 不是艺术，是决策支持」。两个动作：
- `screen`：校验屏幕设计——goal/success_criteria 非空、信息分区 ≥3、组件带状态、
  整屏五态覆盖（normal/loading/empty/error/disabled）、a11y 三底线（键盘可达/焦点可见/对比度达标）。
- `ux`：校验可用性评估——problem 非空、causes ≥1、improvements ≥1、validation.metrics 非空。

核心红线：**状态集合是「整屏覆盖」不是「单个组件凑齐」**——把全部组件的 states
并集后，五态任一缺失即 BLOCKER；a11y 三底线任一 False 即 BLOCKER。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`uiux.states`（5 态）、`uiux.zones_min`（3）。

**screen 校验规则**：
- `goal` / `success_criteria` 空 → BLOCKER。
- `zones` <3 → BLOCKER。
- `components` 空，或任一组件缺 name / states → BLOCKER。
- 全组件 states 并集缺 normal/loading/empty/error/disabled 任一 → BLOCKER。
- `a11y.keyboard_operable` / `focus_visible` / `contrast_ok` 任一非真 → BLOCKER。

**ux 校验规则**：
- `problem` 空、`causes` 空、`improvements` 空、`validation.metrics` 空 → 各自 BLOCKER。

**输出键**：screen → `zone_count/component_count/states_covered`；ux → `cause_count/improvement_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/screen.json`：goal/success_criteria 非空、4 分区、3 组件（states 并集覆盖五态）、
  a11y 三 true → ok=true、verdict=PASS。
- `examples/ux.json`：problem + 3 causes + 3 improvements + validation.metrics → ok=true。
- 脏夹具 `screen_dirty.json`：goal/success_criteria 空、1 分区、无组件、a11y 缺 focus/contrast → ok=false / exit 1。
- 脏夹具 `ux_dirty.json`：全空 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **五态覆盖是并集不是交集**：单个组件只带 `["normal","loading"]` 不是问题，
  问题是整屏所有组件并起来仍缺 `empty`。用 `set().update()` 汇集后查缺失集合。
- **a11y 三底线独立判**：keyboard_operable、focus_visible、contrast_ok 分别成一条 check，
  缺一个单独 BLOCKER，别合成一个布尔（会掩盖「键盘可达但无焦点可见」的隐性缺陷）。
- **components 里可能有非 dict**：遍历要 `isinstance(comp, dict)` 兜底，
  否则脏夹具里塞个字符串会抛 AttributeError 而不是产出 check。
- **ux 的 validation.metrics 要「可测」**：空字符串和缺键都算不通过，别用 `bool(validation)`
  只判对象存在。
