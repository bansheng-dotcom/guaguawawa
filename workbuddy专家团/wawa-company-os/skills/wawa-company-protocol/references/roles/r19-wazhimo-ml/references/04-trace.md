# 04 · Agent Trace 与调试口径（trace）
> 蒸馏自: 补充技能/01-当前能力域/mlflow__mlflow/mlflow/assistant/skills/mlflow-trace-analysis/SKILL.md
>


> 技能：`trace` ｜ 动作：`analyze`（Trace 分析）、`retrieval`（Trace 检索）
> 来源：mlflow__mlflow（`mlflow-trace-analysis` 的 span 树检查、错误定位、反馈判读；`mlflow-trace-retrieval` 的 trace 过滤/时间窗；`mlflow-trace-instrumentation` 的 span 类型）

## 第一层：方法论

Trace 是**调试的证据，不是结论**。状态、span 树、错误定位、时间窗——这四样构成
「这条链路到底发生了什么」的地基。把这段做成确定性校验的价值，不在于「追得更深」，
而在于**让不可解释的链路在采集层就发不出来**。

三条方法论：

1. **`OK` 状态只说明执行成功，不代表输出正确**。一条 trace 的 `state=OK` 意味着
   "所有 span 都跑完了、没抛异常"，不意味着"Agent 答对了"。把 OK 当成"结果没问题"
   是 trace 分析最常见的误读。
2. **`STATUS_CODE_UNSET` 不是错误**。它是"未显式标记状态"，与 `ERROR` 有本质区别。
   把 UNSET 当 ERROR 处理会制造大量假告警。
3. **span 树必须结构完整**。除了根 span，每个 span 的 `parent_span_id` 必须指向
   一个真实存在的 span。悬空的父引用说明 trace 采集不完整，链路断了。

**本角色绝对不做的事**：**绝不修改应用代码**。R19 的诊断止于「证据 + 建议」，
真正的修复走 s05 release 的回归流程（诊断层 → 修复 → fail-before/pass-after）。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| analyze.trace_id | 非空 | mlflow-trace |
| analyze.state | ∈ `trace.trace_states` = `[OK, ERROR, IN_PROGRESS, STATUS_CODE_UNSET]` | mlflow-trace-analysis |
| analyze.spans | ≥ 1 个 span | mlflow-trace-analysis |
| analyze.span_type | 每个 span 的 type ∈ `trace.span_types` | mlflow-trace-instrumentation |
| analyze.parent_integrity | 非根 span 的 parent_span_id 必须存在 | mlflow-trace-analysis |
| analyze.error_loc | state=ERROR 时必须定位到 status=STATUS_CODE_ERROR 的 span | mlflow-trace-analysis |
| retrieval.condition | trace_id 或 filter_string 至少一个非空 | mlflow-trace-retrieval |
| retrieval.time_window | start_ms 与 end_ms 都非空 | mlflow-trace-retrieval |
| retrieval.window_order | start_ms ≤ end_ms | mlflow-trace-retrieval |
| retrieval.max_results | 整数且 > 0 | mlflow-trace-retrieval |

**阈值单一真源**：`trace.trace_states` / `trace.span_types` 以
`experience/thresholds.json` 的 `trace` 段为准。

## 第三层：已验证的算例

**算例 A（干净分析）**：`examples/trace_analyze.json`
```
tr-77a1 / state=OK / 3 span（AGENT→RETRIEVER、AGENT→LLM）
```
类型全合法、parent 引用完整 → `ok=true`，`verdict=PASS`。

**算例 B（脏分析）**：`examples/trace_analyze_dirty.json`
```
tr-77a2 / state=ERROR / span s1: parent_span_id=sX、type=VECTOR_DB
```
BLOCKER ×3：`type='VECTOR_DB'` 不在白名单；parent `sX` 悬空；ERROR 状态未定位
到错误 span。

**算例 C（干净检索）**：`examples/trace_retrieval.json`
```
filter_string="state='ERROR' AND tag.env='staging'" / 时间窗有序 / max_results=50
```
条件非空、时间窗有序、上限合法 → `ok=true`。

**算例 D（脏检索）**：`examples/trace_retrieval_dirty.json`
```
trace_id="" / filter_string="" / start>end / max_results=0
```
BLOCKER ×4：无检索条件、时间窗倒挂、上限为 0。

## 第四层：实战踩坑

1. **UNSET 不等于 ERROR**。`STATUS_CODE_UNSET` 是"没标"，`STATUS_CODE_ERROR`
   才是"出错"。error_loc 检查的是后者，别把 UNSET 算进错误 span。

2. **根 span 的 parent 是空串不是缺失**。`parent_span_id=""` 表示这是根，合法；
   `parent_span_id="sX"` 而 sX 不在 span 列表里，才是悬空。两者必须区分。

3. **span type 白名单是 mlflow 的枚举**，不是 OpenTelemetry 的
   `SpanKind`（INTERNAL/CLIENT/SERVER）。用 OTel 的 kind 填 mlflow 的 type 会被
   拦——这是两个不同维度。

4. **检索必须有时间下界**。mlflow-trace-retrieval 的铁律：按会话/用户搜索时，时间
   窗是为了避免全表扫描。缺 start 的检索在大规模 trace 库里代价极高。

5. **max_results=0 不是"不限"**。0 是"取 0 条"（无意义），不是"取全部"。要"全部"
   必须显式给一个大的正整数，不允许用 0 或负数表示。

6. **HUMAN 反馈描述的是"报告体验"不是"系统错误"**。用户说"答得不好"是体验反馈，
   需要 span 佐证（比如 RETRIEVER 召回为空、LLM 超时）。不要直接把 HUMAN 反馈当
   错误信号。

7. **不要在结论里写"我已修复了检索 span"**。trace 角色不改代码。正确写法：
   "定位到 s1（RETRIEVER）为错误 span，根因疑似检索空返回，修复建议移交 release
   的回归流程。"
