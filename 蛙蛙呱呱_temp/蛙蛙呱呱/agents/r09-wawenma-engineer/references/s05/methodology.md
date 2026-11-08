# s05 测试与浏览器验证（testing）方法论

来源沉淀：`obra__superpowers`（test-driven-development）+ `browser-use__browser-use`（qa）。

## 一、方法论（什么时候用、核心口径）

测试与浏览器验证回答「怎么证明它能用」。两个动作：
- `suites`：测试套件——类型白名单、跳过/失败测试拦截、覆盖率门槛。
- `browser`：浏览器关键路径——flow 结果枚举、flaky 拦截、playwright 轨迹留证。

核心红线：**跳过测试 = 假通过**；**浏览器验证不留轨迹 = 结论无法复核**。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

套件类型、flow 结果、覆盖率门槛、跳过上限外置：
`testing.suite_types/flow_results/coverage_min/max_skipped`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s05_testing.suites/browser`）

**suites 校验规则**：
- suites 为空 → `testing:suites` CRITICAL。
- suite_type 不在白名单 → `testing:suite_type` HIGH。
- skipped>0 → `testing:skipped` HIGH；failed>0 → `testing:failed` HIGH。
- 总跳过 > max_skipped → `testing:skip_cap` CRITICAL。
- 覆盖率缺/低于 coverage_min → `testing:coverage/coverage_min` CRITICAL。

**browser 校验规则**：
- flows 为空 → `testing:flows` CRITICAL。
- result 不在枚举 → `testing:flow_result` HIGH。
- flaky → `testing:flaky` HIGH；failed → `testing:flow_failed` HIGH。
- 缺 playwright_trace → `testing:trace` HIGH。

**输出键**：suites → `suite_count / skipped / coverage / verdict / next`；
browser → `flow_count / passed / flaky / failed / playwright_trace / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/testing_suites.json`（3 套件 0 跳过，覆盖率 0.87）：verdict=PASS。
`examples/testing_browser.json`（3 流程全 passed，轨迹在）：passed=3，flaky=0，verdict=PASS。
脏夹具 `testing_suites_dirty.json`：跳过 5 + 覆盖率 0.55 → ok=false；
`testing_browser_dirty.json`：1 条 flaky + 无轨迹 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **覆盖率门槛要与 review 的 test_skipped_gate 一致**：两处都读 coverage_min，
  改阈值要同步，否则评审器和技能判定打架。
- **flaky 不是小事**：浏览器流程 flaky 是「假通过」的高发区，必须按失败拦，
  不能当 INFO 放行。
