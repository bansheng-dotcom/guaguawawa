# 25 · 运行账本（deliver）：manifest、事件与签发边界

> R06 报告链第 10 段的领域依据。可复现不是“再跑一次看看”，而是每一步都有账。

## 1. manifest 必须回答什么

| 问题 | 字段 |
|---|---|
| 谁产的 | `producer` |
| 谁签发 | `author_role`（本仓固定 r01） |
| 能不能对外 | `publishable`（本仓固定 false） |
| 用了哪些证据 | `files`（每个工件 sha256） |
| 质检过没过 | `quality` / `gate` |
| 结论可追吗 | `trace`（可追率与未追到列表） |
| 哪些没进正文 | `bounded_modules` |

R06 只产草稿：`author_role=r01`、`publishable=false`、`requires_signoff=true`。
签发与对外口径归 R01，这是角色边界，不是流程装饰。

## 2. run_events 记什么

四个阶段各一条事件：verify / chart / write / deliver，字段：

- `ts`：ISO 时间；
- `stage`：阶段名；
- `status`：ok / fail；
- `grade`：PASS / WARN / FAIL；
- `run_id`：本次运行标识。

事件不写业务数据，只写“哪一步、什么结论”。这样既能复现，也不泄漏项目内容。

## 3. 哈希清单

`files` 记录 report.html 与四个上游工件的 sha256。
审计时任何一个文件被改动，哈希对不上，manifest 即失效。
这比“我记得跑过”可靠，也比把全文复制进 manifest 节省空间。

## 4. 渲染与打印边界

- 静态 HTML，`@media print` 固定 A4；
- 无斜体、字阶 ≥4、图表用 `aria-label`；
- 交互图不进报告，只用于教学画廊。

## 5. 本仓落点

| 能力 | 代码 | 门禁 |
|---|---|---|
| manifest | `analysis_chain/deliver.py` | 字段齐全、author_role/publishable 固定 |
| 事件 | 同上 `_events` | run_events.jsonl ≥4 条 |
| 呈现 | 同上 `_presentation` | 无斜体、有打印样式、字阶 ≥4 |
| 可追 | `audit_trace` | 正文数字 100% 可追 |

## 6. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 报告没有 manifest | 无法复核谁产、何时产 | deliver 必须写 manifest |
| manifest 不记哈希 | 文件被改也发现不了 | files 必填 sha256 |
| R06 直接签发“可对外” | 越权 | publishable 固定 false |
| 只写结果不写事件 | 出问题无法定位阶段 | run_events ≥4 条 |
| 用交互图替代打印图 | A4 丢失信息 | 只走静态 SVG |

## 7. 来源

- Google SRE Book（Beyer et al.）：可观测性与事件记录。
- OpenTelemetry 规范（CNCF）：事件/span 的最小字段。
- W3C PROV-O：来源与派生关系的本体模型。
- DAMA-DMBOK：数据血缘与审计追踪。
- 本仓 `_refs/dar/references/analysis_run_observability_contract.md`：分析运行事件契约（只借结构）。
