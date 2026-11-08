# W7：AB 实验进阶工程（9/8 — 9/14）

> 🎯 **本周目标**：W6 你学会了实验的基础工程——统一返回格式、SRM 前置检查、样本量计算。本周你要进入进阶区——CUPED 方差缩减不是背公式，是理解"为什么 θ 必须在对照组估计"；SUTVA 违反不是背概念，是用模拟亲眼看到"网络效应怎么污染你的 ATT"；14 坑中的 5 个核心坑要写成防御性 assert——不是"以后注意"，是"代码不让你通过"。学完这周，面试官让你闭卷写出 CUPED 公式并解释原理——你能从"公式是什么"讲到"为什么这样设计"再到"什么时候不该用"。
>
> 📎 **本周主课**：AB 实验（下）——MDE 深度/CUPED/网络效应/实验平台/14 坑/全流程模拟
>
> 🏢 **本周鲜果多剧情**：首页改版实验做完了——p 显著，但提升只有 2%，需要的样本量是 3500/组——跑了 7 天才出结果。运营总监问"能不能更快？"——你引入了 CUPED，用实验前数据作为协变量，方差缩减 52%——等价于样本量翻倍，实验从 7 天缩短到 4 天。但你还发现一个隐患：实验组用户通过分享链接影响了对照组——SUTVA 被违反。你需要评估偏差并决定是否改用 Cluster 实验。

---

## D1（周一 9/8）：CUPED 方差缩减——不只是公式，是"为什么 θ 必须在对照组算"

> 📓 今日主课：MDE 深度应用——MDE=业务沟通工具/反向 MDE 二分法/敏感性分析

---

### 🔴 认知冲突

你在 W6D5 学了样本量公式——n ∝ 1/MDE²。MDE 减半，样本量翻 4 倍。你把这个结论告诉了运营总监。她问："有没有办法不增加样本量，也能提升实验效率？"

你搜到了 CUPED——"用实验前数据作为协变量，减少方差，等价于增加样本量"。你照着公式写了出来：`Y_adj = Y - θ(X - E[X])`。代码跑通了——p 值变小了，效果很好。

然后面试官追问："θ 是用哪部分数据估计的？"

你愣住了。你没想过这个问题——你是用全量数据（对照组+实验组一起）算的 θ。面试官摇了摇头："实验组的 Y 里含有实验效应——你用含有实验效应的数据去估计 θ，再把 θ 用到同一个数据上调整——你调整了什么？"

**问题**：θ 为什么必须在对照组上估计？如果用全量数据估计——θ 里混入了什么？这会导致 CUPED 高估还是低估实验效应？这个问题在 AB 实验面试中被问到的概率超过 80%。

---

### 📖 核心原理

**CUPED 的本质——用"实验前的你"预测"实验后的你"，去除"预测得了的差异"。**

理解这个之前，先理解一个问题：为什么两组随机化之后，还需要 CUPED？

随机化保证两组在**期望**上是平衡的。但在**一次具体的实验**中——对照组和实验组之间必然有随机差异。比如——对照组恰巧分到了几个"本来就爱花钱"的用户。这种随机差异会增大方差——让你更难检测到真实的实验效应。

CUPED 的思路：如果你能度量"这个用户在实验前就爱花钱"（X）——你可以用它来解释一部分实验后的客单价（Y）——把"本来就爱花钱"这部分差异从方差中剔除。剩下的差异——就是更纯粹地由实验操作引起的。

**公式每一部分的含义：**

```
Y_adj = Y - θ(X - E[X])

Y         = 实验后的指标（你关心的——如客单价）
X         = 实验前的同一指标（如实验前 30 天的平均客单价）
E[X]      = X 的总体均值（对照+实验一起算——这是"预期水平"）
(X-E[X])  = "实验前你的水平比平均水平高多少"——这是"本来就存在的差异"
θ         = Y 和 X 的回归系数——X 每比均值高 1，Y 预期高多少
θ(X-E[X]) = "实验后因为'你本来就高'那部分差异"
Y_adj     = 去掉"本来就存在的差异"之后的调整值——剩下的更接近"实验操作导致的差异"
```

**为什么 θ 必须在对照组上估计——这是本周最重要的概念。**

θ 衡量的是"在没有实验干预的自然状态下，X 能在多大程度上预测 Y"。这个"自然状态"在哪里能看到？——在**对照组**身上。因为对照组没有受到任何实验干预——他们身上的 X→Y 关系是"自然的"。

如果用在实验组的数据来估计 θ——实验组的 Y 里已经包含了实验效应。比如说实验让每个人的客单价提高了 5 元——这个 +5 效应会混入 θ 的估计中——让 θ 偏大（因为 Y 被实验效应抬高了）。然后用这个偏大的 θ 去调整 Y——`Y_adj = Y - θ_bias(X-E[X])`——你减掉的部分超过了真实应该减掉的部分——**实验效应被过度纠正、低估了**。

**模拟验证——用代码亲眼看到这个偏差：**

```python
import numpy as np
rng = np.random.default_rng(42)

# 真实参数
n = 5000
true_effect = 5.0        # 实验让客单价提升了 5 元
theta_true = 0.8         # X 和 Y 之间的自然关系: 每高 1 元 → 实验后高 0.8 元

# 生成数据——X（实验前客单价）对两组都一样
x_control = rng.normal(100, 20, n)
x_treatment = rng.normal(100, 20, n)

# Y = 自然关系 + 实验效应（仅实验组有）
y_control = theta_true * x_control + rng.normal(0, 5, n)
y_treatment = theta_true * x_treatment + true_effect + rng.normal(0, 5, n)

# 对比两种 θ 估计方式
# 方式1（✅ 正确）：只在对照组估计
theta_correct = np.cov(y_control, x_control)[0, 1] / np.var(x_control)

# 方式2（❌ 错误）：用全量数据——实验效应混入
x_all = np.concatenate([x_control, x_treatment])
y_all = np.concatenate([y_control, y_treatment])
theta_wrong = np.cov(y_all, x_all)[0, 1] / np.var(x_all)

print(f"θ_true = {theta_true}")
print(f"θ_correct (仅对照) = {theta_correct:.4f}  ← 接近真实值")
print(f"θ_wrong (全量)   = {theta_wrong:.4f}  ← 偏大——混入了实验效应")
# 典型输出: θ_correct ≈ 0.8003, θ_wrong ≈ 0.8127——偏高
```

**完整实现——CUPED 函数 + 面试注释：**

```python
from typing import Tuple
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


def cuped_adjust(
    y_control: np.ndarray,
    x_control: np.ndarray,
    y_treatment: np.ndarray,
    x_treatment: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """CUPED 方差缩减——用实验前数据减少实验后指标的方差。

    ⚠️ 核心约束（面试必问）:
    θ 必须在对照组数据上估计！
    - 对照组 = 没有实验干预 → 其 X→Y 关系是"自然的"
    - 实验组的 Y 含有实验效应 → 用全量数据估计 θ，θ 会被污染 → 实验效应被过度纠正/低估
    - 验证方法：对比两种 θ 的差异——差异显著则说明实验效应大（这是好事但不是估计 θ 的理由）

    公式:
        θ = Cov(Y_control, X_control) / Var(X_control)
        Y_adj = Y - θ × (X - E[X_all])

    方差缩减比例 = ρ²(Y_control, X_control)
    - ρ > 0.7 → 缩减 > 49% → 等价于样本量翻倍 → 强烈推荐使用
    - ρ 0.3-0.7 → 缩减 9-49% → 有价值
    - ρ < 0.3 → 缩减 < 9% → 不值得引入 CUPED 的复杂度

    ⚠️ 不适用场景:
    - 没有高质量的实验前数据（如新用户 = 实验前数据为空）
    - X 和 Y 的时间间隔内有重大外部事件（导致自然关系被破坏）
    - 实验前数据本身受到之前实验的污染（需要清洗实验残留效应）

    ⚠️ 面试常见追问:
    Q: "为什么 θ 不能在全量数据上估计？"
    A: 实验组的 Y = 自然关系 + 实验效应。全量估计 θ 时，实验效应会被当成 X 和 Y 之间的"自然关系"——导致 θ 偏大。然后用偏大的 θ 调整 Y → 过度纠正 → 实验效应被低估。正确做法：只在"不受实验干预的"对照组上估计 θ。

    Q: "CUPED 和分层采样的区别？"
    A: 分层采样 = 实验前按 X 分层，保证每层内两组平衡——在实验设计阶段做。
       CUPED = 实验后统计调整——不需要在实验中干预分流逻辑。
       CUPED 更灵活（可用于任何已完成实验的事后分析），但分层采样在某些场景下效率更高。

    Args:
        y_control: 对照组实验后指标
        x_control: 对照组实验前指标（同一用户的历史值）
        y_treatment: 实验组实验后指标
        x_treatment: 实验组实验前指标

    Returns:
        (y_control_adj, y_treatment_adj, variance_reduction)
        variance_reduction = ρ² —— 如 0.52 表示方差缩减 52%
    """
    # Step 1: 只在对照组上估计 θ
    cov = np.cov(y_control, x_control)[0, 1]
    var = np.var(x_control)

    if var == 0:
        logger.warning("CUPED: X 的方差为 0——无法估计 θ。返回原始数据。")
        return y_control, y_treatment, 0.0

    theta = cov / var

    # Step 2: 全局 X 的均值——注意 E[X_all] 是用来中心化的
    x_all = np.concatenate([x_control, x_treatment])
    x_mean = np.mean(x_all)

    # Step 3: 用同一个 θ 调整两组
    y_control_adj = y_control - theta * (x_control - x_mean)
    y_treatment_adj = y_treatment - theta * (x_treatment - x_mean)

    # Step 4: 计算方差缩减比例 = ρ²
    corr = np.corrcoef(y_control, x_control)[0, 1]
    var_reduction = corr ** 2

    # 诊断日志
    logger.info("CUPED: θ=%.4f (仅在对照组估计), ρ=%.3f, 方差缩减=%.1f%%",
                theta, corr, var_reduction * 100)
    if var_reduction > 0.49:
        logger.info("  → 方差缩减 > 49%%——等价于样本量翻倍")
    elif var_reduction < 0.09:
        logger.warning("  → 方差缩减 < 9%%——CUPED 收益不大，考虑其他方法")

    return y_control_adj, y_treatment_adj, var_reduction
```

---

### 🏢 鲜果多案例

鲜果多首页改版实验——CUPED 的 X = 实验前 30 天用户的平均客单价，Y = 实验期间用户的客单价。你发现 ρ = 0.72——方差缩减约 52%。这意味着：同样的样本量，检测效率提升了 52%；或者说——达到同样的统计功效，只需要约一半的样本量。实验从 7 天缩短到 4 天。

你在实验报告中写了："用 CUPED 缩减方差 52%（ρ=0.72）。θ 在对照组（n=3520）上估计为 0.73——意味着实验前客单价每高 1 元，实验后客单价自然高 0.73 元。CUPED 调整后的 ATT 为 +4.2%（调整前为 +4.1%）——在这个案例中纠正幅度不大，因为两组实验前客单价本身平衡得很好。"

运营总监不需要理解 θ、ρ、Cov——但她需要知道"实验从 7 天变成了 4 天"。这就是工程化翻译：你理解深层原理，但输出浅层价值。

---

### ✍️ 动手练习

1. 在 `src/analysis/experiment.py` 中实现 `cuped_adjust()` 函数（复制上面的代码——但要逐行理解并写自己的注释）。
2. 用你主课的数据或鲜果多模拟数据跑一遍：
   - 找一个实验前指标 X 和实验后指标 Y——算 ρ 是多少？
   - 分别用"对照组 θ"和"全量 θ"跑一遍——对比两种方式得到的 ATT 差异。
   - 这个差异是什么方向？为什么？（用你自己的话写在注释里）
3. 在 CUPED 调整后的数据上跑 t-test——对比使用 CUPED 前后 p 值的变化。标注"方差缩减了 X%——等价于样本量增加了 Y%"。
4. 在代码注释里闭卷写出面试回答——包括"为什么 θ 在对照组估计"和"CUPED 和分层采样的区别"。
5. `git add . && git commit -m "implement CUPED with correct theta estimation on control group + simulation verification" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- ρ = Cov(Y_control, X_control) / (σ_Y_control × σ_X_control)。如果 X 和 Y 高度相关——ρ > 0.5。
- θ_correct（仅对照）≈ 0.80，θ_wrong（全量）≈ 0.81——全量估计的 θ 偏大。因为实验组 Y 被实验效应抬高了，cov(Y_all, X_all) 包含了这部分"非自然的"协方差。
- 用偏大的 θ 调整 Y → 减掉了不该减的部分 → ATT 被低估。

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "θ 在对照组和全量上差不多——说明可以混用" | 那是因为实验效应很小。但如果实验效应很大（如 ATT = +20%），θ_wrong 的偏差会很显著 | 不是"差不多"就可以——这是原则问题。面试官看到你混用会判定为"不理解 CUPED 原理" |
| "variance_reduction 算出来是 NaN" | 可能 X 的方差为 0（所有用户实验前客单价一样）。或者 X 和 Y 的相关系数为负（这不常见但可能——用户在实验前买了大单后"消费透支"） | 先检查 `np.var(x_control)` 是否 > 0。如果 ρ 为负——意味着 X 和 Y 反向关系，CUPED 仍然有效（方差仍然被缩减——缩减比例是 ρ²，正的） |
| "CUPED 调整后实验组的方差反而变大了" | θ 的符号和实际关系不一致——比如你用错了估计数据。也可能是 X 和 Y 无关（ρ≈0）——调整引入了噪音 | 先算 ρ——如果 |ρ| < 0.2，CUPED 在你的数据上不适用。如果 ρ 显著但不为正——检查 X 和 Y 的时间对齐（实验前 X 必须在实验前采集——不是在实验期间采集的） |

---

### 🔗 与主课联动

今天主课学的是 MDE 深度——MDE 是样本量的"控制旋钮"。CUPED 是另一个"旋钮"——两个旋钮一起拧：MDE 从 2pp 谈到 1.5pp → n 减少 44%；CUPED ρ=0.7 → 等价 n 翻倍。组合使用——你可以在有限的流量下做更多的实验。面试时把这两个旋钮放在一起回答——面试官知道你不是"背了公式"而是"理解实验效率的系统性管理"。

---

### 📎 参考速查

- W6D5——样本量计算（CUPED 如何影响所需样本量）
- W5D1——浮点精度（协方差计算中的数值稳定性）

---

## D2（周二 9/9）：MDE 敏感性分析——三个参数对样本量的影响

> 📓 今日主课：CUPED 方差缩减——Y_adj = Y - θ(X - E[X])

---

### 🔴 认知冲突

产品经理问你三个问题："①如果我们把显著性水平从 0.05 改成 0.01——样本量要多多少？②如果我们要 95% 功效而不是 80% 呢？③如果基线转化率从 10% 变成 5% 呢？"

你答不上来——因为你只算过一个固定的样本量（W6D5 的 `required_sample_size(0.10, 0.02, 0.05, 0.8)`）。你从来没有"玩过参数"——没有看过当 alpha/power/baseline 变化时，n 怎么变化。

**问题**：你不需要记住所有的组合——但你需要**理解每个参数对 n 的影响方向和幅度**，以及**哪个参数对 n 的影响最大**。面试官不在乎你背了多少表——他在乎你在和 PM 协商实验设计时能不能快速判断"这个要求是不是可行的"。

---

### 📖 核心原理

**四个参数对样本量的影响——方向和幅度：**

| 参数 | 变化 | n 变化方向 | 幅度 | 面试一句解释 |
|------|------|----------|------|-----------|
| **MDE** | 减半（2pp→1pp） | ↑ | **×4** | "MDE 在分母上是平方——减半意味着 1/4 的分母，n 翻 4 倍。MDE 对 n 的影响远超所有其他参数——所以和 PM 对齐 MDE 是最重要的实验前协商" |
| **alpha** | 0.05→0.01 | ↑ | +40% | "更严格的显著性 → 需要更大的 Zα（1.96→2.576）→ n 约增加 40%" |
| **power** | 80%→95% | ↑ | +60% | "更高的功效 → 需要更大的 Zβ（0.842→1.645）→ n 约增加 60%" |
| **baseline** | 10%→5% | ↓ | -30% | "p(1-p) 在 p=0.5 时最大。基线从 10% 降到 5%——方差从 0.09 降到 0.0475——n 减少约 30%。注意：不能为了省样本量去'选一个低的 baseline'——baseline 是客观数据，不是你可以选的参数" |

**面试时的完整回答（60 秒）——从"哪个参数影响最大"开始：**

> "四个参数对样本量有不同的影响幅度。MDE 影响最大——因为它在分母上且是平方项。MDE 减半 → n 翻 4 倍。alpha 和 power 的影响是线性的（通过 Z 值），各约 40-60%。baseline 通过方差项 p(1-p) 影响——越接近 50% 需要的 n 越多。这告诉我们——和 PM 谈判 MDE 是实验前最重要的环节。把 MDE 从 1pp 谈到 2pp，比把 alpha 从 0.01 放宽到 0.05 省更多的样本量。如果 PM 坚持小 MDE——你可以算'实验需要多少天'作为回应——让 PM 自己判断这个 MDE 是否现实。"

**代码实现——MDE 敏感性热力图：**

```python
import numpy as np
from scipy import stats
import pandas as pd
import matplotlib.pyplot as plt

def mde_sensitivity_grid(baselines, powers, alphas, mde, output_path=None):
    """三个参数维度的 MDE 敏感性分析——输出热力图数据。

    输入三个参数的各取值 → 输出每种组合下的 n_per_group。
    用于和 PM 讨论"可行性"——如果某种组合需要的样本量不可实现，
    回到参数表调整。
    """
    results = []
    for p0 in baselines:
        for power in powers:
            for alpha in alphas:
                n = _required_sample_size(p0, mde, alpha, power)
                results.append({
                    'baseline': p0, 'power': power, 'alpha': alpha,
                    'n_per_group': n, 'days_needed': n / 500  # 如果每天500新用户
                })
    return pd.DataFrame(results)
```

---

### 🏢 鲜果多案例

鲜果多首页改版实验——PM 希望 MDE=1pp（从 10% 提升到 11%），alpha=0.05，power=80%。你算出来：n≈14000/组，鲜果多日均新用户 500 人——需要 28 天。PM 说"太久了——我们每次发版 2 周一次"。

你跑了一个敏感性分析——把 MDE 从 1pp 改到 2pp：
- MDE=2pp → n≈3500/组 → 7 天 → **可行**
- MDE=1.5pp → n≈6200/组 → 12 天 → 勉强可行（两周一版，留 2 天余量）

你向 PM 展示了敏感性矩阵——"MDE 从 1pp 谈到 1.5pp，实验时间从 28 天降到 12 天。1.5pp 的提升值得上线吗？"PM 想了想："如果提升不到 1.5pp——开发成本也覆盖不了——不值得上线。就用 1.5pp。"

**这就是 MDE 敏感性分析的价值——不是算出一个数给 PM 看，而是让 PM 参与决策。**

---

### ✍️ 动手练习

1. 实现 `mde_sensitivity_grid()` 函数——至少遍历三个维度：baseline=[0.05, 0.10, 0.20], power=[0.7, 0.8, 0.9, 0.95], alpha=[0.01, 0.05, 0.10]。
2. 生成一张敏感性折线图——X 轴=power, Y 轴=n_per_group, 不同颜色的线=不同 baseline。保存为 `output/mde_sensitivity.png`。
3. 在图的标题上写结论："MDE=1pp 固定时，baseline 从 10% 降到 5% → n 减少 ~30%（方差效应）。power 从 80% 提升到 95% → n 增加 ~60%。alpha 从 0.05 到 0.01 → n 增加 ~40%。"
4. 在代码注释里写"面试标准回答"——60 秒版。这是你面试前直接看的。
5. `git add . && git commit -m "add MDE sensitivity analysis with 3-parameter grid + interview talking point" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- MDE=1pp, baseline=10%, alpha=0.05, power=0.8 → n≈14000/组
- 同参数仅 alpha 改为 0.01 → n≈20000/组（+43%）
- 同参数仅 power 改为 0.95 → n≈22500/组（+61%）
- 同参数仅 baseline 改为 5% → n≈10000/组（-29%）

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "baseline 从 10%→5%，n 反而减小了？难以置信" | p(1-p) 在 p=0.5 最大——不是越极端需要的 n 越多。p=0.10→p(1-p)=0.09, p=0.05→p(1-p)=0.0475——确实 5% 的方差更小 | 这是对的——不是 bug。面试时主动说这一点——加分项："注意基线率越低方差越小——但这不能人为选择——baseline 是客观数据" |
| "power 从 80% 到 95%，n 增加超 60%？" | Zβ 从 0.842（80%）→1.645（95%）——Zα+Zβ 从 2.80→3.61→平方后约增加 66% | 检查 Z 值表——0.842 和 1.645 对应 80% 和 95% 功效 |
| "算出来的 n 和在线计算器不一样" | 不同计算器用了不同的公式变体（连续性校正/单双尾/近似公式） | 差异 < 5% 忽略。> 10% 则检查 Z 值和公式版本 |

---

### 🔗 与主课联动

今天主课学 CUPED 的方差缩减——ρ²。MDE 敏感性分析告诉你：如果 ρ=0.7，有效样本量 ≈ n/(1-ρ²) ≈ 2n——等价于把 MDE 从 1pp 改善到 0.7pp。但 CUPED 不花钱——而改 MDE 需要和 PM 谈判。理解两个"旋钮"的相对成本——面试时这是高级回答。

---

## D3（周三 9/10）：SUTVA 违反模拟——网络效应/溢出效应/一般均衡

> 📓 今日主课：网络效应与复杂实验设计——SUTVA 违反/Cluster/Switchback/Holdout

---

### 🔴 认知冲突

你做了鲜果多首页改版 AB 实验——对照组和实验组各 50% 流量。p=0.03，ATT=+4%——显著、有效应量、护栏指标没恶化——一切看起来完美。

但你的同事指出了一个隐患："实验组用户看了新首页，买了很多东西，然后把链接分享到微信群里——对照组用户看到链接，也去买了同样的东西。你的实验假设两组独立——但在这个场景下，实验组的处理通过社交网络'传染'到了对照组。"

实验组的处理通过社交网络影响到了对照组——对照组不再是"纯净的对照"。实验组的 ATT 可能被**低估**了（因为对照组也被实验效果波及——两组差异被人为缩小）。

**问题**：SUTVA 说"每个人的处理状态不影响其他人的结果"。如果这个假设被违反——你的实验结论偏了多少？方向是什么？怎么在你的代码中检测？

---

### 📖 核心原理

**SUTVA 违反的三种典型场景——每一种导致不同的偏误方向：**

**场景一：网络效应（低估 ATT）**

用户在社交网络中互相影响。实验组用户被新推荐算法引导买了更多东西 → 在微信群里分享好物链接 → 对照组用户点了链接也买了。对照组的购买行为被实验组"染"到了——但你的 t-test 把他们归为"对照组的自然行为"。ATT 被**低估**。

用代码模拟这个效应：

```python
import numpy as np
rng = np.random.default_rng(42)

n_per_group = 1000
true_effect = 5.0          # 真实实验效应: +5 元
spillover_pct = 0.3       # 30% 的对照组用户被实验组"传染"
spillover_effect = 3.0    # 被传染的用户额外 +3 元（但小于真实效应的 5 元）

# 无传染时——真实的 ATT
control_true = rng.normal(100, 20, n_per_group)
treatment_true = rng.normal(100 + true_effect, 20, n_per_group)
att_true = treatment_true.mean() - control_true.mean()  # ≈ 5.0

# 有传染时——观测到的 ATT（被低估）
n_spillover = int(n_per_group * spillover_pct)
control_observed = control_true.copy()
control_observed[:n_spillover] += spillover_effect  # 被传染的用户被拉高了
treatment_observed = treatment_true  # 实验组不变
att_observed = treatment_observed.mean() - control_observed.mean()  # ≈ 3.5-4.0

print(f"真实 ATT: {att_true:.2f}")
print(f"观测 ATT: {att_observed:.2f} (被低估了 {att_true - att_observed:.2f})")
# 输出: 真实 ATT ≈ 5.0, 观测 ATT ≈ 3.5-4.0——被低估约 20-30%
```

**场景二：溢出效应（高估 ATT）**

实验组发优惠券 → 用户为了用券跨区域消费 → 本应属于对照组的订单被实验组"抢"了。对照组的订单减少（被实验组抢走了），实验组的订单增加了（抢了对照组的）。ATT 被**高估**——实验看起来比实际更有效。

**场景三：一般均衡效应（结论不能外推）**

在 1% 用户上测试"全场降价 10%"——销量提升 25%。全量上线后——所有商品都降价 10% → 竞争对手跟进降价 → 你的相对价格优势消失 → 全量效果远低于小实验的 25%。这是因为在小实验中"其他商家没降价"的条件——在全量上线后被打破了。

**三种场景的偏误方向总结——面试口答必备：**

| 场景 | 偏误方向 | 机制 | 解法 |
|------|---------|------|------|
| 网络效应 | **低估 ATT** | 对照组被"传染"→两组差异缩小 | Cluster 实验（按社交群组分流） |
| 溢出效应 | **高估 ATT** | 实验组"抢"对照组的量→两组差异放大 | Geo 实验（按地理区域分流） |
| 一般均衡 | 不确定 | 小实验的环境条件在大规模推广后不成立 | Holdout + 逐步放量观察 |

**在你的实验中怎么检测 SUTVA 违规？**

```python
def assess_sutva_risk(
    has_social_feature: bool,      # 实验中有社交功能吗？
    has_geographic_overlap: bool,  # 两组用户有地理重叠吗？
    rollout_pct: float,            # 实验覆盖了多少%的用户？
    cluster_possible: bool         # 能否改用 Cluster 分流？
) -> dict:
    """评估 SUTVA 违反风险——生成风险报告。"""
    risk = 'low'
    reasons = []
    recommendation = '标准 AB Test'

    if has_social_feature:
        risk = 'medium'
        reasons.append('实验含社交功能（分享/邀请）→ 网络效应风险 → ATT 可能被低估')
        if cluster_possible:
            recommendation = 'Cluster AB（按社交群组分流）'
        else:
            recommendation = '标准 AB + 报告标注"ATT 为下限估计——实际效应可能更大"'

    if has_geographic_overlap:
        if risk == 'medium':
            risk = 'high'
        else:
            risk = 'medium'
        reasons.append('两组用户地理重叠 → 溢出效应风险 → ATT 可能被高估')
        recommendation = 'Geo AB（按城市/区域分流）'

    if rollout_pct > 0.05:
        reasons.append(f'流量占比 {rollout_pct:.0%}——大比例覆盖时注意一般均衡风险')

    return {
        'risk_level': risk,
        'reasons': reasons,
        'recommendation': recommendation,
        'att_bias_direction': 'underestimate' if has_social_feature else ('overestimate' if has_geographic_overlap else 'unknown')
    }
```

---

### 🏢 鲜果多案例

鲜果多首页改版实验中——"分享好物得优惠券"是一个核心功能。这正好是 SUTVA 的高风险场景——用户分享到微信群，对照组用户也可能被吸引去购买。

你在实验报告里标注了：
> "⚠️ SUTVA 风险评估：实验含社交分享功能——存在网络效应风险。ATT = +4.2% 应被解读为**下限估计**——实际效应可能更大（因为对照组也可能被间接影响，两组差异被人为缩小）。建议下一步做 Cluster AB——按微信群关系链分流。"

这就是工程化对分析结论的影响——你不是在实验报告里写"假设 SUTVA 成立"然后当它成立。你写"SUTVA 可能不成立——如果成立，ATT 估计是保守的（下限）"。

---

### ✍️ 动手练习

1. 实现 `assess_sutva_risk()` 函数——含三种场景的风险评估逻辑。
2. 用 D1 的模拟代码构造一个网络效应场景——亲眼看到 ATT 被低估。
3. 在你的 AB 实验全流程函数（W6D6 的 `run_full_ab_test()`）中——在"决策"之前加入 SUTVA 风险评估步骤。
4. 在代码注释里画一张"三种 SUTVA 违反 + 偏误方向 + 解法"的 ASCII 速查表。
5. `git add . && git commit -m "add SUTVA risk assessment and network effect simulation" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- 网络效应：对照组 30% 用户被传染 +3 元 → 真实 ATT=5.0 → 观测 ATT≈3.5-4.0（低估 20-30%）
- 溢出效应：实验组抢对照组订单 → ATT 被高估
- 一般均衡：小实验 1% → 全量上线后环境变化 → 结论不可外推

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "觉得 SUTVA 太理论化——实际工作中碰不到" | 任何含社交/分享/邀请/评论的实验都有网络效应风险；任何含地域的实验都有溢出效应风险 | 这两个类别覆盖了 80% 的互联网 AB 实验 |
| "SUTVA 违规怎么办——有没有补救方法？" | 改实验设计（Cluster/Geo/Switchback）——不是在统计分析阶段纠偏 | 实验设计阶段评估 SUTVA 风险——不是实验后。设计阶段有社交功能 → 直接做 Cluster AB |
| "分不清低估和高估" | 网络效应→实验组影响对照组→对照组被拉高→差异缩小→低估。溢出→实验组抢对照组→差异放大→高估 | 用"谁被影响了"判断方向：对照组被拉高=低估，对照组被压低=高估 |

---

## D4（周四 9/11）：实验方法选择决策树——什么时候用什么

> 📓 今日主课：实验平台与架构——六大模块/分流服务/分层分流

---

### 🔴 认知冲突

你跟 PM 讲 AB 实验——PM 说"我们不能随机化——这个推荐功能是全量上线然后看效果"。你说"那不能用 AB Test"。PM 问"那怎么办？"

你需要一个决策框架——从"能不能做 AB Test"开始，沿着决策树往下走。每一步对应一种方法——每种方法有它自己的假设和适用条件。

**问题**：面试官问你"不能用 AB Test 时你用什么？"——你不能只回答"DID"。你需要能画出一整棵决策树——从 Gold Standard 到最后的"这是相关性分析，不是因果推断"。

---

### 📖 核心原理

**实验方法选择决策树——从根到每种叶子：**

```python
def choose_experiment_method(
    can_randomize: bool,        # 能随机化吗？
    has_panel_data: bool,       # 有面板数据（处理前后都有观测）吗？
    has_control_group: bool,    # 有对照组吗？
    has_instrument: bool,       # 有工具变量吗？
    has_clear_cutoff: bool,     # 有清晰的断点/门槛吗？
    has_social_feature: bool,   # 有社交功能（SUTVA 风险）吗？
) -> dict:
    """实验/因果推断方法选择决策树。

    面试时闭卷画出这棵树——面试官知道你不是在背答案，
    而是在展示你的判断框架。
    """
    if can_randomize:
        if has_social_feature:
            return {
                'method': 'Cluster AB Test',
                'why': '有社交功能→网络效应风险→按社交群组分流以保证 SUTVA',
                'assumptions': 'SUTVA（在群组级别成立）+ 群组间无溢出',
                'limitations': '统计功效低于标准 AB（群组数量 < 用户数量）'
            }
        else:
            return {
                'method': '标准 AB Test (Gold Standard)',
                'why': '随机化保证已知和未知混淆变量都被平衡',
                'assumptions': 'SUTVA + 无新奇效应 + 无预期效应',
                'limitations': '可操作范围有限（某些变量无法随机化——如性别/年龄）'
            }

    # 不可随机化——沿决策树往下
    if has_panel_data and has_control_group:
        return {
            'method': 'DID（双重差分）',
            'why': '有面板+有对照→可以分离'处理效应'和'时间趋势'',
            'assumptions': '平行趋势假设——处理前两组趋势平行',
            'limitations': '时变混淆变量仍然有偏；只能识别 ATT（处理组效应）',
            'validation': '处理前趋势图 + 事件研究法 + 安慰剂检验'
        }

    if has_clear_cutoff:
        return {
            'method': 'RDD（断点回归）',
            'why': '断点附近近似随机化——刚好过线和刚好不过线的个体可比',
            'assumptions': '连续性假设 + 不能精确操纵 running variable',
            'limitations': '只能估计 LATE（断点附近的局部效应）——不能外推',
            'validation': 'McCrary 密度检验 + 前定变量连续性检验'
        }

    if has_control_group and not has_panel_data:
        return {
            'method': 'PSM（倾向得分匹配）',
            'why': '有对照但无面板→在观测协变量上匹配最相近的个体作为反事实',
            'assumptions': 'CIA（条件独立假设）——所有混淆变量都被观测到了',
            'limitations': '未观测混淆变量仍可能导致偏误；匹配质量取决于 Common Support',
            'validation': '匹配后 SMD < 0.1 + Rosenbaum 敏感性分析'
        }

    if has_instrument:
        return {
            'method': 'IV（工具变量）',
            'why': '有工具变量→利用外生变异（与处理相关、与结果无关）分离因果效应',
            'assumptions': '相关性（IV 和 treatment 相关）+ 外生性（IV 只通过 treatment 影响 outcome）',
            'limitations': '弱工具变量（第一阶段 F<10）→ IV 估计比 OLS 更偏',
            'validation': '第一阶段 F > 10 + 过度识别检验（如果有多个 IV）'
        }

    return {
        'method': '相关性分析（非因果推断）',
        'why': '不满足任何因果推断方法的条件→只能报告相关性',
        'limitations': '不能用于因果决策——只能用于生成假设'
    }
```

---

### ✍️ 动手练习

1. 在 `src/analysis/causal.py` 顶部用 ASCII art 画出完整的决策树。
2. 用 5 个不同场景的参数组合测试 `choose_experiment_method()`——确认每个分支返回了正确的方法。
3. 在决策树的 ASCII art 下方标注每种方法的"面试必问假设"。
4. `git add . && git commit -m "add experiment method selection decision tree" && git push`

---

## D5（周五 9/12）：5 个防御性 assert——把"14 坑"变成"代码不让你通过"

> 📓 今日主课：AB 实验避坑大全——十大陷阱/三连击/10 问审查清单

---

### 🔴 认知冲突

你读了 AB 实验 14 坑的文章。你记住了每个坑。但"记住"和"防住"之间隔着一整条鸿沟。

你上线了一个新实验——p=0.04，显著，你兴奋地报告"实验成功"。同事问了一句："你做了 Bonferroni 校正吗？"你沉默了——你测了 6 个指标，你用的是 p=0.05——没有校正。**你是 6 个指标里挑了 p 最小的那一个报告的——你下意识地做了 p-hacking，你自己都没意识到。**

**问题**：怎么让"知道这些坑"变成"这些坑不会发生"？答案——把坑写成代码检查。代码不会忘、不会被 deadline 压力影响、不会"觉得这次没事算了"。

---

### 📖 核心原理

**在 `run_full_ab_test()` 中加入 5 道"防御性 assert"——任何一道不通过，函数拒绝给出结论：**

```python
def run_full_ab_test_with_guardrails(
    control_data, treatment_data, metrics, guardrail_data=None,
    alpha=0.05, expected_ratio=0.5,
    novelty_excluded=True, bonferroni_applied=False, peeked=False
):
    """完整 AB 实验分析——5 道防御性 assert 保护实验结论不被误用。

    5 道检查——每道对应一个经典坑：
    """

    # 🛡️ 坑1: Peeking（偷看）
    # "在样本量不够时多次看 p 值，看到显著就停"
    assert not peeked, (
        "Peeking 检测失败：实验中多次查看过 p 值。\n"
        "Peeking 会膨胀第一类错误——看 5 次后实际 α 从 5% 膨胀到 ~14%。\n"
        "解法：①事前用 required_sample_size() 确定最小样本量 ②用序贯检验代替固定样本检验"
    )

    # 🛡️ 坑2: 多重比较（Multiple Comparisons）
    # "测了 6 个指标，挑 p 最小的说'这个指标显著'"
    n_metrics = len(metrics)
    if n_metrics > 1 and not bonferroni_applied:
        adjusted_alpha = alpha / n_metrics
        logger.warning(
            "多重比较风险: %d 个指标未做校正。\n"
            "建议 α 从 %.4f 校正为 %.4f (Bonferroni: α/n)。\n"
            "如果不校正——大约 %.0f%% 的概率至少有一个指标'显著'（即使在 H0 为真时）",
            n_metrics, alpha, adjusted_alpha, (1 - (1-alpha)**n_metrics)*100
        )
    # 这不是硬 assert——是强制性 WARNING。因为在探索性分析中你确实需要看多个指标。
    # 但在确认性实验中——必须校正。

    # 🛡️ 坑3: SRM（Sample Ratio Mismatch）
    srm = check_srm(len(control_data), len(treatment_data), expected_ratio)
    assert not srm['srm_detected'], (
        f"SRM 失败: p={srm['p_value']:.4f}\n"
        "分流系统有问题——两组不是随机分配的。\n"
        "先排查分流 bug——不要继续分析实验指标。"
    )

    # 🛡️ 坑4: 新奇效应（Novelty Effect）
    # "用户对新功能感到好奇——前 3 天效果很好，第 4 天回到基线"
    assert novelty_excluded, (
        "未排除新奇效应窗口。\n"
        "建议排除前 3-7 天数据——用户对新功能的好奇可能导致短期效果虚高。\n"
        "Day 1-3 和 Day 4+ 分段的效应量如果不一致 → 新奇效应存在 → 只分析 Day 4+ 的稳定期数据。"
    )

    # 🛡️ 坑5: 护栏恶化（Guardrail Deterioration）
    # "核心指标显著提升——但护栏指标也恶化了——被忽略"
    if guardrail_data:
        for name, (ctrl, trt) in guardrail_data.items():
            _, p_gr = stats.ttest_ind(trt, ctrl, equal_var=False)
            mean_diff = np.mean(trt) - np.mean(ctrl)
            if p_gr < alpha and mean_diff < 0:  # 护栏显著恶化
                raise AssertionError(
                    f"护栏指标恶化: {name}\n"
                    f"差异: {mean_diff:.4f} (p={p_gr:.4f})\n"
                    f"护栏一票否决——无论核心指标多好，实验不可上线。"
                )

    # ✅ 所有检查通过——继续实验分析
    logger.info("✅ 5 道防御检查全部通过——开始实验分析")
    return run_z_test(control_data, treatment_data, alpha=alpha)
```

**面试视角——为什么数据分析师需要防御性 assert？**

> "assert 不是给 Python 看的——是给'三个月后的我'和'接手我代码的同事'看的。14 坑我读过文章——但如果我写完代码不把坑写成检查——我三个月后一定会忘。防御性 assert 强制每次实验分析执行同样的检查——即使我在 deadline 压力下、即使我忘了看 Peeking、即使没人提醒我做 Bonferroni 校正。这是工程化对分析严谨性的保障。"

---

### ✍️ 动手练习

1. 在你的 `run_full_ab_test()` 中嵌入 5 道防御性 assert。
2. 构造一个测试文件 `tests/test_ab_guardrails.py`——逐一验证每种 assert 在正确的条件触发：
   - 验证 Peeking assert：设 `peeked=True` → assert 触发
   - 验证 SRM assert：构造两组人数差异极大的数据 → assert 触发
   - 验证护栏恶化 assert：构造实验组护栏明显差于对照组的数据 → assert 触发
3. `pytest tests/test_ab_guardrails.py -v`——5 个 test 全绿。
4. `git add . && git commit -m "add 5 defensive asserts to AB test pipeline + test suite" && git push`

---

### ✅ 自检

- 5 道 assert 各有独立的测试用例
- 每个 assert 的错误消息含"为什么这是坑 + 怎么修"
- 面试时能说出至少 3 个防御性 assert 的具体场景

---

## D6（周六 9/13）：周项目——AB 全流程 + 防御代码整合 + SUTVA 评估

把 D1-D5 全部整合到 `run_full_ab_test_with_guardrails()`：

**流程**：CUPED 调整（D1）→ MDE 验证（D2——样本量够了吗？不够则标记 `increase_sample`）→ SUTVA 风险评估（D3——如果社交功能存在则标注"ATT 是下限估计"）→ SRM 检查 → 检验 → 多重比较警告 → 护栏 → 新奇效应 → **5 道防御 assert 全部通过** → 决策。

跑完整实验——从数据到带风险评估的决策报告。

---

## D7（周日 9/14）：W7 审计——闭卷 CUPED + clone 测试

### 📝 核心概念闭卷

- **闭卷写出 CUPED 公式** + 解释"为什么 θ 必须在对照组算"（用"实验组的 Y 含有实验效应"解释）
- **闭卷画出实验方法选择决策树**——从"能随机化吗"到 IV 的完整树
- **闭卷说出 MDE/alpha/power/baseline 对 n 的影响方向和幅度**
- **闭卷说出 ≥ 3 种 SUTVA 违反场景 + 偏误方向 + 解法**
- **闭卷说出 ≥ 5 个 AB 实验坑 + 对应的防御性 assert**
- **clone 测试**：`git clone → pip install → pytest tests/ -v → python main.py`

---

> 📌 W7 完成。你的 AB 实验代码现在不只是"能跑"——它有 CUPED（正确的 θ 估计）、SUTVA 风险评估、实验方法决策树、5 道防御性检查。面试官问你 AB 实验的任何一个方面——你都能从"原理"讲到"代码实现"再到"防御性设计"。
