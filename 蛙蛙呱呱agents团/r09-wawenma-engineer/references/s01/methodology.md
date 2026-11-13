# s01 技术规格与架构（spec）方法论

来源沉淀：`wshobson__agents`（AGENTS.md / ARCHITECTURE.md）+ `Jeffallan__claude-skills`。

## 一、方法论（什么时候用、核心口径）

技术规格回答「这块代码的边界在哪」。两个动作：
- `spec`：技术规格——每个模块必须声明 inputs/outputs，命名全局唯一，否则边界不可判。
- `arch`：架构拓扑——topology 枚举限定，服务间边引用必须指向存在的服务（无悬空边）。

核心红线（R09 身份边界）：**模块边界不清晰不写代码**；边界校验失败即 FAIL，不进入实现。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

topology 四型、模块必填键全部外置：`spec.topology_types`、`spec.module_required`，
最低模块数 `spec.min_modules`，枚举 `spec.verdict_enum`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s01_spec.spec/arch`）

**spec 校验规则**：
- modules 为空 → `spec:modules` CRITICAL。
- 模块缺 name/inputs/outputs 任一 → `spec:module_fields` HIGH。
- 模块 name 为空 → `spec:module_name` HIGH；重名 → `spec:module_dup` HIGH。
- boundary_ok = 模块齐备且命名唯一。

**arch 校验规则**：
- topology 不在枚举 → `spec:topology` CRITICAL。
- services 为空 → `spec:services` CRITICAL。
- 边 from/to 引用不存在的服务 → `spec:dangling_edge` HIGH，记入 dangling_edges。

**输出键**：spec → `module_count / boundary_ok / verdict / next`；
arch → `service_count / topology / edge_count / dangling_edges / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/spec_spec.json`（2 模块）：module_count=2，boundary_ok=true，verdict=PASS。
`examples/spec_arch.json`（3 服务 3 边）：service_count=3，edge_count=3，dangling_edges=[]。
脏夹具 `spec_spec_dirty.json`：模块重名+缺键 → ok=false；`spec_arch_dirty.json`：topology 非法+悬空边 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **边界键必须对齐契约**：模块必填键写进 contracts 与技能读取口径要一致，
  否则契约放行但技能拦截（或反之），闭环矩阵会红。
- **重名是边界模糊的信号**：两个模块同名意味着输入输出无法归因，必须当作 HIGH 失败，
  不能只 INFO 提示。
