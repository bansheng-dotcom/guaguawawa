# 报告门禁契约（v2，2026-11-20）

> 一句话：**默认产线的产物必须能过自己的门禁；门禁的改动必须留痕；
> 门禁结论只能由 manifest 出，不能由正文或对话自述。**

## 1. 为什么有这份文档

2026-11-20 的个护调研测试暴露了一条链：

1. `core/report_theme` 的 flow 渲染器输出 `class="ex-src"`，门禁只认 `class="fig-src"`；
2. flow 把 `<section class="flow-block summary" id="summary">` 的 class 写在 id 前，
   门禁正则写的是 `<section id="summary">`；
3. flow 把来源块排在「口径与分数」之后，门禁要求口径是末节；
4. 于是**默认 flow 的产物必然挂 3 条判据**，执行者要么退到 `--layout paper`，
   要么改门禁；
5. 那次改了门禁（放宽 F7 / F3），然后自己宣布 PASS。

所以 v2 的判据不是"更严"，而是**可验证 + 留痕 + 不许自证**。

## 2. 标记契约（单一出处）

`core/report/report_marks.py`：

| 常量 | 值 | 用在哪 |
|---|---|---|
| `FIGURE_SRC_CLASS` | `fig-src` | 门禁只认这个类名 |
| `FIGURE_SRC_CSS_ALIAS` | `ex-src` | 旧主题 CSS；渲染时两个类一起挂，判据不看它 |
| `BOUNDARY_LABEL` | `本节边界` | `data-label` 属性 |
| `SUMMARY_SECTION_ID` | `summary` | F3 定位结论段 |
| `CALIBER_TITLE` | `口径与分数` | F6 定位末节 |

**规则**：渲染器和门禁都 `import` 这里的常量；任何一边出现字面量 = 回归。

## 3. 判据（v2）

| id | 判据 | v2 的收紧点 |
|---|---|---|
| F1 | 版式四规则 | 复用 `check_report_layout.py` |
| F2 | 首屏有数字 | `_text()` 先剥 `<head>`，`<title>` 里的数字不算 |
| F3 | 结论段有数字 | 按属性匹配 `id="summary"`，不再要求 id 在最前 |
| F4 | 每节有数字 | 不变 |
| F5 | 边界 | **要正文**：独立边界节 / 每节边界 ≥8 字 / 口径节写清"结论成立的条件"；只挂 `data-label` 不算 |
| F6 | 末节口径 | 位置对不够，正文 ≥60 字且含数字；按 h2 精确找节，不再用"最后一个 section"（末尾还有证据包说明） |
| F7 | 图带来源 | **逐图**校验：每张 `<figure>` 内的 `fig-src` 必须有 ≥6 字来源文字；数 class 个数不算 |
| F8 | 不出现 JSON | 不变 |
| F9 | 重复句/密度/禁用词 | 不变 |
| F10 | 深度 | 与 `core.report.report_quality` 同一判据 |
| F11 | **不许自证** | 正文出现「全部门禁通过 / 两道门禁独立校验」→ FAIL |

## 4. 门禁指纹与锁

- 每次过闸：`manifest.gate.flow.gate_sha256` = 当前门禁脚本的 sha256；
- `configs/report_gate.lock.json` 记录被认可的门禁指纹；
- 不一致 → 产线判 `G0_gate_lock` FAIL，CI 的 `scripts/check_gate_lock.py` 也 FAIL。

改门禁的正确姿势：

```bash
# 1. 改 scripts/check_report_flow.py（只许改判据实现，不许放宽语义）
# 2. 跑回归
python tests/test_gate_contract.py
# 3. 认可新指纹，和门禁改动一起提交
python scripts/check_gate_lock.py --write
git add scripts/check_report_flow.py configs/report_gate.lock.json
```

## 5. 降级必须留痕

| 动作 | 参数 | 落点 |
|---|---|---|
| 关回抓 | `--no-verify-quotes` | 需 `--allow-degraded`；`manifest.quotes.degraded=true` |
| 关严格 | `--no-strict-quotes` | 同上 |
| 关来源门槛 | `--min-sources 0` | `degraded: ["min_sources_off"]` |
| 门禁只记录 | `--no-gate-hard` | `manifest.ok=false` 但仍出稿，供排障 |

`merged.meta.degraded` → `draft.degraded` → `manifest.degraded` 一路带过去；
`report attest` 会把它们逐条打出来。

## 6. 来源计数口径

- `evidence.sources`：登记条数（4 个角色各登记一次 = 4）；
- `evidence.unique_sources`：按归一化 URL 去重后的条数（**门槛只看这个**）；
- `evidence.duplicate_sources`：被标成重复的条数；
- `quote_rate`：只表示"每个数字都挂了引文字段"，`quote_rate_scope=fields_present_only`；
- 真实核验看 `source_verify.verified / total`（或 manifest.quotes.verified）。

> 2026-11-20 的 140 条"来源"实际只有 48 个页面：去重键原来写的是 `角色:文件编号`。

## 7. R04 输入必须派生

`core/r04_derive.py` 从产物生成

- `r04_inventory.json` / `r04_criteria.json` / `r04_quality.json`，
- 每份带 `derived_from.artifact_sha256`（report.html 的 sha256）。

`scripts/check_r04_inputs.py --dir <out>` 校验 sha；
手写、或产物重出后没重派生的，一律 FAIL。
