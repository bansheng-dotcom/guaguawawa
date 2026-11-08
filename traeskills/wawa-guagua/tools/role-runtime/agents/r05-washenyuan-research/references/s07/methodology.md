# s07 自动化研究辅助（auto）方法论

来源沉淀：`karpathy__autoresearch` program.md 自主研究循环范式 +
`K-Dense-AI` 研究运营工具链。

## 一、方法论（什么时候用、核心口径）

研究辅助回答「研究流程怎么组织、怎么知道做完了」。两个动作：
- `plan`：研究计划——问题、来源类型、方法白名单、覆盖矩阵。
- `track`：运行追踪——完成率、覆盖缺口显式列出。

核心口径（源自 karpathy autoresearch）：定义问题 → 执行取证 → 记录结果 →
保留/丢弃 → 迭代下一轮；覆盖缺口不许悄悄漏。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

状态机、方法白名单、最低问题数全部外置：`auto.plan_statuses`（5 态）、
`auto.method_whitelist`（8 法）、`auto.min_questions`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s07_auto.*`）

**plan 校验规则**：
- topic 为空 → `auto:topic` CRITICAL。
- research_questions 数 < min_questions → `auto:min_questions` HIGH。
- 每条问题须有 id + text → `auto:question_fields` HIGH。
- source_types 为空 → `auto:source_types` HIGH。
- methods 为空 → `auto:methods` HIGH；method 不在白名单 → `auto:method_whitelist` HIGH。
- timeline 为空 → `auto:timeline` HIGH。
- coverage_matrix = 每个问题 × 每类来源一格（取证计划）。

**track 计算规则**：
- run.status 不在白名单 → `auto:run_status` HIGH。
- completion_rate = completed run 数 / 总 run 数。
- covered_ids = 所有 completed run 的 questions_covered 并集。
- coverage_gaps = 计划问题中未被任何 completed run 覆盖的 id（显式列出）。
- 有覆盖缺口 → `auto:coverage_gaps` MEDIUM（注意：MEDIUM 也令 ok=false，缺口即失败）。

**输出键**：plan → `question_count / coverage_matrix / verdict / next`；
track → `run_count / completed_runs / completion_rate / coverage_gaps / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/auto_plan.json`（3 问题 / 3 来源 / 2 方法）：
- question_count=3，coverage_matrix 长 3（每问题配 3 类来源），verdict=PASS。
`examples/auto_track.json`（4 run，3 completed / 1 in_progress）：
- run_count=4，completed_runs=3，completion_rate=**0.75**，coverage_gaps=[]，verdict=PASS。
  （Q1/Q2/Q3 三个计划问题分别被三个 completed run 覆盖，in_progress 的 ledger 不计入覆盖。）
脏夹具 `auto_plan_dirty.json`：缺问题/方法越白名单 → ok=false。
脏夹具 `auto_track_dirty.json`：存在覆盖缺口 → coverage_gaps 非空，ok=false。

## 四、实战踩坑（真拦下来的教训）

- **覆盖缺口 MEDIUM 也判 FAIL**：`_common.result` 的 ok 是「所有检查全过」，MEDIUM 失败
  同样令 ok=false。缺口不是「提醒一下」，是「研究没做完」。
- **只有 completed run 才算覆盖**：in_progress/blocked/skipped 的 run 即使填了
  questions_covered 也不计入 covered_ids——否则「在做」被当成「做完了」。
- **coverage_gaps 必须显式列出 id**：输出键里要有完整的 gap 清单（不是只给个数），
  这样下游/编排器能精确知道还差哪个问题没被覆盖。
- **`run_count / completion_rate` 是证据数字**：登记进 `review.evidence_keys`，
  否则 T7 evidence_gate 误杀干净产出。
