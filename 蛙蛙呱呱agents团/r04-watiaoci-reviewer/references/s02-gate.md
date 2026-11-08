# S02 硬门禁执行与门禁强度审计
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/design/design-critique/SKILL.md
>


## 方法论（来源 harness-engineering / verify + harness-audit）

**门禁的唯一信号是退出码**：文档说「这是门禁」不算数，跑一次看退出码才算。
R04 的两个动作：

- **run**：替调用方真实执行一组验收命令，逐条记 PASS/FAIL/SKIPPED；
- **audit**：审「门禁自己」的证据——它是真门禁，还是门禁剧场（theatre）。

七个剧场模式（STRENGTH-001..007）：blocking-gate 被声明成永不阻断 /
基线自动更新 / skip 无理由 / 分层无阈值 / 默认最低档 / 基线 PR 自动批 /
快照说 passed 但从未运行。

## 可执行口径

- run：每条命令 subprocess 真实执行——
  - 退出码 0 = PASS；非 0 = FAIL；命令为 `gate.skipped_command` = SKIPPED；
  - 超时 = FAIL"TIMEOUT"，超时秒数 `gate.timeout_s`；
  - stdout/stderr 截尾保留 `gate.tail_chars` 字符作证据；
  - 全部 SKIPPED → overall=PASS（没有失败项；skip 的强度问题交给 audit）。
- audit：七模式判定规则外置在 `strength.patterns`（含 severity 与 remediation）；
  - score = 100 − error 数 × `strength.error_penalty` − warning 数 × `strength.warning_penalty`；
  - tier：score ≥ `strength.solid_min` → solid；≥ `strength.at_risk_min` → at-risk；更低 → theatre；
  - **error 存活即 FAIL**（分数再高也过不了）；
  - 证据为空 → NOT_EVALUABLE（宁可判「不可评」，不判「过」）。

## 已验证算例

- `cases/harness-audit/`：v1 证据 STRENGTH-001（never blocks 声明）+
  STRENGTH-007（快照 passed 但 signals 无运行记录）双触发 →
  2 error / score 70 / at-risk / FAIL；v2 修复后 0 命中 → 100 / solid / PASS。
- `examples/gate_run.json`：真实命令逐条执行全绿；
  `examples/gate_run_dirty.json`：exit 3 的失败命令 + 1 秒超时（`--timeout` 覆盖），
  FAIL 与 TIMEOUT 双语义可复现。

## 实战踩坑

- **Windows 管道孤儿**：`shell=True` + 捕获管道输出时，超时杀掉的是 cmd 壳，
  管道被孙进程（如 python sleep）持有，读 EOF 永远等不回来——测试卡死。
  解法：stdout/stderr 改写**临时文件**承接，超时后直接返回；
- 超时判 FAIL 的语义必须是确定性的：实测脏夹具（sleep 20 / timeout 1）约 1 秒返回；
- 本机没有 `ping` 命令：造超时夹具用 `python -c "import time; time.sleep(...)"`；
- STRENGTH-001 的判定对象可能是纯字符串项——先 isinstance 分流再取键，别假设全是 dict。
