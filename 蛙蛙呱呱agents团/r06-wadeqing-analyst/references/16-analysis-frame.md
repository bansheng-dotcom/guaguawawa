# 16 · 分析框架（frame）：把业务问题变成可证伪假设

> 本文是 R06 分析链第 1 段的领域依据。目标不是“想得更全”，而是**让每个假设都能被数据推翻**，并且每个假设都绑定一个决策。
> 来源为公开方法论与论文，本仓只引用方法，不复制原文。

## 1. 解决什么问题

业务问题通常是“利润为什么下滑”“客户为什么流失”。直接算数会得到一堆相关关系，最后变成“可能是……也可能是……”。
frame 段的作用是先写下 3–5 个互斥假设，并给每个假设一个**推翻条件（falsifiable_if）**，再进入数据。

判据不是“假设听起来合理”，而是：**如果数据长成 X，这个假设就必须被放弃。**

## 2. 最小契约（本仓 `analysis_chain/frame.py`）

| 字段 | 要求 | 门禁 |
|---|---|---|
| `question` | 业务问题原文 | 非空 |
| `decision_use` | 这份分析要支持什么决策 | 非空 |
| `metric` | 分析指标列（可与业务叫法不同） | 非空 |
| `dimensions` | 1–3 个切分维度 | 不重复、不超过 3 |
| `hypotheses[]` | 3–5 条 | 数量与 ID 唯一 |
| `hypotheses[].falsifiable_if` | 带阈值的推翻条件 | 长度 ≥8 且含数值语义 |
| `hypotheses[].decision_if_true/false` | 成立/不成立各做什么 | 均非空 |
| `hypotheses[].evidence_required` | 需要哪些证据 | 非空 |
| `hypotheses[].status` | 看数前必须是 `unverified` | 否则 HIGH |
| `mece` | 互斥 + 覆盖指标恒等式 | 未覆盖即 CRITICAL |

恒等式按领域内置：

- 利润 = 收入 − 成本；收入 = 量 × 价（利润域覆盖“收入/成本”两类驱动）
- 收入 = 量 × 价（收入域）
- 流失 = 新客流失 + 老客流失（流失域）
- 增长 = 供给 × 分发（增长域）

## 3. MECE 的正确用法

MECE（Mutually Exclusive, Collectively Exhaustive）不是“多列几个维度”，而是：

1. **互斥**：同一个变化只能落到一个驱动上，否则贡献会重复计算；
2. **穷尽**：所有驱动加起来必须能还原指标恒等式，否则会漏掉真因。

本仓把“维度（channel/category）”与“驱动（价格/销量/成本/结构）”分开：
维度用于切数据，驱动用于解释恒等式。把维度当驱动，是常见的第一类错误。

## 4. 适用边界

- 适合：单指标、单窗口、要先定位主因再决定动作的诊断型问题；
- 不适合：开放式探索（先用 explore 找现象，再回来 frame）；
- 不适合：没有可比较前后期/对照组的数据（此时只能描述，不能归因）；
- 假设数量上限 5：超过 5 条通常意味着问题没拆干净，应先拆问题。

## 5. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 把“时间”当驱动（“9 月下滑是因为到了 9 月”） | 同义反复，不可证伪 | `driver in {time,时间,日期,趋势}` → CRITICAL |
| 只写“可能是价格、也可能是成本”，不写推翻条件 | 看完数仍无法判断 | `falsifiable_if` 为空/过短 → CRITICAL |
| 假设没有对应决策 | 分析做完也不知道做什么 | `decision_if_true/false` 为空 → CRITICAL |
| 先看数再补假设（HARKing） | p 值与结论都被污染 | `status` 必须 `unverified`；plan 段再做一次预注册门禁 |

## 6. 来源

- Popper, K. *Conjectures and Refutations* (1963)：可证伪性作为科学假设的判据。
- Minto, B. *The Pyramid Principle* (1987)：MECE 与结论先行的结构化表达。
- Kerr, N. L. (1998). HARKing: Hypothesizing After the Results are Known. *Personality and Social Psychology Review*, 2(3), 196–217.
- Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *PNAS*, 115(11), 2600–2606.
- Hernán, M. A., & Robins, J. M. *Causal Inference: What If* (2020)：把“因果问题”与“描述问题”分开表述。
