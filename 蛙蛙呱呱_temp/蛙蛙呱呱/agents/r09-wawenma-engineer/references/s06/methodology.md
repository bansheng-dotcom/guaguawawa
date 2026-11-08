# s06 调试性能重构（debug）方法论

来源沉淀：`obra__superpowers`（systematic-debugging 的 Iron Law）。

## 一、方法论（什么时候用、核心口径）

调试与重构回答「为什么坏、怎么改不坏」。两个动作：
- `debug`：稳定复现 → 定位根因 → 修复。**无根因不修复**（Iron Law）。
- `refactor`：性能热点剖析 + 回归测试保护下重构。

核心红线：**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**（无根因不修复）；
**重构必须在测试保护下进行**。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

最低复现步数外置：`debug.min_repro_steps`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s06_debug.debug/refactor`）

**debug 校验规则**：
- 缺 symptom → `debug:symptom` CRITICAL。
- 复现步骤数 < min_repro_steps → `debug:repro` CRITICAL（须稳定复现）。
- 缺 root_cause → `debug:root_cause` CRITICAL（无根因不修复）。
- 缺 fix → `debug:fix` CRITICAL。

**refactor 校验规则**：
- hotspots 为空 → `debug:hotspots` CRITICAL。
- 热点缺 before/after 度量 → `debug:hotspot_measure` HIGH。
- after > before（劣化）→ `debug:hotspot_regress` HIGH。
- regression_tests 为空 → `debug:regression` CRITICAL。
- 回归测试有 failed → `debug:regression_failed` CRITICAL。

**输出键**：debug → `symptom / repro_step_count / root_cause / verdict / next`；
refactor → `hotspot_count / regression_count / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/debug_debug.json`（4 步复现+根因+修复）：repro_step_count=4，verdict=PASS。
`examples/debug_refactor.json`（2 热点优化+2 回归全绿）：hotspot_count=2，regression_count=2。
脏夹具 `debug_debug_dirty.json`：0 复现步+空根因 → ok=false；
`debug_refactor_dirty.json`：热点劣化+无回归 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **「无根因不修复」必须落到确定性判据**：只要 root_cause 为空就 CRITICAL，
  否则「先打个补丁」会被放过。
- **劣化检测比优化检测更重要**：after_ms > before_ms 是负优化，必须 HIGH，
  不能只看「有没有改」。
