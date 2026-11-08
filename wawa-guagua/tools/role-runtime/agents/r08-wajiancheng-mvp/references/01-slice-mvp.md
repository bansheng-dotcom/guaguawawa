# s01 产品切片与 MVP（slice / mvp）方法论
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/product-management/roadmap-update/SKILL.md
>


来源沉淀：`makerskills`（product-slice / mvp-design）。

## 一、方法论（什么时候用、核心口径）

「把一颗想验证的假设切到能最快上线的可测形态」。两个动作：
- `slice`：校验产品切片——artifact_type 必须在 7 类可交付形态内，slices ≥1 且每条切片
  都有 name / testable_hypothesis / success_criterion（均非空）。
- `mvp`：校验 MVP 设计——五 gate 齐全（assumption/mvp/experiment/criteria/handoff），
  假设风险类型合法，实验 method+metric 可测，成败判据成对出现。

核心红线（R08 实现型身份）：**MVP 是「验证」不是「上生产」**。只交付能最快验证假设的
可测形态，不做生产工程；handoff 键是给 R09/R20 的移交口，不能省略。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

形态白名单、风险类型、五 gate 全部外置：`slice.artifact_types`、`mvp.gates`、
`mvp.risk_types`（验证链：`experience/thresholds.json → _common.load_thresholds()
→ s01_slice._validate_slice/_validate_mvp`）。

**slice 校验规则**：
- `artifact_type` 不在白名单（cli/tool/web/landing/saas/email/app）→ `slice.artifact_type` BLOCKER。
- `slices` 为空或非数组 → `slice.count` BLOCKER。
- 每条 slice 缺 name / testable_hypothesis / success_criterion → `slice.{f}` BLOCKER。

**mvp 校验规则**：
- 五 gate（assumption/mvp/experiment/criteria/handoff）任一缺失或为空 → `mvp.{g}` BLOCKER。
- `assumption.risk_type` 不在 8 类（value/usability/viability/feasibility/ethics/gtm/
  strategy/team）→ `mvp.risk_type` BLOCKER。
- `experiment` 每项缺 method / metric → `mvp.experiment.{f}` BLOCKER。
- `criteria.success` / `criteria.fail` 任一缺失 → `mvp.criteria` BLOCKER。
- `passed_gates` = 非空的 gate 数（0..5）。

**输出键**：slice → `artifact_type / slice_count / verdict / next`；mvp → `passed_gates /
verdict / next`。`verdict` 只有 PASS/FAIL（实现门禁二值语义）。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/slice.json`：artifact_type=landing、1 条切片 → ok=true、slice_count=1、verdict=PASS。
- `examples/mvp.json`：五 gate 全非空、risk_type=value、experiment 1 项 method+metric、
  criteria 成对 → ok=true、passed_gates=5、verdict=PASS。
- 脏夹具 `slice_dirty.json`：artifact_type=game（非法）+ slices=[] → ok=false / exit 1。
- 脏夹具 `mvp_dirty.json`：缺 criteria → ok=false / exit 1（五 gate 拦下）。

## 四、实战踩坑（真拦下来的教训）

- **`_nonempty` 是判定核心，别用 `bool(v)` 代替**：dict/list 的空结构 `bool({})==False`
  会把「结构存在但空」误判为「结构缺失」。统一走 `_nonempty`（str 看 strip、容器看 len）。
- **risk_type 大小写归一**：校验前必须 `.strip().lower()`，否则 `"Value"` 会被误拦；
  同理 `artifact_type` 也必须先归一再进白名单。
- **passed_gates 计数与 ok 是两个概念**：五 gate 只要非空就计入 passed_gates，但只有
  全部通过才 ok=true；脏夹具必须真的产出 ok=false 并 exit 1，只断言「能跑」会掩盖「产出坏」。
- **handoff 是门禁不是备注**：MVP 的 handoff 键缺失会被当作 gate 失败拦下——它承载
  「验证完交谁」的边界信息，删掉它等于把 MVP 伪装成生产交付。
