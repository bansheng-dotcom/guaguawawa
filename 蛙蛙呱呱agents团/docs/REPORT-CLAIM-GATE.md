# ClaimCard 头条门禁（REPORT-CLAIM-GATE.md）

> 版本：v0.2 · 2026-11-17（P11）
> 实现：`core/claim_gate.py`，接入 `core/report_compose.py`。

## 0. P11 补丁

- 每条 finding 有逐方法 `falsifier`（`analysis_methods.FALSIFIERS`）；
- `claim_gate` 构建完整 `ClaimCard`（comparability/rivals/decision），跑 `validate`；
- `full_schema_ok` 写进 `manifest.claims`；
- `REPORT_CLAIM_CARD_GATE=1` 时，完整 schema 不过也会降级；默认 **0**（审计，不阻断）。

## 1. 规则

头条（`standfirst`）必须同时满足：

1. **actionable**：引用来源可解析、决策问题明确；
2. **有 falsifier**：写清什么会推翻它；
3. **来源 verified 且 grade ≤ B**：
   - `source_records.quote_status == "ok"`；
   - `grade ∈ {A, B}`；
   - 内部数据文件（`FILE:`）按 **B 级可复现数据**处理，不需要 web quote。

不满足 → **不进标题**：`standfirst` 降级为“本报告含 1 条待验证判断；标题不承载未核验断言，见正文。”
正文与 sections 保留。

## 2. 当前 v9 的发现

P9 接入后，水果 pipeline 的四份报告头条都被降级，原因主要是：

- v9 的 section 没有把 `falsifier` 写进 `draft`；
- section refs 是 `E001…` 内部证据号，已按 `FILE:` 处理为 B 级；
- 没有 falsifier → 按规则不能进标题。

**这不是门禁坏了，是产线还没写 falsifier。** 正确动作是把 falsifier 写进 claim，而不是 `REPORT_CLAIM_GATE=0`。

## 3. 开关

```bash
REPORT_CLAIM_GATE=0 python guagua.py report build ...      # 关闭三条硬规则
REPORT_CLAIM_CARD_GATE=1 python guagua.py report build ...  # 完整 ClaimCard 硬门禁
```

`REPORT_CLAIM_CARD_GATE=0`（默认）只审计 `comparability/rivals`，不阻断；  
`=1` 时 `full_schema_ok=false` 会降级头条。

P11 时 pipeline 的 `full_schema_ok=false`，原因是第一条 claim 跨多个期次/单位：
`same_period=unknown`、`same_unit=unknown`。这不是代码错，是 claim 还没做可比性收敛。

### P12：可比切片

`claim_gate._narrow()` 把 ClaimCard 收敛到同 `(period, unit)` 的一组 refs：

```json
"scope": {"narrowed": true, "refs_total": 102, "refs_used": 12}
```

正文仍可跨期/跨单位；**ClaimCard 只对可比切片负责**。  
P12 后四个 lens 的 `full_schema_ok=true`；`scope` 明确写出缩到哪一组。

## 4. 与完整 ClaimCard 的关系

- `core/claim_card.py` 是完整 schema（comparability/rivals/decision/expiry）；
- `core/claim_gate.py` 是 build 路径的**三条硬规则**；
- 两者不重复：完整审计仍用 `python -m core.claim_card audit --claims …`。

## 5. 验收

- `tests/test_claim_gate.py`：可行动放行；C 级/未核验/无 falsifier 降级；
- `manifest.claims.demoted=true` 时，`gates.claim` 仍为 pass（门禁已执行，头条已降级）；
- 报告仍过渲染/风格/密度门禁。
