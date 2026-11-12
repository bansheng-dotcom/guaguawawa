# 方法代码深度升级 SOP（可执行版）

> 版本：2026-11-12 ｜ 适用：`shared/methods/*.py`、各角色 `skills/` 中的方法技能
> 一句话：**「能算出数」只是 L1；能说清识别、给出不确定性、通过反驳和留出验证，才算 L3。**
> 配套审计：`python scripts/audit_method_depth.py`

---

## 0. 为什么需要这份 SOP

上一轮我们补了 `matched/did/elasticity/mmm/rdd/fulfillment`，但对照 GitHub 成熟实现（DoWhy、pyfixest、Robyn、rdrobust、SimPy），多数只到「能算」：没有平衡检验、没有聚类标准误、没有平行趋势、没有 adstock/饱和、没有带宽敏感性。**这不叫深度，叫公式翻译。**

这份 SOP 把「深度」拆成可检查的组件和可执行的验收测试，防止再用「代码能跑」冒充「方法可靠」。

---

## 1. 深度分级（L0—L4）

| 级别 | 标准 | 典型特征 |
|---|---|---|
| **L0 伪方法** | 名字像方法，实际是描述统计 | 把均值差叫 DID；把相关系数叫因果 |
| **L1 能算** | 公式正确、能跑通 | 有估计值，无 SE/CI/诊断 |
| **L2 可解释** | 有不确定性 + 至少一项诊断 | bootstrap CI、SMD、pretrend、placebo、holdout 之一 |
| **L3 可审计** | 识别假设、稳健性、验证齐全 | 聚类 SE、平衡、平行趋势、带宽/安慰剂、留出验证 |
| **L4 可发表** | 达到参考实现主路径 + 反驳测试 | 事件研究、交错处理、偏差校正、预算优化、覆盖模拟 |

当前状态（`audit_method_depth.py`）：

| 方法 | 得分 | 级别 | 本轮补齐 |
|---|---|---|---|
| 匹配/PSM | 6/6 | L4 | 聚类自助、安慰剂+子集反驳 |
| DID/TWFE | 6/6 | L4 | 事件研究、置换安慰剂、交错处理 |
| 价格弹性 | 6/6 | L4 | 面板 FE、2SLS + 一阶段 F |
| MMM | 8/8 | L4 | 预算分配、贡献块自助 CI |
| RDD | 6/6 | L4 | 二次偏差校正、协变量平衡 |
| 履约/库存 | 6/6 | L4 | 预热期、履约率 CI |

> 目标：P0 方法到 L3；对外交付的方法不得低于 L2。**本轮 6 个方法已全部到 L4（按特征审计）**，测试验证恢复真值。

---

## 2. 每个方法的最低组件（DoD）

### 2.1 匹配 / PSM

| 组件 | 要求 | 验收 |
|---|---|---|
| 倾向得分 | logit/IRLS，协变量明确 | 系数收敛、无完全分离 |
| 匹配 | 最近邻 + 卡尺 + 共同支撑 | 匹配数 ≥ 处理组 70% |
| 平衡 | 匹配前后 SMD | 匹配后 max\|SMD\| < 0.1 |
| 不确定性 | 自助法 CI | CI 覆盖真值（模拟 95%） |
| 反驳 | 安慰剂处理/随机共同原因 | 安慰剂效应接近 0 |

### 2.2 DID / TWFE

| 组件 | 要求 | 验收 |
|---|---|---|
| 固定效应 | unit + time 双向去均值 | 与 `pyfixest` 点估计差 < 1e-6（平衡面板） |
| 标准误 | 聚类到 unit | 聚类数 ≥ 30；少于 30 用 wild bootstrap |
| 平行趋势 | pre 期 treated×time 检验 | p > 0.05 才可解释 |
| 动态效应 | 事件研究 leads/lags | 事前系数不显著 |
| 稳健性 | 安慰剂处理时点/置换 | 安慰剂效应 < 主效应 1/3 |

### 2.3 价格弹性

| 组件 | 要求 | 验收 |
|---|---|---|
| 函数形式 | log-log，弹性=系数 | 合成数据恢复 ±0.1 |
| 控制变量 | 至少一个混杂控制 | 系数方向不翻转 |
| 稳健 SE | HC1/聚类 | CI 覆盖真值 |
| 面板 | 固定效应去均值 | 组内估计与 FE 一致 |
| 内生性 | IV/滞后/外生冲击 | 一阶段 F > 10（若用 IV） |

### 2.4 MMM

| 组件 | 要求 | 验收 |
|---|---|---|
| adstock | 几何/延迟，θ 网格 | 合成数据 θ 恢复 ±0.2 |
| 饱和 | Hill/logistic，参数可解释 | 边际收益递减 |
| 正则 | ridge/lasso，λ 可调 | 共线渠道系数稳定 |
| 趋势/季节 | 线性趋势 + 周期项 | 残差无趋势 |
| 留出验证 | 末 20% holdout | R²_holdout > 0.8 |
| 贡献 | 贡献占比 + 不确定性 | 占比合计 100%，CI 可给 |
| 预算 | 边际 ROI 分配 | 给定预算下总贡献提升 |

### 2.5 RDD

| 组件 | 要求 | 验收 |
|---|---|---|
| 局部线性 | 三角核，左右分别拟合 | 合成跳跃恢复 ±0.2 |
| 带宽 | 网格敏感性 | 估计随带宽稳定（±20%） |
| 安慰剂 | 假断点 | 安慰剂 p < 0.1 |
| 密度 | McCrary 型检验 | p > 0.05（无操纵） |
| 偏差校正 | 局部二次/robust bias-corrected | 与线性估计差 < 1 SE |
| 协变量 | 断点处平衡 | 协变量跳跃不显著 |

### 2.6 履约 / 库存

| 组件 | 要求 | 验收 |
|---|---|---|
| 策略 | (s,S) 或 (R,Q) | s<S，参数可解释 |
| 随机性 | 需求 + 提前期分布 | 多次仿真 CI 收敛 |
| 服务水平 | 履约率 + 周期服务水平 | 与目标服务水平差 < 3pp |
| 预热 | 丢弃前 10% 仿真期 | 平均库存稳定 |
| 容量 | 库存上限约束 | 无负库存/爆仓 |

---

## 3. 参考实现对照（从 GitHub 学什么）

| 参考 | 学什么 | 我们对应 |
|---|---|---|
| **DoWhy** | identify → estimate → **refute** 三段式；安慰剂/随机共同原因/子集反驳 | `deep.psm_att` 已有 PSM+平衡；缺 refute |
| **pyfixest** | 高维 FE、聚类/HAC/wild bootstrap、TWFE/Did2s/Sun-Abraham、平行趋势 | `deep.twfe_did` 有 FE+聚类+pretrend；缺事件研究/交错 |
| **Robyn** | adstock、饱和、ridge、趋势季节、多目标超参、预算分配 | `deep.mmm_deep` 有 adstock/饱和/ridge/holdout；缺预算/CI |
| **rdrobust** | 带宽选择、偏差校正、密度检验、协变量 | `deep.rdd_sensitivity` 有网格/安慰剂/密度；缺 RBC/协变量 |
| **statsmodels** | HC1/HAC、诊断、置信区间 | `deep.elasticity_ols` 有 HC1/CI；缺 FE/IV |
| **SimPy / OR-Tools** | (s,S)/(R,Q)、随机提前期、服务水平优化 | `deep.fulfillment_deep` 有 (s,S)+随机 LT；缺预热/优化 |

**学习动作**：读 README/API → 列出「主路径组件」→ 写合成数据 parity test → 实现最小版 → 与参考结果对比（容差写死）→ 再谈优化。

---

## 4. 执行流程（每个方法 7 步）

```bash
# 1) 审计现状
python scripts/audit_method_depth.py

# 2) 建缺口单：方法/缺口/验收测试名/负责人
#    例：DID 缺事件研究 → test_did_event_study

# 3) 在 shared/methods/deep.py 实现；不改 core.py 的向后兼容行为

# 4) 合成数据测试（真值已知）
python -m pytest tests/test_methods_deep.py -q

# 5) 反驳测试：安慰剂/随机化/子集/带宽/留出
#    每个方法至少 1 个反驳测试

# 6) 接角色技能（可选 --deep 开关，默认行为不变）
python guagua.py call r06 did --input ... --unit unit --time period
python guagua.py call r06 rdd --input ... --sensitivity
python guagua.py call r12 mmm --input ... --deep
python guagua.py call r15 fulfill-sim --demand ... --s --S --lead-sd 0.5

# 7) 契约 + 文档 + CI
python guagua.py call r06 contract validate --skill did --action did --output result.json
python scripts/ci_upgrade_checks.py
```

---

## 5. 验收测试（必须可执行）

| 测试 | 断言 | 文件 |
|---|---|---|
| PSM 恢复 | ATT 与真值差 < 0.2；SMD_after < 0.1 | `tests/test_methods_deep.py::test_psm...` |
| TWFE 恢复 | ATT 差 < 0.2；pretrend p > 0.05 | `test_twfe...` |
| 弹性恢复 | 弹性差 < 0.1；CI 覆盖真值 | `test_elasticity...` |
| RDD 恢复 | 跳跃差 < 0.2；placebo p 可算 | `test_rdd...` |
| MMM 留出 | R²_train > 0.95；R²_holdout > 0.8 | `test_mmm_deep` |
| 履约 | 履约率/CSL 在 0—100；CI 收敛 | `test_fulfillment_deep` |

> 测试用固定 seed；数值容差写死；不得用「跑通」代替「恢复真值」。

---

## 6. CI 门禁

`scripts/ci_upgrade_checks.py` 已加入：

| 门禁 | 命令 | 失败条件 |
|---|---|---|
| 方法深度 | `python scripts/audit_method_depth.py` | 任一方法 < L2（得分 < 50%） |
| 深度测试 | `pytest tests/test_methods_deep.py` | 任一失败 |
| 回归 | `pytest tests/test_methods_core.py` | 任一失败 |
| 角色入口 | `guagua.py check` | 非 20/20 |

目标（下一阶段）：把深度门禁从「≥L2」提到「P0 方法 ≥L3」。

---

## 7. 当前缺口与优先级

| 优先级 | 方法 | 状态 | 说明 |
|---|---|---|---|
| P0 | DID 事件研究/安慰剂 | ✅ 已补 | `event_study` / `did_placebo` / `staggered_att` |
| P0 | PSM 反驳 | ✅ 已补 | `psm_refute`（安慰剂+子集） |
| P0 | RDD 偏差校正/协变量 | ✅ 已补 | `_local_quadratic` / `rdd_covariate_balance` |
| P1 | 弹性 FE/IV | ✅ 已补 | `elasticity_fe` / `elasticity_iv`（F 统计） |
| P1 | MMM 预算/CI | ✅ 已补 | `mmm_budget` / `mmm_contribution_ci` |
| P1 | 履约预热 | ✅ 已补 | `fulfillment_deep(warmup=...)` |
| P2 | 完整 CS/RBC | 未做 | 需要面板数据与参考实现对比；当前为简化版，文档已标注 |

---

## 8. 禁止事项（防止伪深度）

1. 不得把 OLS 系数写成「因果效应」；必须写识别假设。
2. 不得只给点估计不给不确定性；至少 bootstrap CI 或稳健 SE。
3. 不得用全样本拟合再报「样本内 R²」冒充预测力；必须有 holdout。
4. 不得在未做平行趋势时解释 DID；未做密度检验时解释 RDD。
5. 不得把「代码能跑」写进验收；验收必须是「恢复已知真值/通过反驳」。
6. 不得为了过测试放宽容差；容差先写死，再实现。

---

## 9. 完成定义（DoD）

一个方法算「升级完成」，必须同时满足：

- [ ] `audit_method_depth.py` ≥ L3（或书面豁免理由）
- [ ] `tests/test_methods_deep.py` 有恢复真值测试 + 至少 1 个反驳测试
- [ ] 角色技能有 `--deep`/高级开关，默认行为不变
- [ ] `contract validate` 通过
- [ ] `ci_upgrade_checks.py` 全绿
- [ ] 文档写明识别假设、数据要求、失败模式


---

## 10. 技能层同样适用（2026-11-12 增补）

`audit_method_depth.py` 只管 6 个统计方法；全团 202 个技能用 `scripts/audit_skill_depth.py` 审计。

- 合规/结构校验器（合同、隐私、备份、状态页、webhook 映射）**L1 是本职**，不强行建模；
- 决策/诊断技能（决策、定价、渠道、健康分、库存、评测、SLO）必须有估计量 + 不确定性/敏感性；
- 新技能必须声明 `DEPTH = "L3"`（或 L4），并带契约 + 测试；
- 本轮已补 10 个：R01 `ev`、R02 `queue`、R05 `tam-mc`、R07 `rice`、R12 `power`、
  R16 `funnel`、R17 `retry-model`、R18 `profile`、R19 `eval-ci`、R20 `slo`。

审计命令：

```bash
python scripts/audit_skill_depth.py
```
