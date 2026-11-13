# ML_SPEC.md — R19 蛙智模 · 模型工程与 AI 评估统一规格账本 (SSOT)

> **版本**：v13.0  
> **单一信任源 (Single Source of Truth)**：本账本定义「从实验追踪到发布证据」全链路的
> 评估指标口径、证据链标准、资产溯源要求与 **8 维发布硬门禁**。任何 skill / harness /
> review / engine 的阈值判定，必须引用本账本，不得在代码里各自硬编码。  
> **对标标杆**：`mlflow/mlflow` Model Registry & Evaluation（>20k）· `dbt-labs/dbt-semantic-layer`（>10k）·
> `scikit-learn` metrics 口径（>60k）· `OASIS SARIF v2.1.0`。

---

## 一、 北极星指标与核心准则 (North Star & KPI)

| 指标代号 | 指标名称 | 目标基准线 | 确定性口径 |
| :--- | :--- | :--- | :--- |
| **ERA** | 评估可复算率 (Evaluation Recomputability Accuracy) | **= 100.0%** | 每条评估记录必须有 `expected` 与 `predicted`；accuracy/precision/recall/f1 必须可由混淆矩阵 `tp/fp/tn/fn` 重算，`tp+fp+tn+fn = n`，容差 **0.00** |
| **GGR** | 回归门禁通过率 (Gate Green Rate) | **= 100.0%** | 发布候选裁决 PASS 必须挂回归报告，且 `fail_before=true / pass_after=true / existing_green=true` 三者齐备 |
| **ATR** | 资产可溯源率 (Artifact Traceability Rate) | **= 100.0%** | 每个模型资产必须同时具备非空 `path`、绑定的 `run_id` 与可校验的 `sha256` |
| **CLR** | 凭据零泄露率 (Credential Leak-free Rate) | **= 100.0%** | 工件内 api_key / secret / password / token / 私钥 / 连接串出现次数必须为 **0** |
| **BTA** | 勾稽容差绝对值 (Balance Tolerance Accuracy) | **= 0.00** | 指标与金额类算子一律零容差；浮点比较须 `abs(delta) <= 1e-9` |

---

## 二、 模型工程计算规范 (ML Calculation Models)

1. **分类指标守恒公式 (Classification Metric Conservation)**：
   $$\text{accuracy} = \frac{tp + tn}{n},\quad
     \text{precision} = \frac{tp}{tp + fp},\quad
     \text{recall} = \frac{tp}{tp + fn},\quad
     \text{f1} = \frac{2 \cdot precision \cdot recall}{precision + recall}$$
   - 约束：$tp + fp + tn + fn = n$，容差 0.00；分母为 0 时取 0.0（零除安全，不抛异常）。
2. **延迟分位精算 (Latency Percentile)**：
   $$p_k = \text{linear\_interp}\big(\text{sorted}(x),\, k\big)$$
   - p50 / p95 / p99 必须由实测样本线性插值得到，禁止输入自报。
3. **发布三裁决 (Release Tri-Verdict)**：
   $$verdict \in \{PASS,\ BLOCK,\ NEEDS\_REVIEW\}$$
   - PASS 的唯一通行证是「评估证据 + fail-before/pass-after 回归」；主观感受不构成证据。
4. **资产溯源指纹 (Artifact Fingerprint)**：
   $$\text{sha256}(f) = \text{digest}(\text{bytes}(f)),\quad
     \text{traceable} = (path \ne \varnothing) \wedge (run\_id \ne \varnothing)$$
5. **模型阶段唯一性 (Stage Uniqueness)**：
   $$\#\{v \in versions \mid v.stage = production\} \le 1$$
   - 同一模型不得同时存在两个 production 版本。

---

## 三、 八维发布硬门禁矩阵 (The 8-Dimension Release Gate Matrix)

| 门禁 ID | 门禁名称 | 刚性校验标准 | 破坏后果与处置 |
| :--- | :--- | :--- | :--- |
| **GATE-01** | 评估指标可复算门禁 (Metric Recomputability Gate) | **记录含 expected/predicted 且混淆计数守恒 (容差 0.00)** | 指标不可复算 → CRITICAL，评估报告作废 |
| **GATE-02** | 证据链完整门禁 (Evidence Chain Gate) | **PASS 裁决必须 `evidence ≥ 1`** | 无证据 PASS → 阻断，降级 NEEDS_REVIEW |
| **GATE-03** | 回归门禁 (Regression Gate) | **fail_before / pass_after / existing_green 皆 True 且挂 regression_id** | 无回归 PASS → 阻断，退回补回归 |
| **GATE-04** | 资产可溯源门禁 (Artifact Traceability Gate) | **path 非空 + run_id 绑定 + sha256 可校验** | 悬空资产 → 阻断，禁止入库 |
| **GATE-05** | 凭据零泄露门禁 (Credential Zero Gate) | **凭据词命中数 = 0** | 凭据入工件 → CRITICAL，退回密钥管理 |
| **GATE-06** | 阶段唯一性门禁 (Stage Uniqueness Gate) | **production 版本数 ≤ 1** | 多 production → 阻断，回滚多余版本 |
| **GATE-07** | 枚举合规门禁 (Enum Compliance Gate) | **verdict/stage/risk_tier/license 均在白名单** | 枚举越界 → 阻断，按白名单归一 |
| **GATE-08** | 越权移交门禁 (Publication Handoff Gate) | **发布动作必须声明 handoff / authorized_by** | 越权发布 → `[REDLINE BLOCKED]`，移交 R09/R20/R03 |

---

## 四、 角色红线与合规边界 (Non-Negotiable Boundaries)

1. **严禁凭「效果看起来不错」放行**：任何上线结论必须有评估证据 + 回归报告；主观感受一律拦下。
2. **严禁不做统计结论 / 业务归因 / 决策建议**：相关性、显著性、归因、增长建议一律移交 **R06 蛙得清**。
3. **严禁执行生产部署 / 灰度 / 流量切分 / 模型分发**：落地与监控告警执行移交 **R09 蛙联调 / R20 蛙值守**；模型风险与许可的法律判定移交 **R03**。
4. **严禁凭据入工件**：api_key / secret / password / token / 私钥 / 连接串一律走环境变量或密钥管理。
5. **严禁篡改已归档的历史裁决与评估结果**：已发布结论不可回填覆盖，必须走新的候选版本，移交 **R04 蛙挑刺 + R20** 审计。
