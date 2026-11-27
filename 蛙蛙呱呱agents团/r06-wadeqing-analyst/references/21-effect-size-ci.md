# 21 · 效应量、置信区间与多重检验（test）

> R06 分析链第 6 段的领域依据。核心：**p 值不等于效应量，显著不等于重要**；没有区间与敏感性，就不下结论。

## 1. 为什么要同时给效应量与区间

只看 p 值会得到两个错误结论：

1. 大样本下 0.1% 的差异也“显著”，但业务上不值得动作；
2. 小样本下 20% 的差异“不显著”，被误判为没变化。

本仓要求 headline 同时包含：

| 指标 | 含义 | 门禁 |
|---|---|---|
| 均值差 / 相对 lift | 业务可读的变化幅度 | 必填 |
| Cohen's d | 标准化效应量（小/中/大） | 必填 |
| bootstrap 95% CI | 差异的不确定性区间 | 必填，lo ≤ hi |
| Welch t 的 p | 独立样本均值差异的显著性 | 必填，标注 exact/approx |
| 样本量 | 每组 n | 每组 ≥30，否则 CRITICAL |
| 敏感性 | 截尾 1% 后差异变化 | 必填，变化 >20% 记 HIGH |

## 2. Welch t 与正态近似

两组独立样本、方差不齐时用 Welch t，而不是 Student t。本仓复用 `skills/_stats.py`：

- `t = (mean_a − mean_b) / sqrt(var_a/n_a + var_b/n_b)`；
- 自由度按 Welch–Satterthwaite 近似；
- p 优先用 `shared.stats_exact`（scipy 可用时），否则用正态近似，并在输出中标注 `p_method`。

近似要在结论里可见，不能把 approx 当 exact 用。

## 3. Bootstrap 置信区间

不依赖正态假设：

1. 对每组有放回重采样，样本量不变；
2. 计算均值差；
3. 重复 1000 次，取 2.5% / 97.5% 分位。

本仓固定随机种子（默认 0），保证复算一致；CI 与 p 值要一起看：CI 跨 0 时，即使 p<0.05 也要谨慎解释。

## 4. Holm 多重检验校正

分段越多，偶然“显著”的概率越高。本仓对同一维度的分段检验做 Holm 校正：

1. 把 m 个 p 值升序排列；
2. 第 i 个校正 p = max(前一个校正 p, (m − i + 1) × p_i)；
3. 上限 1。

只报校正后仍显著的结论；未校正的 p 保留在明细里供复核，但不得作为主结论依据。

## 5. 前提检查与敏感性

| 检查 | 判据 | 不满足时 |
|---|---|---|
| 样本量 | 每组 ≥30 | CRITICAL（不得下结论） |
| 偏度 | |skew| ≤1 | HIGH（提示用 bootstrap/非参数） |
| 方差比 | max/min ≤3 | HIGH（Welch 已缓解，但需说明） |
| 截尾敏感性 | 去 1% 极值后差异变化 ≤20% | HIGH（结论对极值敏感） |

这些检查不是形式主义：它们决定结论能不能写成“稳健”。

## 6. 本仓落点

| 能力 | 代码 | 门禁 |
|---|---|---|
| Welch t + Cohen's d | `skills/_stats.welch_t` | headline 必含 |
| Bootstrap CI | `analysis_chain/stats_test.py` | CI 缺失/倒置 → CRITICAL |
| Holm 校正 | 同上 | 分段检验缺 `p_adjusted` → CRITICAL |
| 敏感性 | 截尾 1% | 变化 >20% → HIGH |
| 前提检查 | 样本/偏度/方差比 | 样本不足 → CRITICAL |

## 7. 适用边界

- 适合：两组独立样本的前后期/AB 对比；
- 不适合：同一用户重复观测（应做配对或混合模型，本仓未实现，需标 blocked）；
- 不适合：多组同时比较（应先用 ANOVA，再做事后校正）；
- 不适合：把统计显著直接翻译成“应该上线”。

## 8. 误用反例

| 反例 | 为什么错 | 本仓如何拦 |
|---|---|---|
| 只报 p=0.03，不报效应量与 CI | 无法判断重要性 | headline 必填字段缺失 → CRITICAL |
| 每组 n=8 就宣布显著 | 样本不足 | n<30 → CRITICAL |
| 10 个分段里挑 1 个显著 | 多重比较 | 缺 Holm 校正 → CRITICAL |
| 去掉极值后结论反转仍照报 | 不稳健 | 敏感性 HIGH |
| 把 p 值写成“概率为真” | 误解 p 值 | 输出 method_note 明确口径 |

## 9. 来源

- Welch, B. L. (1947). The generalization of "Student's" problem when several different population variances are involved. *Biometrika*, 34(1/2).
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2).
- Cumming, G. (2014). The New Statistics: Why and How. *Psychological Science*, 25(1).
- Wasserstein, R. L., & Lazar, N. A. (2016). The ASA Statement on p-Values. *The American Statistician*, 70(2).
