# s01 深度研究（research）方法论

来源沉淀：`market-research-reports`（K-Dense-AI scientific-agent-skills）+ `literature-review`。

## 一、方法论（什么时候用、核心口径）

深度研究回答「这条结论凭什么成立」。两个动作：
- `ledger`：构建/校验证据台账——每条 claim 必须挂 sources，覆盖率 1.0 才 PASS。
- `report`：研究报告脚手架——sections 引用的 claim 必须存在且每条 claim 有来源。

核心红线（R05 身份边界）：**claims 必须挂来源，无源断言 = FAIL**。研究只呈现证据与选项，
不替你拍板，决策词（建议/应该/决定）不得出现在结论文本（由 T7 review 的 decision_gate 拦）。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

claim 六类、来源九型白名单全部外置：`research.claim_kinds`、`research.source_types`，
最低来源数 `research.min_sources_per_claim`，枚举 `research.verdict_enum`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s01_research.ledger/report`）

**ledger 校验规则**：
- claim.kind 不在白名单 → `research:claim_kind` HIGH。
- claim.source_ids 指向不存在的 source → `research:dangling_ref` HIGH。
- claim 无 source_ids → 记入 orphan_claims，`research:orphan_claim` HIGH。
- source_ids 数 < min_sources_per_claim → `research:min_sources` HIGH。
- source.type 不在白名单 → `research:source_type` HIGH。
- coverage_rate = 有源 claim 数 / 总 claim 数。

**report 校验规则**：
- section 引用不存在的 claim → `research:dangling_claim` HIGH。
- claim 存在但无 source_ids → `research:unsourced_claim` HIGH。
- claim 引用的 source 不存在 → `research:dangling_source` HIGH。
- citation_coverage = 全有源 section 数 / 总 section 数。

**输出键**：ledger → `source_count / claim_count / orphan_claims / unverified_sources /
coverage_rate / verdict / next`；report → `sections_checked / citation_coverage /
orphan_claims / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/research_ledger.json`（2 source / 3 claim）：
- source_count=2，claim_count=3，orphan_claims=[]，coverage_rate=1.0，verdict=PASS。
`examples/research_report.json`（2 section 引用 3 claim）：
- sections_checked=2，citation_coverage=1.0，orphan_claims=[]，verdict=PASS。
脏夹具 `research_ledger_dirty.json`：orphan_claims 非空 → ok=false / exit 1（门禁拦下）。
脏夹具 `research_report_dirty.json`：orphan_claims 非空 → ok=false（悬空 claim 拦截）。

## 四、实战踩坑（真拦下来的教训）

- **评审器读错键名 = 门禁全失效**：review.py 曾读 `ch.get("severity")`，但 `_common.ck`
  输出的是 `sev`，导致 blocker 恒为空、五个评审负例全部误判 PASS。教训：评审器/契约校验器
  读的键必须与 `_common.ck` 输出键逐字对齐，`severity` ≠ `sev`。
- **输出契约漏 required = 缺字段也能过**：`contracts._out` 早期把动作专属字段只写进
  `properties` 没加进 `required`，缺 `orphan_claims` 的产出竟通过 `contract validate`。
  教训：产出契约的 `required` 必须包含动作专属字段，不只 `ok/checks`。
- **evidence_keys 是评审的「证据白名单」**：T7 的 evidence_gate 按 `review.evidence_keys`
  判断「有没有证据字段」。键清单太短会把干净产出（如 industry 的 `hhi`）判成「无证据」误杀。
  每新增一个技能输出键，都要回填 evidence_keys。
- **orphan_claims 是防幻觉核心，不是摆设**：脏夹具必须真的产出 orphan_claims 并 FAIL，
  证明无源断言确实被拦；只断言「能跑」会掩盖「产出坏」。
