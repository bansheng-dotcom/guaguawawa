# s04 跨端生产工程（crossplatform）方法论

来源沉淀：`flutter__flutter` + `mattpocock__skills`（跨端工程与构建口径）。

## 一、方法论（什么时候用、核心口径）

跨端生产回答「原型能上生产吗」。两个动作：
- `build`：构建矩阵——每个平台必须有 success 构建结果，skipped/failed 即拦。
- `platform`：平台差异——状态管理方案白名单，平台差异必须文档化。

核心红线：**跳过构建 = 假通过**（对齐 R09 总边界）；平台差异不文档化 = 生产埋雷。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

平台、构建状态、状态管理方案外置：`crossplatform.platforms/build_statuses/state_management`，
跳过上限 `crossplatform.max_skipped`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s04_crossplatform.build/platform`）

**build 校验规则**：
- targets 为空 → `crossplatform:targets` CRITICAL。
- platform 不在白名单 → `crossplatform:platform` HIGH。
- status 不在枚举 → `crossplatform:status` HIGH。
- status=skipped → `crossplatform:skipped` HIGH；failed → `crossplatform:build_failed` HIGH。
- 跳过数 > max_skipped → `crossplatform:skip_cap` CRITICAL。

**platform 校验规则**：
- state_management 不在白名单 → `crossplatform:state_management` HIGH。
- diffs 为空 → `crossplatform:diffs` HIGH（平台差异必须文档化）。

**输出键**：build → `target_count / skipped / verdict / next`；
platform → `target_count / state_management / diff_count / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/crossplatform_build.json`（3 平台全 success）：target_count=3，skipped=0，verdict=PASS。
`examples/crossplatform_platform.json`（3 目标 2 差异）：diff_count=2，verdict=PASS。
脏夹具 `crossplatform_build_dirty.json`：web 构建 skipped → ok=false；
`crossplatform_platform_dirty.json`：platform 非法+无差异文档 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **skipped 必须按失败处理**：构建跳过在统计上最容易「看起来都绿」，
  必须显式计数并与 max_skipped 比较，否则跨端工程形同虚设。
- **状态管理多方案是风险信号**：同一项目多套状态管理要显式提示，避免交接时踩坑。
