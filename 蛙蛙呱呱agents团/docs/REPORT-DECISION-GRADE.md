# 决策级报告定义（REPORT-DECISION-GRADE.md）

> 版本：v0.1 · 2026-11-17
> 这是升级 SOP 的 P1 产物，也是后续所有报告门禁的**唯一判据**。
> 实现：`core/claim_card.py`　｜　体检命令：`python -m core.claim_card audit --claims <json>`

---

## 1. 一句话

**决策级报告 = 每个头条断言都能回答“可比吗、还有什么解释、什么会推翻它、它能支持哪个决定”。**

不是“数字多”，不是“页数长”，不是“门禁 PASS”。一个数字全可追溯但不可比的报告，仍然不是决策级。

---

## 2. 断言（Claim）的五件事

| # | 问题 | 字段 | 不合格的后果 |
|---|---|---|---|
| 1 | 这句话是什么 | `statement` / `refs` / `values` | 无 refs → 不能进正文 |
| 2 | 比较是否可比 | `comparability`：同品/同期/同单位/同渠道 | 任一 `unknown`/`no` → 不能 `actionable` |
| 3 | 还有什么解释没排除 | `rivals`：竞争解释 + 状态 + 证据 | 有 `unruled` → 不能 `actionable` |
| 4 | 什么会推翻它 | `falsifier` | 空 → 不能 `actionable` |
| 5 | 能拿来做决策吗 | `actionable` / `confidence` / `grade` / `decision` / `expiry` | `false` → 不能进标题、不能进动作 |

---

## 3. ClaimCard 规则（写进代码，不靠纪律）

```
headline=true  => actionable=true
actionable=true => comparability 无 unknown/no
                  rivals 全部 ruled / partially_ruled（partially 要有 evidence）
                  falsifier 非空
                  decision 非空
                  confidence ∈ {low, medium, high}
                  grade ∈ {A, B, C, D}
预测类（kind=forecast/prediction）=> expiry 必填
```

### 3.1 什么能进标题

- 只有 `actionable=true` 的断言能进标题；
- 标题里的数字必须是 `refs` 能解释的数字；
- 标题不得使用报告自己标为“不可比”的比较。

### 3.2 什么能进动作清单

- 只有 `actionable=true` 且 `decision` 非空的断言能进动作；
- 每条动作必须有 `owner`、`stop`（停止条件）、`expiry`（复核时点）。

### 3.3 什么只能进“观察/假设/缺口”

- `actionable=false` 的断言只能出现在观察、假设、缺口三节；
- 必须写清“缺什么才能变成 actionable”（`gaps`）；
- 不得用“值得关注/有待观察”这类词替代缺口说明。

---

## 4. 与 M1–M5 的关系

| 模块 | 用 ClaimCard 做什么 |
|---|---|
| M1 问题定义 | 每个必答问题对应 1–3 条 claim；没有问题对应 = 该节不该存在 |
| M2 数据校验 | `refs` 必须指向 A/B/C/D 等级来源；C/D 级只能支撑 `actionable=false` |
| M3 结构化推导 | 每条 claim 走 观察→对照→机理→落点→证伪；`rivals` 是“对照”的硬要求 |
| M4 风险 | `rivals` 未排除项 + `falsifier` + `expiry` 汇总成风险节 |
| M5 动作 | 只有 `actionable=true` 的 claim 能生成动作与停止条件 |

---

## 5. 三个例子（来自水果项目 P1 试点）

### C01 — 不可行动的头条（交付稿原文）

```json
{
  "statement": "呼市富士苹果批发价是赤峰的 1.98 倍，但零售只差 8.0%，钱不在价差里",
  "comparability": {"same_product": "unknown", "same_period": "yes",
                    "same_unit": "yes", "same_channel": "yes"},
  "rivals": [{"name": "等级/规格差异", "status": "unruled"},
             {"name": "市场势力", "status": "unruled"}],
  "falsifier": "同等级同规格批发价差 < 20%",
  "actionable": false,
  "headline": true
}
```

**判定：FAIL。** 头条断言不可行动，不能进标题。缺等级/规格标注；S01/S03 页面没有等级信息。

### C04 — 可行动的经营断言

```json
{
  "statement": "12 个品类里 7 个扣损耗与冷链后净毛利为负",
  "comparability": {"same_product": "yes", "same_period": "yes",
                    "same_unit": "yes", "same_channel": "yes"},
  "rivals": [{"name": "损耗/冷链假设偏差", "status": "partially_ruled",
              "evidence": "A2 声明假设 + 敏感性"}],
  "falsifier": "企业实际损耗/冷链比假设低 20% 时，负毛利品类数 <5",
  "actionable": true,
  "decision": "哪些品类停采/换源/提价"
}
```

**判定：PASS，但带 warning。** `grade=C`，必须保留敏感性；如果企业台账证明假设偏差 >20%，降级为假设。

### C03 — 只能进观察的预测

```json
{
  "statement": "未来两个月水果篮子基准 +2.0%",
  "comparability": {"same_product": "yes", "same_period": "no"},
  "rivals": [{"name": "去年单年季节性不代表今年", "status": "unruled"}],
  "actionable": false,
  "kind": "forecast",
  "expiry": "2027-01-16"
}
```

**判定：只能进“观察/情景”，不能进标题和动作。** 去年同期单年样本，未排除天气/供给/基数效应。

---

## 6. 与旧门禁的区别

| 旧门禁（F1–F10 / Q1–Q7） | 新门禁（ClaimCard） |
|---|---|
| 检查文档：标题带数、密度、图源、禁用词 | 检查断言：可比性、竞争解释、证伪、决策 |
| 数字可追溯即可 | 数字可追溯 **且** 比较可识别 |
| 作者自证 + R04 清点 | 独立 R04 审计 claim card |
| 分数 100 = 合规 | `actionable_ratio` = 决策可用度 |
| 可以靠加数字/加图提高分 | 不能靠形式提高 actionable |

**旧门禁不是废掉，而是降级为“形式建议项”**；放行由 ClaimCard + coverage 决定。

---

## 7. P1 试点结果（水果项目 10 条断言）

| 指标 | 值 |
|---|---|
| 断言总数 | 10 |
| actionable | **6 / 10（60%）** |
| unidentified | **4 / 10（40%）** |
| headline 总数 | 4 |
| headline actionable | **3 / 4** |
| headline 不可行动 | **1（C01，交付稿头条）** |
| 证据等级 | A 0 / B 1 / C 9 / D 0 |
| 置信度 | low 4 / medium 5 / high 1 |
| 有 refs | 10 / 10 |
| actionable 有 falsifier | 6 / 6 |

**结论：**

1. 交付稿的头条（1.98x）是唯一不可行动的头条；4 份 pipeline 报告的头条里 3 条可行动。
2. 40% 的断言不可行动，主要缺口是**等级/规格、期间对齐、单位换算**，不是“数字不够多”。
3. 9/10 是 C 级来源；没有 A 级。说明“证据规模”不是问题，**证据等级**才是。
4. C08 的 5.99/6.80 与来源 6.00/14.00 不一致，且元/斤 vs 元/公斤未统一——这是 P3 数据 intake 要解决的。

---

## 8. P1 Gate 建议

**不要求 `audit.ok=true`**——当前报告本来就不合格，P1 的目的是把问题量出来。建议的 Gate 是：

- [x] 10 条断言全部有 refs；
- [x] ≥3 条 `actionable=false` 且写清缺口（实际 4 条）；
- [x] 1.98x、0.99、+2.0% 三条全部被判 `actionable=false`；
- [x] 每条可行动断言有 `falsifier`；
- [ ] 创始人确认：接受 60% 作为基线，进入 P2（能力图 + coverage），还是先补 C01/C02/C08 的数据再进。

**建议：进入 P2，但把 C01/C02/C08 作为 P3 数据 intake 的第一批任务。** 因为这三条缺的是“等级/规格/单位/同期”，不是“再跑一次报告”。
