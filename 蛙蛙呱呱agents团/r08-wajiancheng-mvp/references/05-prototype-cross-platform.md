# s05 跨平台原型（prototype / screen）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/design-system/SKILL.md
>


来源沉淀：`flutter`（Flutter 跨端）+ `makerskills`（prototype）。

## 一、方法论（什么时候用、核心口径）

「把 PRD 快速搭成跨平台可跑原型」。两个动作：
- `prototype`：校验原型结构六件套（main/app/core/features/shared_widgets/router）、
  feature 分层（data/domain/presentation/providers）、平台白名单。
- `screen`：校验单屏 Widget——类型（stateless/stateful）、常量构造、响应式断点、
  表单三件套（若存在）。

核心红线（R08 实现型身份）：**原型服务于演示与验证，不做生产 App 工程**。
发布签名、应用商店流程、性能调优不在本技能范围（移交 R09/R20）；prototype 的完成
定义 = 结构分层正确 + 各平台可跑通导航。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

结构键、分层、平台白名单全部外置：`prototype.structure_keys`、`prototype.feature_layers`、
`prototype.platforms`（验证链：`experience/thresholds.json → _common.load_thresholds()
→ s05_prototype._validate_prototype/_validate_screen`）。

**prototype 校验规则**：
- 六结构键任一缺失 → `prototype.{k}` BLOCKER。
- `features` 为空 → `prototype.features` BLOCKER；每项缺 name → `prototype.feature.name`；
  缺 layers（dict）→ `prototype.feature.layers`；layers 缺四层任一 →
  `prototype.feature.layers` BLOCKER。
- `platforms` 每项不在白名单（android/ios/web/desktop）→ `prototype.platforms` BLOCKER。

**screen 校验规则**：
- `widget_type` 不在 stateless/stateful → `screen.widget_type` BLOCKER。
- `const_constructor` 非布尔 → BLOCKER；stateless 必须为 True →
  `screen.const_constructor` BLOCKER（const 构造是 Flutter 性能底线）。
- `breakpoints` 缺 mobile / tablet / desktop 任一 → `screen.breakpoints` BLOCKER。
- `form` 若存在，缺 form_key / controller / validator → `screen.form.{f}` BLOCKER。

**输出键**：prototype → `feature_count / verdict / next`；screen → `widget_type /
verdict / next`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/prototype.json`：六键齐、登录 feature 四层齐、平台 3 个合法 →
  ok=true、feature_count=1、verdict=PASS。
- `examples/screen.json`：stateless + const=True + 三断点 →
  ok=true、widget_type=stateless、verdict=PASS。
- 脏夹具 `prototype_dirty.json`：platforms=["harmonyos"]（非法）→ ok=false / exit 1。
- 脏夹具 `screen_dirty.json`：stateless + const=False → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **stateless 的 const 校验是条件式**：只有 stateless 强制 const_constructor=True；
  stateful 允许 False（有状态组件无法 const 构造）。写成无条件强制会把合法的
  stateful 屏全部误杀。
- **breakpoints 是三键硬要求**：只写 mobile 的响应式声明是「假响应式」；
  mobile/tablet/desktop 三档齐备才允许进入下一阶段截图验收。
- **platforms 白名单外一律拦**：曾出现 `["harmonyos"]` 这样的「想当然平台」——
  原型目标平台必须是被支持的四类之一，否则演示无法跑通。
- **feature.layers 用 dict 而非 list**：四层是「层名→职责描述」的映射；
  用 list 表达会丢失层名与描述的对应关系，门禁按 dict 校验，写 list 直接 BLOCKER。
