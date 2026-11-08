# s02 Logo 与图标（logo / favicon）方法论
> 蒸馏自: 补充技能/01-当前能力域/kaankiziltug__logo-design-skill/SKILL.md
>


来源沉淀：`kaankiziltug__logo-design-skill`（8 类 mark type、测试阶梯、光学修正）
+ `jgerton__brand-toolkit`（brand-visual-identity）。

## 一、方法论（什么时候用、核心口径）

「logo 不能只在 512px 好看」。两个动作：
- `logo`：校验 logo 设计包——mark_type 白名单、concepts ≥3（样式寻路）、
  尺寸测试覆盖 16/32/64、单色可读 + 16px 可辨识、商标排查 ≥1、主/次色 hex 合法且对比度 ≥3.0。
- `favicon`：校验图标变体包——variants ≥3（含 favicon 与 app-icon 类）、source 为 svg。

核心红线：**多尺寸 + 单色 + 小尺寸三关是全或无**，任一尺寸缺失即 BLOCKER；
商标排查不是「有就好」，至少 1 条筛查记录承载「不撞标」的边界。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

白名单外置：`logo.mark_types`（8 类）、`logo.test_ladders`（[16,32,64]）。

**logo 校验规则**：
- `mark_type` 不在 8 类（wordmark/monogram/letterform/pictorial/abstract/emblem/mascot/combination）→ BLOCKER。
- `concepts` <3 或任一缺 name/idea → BLOCKER。
- `tests` 缺 16/32/64 任一尺寸键 → BLOCKER；`one_color.readable` 非真 → BLOCKER；`16px.legible` 非真 → BLOCKER。
- `trademark_check` 空 → BLOCKER。
- `colors.primary/secondary` 非 hex → BLOCKER；`c.contrast(primary, secondary) < 3.0` → BLOCKER。

**favicon 校验规则**：
- `variants` <3 或任一缺 name → BLOCKER；必须含 `favicon` 与至少一个含 `app` 的变体 → 否则 BLOCKER。
- `source` 非 `.svg` 结尾 → BLOCKER。

**输出键**：logo → `mark_type/concept_count/tests_passed`；favicon → `variant_count/source`。
对比度用 WCAG 相对亮度公式（`_common.contrast`），主/次色对比 ≥3.0（图形可辨）。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/logo.json`：mark_type=letterform、3 个概念（各 name+idea）、尺寸 16/32/64 齐、
  单色可读、16px 可辨识、2 条商标排查、主/次色 #1E3A5F/#FFC21A（对比度 ≥3.0）→ ok=true、verdict=PASS。
- `examples/favicon.json`：3 个变体（favicon/apple-touch-icon/android-icon）+ source=logo.svg → ok=true。
- 脏夹具 `logo_dirty.json`：concepts 仅 1 个、缺尺寸测试、colors 用 "blue"/"yellow" → ok=false / exit 1。
- 脏夹具 `favicon_dirty.json`：variants 仅 1 个 + source=logo.png → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **test_ladders 键是字符串不是数字**：JSON 里 `{"16": true}` 的键是 `"16"`，
  校验时要用 `str(s) in tests` 而不是 `s in tests`，否则数字 16 永远找不到。
- **one_color 与 16px 是嵌套对象不是布尔**：`one_color.readable` 和 `16px.legible`
  分别单独判，别把 `tests["16px"]` 当布尔直接判。
- **对比度要算不要猜**：`#1E3A5F` vs `#FFC21A` 的对比度是算出来的（≈5.9），
  别凭肉眼写死「够不够」。`is_hex_color` 先于 `contrast` 判，否则非法色会抛异常。
- **favicon 覆盖要含 app 类**：`variants` 有 3 个全是 favicon 变体不算数，
  「favicon + app-icon + 可缩放」三件套才够，校验 `any("app" in s)`。
