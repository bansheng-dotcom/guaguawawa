# W6：AB 实验基础工程（9/1 — 9/7）

> 🎯 **本周目标**：AB 实验不只是"算 p 值"。本周你要把实验代码工程化——统一返回格式、全流程日志、路径管理升级、SRM 前置检查、样本量计算、pipe 串联实验全流程。学完这周，你的实验代码能直接贴进实验报告。
>
> 📎 **本周主课**：AB 实验（上）——随机化/SUTVA/三要素、p 值+两类错误、样本量与 MDE、实验设计完整流程、AA 实验与 Peeking、AB 综合实战
>
> 🏢 **本周鲜果多剧情**：运营总监想做一次实验——在 App 首页改版推荐算法，看能不能提升客单价。你需要从实验设计到分析报告，全流程用代码实现。这不是"跑一个 t-test 看 p 值"——你需要验证分流是否正确、样本量是否足够、护栏指标是否恶化、结论是否可靠。

---

## D1（周一 9/1）：实验函数的标准化——从"散落的数字"到"结构化结论"

> 📓 今日主课：AB 实验是什么——随机化/SUTVA/三要素

---

### 🔴 认知冲突

你写了一个 z-test 函数，返回 p 值——`return p_value`。然后你又写了一个函数算效应量——`return cohens_d`。然后你又写了一个函数画置信区间——`return (ci_low, ci_up)`。三个函数、三个返回值格式——你在 main.py 里手动拼凑它们。

三个月后你回头看这段实验代码——你找不到"实验结论是什么"。p 值散落在一个函数里，效应量在另一个里，决策（上线/不上线）没有地方体现。

**问题**：你的 AB 实验函数应该返回什么？为什么"统一返回格式"是实验代码工程化的第一要求？

---

### 📖 核心原理

**实验中每个函数的输出应该是同一个"语言"——标准化的 Dict。**

这不是形式主义。实验分析有一个特点：**所有的数字最终要汇总成一个决策。** p 值、效应量、置信区间、样本量——这些不是独立的输出，它们是同一个结论的不同侧面。如果每个函数返回不同格式——你在拼凑结论时就得手动翻译。

**标准化返回格式——定义一个"实验结论"的数据结构**

```python
from typing import Dict, Union, Optional
import numpy as np

def run_z_test(
    control: np.ndarray,
    treatment: np.ndarray,
    alpha: float = 0.05,
    alternative: str = 'two-sided'
) -> Dict[str, Union[float, bool, str]]:
    """双样本 z 检验（大样本比例类指标）。

    前提假设（使用者必须确认）：
    1. 两组样本独立（不是配对数据）
    2. 样本量足够大（每组 ≥ 100）——CLT 保证均值的抽样分布近似正态
    3. 适用于比例类指标（转化率、点击率等）。连续类指标优先用 Welch's t-test。

    Args:
        control: 对照组观测值（0/1 二元或连续值）
        treatment: 实验组观测值
        alpha: 显著性水平
        alternative: 'two-sided' / 'less' / 'greater'

    Returns:
        Dict 含以下标准字段（所有实验函数统一此格式）:
            p_value: 检验 p 值
            effect_size: Cohen's d 效应量
            ci_lower / ci_upper: 置信区间的上下界
            mean_control / mean_treatment: 两组均值
            n_control / n_treatment: 两组样本量
            relative_lift: 相对提升（(treatment - control) / control）
            significant: p < alpha 则为 True
            recommendation: 'ship' / 'hold' / 'increase_sample'
            method: 使用的检验方法名称
    """
    from scipy import stats

    n_c, n_t = len(control), len(treatment)
    m_c, m_t = np.mean(control), np.mean(treatment)
    s_c, s_t = np.std(control, ddof=1), np.std(treatment, ddof=1)

    # z 统计量
    se = np.sqrt(s_c**2 / n_c + s_t**2 / n_t)
    z = (m_t - m_c) / se if se > 0 else 0.0

    # p 值
    if alternative == 'two-sided':
        p = 2 * (1 - stats.norm.cdf(abs(z)))
    elif alternative == 'less':
        p = stats.norm.cdf(z)
    else:  # greater
        p = 1 - stats.norm.cdf(z)

    # Cohen's d
    pooled_std = np.sqrt((s_c**2 + s_t**2) / 2)
    d = (m_t - m_c) / pooled_std if pooled_std > 0 else 0.0

    # 95% CI
    ci_margin = 1.96 * se
    ci_low = (m_t - m_c) - ci_margin
    ci_up = (m_t - m_c) + ci_margin

    # 相对提升
    lift = (m_t - m_c) / m_c if m_c > 0 else 0.0

    # 决策建议
    significant = p < alpha
    if not significant:
        recommendation = 'hold'
    elif d < 0.1:
        recommendation = 'hold'  # 统计显著但效应量太小——实际意义不大
    else:
        recommendation = 'ship'

    return {
        'p_value': p,
        'effect_size': d,
        'ci_lower': ci_low,
        'ci_upper': ci_up,
        'mean_control': m_c,
        'mean_treatment': m_t,
        'n_control': n_c,
        'n_treatment': n_t,
        'relative_lift': lift,
        'significant': significant,
        'recommendation': recommendation,
        'method': 'z-test (two-sample, two-sided)' if alternative == 'two-sided' else f'z-test (two-sample, {alternative})'
    }
```

**为什么返回 Dict 而不是 namedtuple 或 dataclass？**

Dict 可以直接用 `json.dumps()` 序列化——方便保存到实验日志。Dict 字段可增可减——不破坏旧代码。对于你现在的阶段，Dict 是最简单也最灵活的方案。

**所有实验函数必须遵循同样的字段名——这是"统一格式"的核心**

不管内部用的是 z-test、t-test、Mann-Whitney U——返回的 Dict 必须包含相同的字段名（`p_value` / `effect_size` / `ci_lower` / `ci_upper` / `significant`）。这样 `main.py` 里调完检验后——不管底层用什么方法，都能用同样的方式访问结论。

---

### 🏢 鲜果多案例

鲜果多做了首页改版实验。你用 `run_z_test(control, treatment)` 得到结论 dict。运营总监问"效果怎么样？"——你不用翻三处代码。你打开 dict：`p=0.032, d=0.28, lift=+4.2%, recommendation='ship'`——一句话说完。

然后你把这个 dict 序列化成 JSON，存到 `output/experiment_result.json`——这成了实验记录的永久档案。三个月后有人质疑"上次那个实验结论怎么来的"——你直接打开这个 JSON，字段一清二楚。

---

### ✍️ 动手练习

1. 在 `src/analyze.py` 中实现 `run_z_test()`（或 t-test 版本——你主课用的哪种就写哪种）。
2. 确保返回的 Dict 包含上述所有标准字段（至少 p_value/effect_size/ci_lower/ci_upper/significant/recommendation）。
3. 用你主课里的 AB 测试数据跑一次，打印返回的 Dict——感受"统一格式"的便利。
4. 在代码注释里写：**"此后所有实验函数统一返回此 Dict 格式。新增实验方法只需保证字段名一致。"**
5. `git add . && git commit -m "add standardized AB test function with unified return format" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- `run_z_test()` 返回的 Dict 至少含 8 个字段。
- `recommendation` 字段不是只基于 p 值——同时考虑了效应量（d < 0.1 即使 p 显著也不推荐上线）。

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "少了一些字段" | 刚起步时容易只返回 p_value 和 significant——因为"只要知道显著不显著就行" | 补全。效应量、CI、样本量——这三项在实验报告中缺一不可。面试官必问 |
| "recommendation 只基于 p 值" | 统计显著 ≠ 业务显著。p < 0.05 但提升只有 0.1%——值得上线吗？ | recommendation 要同时考虑效应量和业务成本 |
| "没有 `method` 字段" | 将来你可能同时用 z-test 和 t-test 做敏感性分析——不标注方法，回头分不清结论来自哪个检验 | 加上 `method` 字段——这是一行代码但关键时刻省半小时排查 |

---

### 🔗 与主课联动

今天主课学 AB 实验三要素——随机化、SUTVA、对照组。你的 `run_z_test()` 的 docstring 里的"前提假设"——"两组样本独立"——就是在声明 SUTVA 假设。如果 SUTVA 被违反（如网络效应），这个检验的基础就不存在了（W7D3 专门讲）。

---

### 📎 参考速查

- [工程化专项计划 第4章](../工程化专项计划.md)——Type Hints 速查（Dict 类型标注）

---

## D2（周二 9/2）：实验全流程日志——z-test 日志能直接贴进实验报告

> 📓 今日主课：假设检验与 AB 实验——p 值+两类错误+三件套

---

### 🔴 认知冲突

你的 `run_z_test()` 返回了漂亮的 dict。但运营总监追问了一句："对照组和实验组各多少人？均值分别是多少？标准差呢？"

你不在代码里——你打开了 Python 交互模式，重新跑一遍，手动提取——因为 dict 虽然全但这些数字没有在日志里自动输出。你每次都要手动打印。

**问题**：实验函数不应该只是"算出数字"——它应该在计算过程中**自述**"我看到了什么、我做了什么、我得出什么结论"。怎么让实验代码的日志能直接贴进实验报告？

---

### 📖 核心原理

**实验函数的三段式日志：检查数据 → 执行检验 → 输出结论。**

每一段的日志信息密度应该足够高——高到可以直接粘贴进邮件或报告。

```python
def run_z_test(control, treatment, alpha=0.05, alternative='two-sided'):
    # === 第一段：检查数据（Describe） ===
    n_c, n_t = len(control), len(treatment)
    m_c, m_t = np.mean(control), np.mean(treatment)
    s_c, s_t = np.std(control, ddof=1), np.std(treatment, ddof=1)

    logger.info("=" * 50)
    logger.info("AB 实验: z-test 分析开始")
    logger.info("对照组: n=%d, mean=%.4f, std=%.4f", n_c, m_c, s_c)
    logger.info("实验组: n=%d, mean=%.4f, std=%.4f", n_t, m_t, s_t)
    logger.info("相对差异: %+.2f%%", (m_t - m_c) / m_c * 100 if m_c > 0 else 0)

    # === 第二段：执行检验（Analyze） ===
    # ... 检验计算 ...

    # === 第三段：输出结论（Conclude） ===
    logger.info("---")
    logger.info("检验结果: p=%.4f, Cohen's d=%.3f, 95%% CI=[%.4f, %.4f]",
                p, d, ci_low, ci_up)
    logger.info("结论: %s (%s)",
                "显著" if p < alpha else "不显著",
                "效应量小" if abs(d) < 0.2 else ("效应量中" if abs(d) < 0.5 else "效应量大"))
    logger.info("建议: %s", recommendation)
    logger.info("=" * 50)

    return {...}
```

输出效果：
```
14:32:05 | INFO     | run_z_test | ==================================================
14:32:05 | INFO     | run_z_test | AB 实验: z-test 分析开始
14:32:05 | INFO     | run_z_test | 对照组: n=5000, mean=0.1230, std=0.3281
14:32:05 | INFO     | run_z_test | 实验组: n=5023, mean=0.1282, std=0.3340
14:32:05 | INFO     | run_z_test | 相对差异: +4.23%
14:32:05 | INFO     | run_z_test | ---
14:32:05 | INFO     | run_z_test | 检验结果: p=0.0321, Cohen's d=0.283, 95% CI=[0.0035, 0.0105]
14:32:05 | INFO     | run_z_test | 结论: 显著 (效应量中)
14:32:05 | INFO     | run_z_test | 建议: ship
14:32:05 | INFO     | run_z_test | ==================================================
```

**这一段日志的价值**

1. **可复制**：直接选中终端 8 行，粘贴到实验报告的"分析结果"章节。
2. **可追溯**：3 个月后你打开 `output/run.log`，搜索 `AB 实验`——能看到每次实验的完整记录。
3. **可审查**：别人从日志就能判断你的分析是否正确——不需要读懂你的代码。

---

### 🏢 鲜果多案例

鲜果多首页改版实验做完后，运营总监在 Slack 上问你"实验组比对照组好多少？"。你不用重新跑代码——打开 `output/run.log`，搜索 `AB 实验`，复制 8 行日志——粘贴到 Slack——30 秒完成回复。

---

### ✍️ 动手练习

1. 在 `run_z_test()` 中加入三段式日志——Describe → Analyze → Conclude。
2. 确认每段日志的信息密度：Describe 含 n/mean/std/相对差异；Analyze 含 p/d/CI；Conclude 含显著判断+效应量判断+建议。
3. 跑一次实验，终端输出能直接贴进实验报告吗？——不能就继续加信息直到能。
4. `git add . && git commit -m "add three-stage logging to AB test function" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- 终端输出含对照组和实验组的完整描述统计 + 检验结果 + 结论建议。
- 日志中的数字精度合适（p 值 4 位小数、效应量 3 位、均值 2-4 位、百分比 2 位）。

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "日志太多了——终端刷屏" | 确实。INFO 级别的日志在生产中可能过多 | 实验函数日志用 INFO（需要永久记录）。如果你觉得每次开发时太吵——临时把 level 设成 WARNING，跑实验时切回 INFO |
| "信息密度不够" | `日志：对照组均值 0.1230`——缺少比较维度 | 加一行"相对差异: +4.23%"——让读者一眼看到核心发现 |
| "和 W2D3 的 logging 讲的有重复" | 这确实是对 W2D3 的深化——从"如何用 logging"到"实验场景下 logging 怎么设计" | — |

---

### 🔗 与主课联动

今天主课学两类错误和统计功效。你的三段式日志里——Conclude 段不只说"显著/不显著"——还说了效应量大小。因为"统计显著+效应量极小"往往是样本量过大导致的——属于第一类错误（假阳性）的工程表现。

---

### 📎 参考速查

- [工程化专项计划 第5章](../工程化专项计划.md)——logging 五级+配置模板

---

## D3（周三 9/3）：pathlib 全量迁移——所有路径告别字符串拼接

> 📓 今日主课：样本量与 MDE——n ∝ 1/Δ² / 正反向 MDE

---

### 🔴 认知冲突

W1 你学了相对路径。W4 你做了 clone 测试。但你的代码里仍然残留着 `'data/' + filename`、`'output/' + report_name + '.csv'`、`os.path.join('data', 'subdir', 'file.csv')`。

这些字符串拼接在 Windows 上勉强能跑（`\` vs `/` 的问题被 Python 掩盖了）。但在做实验时问题暴露了——你需要同时读写多个文件：原始数据、清洗后数据、实验配置、分析结果、图表。路径拼接散落在代码各处——你想把输出目录从 `output/` 改成 `output/experiments/2026-09/`——改了 12 处。

**问题**：pathlib 到底比字符串拼接好在哪？为什么 "`DATA_DIR / 'orders.csv'`" 比 "`'data/orders.csv'`" 更好？

---

### 📖 核心原理

**pathlib 的三个核心优势——不只是"用 / 代替 +"**

**1. `/` 运算符——路径拼接的语义比字符串拼接更清晰**

```python
# 字符串拼接：你以为在拼路径，实际在拼字符串
path = 'data' + '/' + 'orders.csv'         # 如果 data 已经以 / 结尾——双斜杠
path = os.path.join('data', 'orders.csv')  # 更好但冗长，且还是字符串

# pathlib：/ 就是"在这个目录下"
from pathlib import Path
DATA_DIR = Path('data')
path = DATA_DIR / 'orders.csv'             # Path('data/orders.csv')
path = DATA_DIR / 'subdir' / 'orders.csv'  # Path('data/subdir/orders.csv')
```

**2. 不假设分隔符——Windows 和 Linux 自动适配**

```python
# 在 Windows 上：
Path('data') / 'orders.csv'   # → Path('data\\orders.csv')——自动用反斜杠

# 在 Linux 上：
Path('data') / 'orders.csv'   # → Path('data/orders.csv')——自动用正斜杠

# 字符串拼接做不到——你在 Windows 上写 '/' Python 可以容忍，但不够干净
```

**3. 自带常用操作——不需要 import os/os.path/shutil**

```python
# 检查文件存在
if Path('data/orders.csv').exists():
    ...

# 创建目录（含所有父目录）
Path('output/experiments/2026-09').mkdir(parents=True, exist_ok=True)

# 读取文件内容
text = Path('README.md').read_text(encoding='utf-8')

# 列出所有 CSV
csv_files = list(Path('data').glob('*.csv'))

# 获取文件名/后缀/父目录
path = Path('data/orders.csv')
path.name       # 'orders.csv'
path.stem       # 'orders'（不含后缀）
path.suffix     # '.csv'
path.parent     # Path('data')
```

**项目级别的路径管理——定义一次，到处使用**

```python
# src/paths.py（或 main.py 顶部）
from pathlib import Path

ROOT = Path(__file__).parent.parent       # 项目根目录
DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'output'
CONFIG_DIR = ROOT / 'config'

# 在项目的任何文件中：
from src.paths import DATA_DIR, OUTPUT_DIR
df = pd.read_csv(DATA_DIR / 'orders.csv')
df.to_csv(OUTPUT_DIR / 'results.csv', index=False)
```

这样——当你要改输出目录时，只改 `paths.py` 一行。不需要在整个项目里搜索 `'output/'`。

---

### 🏢 鲜果多案例

鲜果多项目现在有三个数据来源和两种输出格式。你的路径散落在 4 个文件里——`io.py` 里写了 `'data/orders.csv'`，`main.py` 里写了 `'output/report.csv'`，`visualize.py` 里写了 `'output/charts/revenue.png'`。

你想加一个实验子目录 `output/experiments/`——你改了 4 个文件、8 处路径。改成 pathlib 集中管理后——改 1 个文件、1 行。

---

### ✍️ 动手练习

1. 创建 `src/paths.py`，定义项目级别的路径常量：
   ```python
   from pathlib import Path
   ROOT = Path(__file__).parent.parent
   DATA_DIR = ROOT / 'data'
   OUTPUT_DIR = ROOT / 'output'
   OUTPUT_DIR.mkdir(exist_ok=True)
   ```
2. 搜索项目中所有旧式路径：`grep -rn "data/\|open(\|output/" src/*.py main.py`（不含注释）。
3. 逐个替换成 pathlib 路径。不要留任何 `os.path.join` 或字符串拼接路径。
4. `python main.py` 跑通。
5. `git add . && git commit -m "migrate all paths to pathlib with centralized path constants" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- `grep -rn "data/\|output/" src/*.py main.py` 现在应该没有用字符串硬编码的路径了（除了 pathlib 的 `Path('data')` 定义，那是定义源头）。
- `src/paths.py` 存在，定义了 `DATA_DIR` 和 `OUTPUT_DIR`。

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "换了 pathlib 后 pd.read_csv 报错" | `pd.read_csv(Path('data/orders.csv'))` 应该能工作。如果报错——pandas 版本太旧（1.0之前） | 升级 pandas，或用 `str(path)` 传给 pd.read_csv |
| "所有路径都集中在 paths.py 里很麻烦" | 不是所有路径都要集中——只有被多处引用的目录路径才集中（DATA_DIR/OUTPUT_DIR）。一次性的临时路径可以直接用 pathlib 写 | 判断标准：如果一个路径在两个以上文件中出现，集中到 paths.py |
| "Path 和 str 混用" | `Path('a') / 'b'` 返回 Path。`str(Path('a'))` 返回 str | 统一用 Path——只在传给第三方库（如 pd.read_csv）时它们通常已经支持 Path 对象了 |

---

### 🔗 与主课联动

今天主课学样本量计算——`required_sample_size(baseline_rate, mde, alpha, power) -> int`。这个函数的参数 `baseline_rate` 和 `mde` 是业务参数——应该从配置文件读取而不是硬编码。明天（D4）会讲怎么外提这些参数。

---

### 📎 参考速查

- [工程化专项计划 第9章](../工程化专项计划.md)——pathlib 用法

---

## D4（周四 9/4）：SRM 检验——实验分析的第一道检查

> 📓 今日主课：实验设计完整流程——9 步/8 要素/决策矩阵/护栏一票否决

---

### 🔴 认知冲突

你跑完了 AB 实验——p = 0.03，显著，结论："实验组更好，建议上线。"然后有人问了一句——"分流对吗？"你看了一眼两组样本量——对照组 5000，实验组 3000。预期是各 50%（各 4000）。但实际差了 1000 人——**分流系统出了问题。**

如果分流有问题——你的 p 值不管多漂亮，都没有意义。因为"两组来自同一总体"的根本假设——在分流出错的那一刻就破了。

**问题**：怎么在分析实验指标**之前**先验证分流是否正确？SRM（Sample Ratio Mismatch）检验怎么做？

---

### 📖 核心原理

**SRM 检验——用卡方拟合优度检验验证"实际分流比例是否偏离预期"。**

逻辑很简单：
- H0：实际分流比例 = 预期分流比例（如各 50%）
- 卡方检验：比较"实际人数"和"预期人数"的差异
- p < 0.01 → 分流有问题（SRM detected）——**先修分流系统，不要继续分析指标**

```python
from typing import Dict
from scipy.stats import chisquare
import logging

logger = logging.getLogger(__name__)


def check_srm(
    control_n: int,
    treatment_n: int,
    expected_ratio: float = 0.5,
    threshold: float = 0.01
) -> Dict:
    """SRM 检验——验证分流比例是否符合预期。

    这是实验分析的第一道检查。在分析任何指标之前必须先过此检查。
    SRM 失败 = 分流系统有问题——实验结论不可信。

    为什么阈值用 0.01 而不是 0.05？
    因为 SRM 是一票否决的检查——我们希望只有在非常确定有问题时才否决。
    用更严的阈值减少误报（把正常波动当成系统问题）。

    Args:
        control_n: 对照组实际人数
        treatment_n: 实验组实际人数
        expected_ratio: 预期的对照组比例（如 0.5 = 各 50%）
        threshold: SRM 检测阈值，默认 0.01

    Returns:
        Dict 含:
            srm_detected: True 表示分流可能有问题
            p_value: 卡方检验 p 值
            expected_n: 预期每组人数
            actual_ratio: 实际对照组比例
    """
    total = control_n + treatment_n
    expected_control = total * expected_ratio
    expected_treatment = total * (1 - expected_ratio)

    chi2, p = chisquare(
        f_obs=[control_n, treatment_n],
        f_exp=[expected_control, expected_treatment]
    )

    srm_detected = p < threshold

    if srm_detected:
        logger.error(
            "⚠️ SRM 检测失败！实际比例 %.1f%%/%.1f%% (预期 %.0f%%/%.0f%%), p=%.4f",
            control_n / total * 100, treatment_n / total * 100,
            expected_ratio * 100, (1 - expected_ratio) * 100, p
        )
        logger.error("SRM 失败应先排查分流系统——不要继续分析实验指标！")
    else:
        logger.info("✓ SRM 通过: 实际比例 %.1f%%/%.1f%%, p=%.4f",
                    control_n / total * 100, treatment_n / total * 100, p)

    return {
        'srm_detected': srm_detected,
        'p_value': p,
        'control_n': control_n,
        'treatment_n': treatment_n,
        'expected_ratio': expected_ratio,
        'actual_ratio': control_n / total if total > 0 else 0.0
    }
```

**SRM 为什么是"前置检查"——不是"分析完再看看"？**

因为 SRM 失败意味着分流系统有 bug——可能是：
- 某些用户没被正确分配（落到两个组之间或之外）
- 实验组的代码有 bug 导致部分用户被排除
- 残留效应——上一轮实验的用户还在这一轮里

这些情况下——你的两组数据不是"除了实验变量不同外其他都相同"——随机化失败了。所有后续分析（t-test、效应量、CI）**全都不再有效。**

---

### 🏢 鲜果多案例

鲜果多首页改版实验——预期分流 50:50。实际跑了之后：对照组 4820，实验组 5180。比例接近但有点偏——SRM p = 0.08 > 0.01——**通过。** 这点波动在随机分流中是正常的。

但如果实际是"对照组 3500，实验组 6500"——SRM p < 0.001——**失败。** 排查后发现：实验组的 App 版本有个 bug——导致部分 Android 用户进实验组后 crash，重新打开后被重新分流到了对照组——造成了人数差异。这不仅仅是 SRM 问题——crash 还影响了用户行为——两组用户的体验完全不同了。

---

### ✍️ 动手练习

1. 在 `src/analyze.py` 中实现 `check_srm()` 函数（或复制上面的代码，理解每一行）。
2. 在你的 AB 实验分析流程中——**在 `run_z_test()` 之前**调用 `check_srm()`。如果 `srm_detected` 为 True——`return {'error': 'SRM failed', ...}` 提前终止分析。
3. 用正常数据验证（两组接近 50:50）——确认 SRM 通过。
4. 故意构造一个"分流偏差"的数据（如一组 3000 一组 7000）——确认 SRM 检测到并报错。
5. `git add . && git commit -m "add SRM check as pre-condition for AB test analysis" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- 正常分流（如 5000/5020）：SRM 通过，p > 0.01。
- 异常分流（如 3000/7000）：SRM 失败，logger.error 输出，分析函数提前终止。

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "SRM 阈值为什么是 0.01 不是 0.05" | SRM 是一票否决——如果 SRM 失败，整个实验作废。代价很高——所以需要更严格的证据才否决 | 核心原理中已解释。理解"不同决策场景需要不同阈值" |
| "SRM 通过了但两组人数不完全相等" | 随机分流天然有波动——5000 vs 5020 差 20 是正常的。SRM 检验的就是"这个波动在不在随机波动的正常范围内" | SRM p > 0.01 → 波动在正常范围 → 通过 |
| "忘了在分析前调 SRM" | SRM 是前置检查——放在实验分析 pipeline 的第一步 | 写一个 `run_full_ab_test()` 函数（D6 会做）把 SRM→检验→护栏→决策串起来——确保不会漏 |

---

### 🔗 与主课联动

今天主课学实验设计完整流程——9 步中的"设计检查点"。SRM 就是第一个检查点——在"随机化"之后、"分析"之前。你在代码中把这个检查点实现成了一个独立函数——以后每个实验都能复用。

---

### 📎 参考速查

- W3D1——数据验证金字塔（SRM 是大数据场景下的"跨表一致性"检查）

---

## D5（周五 9/5）：样本量计算——MDE 和 n 的对偶关系

> 📓 今日主课：AA 实验与 Peeking——AA/Peeking/SRM/序贯检验

---

### 🔴 认知冲突

产品经理说"帮我做一个实验，检测 2 个百分点的转化率提升——从 10% 到 12%。"你算了一下样本量——每组需要约 3500 人。PM 说"我们每天只有 200 个用户——那我跑 3 周就够了？"

你点了点头。但 PM 又说"能不能加快一点？——我想把 MDE 设成 1pp（从 10% 到 11%）。"你又算了一次——**MDE 减半，样本量翻了 4 倍——每组需要约 14000 人。**

PM："为什么会这样？"

**问题**：MDE 和所需样本量之间的"平方反比关系"是怎么来的——不只是背公式，而是理解为什么。面试官一定会追问。

---

### 📖 核心原理

**样本量公式为什么长这样——n ∝ 1/MDE²**

样本量公式（比例类指标、双尾 z-test）：

```
n = (Z_α/2 + Z_β)² × (p₁(1-p₁) + p₂(1-p₂)) / (p₂ - p₁)²
```

其中 `(p₂ - p₁)` 就是 MDE（你希望检测的最小效果量）。它在分母上——**平方**。

所以：MDE 减半 → 分母变成原来的 1/4 → n 变成原来的 4 倍。

**白话版**：你要检测更小的差异——就需要更大样本量来克服随机噪音。检测 2pp 的差异——群体中"信号"（2pp）相对"噪音"（随机波动）还算明显。检测 1pp 的差异——信号变小了——你需要更多样本来"放大"信号。

**面试时的标准回答**

> "MDE 和样本量之间是平方反比关系——MDE 减半，样本量约翻 4 倍。这决定了实验的可行性：如果每周只能获得 500 个新用户，而所需样本量是 14000——这意味着实验要跑 28 周。业务上这是不可接受的——我们就需要重新讨论 MDE 是否合理，或考虑用方差缩减技术如 CUPED。"

**实现样本量计算函数**

```python
from typing import Dict
from scipy import stats
import numpy as np


def required_sample_size(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8
) -> Dict:
    """计算 AB 实验所需最小样本量（每组）。

    关键关系: MDE 减半 → 样本量翻约 4 倍（因为 n ∝ 1/MDE²）。

    面试常见追问:
    Q: "为什么样本量不够时不能提前看结果？"
    A: Peeking 会膨胀第一类错误。假设每看一次就检验一次——看 5 次后，
       实际第一类错误率从 5% 膨胀到 ~14%。停止规则必须事前确定。

    Args:
        baseline_rate: 对照组预期转化率（0~1）
        mde: 最小可检测效应（Minimum Detectable Effect），绝对差值
        alpha: 显著性水平，默认 0.05
        power: 统计功效，默认 0.8

    Returns:
        Dict 含:
            n_per_group: 每组最小样本量
            total_n: 总样本量
            mde_relative: MDE 的相对值（相对于 baseline_rate）
            formula_note: 公式说明

    Example:
        基线 10%, 目标检测 2pp 提升 → n ≈ 3500/组
        基线 10%, 目标检测 1pp 提升 → n ≈ 14000/组（MDE 减半, n 翻 4 倍）
    """
    p1 = baseline_rate
    p2 = baseline_rate + mde

    # z 值
    z_alpha = stats.norm.ppf(1 - alpha / 2)  # 双尾
    z_beta = stats.norm.ppf(power)

    # 样本量公式（比例类指标，双尾，等样本量）
    numerator = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))
    denominator = mde ** 2
    n = int(np.ceil(numerator / denominator)) if denominator > 0 else 0

    logger.info("样本量计算: 基线=%.1f%%, MDE=%.2fpp, alpha=%.2f, power=%.0f%% → n=%d/组",
                baseline_rate * 100, mde * 100, alpha, power * 100, n)
    logger.info("MDE减半→n翻约4倍: 若MDE=%.2fpp→n≈%d/组", mde / 2 * 100, n * 4)

    return {
        'n_per_group': n,
        'total_n': n * 2,
        'mde_absolute': mde,
        'mde_relative': mde / baseline_rate if baseline_rate > 0 else 0.0,
        'baseline_rate': baseline_rate,
        'alpha': alpha,
        'power': power,
        'formula_note': 'n = (Zα/2 + Zβ)² × (p1(1-p1) + p2(1-p2)) / MDE²'
    }
```

---

### 🏢 鲜果多案例

鲜果多想做首页改版实验——目标检测转化率从 10% 提升到 12%（MDE = 2pp）。每天新用户约 500 人。你算出每组需要约 3500 人——7 天能跑完。

PM 说"能不能只测 1pp 的提升？"你调了 MDE 参数——n 变成约 14000/组——需要 28 天。PM 沉默了——28 天的实验在业务上跑不起（期间不能改别的，市场也在变化）。

你们决定：先用 2pp MDE 跑 7 天。如果结果不显著——说明提升不到 2pp——但这个提升本身可能也没有业务意义（提升 < 2pp → ROI 不够覆盖开发成本）。

---

### ✍️ 动手练习

1. 实现 `required_sample_size()` 函数（复制上面的代码或自己写）。
2. 用三种 MDE 值跑对比：`baseline=10%, mde=0.02/0.01/0.005`。记录每次的 n——感受平方反比关系。
3. 在代码注释里写一个"面试标准回答"——用你自己的话解释"为什么 MDE 减半样本量翻 4 倍"。
4. `git add . && git commit -m "add sample size calculator with MDE sensitivity notes" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- baseline=10%, mde=2pp → n ≈ 3500/组
- baseline=10%, mde=1pp → n ≈ 14000/组
- baseline=10%, mde=0.5pp → n ≈ 56000/组
- 规律：MDE 每减半 → n × 4

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "算出来的 n 和在线计算器不一样" | 在线计算器可能用了不同的公式变体（如是否用连续性校正、单双尾） | 差异如果在 5% 以内——正常。差异超过 10%——检查 z 值（alpha/power 参数） |
| "n 算出来是 0" | denominator = MDE² = 0（MDE=0）| MDE 不能为 0。MDE 是你想检测的最小差异——如果差异为 0，检验没有意义 |
| "function 返回了 float 而不是 int" | `n = ceil(...)` 确保 n 是整数 | 样本量必须是整数。28.3 个人？——不存在。用 `np.ceil()` 或 `int(round(...))` |

---

### 🔗 与主课联动

今天主课学 AA 实验与 Peeking——Peeking 是"在样本量不够时多次看结果"。如果你的 `required_sample_size()` 算出来要 3500/组，但你跑 1000/组就开始看 p 值——这就是 Peeking。今天工程化学的样本量函数告诉你"需要多少"——主课告诉你"不够时为什么不能看"。

---

### 📎 参考速查

- W5D1——浮点精度（比例类计算中的数值稳定性）

---

## D6（周六 9/6）：实验全流程 pipe 串联——从 SRM 到决策

> 📓 今日主课：AB 实验综合实战——完整检查清单+标准化报告

---

### 🎯 今日目标

把 D1-D5 的所有实验组件串起来——SRM → 检验 → 护栏 → 决策——成一个完整的实验分析函数。

---

### ✍️ 综合任务

实现 `run_full_ab_test()`：

```python
def run_full_ab_test(
    control_data: np.ndarray,
    treatment_data: np.ndarray,
    alpha: float = 0.05,
    power: float = 0.8,
    expected_ratio: float = 0.5,
    guardrail_data: Optional[Dict] = None
) -> Dict:
    """完整 AB 实验分析：SRM → 检验 → 护栏 → 决策。

    四步顺序不可跳、不可颠倒：
    Step 1: SRM 检查——分流对吗？
    Step 2: 主要指标检验——效果显著吗？
    Step 3: 护栏检查——副作用可控吗？（可选）
    Step 4: 决策——ship / hold / increase_sample

    每步失败都提前终止并返回原因。
    """
    # Step 1: SRM
    srm = check_srm(len(control_data), len(treatment_data), expected_ratio)
    if srm['srm_detected']:
        return {'error': 'SRM failed', 'srm_result': srm, 'decision': 'invalid'}

    # Step 2: 主要指标检验
    result = run_z_test(control_data, treatment_data, alpha=alpha)

    # Step 3: 护栏（如果有）
    guardrail_passed = True
    guardrail_detail = {}
    if guardrail_data:
        for name, (ctrl, trt) in guardrail_data.items():
            gr = run_z_test(ctrl, trt, alpha=alpha, alternative='two-sided')
            # 护栏只检查是否显著恶化（单尾逻辑——实验组不能显著差于对照组）
            if gr['p_value'] < alpha and gr['mean_treatment'] < gr['mean_control']:
                guardrail_passed = False
                logger.error("护栏指标恶化: %s (p=%.4f)", name, gr['p_value'])
            guardrail_detail[name] = gr

    # Step 4: 决策
    if guardrail_passed and result['significant'] and result['effect_size'] >= 0.1:
        decision = 'ship'
    elif not result['significant']:
        decision = 'hold'
    else:
        decision = 'review'  # 显著但有效应量或护栏问题

    return {
        'decision': decision,
        'main_result': result,
        'srm_result': srm,
        'guardrail_passed': guardrail_passed,
        'guardrail_detail': guardrail_detail
    }
```

**验证**：用正常数据跑一次——确认四步全通过。故意构造 SRM 失败的数据——确认提前终止。故意构造实验组不如对照组的数据——确认 decision 为 'hold'。

---

## D7（周日 9/7）：W6 审计——AB 实验代码规范检查

### 📝 8 道概念自测题

**Q1**：你的 `run_z_test()` 返回的 Dict 为什么需要包含 `recommendation` 字段？为什么不能只返回 p 值让调用方自己判断？

**Q2**：SRM 检验为什么必须放在主要指标分析**之前**而不是之后？如果 SRM 失败——后续的 p 值还有没有意义？

**Q3**：MDE 减半 → 样本量翻 4 倍——这个"平方反比关系"是从公式的哪一项来的？用你自己的话解释给 PM 听。

**Q4**：pathlib 的 `/` 运算符和字符串的 `+` 运算符——在做路径拼接时有什么本质区别？

**Q5**：实验三段式日志的三个阶段各自汇报什么信息？为什么信息密度要"能直接贴进实验报告"？

**Q6**：`check_srm()` 的阈值为什么用 0.01 而不是 0.05？这和 p 值的 0.05 阈值有什么不同？

**Q7**：`run_full_ab_test()` 的四步顺序是什么？为什么不能先看 p 值再做 SRM？

**Q8**：如果你的实验结果"统计显著但效应量极小"（p=0.04, d=0.05），你应该建议上线吗？为什么？

---

### ✅ 参考答案

**Q1**：因为"是否上线"不是纯统计判断。它需要同时考虑 p 值（统计显著）、效应量（业务意义）、护栏（副作用）。让调用方只拿到 p 值再做这些判断——容易被忽略。`recommendation` 是函数内部综合了三个维度的判断。偏差：说"方便"——要说出具体"方便在哪三个维度"。

**Q2**：SRM 在前因为"随机化"是整个实验的基础假设。SRM 失败 = 随机化失败 = 两组的任何差异可能都不是实验操作导致的 = 后续所有 p 值分析和因果推断都不再有效。偏差：说"SRM 不过就重跑"——重跑不能修复分流 bug。

**Q3**：MDE（即 p₂-p₁）在样本量公式的分母上——而且是平方（(p₂-p₁)²）。MDE 减半 → 分母变成 (0.5×MDE)² = 0.25×原分母 → n 变成 4 倍。给 PM 的解释："检测越小差异，就像在越嘈杂的环境里听越小的声音——你需要更多的'耳朵'来抵消噪音。"

**Q4**：`+` 只是拼字符串——不关心语义（会不会产生双斜杠？路径分隔符对不对？）。`/` 是 Path 类的运算符——它知道自己在拼路径，会自动处理分隔符、规范化。偏差：只说"方便"——具体说"/"能自动处理什么。

**Q5**：Describe（描述数据——让读者了解样本）、Analyze（执行检验——让读者看到方法）、Conclude（输出结论——让读者不读代码也知道结论）。能贴进报告 = 日志本身就是分析文档。

**Q6**：SRM 阈值 0.01 更严格——因为 SRM 失败的后果太严重（整个实验作废）。p 值阈值 0.05 是统计惯例——平衡第一类和第二类错误。不同阈值对应不同决策成本。

**Q7**：SRM → 检验 → 护栏 → 决策。不能先看 p 值——因为 SRM 是随机化基础，基础不成立则上层全无效。这就像你不能在"房子地基歪了"的情况下评价"墙刷得怎么样"。

**Q8**：不建议。统计显著（p<0.05）+ 效应量极小（d=0.05）说明差异很小——即使提升存在，也不值得投入工程资源上线（开发成本 > 微小提升带来的收益）。但如果这是"零成本改动"（如改个文案）——可以考虑。

---

> 📌 W6 完成。你的 AB 实验代码现在有统一格式、全流程日志、路径管理、SRM 前置检查、样本量计算、完整流程串联。下周 W7 进入 AB 实验进阶——CUPED/网络效应/14 坑防御。
