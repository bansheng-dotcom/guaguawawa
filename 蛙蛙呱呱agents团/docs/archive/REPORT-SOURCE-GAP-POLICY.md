> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 来源缺口政策（REPORT-SOURCE-GAP-POLICY.md）

> 版本：v0.1 · 2026-11-17（P7）
> 适用：`report build` 的 quote 门禁
> 原则：**缺口写清楚，不伪造 quote；strict 拦下，warn 标 ok=false。**

---

## 1. 现在的缺口（水果项目）

| 类型 | 数量 | id |
|---|---|---|
| 页面有品类但引用值不一致 | 3 | S11（鸭梨）、S13（香蕉）、S14（巨峰） |
| 动态页/JS 正文无值 | 3 | S19（草莓）、S22（雨润）、S27（商务预报） |
| 403 / 反爬 | 6 | S15、S17、S18、S28、S29、S30（其中 S15/17/18 曾通过） |
| 合计 | 12 | — |

其中本报告实际引用 11 条；
S15 未被本报告引用。

---

## 2. 门禁规则

```bash
# 看缺口（诊断，不产报告）
python guagua.py report gaps --project <项目目录>

# 默认 strict：有缺口就不出报告
python guagua.py report build --intent "…" --dir <项目> --out <目录>

# warn：可出稿，但 manifest.ok=false
python guagua.py report build --intent "…" --dir <项目> --out <目录> --quote-mode warn

# off：只在 CI 快速路径用，不代表报告合格
```

判定：

```
manifest.ok = 渲染 ok
            且 coverage = COMPLETE
            且 quotes.ok = true
```

`quotes.ok=false` 的报告可以给人看，**不能当“已核验交付物”**。

---

## 3. 关闭缺口的三种合法方式

| 方式 | 做法 | 结果 |
|---|---|---|
| **换源** | 找同事实、可打开的官方/行业来源，补 `quote` | 来源变 `ok` |
| **降级** | 该数字只进“观察/假设”，不进标题/动作 | 断言 `actionable=false` |
| **标 void** | 口径变了/数据不可比 | 台账 `void`，不算命中也不算失败 |

**不允许**：把页面标题当 quote、把“大意”写成引文、把 `unreachable` 改 `ok`。

---

## 4. 为什么不一次性清掉

- S11/S13/S14 的引用值与当前页面不一致，可能是采价时点不同；需要换到**同规格、同期**的页面。
- S19/S22/S27 是 JS 渲染/数据表，HTML 里没有值；需要找 API 或替代页。
- S28/S29/S30 是 403；S15/S17/S18 曾通过、现在反爬；需要快照/换源。
- 这些都不是“再跑一次脚本”能解决的；**没有来源就不补 quote**。

---

## 5. 维护规则

1. 新项目接入时，`sources.json` 每条必须有 `grade` + `quote`；
2. `quote` 必须能在原文命中，不能是标题；
3. 缺口进 `data/quote_gaps.json`，并在报告边界/风险节写出来；
4. strict 是默认，warn 只是过渡；不要把 `off` 当默认；
5. 台账里对引用缺口来源的判断标 `void`，不要用“命中”掩盖。

## 6. 自动处置清单（P13）

```bash
python scripts/dispose_quote_gaps.py --project <项目>
```

输出 `data/quote_gap_disposition.json`：

- 反爬/不可复现 → `void`；
- 页面无引用值 → `downgrade`。

**只出处置，不补 quote、不改核验状态。** strict 仍会阻断。

