# W9：SQL 高级与工程规范（9/22 — 9/28）

> 🎯 **本周目标**：SQL 不只是"查出结果"。本周建立 SQL 代码的工程规范——CTE 分层注释标准、双源验证方法论、窗口函数 ROWS/RANGE 必须显式、EXPLAIN 分析入注释、错题模式化归档。学完这周，你的 SQL 别人（包括三个月后的你）不需要问任何问题就能读懂、验证、优化。
>
> 📎 **本周主课**：SQL 高级特训——窗口函数十类/Gap-and-Island/递归 CTE/面试 SQL/性能调优
>
> 🏢 **本周鲜果多剧情**：数据量涨到百万级——pandas 跑不动——分析逻辑迁移到 SQL。运营总监担心"换 SQL 后数和之前一样吗"——你需要双源验证来保证一致性。公司的另一个分析师也要用你的 SQL——你需要让 SQL 代码本身有清晰的工程规范——不是"能跑"，而是"能维护"。三个月后你自己回来看这条 80 行的 SQL——你还能理解每一层在做什么吗？

---

## D1（周一 9/22）：SQL CTE 分层注释标准——每条 CTE 三要素

> 📓 今日主课：窗口函数十类全映射

---

### 🔴 认知冲突

你写了一篇 60 行的 SQL——3 层子查询嵌套。跑通了，结果看起来对。

两周后产品经理问你"这个转化率的分母含不含退款订单？"——你盯着自己的 SQL，花了 15 分钟才追溯到——"那个 WHERE 条件写在最内层的子查询里——`WHERE status != 'refunded'`——但这个条件被最外层的 JOIN 之后又加了一次——所以有些退款订单被过滤了，有些又没有"。你自己写的 SQL，两周后的你自己看不懂了。

这不是记忆力问题。这是**SQL 作为一种语言的结构性缺陷**——SQL 没有函数签名（你没法写 `(df: pd.DataFrame) -> pd.DataFrame`）、没有 docstring（你没法写"这个子查询做什么、假设什么、输出什么"）、没有模块化（三层嵌套就是一个不可分割的整体——你不能单独测试中间层）。Python 代码从 W1 到 W8 变得越来越模块化——因为 Python 有这个能力。SQL 没有——但你仍然需要对 SQL 做同样的"模块化"——通过**命名和注释**来弥补 SQL 语言本身的缺失。

你打开了一个同事的 SQL——他用 CTE（WITH 子句）把同样的逻辑写成了：
```sql
WITH cleaned AS (...),
     aggregated AS (...)
SELECT * FROM aggregated;
```
你能一眼看出"cleaned 是清洗层、aggregated 是聚合层"。但你仍然不知道——"cleaned 的一行代表什么？一个订单？一个用户？一个订单×用户？"你需要从 GROUP BY 和 SELECT DISTINCT 子句**推导**粒度——这花费了你 3 分钟。而如果他在 CTE 前面加了一行注释——"粒度: 一行 = 一个有效订单"——你只需要 3 秒。

**CTE 只解决了 50% 的可读性问题（给中间结果起了名字）。剩下的 50% 是每层的粒度声明和设计决策——这是 SQL 中最难追溯也最有价值的信息——必须通过注释来弥补。** 这和你在 Python 函数上写 docstring 是同一个道理——但 SQL 没有内建的"注释=文档"机制——你必须自己建立这个规范。

---

### 📖 核心原理

**CTE 分层注释规范——每条 CTE 的前三行注释必须回答三个问题：做什么、粒度是什么（一行=什么）、为什么（如果有关键设计决策）。**

**规范不是"风格建议"——它是你在 W2D1 学的"隐藏实现、暴露接口"原则在 SQL 中的实现。** CTE 的名字 = 接口（这一层产出了什么）。注释中的粒度 = docstring（输入输出的数据结构）。"为什么"注释 = 设计决策记录（类似于你在 Python 函数里写的"为什么用这个方法而不是那个方法"）。

**重构前（子查询嵌套）——三周后需要逐层脑内展开：**

```sql
SELECT city, SUM(total_spent) as gmv
FROM (
    SELECT user_id, city, SUM(amount) as total_spent
    FROM (
        SELECT DISTINCT order_id, user_id, city, amount
        FROM raw_orders
        WHERE amount > 0 AND user_id NOT LIKE 'test_%'
    ) AS cleaned
    GROUP BY user_id, city
) AS user_agg
GROUP BY city;
```

读这段代码的心理过程："最内层——DISTINCT——去重。为什么去重？不知道。中间层——GROUP BY user_id, city——在汇总用户×城市。最外层——GROUP BY city——取城市级别 GMV。"你花了约 30 秒在脑中"展开"这三层。其中 20 秒花在了"为什么 DISTINCT"上——因为没有注释。5 秒花在了"中间层粒度是什么"上——因为需要从 GROUP BY 子句翻译为业务语义。

**重构后（CTE + 分层注释）——从上向下阅读，每层自描述：**

```sql
-- ============================================================
-- 层1: 订单清洗——去除无效数据，产出可直接用于分析的有效订单表
-- 粒度: 一行 = 一个有效订单（order_id 唯一——DISTINCT 保证）
-- 为什么 DISTINCT: ERP 导出 bug 可能导致同一 order_id 出现多行——用 DISTINCT 去重
-- 为什么过滤 test_%: 内部测试账号——user_id 以 'test_' 开头——不影响真实 GMV
-- 为什么 amount > 0: 负值来源于退款单——退款另表处理——不在订单表中混合
-- ============================================================
WITH cleaned_orders AS (
    SELECT DISTINCT
        order_id, user_id, city,
        CAST(order_date AS DATE) AS order_date,
        CAST(amount AS DECIMAL(10,2)) AS amount
    FROM raw_orders
    WHERE user_id NOT LIKE 'test_%'
      AND amount > 0
      AND order_date IS NOT NULL
),

-- ============================================================
-- 层2: 用户月度消费汇总——用于 RFM 计算和用户分群
-- 粒度: 一行 = 一个用户在一个自然月
-- 注意: 某月无订单的用户不出现在此表中（不是"消费=0"——是"不存在这一行"）
-- 下游: 层3 城市汇总 / RFM 计算 / 用户分群 / 复购率分析
-- ============================================================
user_monthly AS (
    SELECT
        user_id,
        DATE_TRUNC('month', order_date) AS order_month,
        COUNT(DISTINCT order_id) AS order_count,
        SUM(amount) AS total_spent,
        AVG(amount) AS avg_order_value
    FROM cleaned_orders
    GROUP BY user_id, DATE_TRUNC('month', order_date)
),

-- ============================================================
-- 层3: 城市月度汇总——GMV 排名报表的直接数据源
-- 粒度: 一行 = 一个城市在一个自然月
-- ============================================================
city_monthly AS (
    SELECT
        c.city,
        DATE_TRUNC('month', c.order_date) AS order_month,
        COUNT(DISTINCT c.order_id) AS order_count,
        SUM(c.amount) AS gmv,
        COUNT(DISTINCT c.user_id) AS unique_users,
        SUM(c.amount) / NULLIF(COUNT(DISTINCT c.user_id), 0) AS gmv_per_user
    FROM cleaned_orders c
    GROUP BY c.city, DATE_TRUNC('month', c.order_date)
)

SELECT city, order_month, gmv, unique_users,
       ROUND(gmv_per_user, 2) AS gmv_per_user,
       RANK() OVER (PARTITION BY order_month ORDER BY gmv DESC) AS rank_by_gmv
FROM city_monthly
WHERE order_month = '2026-09-01'
ORDER BY rank_by_gmv;
```

**同一条 SQL，两种写法对"后来者"的友好程度：**

| 维度 | 子查询嵌套 | CTE + 分层注释 |
|------|----------|---------------|
| 理解"层2 产出什么" | 在脑中展开嵌套→看 GROUP BY→推导粒度（30 秒） | 读注释第一行：`粒度: 一行 = 一个用户在一个自然月`（3 秒） |
| 理解"为什么 DISTINCT" | 看到 DISTINCT——不知道为什么——可能是习惯 | 注释写着："ERP 导出 bug——可能重复订单" |
| 加一个新层 | 拆解嵌套结构——找到插入位置——可能影响整个嵌套 | 在 WITH 链中加一个 CTE——上下游通过名字解耦 |
| 改某层的逻辑 | 可能影响嵌套结构——需要检查所有层 | 只改那一层——上层通过名字引用——不受影响 |
| 单独验证某层 | 不可能——子查询不能独立运行 | 可以——`SELECT * FROM cleaned_orders LIMIT 10`——直接验证清洗逻辑 |
| 新同事接手 | 读 15 分钟——逐层在脑中推导每一层在干什么 | 读 5 行注释——3 分钟理解全貌 |

---

### 🏢 鲜果多案例

鲜果多的 GMV 月报 SQL 从 15 行膨胀到了 80 行（加了留存、复购、渠道维度）。新同事接手后花了半天才理解"每一层在做什么"。你用 CTE 分层标准重构——切成 5 层：清洗→用户月汇总→窗口排名→渠道归因→最终输出。新同事打开 SQL 文件——读了 5 行注释——5 分钟理解了全貌。

两周后运营总监问"复购率的分子是什么"——你打开 SQL，定位到第 2 层 `user_monthly`——注释第一行写了"粒度: 一行 = 一个用户在一个自然月"——你立刻回答——10 秒。这不是因为你记忆力好——是因为**注释替你记住了你自己当时的思考**。

这就像你在 W2D5 学到的——docstring 不是写给别人的——是写给**三个月后的你自己**的。你在 SQL 中做的分层注释——也是同样的道理。三个月后你回来看这条 SQL——你不是在读代码——你是在读你自己三个月前留下的"设计笔记"。

---

### ✍️ 动手练习

1. 拿出你今天主课写的最复杂的一条 SQL（≥ 3 层逻辑）。按 CTE 分层注释标准重构——每条 CTE 的三要素写全。特别注意**粒度声明和 GROUP BY 的一致性**——如果你写了"粒度: 一行 = 一个用户在一个月"但 GROUP BY 是 `GROUP BY user_id, city`——粒度声明是错的。
2. 确认每层之间用 `-- ===...===` 醒目分隔——在 VS Code 中折叠一条 CTE 时不影响阅读其他 CTE。
3. 在重构后的 SQL 文件顶部加一段注释，写"重构前后对比——原来 X 层嵌套→现在 M 层 CTE。改动某层逻辑的时间从 N 分钟降为 M 秒。"
4. 打开你两周前写的一条 SQL——不看注释——给自己 3 分钟理解它。然后对照今天的标准——如果当时有这些注释——理解时间会缩短多少？把答案写在注释里。
5. `git commit -m "refactor SQL to CTE layered annotation standard with granularity declarations" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- 每条 CTE 有独立命名（`cleaned_orders`/`user_monthly`/`city_monthly`——不是 `a`/`b`/`c`）
- 每条 CTE 的第一行注释是"粒度: 一行 = xxx"——这是注释中价值最高的信息——不需要从 GROUP BY 推导
- GROUP BY 子句和粒度声明一致

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "注释写了但粒度和 GROUP BY 不一致" | 先写 SQL 后补注释——粒度是"回忆"的——可能和实际 GROUP BY 不一致 | **先写注释、再写 SQL。** 如果你写不出"粒度: 一行 = xxx"——说明你还没想清楚这一层要产出什么——不应该开始写 SQL |
| "CTE 变多了但每条只有一行注释——反而更难读了——需要上下跳跃" | 拆分 CTE 不是目的——注释才是。没有充分注释的 CTE 比子查询更差——因为你需要在 CTE 之间不断跳跃去理解逻辑 | 每条 CTE 的三要素至少写全——否则不如合并回子查询——至少不用上下跳跃 |
| "觉得'粒度'太啰嗦——GROUP BY 已经说明了" | GROUP BY `user_id, DATE_TRUNC('month', order_date)`——从这行你能一眼看出"一行 = 一个用户在一个自然月"吗？你需要 3 秒在脑中将 SQL 语法翻译为业务语义。注释替你做了这个翻译——你只需要 0.3 秒阅读 | 粒度注释是给"三个月后的你"和"新同事"看的。你现在觉得啰嗦是因为上下文还在脑子里——三个月后上下文不在了——"显而易见"变成"需要推导" |

---

### 🔗 与主课联动

今天主课学窗口函数十类——而窗口函数正是 SQL 中最容易"不知道粒度变化"的语法。`SUM() OVER (PARTITION BY user_id ORDER BY order_date)`——它不改变行数——但每行多了累计信息——**粒度没有变但每行的含义变了**。在 CTE 注释里显式标注"本层窗口函数未改变粒度——行数仍 = 原始订单数——但每行新增了累计列"——这是一个容易被忽略但至关重要的信息。


## D2（周二 9/23）：双源验证——不是"翻译"，是"用两种独立的思路验证同一个结论"

> 📓 今日主课：Gap-and-Island + Sessionization——连续登录/活跃/消费

---

### 🔴 认知冲突

你用 SQL 查出了"上月 GMV = 523 万"。你怎么确认这个数是对的？

你的第一反应——"再看一遍 SQL 逻辑有没有写错"。但你心里知道这是**自欺欺人**——同样的逻辑看两遍，你发现不了逻辑本身的盲点。你的 SQL 里写了 `WHERE status != 'cancelled'`——但 `cancelled` 是英文的——你忘了有些行的 status 写的是中文的 `'已取消'`——这条 WHERE 条件静默漏掉了这些行。你看两遍也发现不了——因为你的脑子在"读 SQL 语法"而不是在"验证业务假设"。

**真正的验证需要一个独立的参照系。** 你需要用 pandas——**不看 SQL 逻辑**——只看着原始数据和业务需求（"计算上月各城市 GMV——排除取消和退款订单"）——独立实现分析。两个独立实现的结果在容差内一致→你可以信任这个数。不一致→差异本身就是"某个假设在两个实现中不同"的证据——这比"两个结果都对不上"更有价值——因为它直接告诉你**两个实现的假设差异在哪里**。

**"翻译"和"独立验证"是两回事。** 翻译 = 你开着 SQL 窗口——一行一行翻译成 pandas 语法。翻译的时候你已经带了 SQL 的假设——你会不知不觉复制同样的 bug。独立验证 = 你关掉 SQL 窗口——只看着业务需求——用 pandas 从零实现。你不会复制 SQL 的假设——因为你看不到它们。**只有当两个独立实现结果一致时——你才真正验证了"分析逻辑本身"——而不是"翻译是否准确"。**

---

### 📖 核心原理

**双源验证三步——每步独立定位不同根因：**

```python
from typing import List, Dict
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def validate_sql_against_pandas(
    df_sql: pd.DataFrame,
    df_pandas: pd.DataFrame,
    key_columns: List[str],
    tolerance: float = 0.001
) -> Dict:
    """双源验证——SQL 结果 vs pandas 独立计算结果。
    
    三步检查——每步失败能独立定位不同的根因:
    Step 1: 行覆盖——外连接找出"只在一边存在"的行 → 口径差异
    Step 2: 列对齐——两边的列名是否一致 → 字段映射/命名差异
    Step 3: 数值容差——逐列检查数值差异 → 浮点精度/聚合顺序/NULL 处理
    
    这不是"翻译验证"——这是"两个独立实现应该得到相同结论"的假设检验。
    """
    # === Step 1: 外连接——找出两边不一致的行 ===
    merged = df_sql.merge(
        df_pandas, on=key_columns, how='outer',
        suffixes=('_sql', '_pd'), indicator=True
    )
    sql_only = merged[merged['_merge'] == 'left_only']
    pd_only = merged[merged['_merge'] == 'right_only']

    issues = []
    if len(sql_only) > 0:
        sample = sql_only[key_columns].head(3).to_dict('records')
        issues.append(
            f"仅在 SQL 中存在 {len(sql_only)} 行——"
            f"SQL 含 pandas 不含的数据。键值示例: {sample}"
        )
    if len(pd_only) > 0:
        sample = pd_only[key_columns].head(3).to_dict('records')
        issues.append(
            f"仅在 pandas 中存在 {len(pd_only)} 行——"
            f"pandas 含 SQL 不含的数据。键值示例: {sample}"
        )

    # === Step 2: 列名对齐 ===
    sql_cols = set(df_sql.columns)
    pd_cols = set(df_pandas.columns)
    if sql_cols != pd_cols:
        only_sql = sql_cols - pd_cols
        only_pd = pd_cols - sql_cols
        if only_sql:
            issues.append(f"仅在 SQL 中存在的列: {only_sql}")
        if only_pd:
            issues.append(f"仅在 pandas 中存在的列: {only_pd}")

    # === Step 3: 数值列逐列检查——相对容差 0.1% ===
    numeric_cols = df_sql.select_dtypes(include='number').columns
    for col in numeric_cols:
        if col not in df_pandas.columns:
            continue
        sql_vals = merged[f'{col}_sql'].fillna(0)
        pd_vals = merged[f'{col}_pd'].fillna(0)
        abs_diff = (sql_vals - pd_vals).abs()
        max_diff = abs_diff.max()

        # 相对容差——max(|sql|,|pd|,1) 避免除零
        max_val = max(sql_vals.abs().max(), pd_vals.abs().max(), 1.0)
        if max_diff > tolerance * max_val:
            worst_idx = abs_diff.idxmax()
            issues.append(
                f"列 '{col}' 差异超容差: "
                f"SQL={sql_vals[worst_idx]:.4f}, pandas={pd_vals[worst_idx]:.4f}, "
                f"差异={max_diff:.4f} | 键值: {merged.loc[worst_idx, key_columns].to_dict()}"
            )

    passed = len(issues) == 0
    if passed:
        logger.info("✅ 双源验证通过: %d 行一致 (容差 %.3f%%)", len(merged), tolerance * 100)
    else:
        logger.error("❌ 双源验证失败: %d 个差异", len(issues))
        for issue in issues:
            logger.error("  - %s", issue)

    return {
        'passed': passed,
        'n_total': len(merged),
        'n_sql_only': len(sql_only),
        'n_pd_only': len(pd_only),
        'issues': issues
    }
```

**双源验证发现的经典差异——不是"谁写错了"，是"两个实现做了不同的假设"：**

| 差异类型 | SQL 的行为 | pandas 的行为 | 对齐方法 |
|---------|----------|-------------|---------|
| NULL 聚合 | `SUM(amount)` 自动跳过 NULL——返回非 NULL 值的和 | `df['amount'].sum()` 也跳过 NULL。但 `a + b` 不跳过——如果 a 是 NULL 则结果为 NULL | 用 `.sum()` 而不是 `+` 运算符 |
| 浮点精度 | 数据库可能用 `DECIMAL(20,4)` 高精度定点数 | Python float = IEEE 754 双精度——约 15 位有效数字 | 容差设为 0.1%——不是 `==` 比较 |
| 字符串比较 | 大小写是否敏感取决于 Collation（如 `utf8_general_ci` 不区分） | Python 严格大小写敏感——`'Cancelled' != 'cancelled'` | 统一 `UPPER()` 或 `.str.upper()` |
| 去重逻辑 | `SELECT DISTINCT *` ——整行所有列参与比较 | `df.drop_duplicates()` 默认也是整行——但可以只根据部分列（subset 参数） | 确认 subset 参数一致——如果 SQL 是 DISTINCT * 则 pandas 不用设 subset |
| 日期边界 | `DATE_TRUNC('month', date)` 可能含时区转换逻辑 | pandas `dt.to_period('M')` 基于 UTC 或 naive datetime | 统一用 DATE 类型（不含时区）——或统一用 UTC |

---

### 🏢 鲜果多案例

鲜果多上月 GMV——SQL 算出来 523 万，pandas 算出来 518 万。差了 5 万（~1%）。双源验证没过——Step 1（行覆盖）发现了差异——"仅在 pandas 中存在 350 行"。

排查后发现：SQL 的 WHERE 条件里有 `status NOT IN ('cancelled', 'refunded')`——排除了取消和退款订单。pandas 里的清洗逻辑只检查了 `status == 'cancelled'`——退款订单（status='refunded'）没有被排除。差的 5 万 = 350 个退款订单的金额。

这个发现不是"修了一个 bug"——是"发现了两个实现之间的一个隐含口径差异"。SQL 用的是"实际成交额"口径（排除取消+退款），pandas 用的是"订单金额"口径（只排除取消——退款仍然算在内）。双源验证让你发现了这个口径差异——而不是困惑于"为什么两个结果不一样"。你更新了 pandas 的逻辑——加入退款排除——重新验证——通过。**双源验证的价值不是"证明大家算的一样"——是"发现大家算的不一样，然后找到差异的根因"。**

---

### ✍️ 动手练习

1. 实现 `validate_sql_against_pandas()` 函数（放在 `src/validate.py`——和 W3D1 的 `validate_input()` 放在一起——数据验证和结果验证是一家人）。
2. 找一条你今天主课写的 SQL——把结果导出为 CSV，用 pandas 加载。然后**关掉 SQL 窗口**——只看业务需求——用 pandas 从原始数据独立实现相同的分析。
3. 跑双源验证。通过了吗？如果没通过——差异的根因是什么？是"两个实现做了不同的假设"还是"其中一个实现有 bug"？
4. 在代码注释里记录："双源验证——SQL 假设了 A（如排除退款），pandas 假设了 B（只排除取消）。差异来源于口径不一致——已统一为口径 A。"
5. `git commit -m "add SQL vs pandas dual-source validation with 3-step check" && git push`

---

### ✅ 自检

- 函数检查三个维度：行覆盖（外连接）/ 列对齐 / 数值容差（不是 `==`）
- 至少一条 SQL 通过双源验证——或发现不一致并标注了差异根因
- 容差设为 0.1%——浮点精度差异不应该被当成"验证失败"


---

## D3（周三 9/24）：窗口函数 ROWS vs RANGE——5 个字母的差异，静默的错误结果

> 📓 今日主课：递归 CTE——递归三要素/BOM 物料清单/组织树

---

### 🔴 认知冲突

你写了一个累计金额的窗口函数：
```sql
SUM(amount) OVER (PARTITION BY user_id ORDER BY order_date)
```
没写 `ROWS` 子句。结果看起来对——数据量小的时候你肉眼扫了一下"差不多"。

一个月后同事发现累计值对不上——同一个用户在同一天有 3 个订单（金额分别为 100、200、300）——但 SQL 输出的是三行完全一样的"累计值"——全都是 600。你预期的行为是"第一行累计 100、第二行累计 300、第三行累计 600"——逐行累加。SQL 实际的行为是"三行全部返回 600"——因为 SQL 默认用了 `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`——RANGE 把 ORDER BY 列**值相同**的所有行视为同一个逻辑行——一起累计。

你少了 5 个字母：`ROWS`。不报错、不警告、不提示——静默地给你一个"看起来合理但完全错误"的结果。而这个错误直到一个月后的财务对账时才被发现——基于错误累计值做的一系列 VIP 等级划分和营销投放——已经发出去了。

**问题**：为什么 SQL 标准委员会的默认是 RANGE 而不是 ROWS？如果默认是错的——为什么不去改？答案——RANGE 在金融场景（"同一天的所有交易一起结算"）中有意义。SQL 标准是为"通用数据库"设计的——不是为"数据分析"设计的。"通用"不等于"适合你"。而且默认行为在 PostgreSQL/MySQL/SQL Server/Hive 之间**不一致**——Hive 默认 ROWS——其他默认 RANGE——同一个 SQL 跨数据库迁移行为会静默改变。

---

### 📖 核心原理

**`ROWS` = 物理行（逐行累计——第 1 行→第 2 行→第 3 行）。`RANGE` = 逻辑值（ORDER BY 列值相同的所有行 = 同一个逻辑行——一起处理）。**

用一个最小可复现实验亲眼看到差异：

```sql
-- 创建测试数据: user_id=1, 同一天 3 个订单, 金额 100/200/300
CREATE TEMP TABLE test_orders AS
SELECT 1 AS order_id, 1 AS user_id, '2026-09-01'::DATE AS dt, 100 AS amount
UNION ALL SELECT 2, 1, '2026-09-01', 200
UNION ALL SELECT 3, 1, '2026-09-01', 300;

-- ROWS 模式（✅ 数据分析师几乎总是要这个——逐行累计）:
SELECT order_id, amount,
       SUM(amount) OVER (ORDER BY dt ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumsum
FROM test_orders;
-- 结果: (1,100,100) / (2,200,300) / (3,300,600) ← 逐行增加——正确

-- RANGE 模式（❌ SQL 默认——同值同组——几乎不是你想要的）:
SELECT order_id, amount,
       SUM(amount) OVER (ORDER BY dt) AS cumsum
FROM test_orders;
-- 结果: (1,100,600) / (2,200,600) / (3,300,600) ← 三行完全一样！因为 dt 值相同
```

**为什么三行都是 600？** RANGE 看到 ORDER BY 列 `dt` 的三行值完全相同（都是 `2026-09-01`）——它认为这三行属于"同一个逻辑组"——`CURRENT ROW` 包含了组内所有值相同的行——所以每行的累计都包含了全部三行——无论你"第几个"执行。

**跨数据库默认行为不一致——这是你必须显式写的根本原因：**

| 数据库 | 默认 frame | 数据分析师的预期 |
|--------|----------|-----------------|
| PostgreSQL | `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` | ❌ 不符合 |
| MySQL 8.0 | `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` | ❌ 不符合 |
| SQL Server | `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` | ❌ 不符合 |
| **Hive** | **`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`** | ✅ 符合 |

同一个 SQL——从 PostgreSQL 迁移到 Hive——不写 frame 子句——行为从"错误"变成"正确"。这不是数据库有 bug——是你**依赖了默认行为**——而默认行为在不同的数据库之间不同。

**什么时候用 ROWS，什么时候用 RANGE——数据分析师版：**

- **ROWS（99% 的窗口函数应该用它）**：逐行累计——"第 1 笔订单→第 2 笔→第 3 笔"。移动平均——"最近 7 行"。行级比较——"上一行 vs 当前行"。
- **RANGE（1% 的场景）**：ORDER BY 列是连续数值且你要"值相同的一起处理"。金融场景——"同一天的所有交易一起结算"。数据分析中——RANK/DENSE_RANK 已经内置了"同值同排名"——不需要 RANGE。移动平均在数据有缺失日期时——RANGE = "最近 7 天"（可能只有 3 行因为缺失了 4 天）——ROWS = "最近 7 行"（不管日期间隙——总是 7 行）。
- **鲜果多项目中——永远用 ROWS。** 因为你的 ORDER BY 列是日期或订单 ID——不是连续数值范围。

**规则：你的项目中不可妥协——每个窗口函数含 `ORDER BY` 必须含显式的 `ROWS` 或 `RANGE` frame。不依赖任何数据库的默认。** 这条规则应该进入你的 SQL code review checklist（D6）。

---

### 🏢 鲜果多案例

鲜果多在计算"用户累计消费金额"——用于划分 VIP 等级（普通→银卡→金卡→VIP）。SQL 用了 `SUM() OVER (ORDER BY order_date)`——没写 `ROWS`——用了默认的 RANGE。同一天下了多个订单的用户——累计值对不上——有十几个用户被错误地标记为"金卡"——享受了不对应的会员折扣。

修复只加了 5 个字母——把 `ORDER BY order_date` 改成 `ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`——但在修复之前——这些用户已经收到了金卡邀请券——营销成本已经花出去了。**5 个字母的工程规范——不是"抠语法"——是防止"静默的数据错误导致不可逆的业务损失"。**

---

### ✍️ 动手练习

1. 在数据库中跑上面的最小可复现实验——亲眼看到 ROWS 和 RANGE 的差异。如果你没有数据库——用 Python + pandas 也可以模拟——但实际跑一遍 SQL 的体验不同。
2. 搜索你项目中所有 SQL 文件的窗口函数：`grep -rn "OVER (" src/sql/`——列出每一个。
3. 确保每一个显式指定了 `ROWS` 或 `RANGE`。裸 `ORDER BY`（不带 frame）的全部补上。
4. 在一条累计类窗口函数上方加注释——解释"为什么用 ROWS——同天订单不应批量累计。数据源可能改精度（从天变成秒）——显式 ROWS 保证行为不变。"
5. 在你的 SQL code review checklist（D6）中加一条——"窗口函数含 ORDER BY 必须含显式 ROWS/RANGE"。
6. `git commit -m "explicit ROWS/RANGE frame in all window functions + simulation verification" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

- ROWS 逐行累计：100→300→600。RANGE 同天批量：三个全部是 600
- 根因：RANGE 把 ORDER BY 列值相同的所有行视为同一逻辑行——一起累计

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "我的数据有精确到秒的时间戳——ROWS 和 RANGE 行为一样——所以不写也没事" | 今天的时间戳精确到秒——明天的数据源改了精度（只保留日期）——行为静默改变 | 不是"会不会出问题"——是"可不可能出问题"。只要有可能——显式写 |
| "Hive 默认是 ROWS——所以我的 SQL 不用写" | 今天在 Hive——明天迁移到 Spark SQL——默认行为可能不同 | 显式写——不依赖任何平台的默认 |
| "移动平均——RANGE 和 ROWS 什么时候不同？" | 数据有缺失日期时。ROWS="最近 7 行"（物理行——可能跨越 10 天）。RANGE="最近 7 天"（逻辑范围——可能只有 3 行因为缺失了 4 天） | 如果你关心的是"最近 7 天的趋势"→RANGE。如果你关心的是"最近 7 笔交易"→ROWS。不确定→ROWS——行为更可预测 |


## D4（周四 9/25）：EXPLAIN 分析入注释——不只是"看执行计划"，是"为未来的自己留下性能上下文"

> 📓 今日主课：面试 SQL（上）

---

### 🔴 认知冲突

你写了一条复杂 SQL——耗时 8 秒——"还行"。两个月后数据量涨了 5 倍——同一条 SQL 跑了 3 分钟。你不知道为什么慢——因为两个月前**你没有在注释里记录当时的执行计划、数据量和基线耗时**。你需要从零分析。

更糟的情况——新同事接手了这条 SQL——他不知道"在数据量 X 时耗时 Y 是正常的"——他以为是代码逻辑有问题——花了一下午重写 SQL——最后发现"不是逻辑问题——是没加索引——type=ALL 全表扫描"。如果当时有 EXPLAIN 注释——5 分钟定位问题。

**EXPLAIN 不是"出问题了才看"——是每次写 SQL 时看一次、记一次。** 因为写 SQL 时的你拥有最完整的上下文——数据量级、索引配置、业务需求。两个月后的你没有这些——注释是你留给自己的"性能快照"。

---

### 📖 核心原理

**EXPLAIN 只看两个关键字段：`type`（访问方式——从快到慢）和 `rows`（预估扫描行数——对照实际数据量）。**

**1. `type` 列——JOIN/查询的访问方式：**

| type | 含义 | 判断 | 优化优先级 |
|------|------|------|----------|
| `const` | 主键等值——只查一行 | ✅ 完美 | 不需要 |
| `eq_ref` | 唯一索引等值 JOIN | ✅ 很好 | 不需要 |
| `ref` | 非唯一索引等值 | ✅ 不错 | 数据量 > 1000 万时关注 |
| `range` | 索引范围扫描（BETWEEN/>/<） | ⚠️ 还行 | 范围太大时考虑分区 |
| `index` | 全索引扫描——读了整个索引 | ⚠️ 需关注 | 索引太大→考虑分区裁剪 |
| **`ALL`** | **全表扫描——每一行都读** | 🔴 **危险** | **立即优化——加索引或分区** |

**2. `rows` 列——预估扫描行数。** 对照实际数据量。差距 > 10 倍→统计信息过期→`ANALYZE TABLE`。

**EXPLAIN 注释模板——每条复杂 SQL 上方：**

```sql
-- ============================================================
-- EXPLAIN 分析 (2026-09-25, PostgreSQL 15, 数据量 ~10万行)
-- ============================================================
-- cleaned_orders: Seq Scan (type=ALL, rows~95,000)
--   → 全表扫描——无索引。当前 <1s 可接受。超 100 万行时加复合索引(order_date, user_id)。
-- user_monthly: HashAggregate (rows~5,000)
--   → GROUP BY 用 Hash——分组数多时合理。
-- 总成本: ~2,500 | 当前耗时: ~0.8s (@10万行)
-- 预估: 100万行→~8s | 1000万行→~80s (type=ALL 线性增长)
-- 优化: ①分区(order_date) ②索引(user_id)——消除 type=ALL
-- ============================================================
```

**三个使用场景——为什么值得花 2 分钟写这条注释：**

**场景 1（两个月后自己回来看）：** "为什么这么慢？"→看到注释"type=ALL, @10万行 0.8s, 预估 @1000万行 80s"→瞬间明白：不是 SQL 写得不好——是数据量超了当初的设计假设——需要加索引或分区。

**场景 2（新同事接手）：** "正常应该跑多久？"→看到注释"当前 ~0.8s @10万行"→如果今天跑了 5 分钟→他知道"这是异常——排查数据量或索引"。

**场景 3（面试——你被要求写一条 SQL 并解释）：** 你写完后在上方加 EXPLAIN 注释。面试官看到——这个人不仅会写 SQL——还知道怎么评估和预测性能。这是区分"SQL 使用者"和"SQL 开发者"的标志。

---

### 🏢 鲜果多案例

鲜果多 GMV 月报 SQL——10 万行时 0.8s。数据涨到 500 万行后——耗时 45s。你打开 SQL——看到自己两个月前写的 EXPLAIN 注释——"type=ALL——超 100 万行时加复合索引(order_date, user_id)"。瞬间定位根因——加索引——`CREATE INDEX idx_orders_date_user ON orders(order_date, user_id)`——type 从 ALL 变成 range——耗时从 45s 降到 2s。

如果没有这条注释——你今天会花一下午排查——从"是不是 JOIN 有问题"到"是不是数据异常"到"是不是数据库配置变了"——最后才想到"哦——该加索引了。"**2 分钟的注释——省了 3 小时的排查。**

---

### ✍️ 动手练习

1. 给今天写的 2 条复杂 SQL 跑 EXPLAIN。关键信息写入 SQL 上方注释：type / rows / 总成本 / 当前耗时 / 数据量增长预估 / 优化方案。
2. 如果看到 `type=ALL`——必须标注优化方案（建什么索引、在哪个列上分区）。
3. 打开一条两周前写的 SQL——你能一眼看出它的性能特征吗？如果不能——补上 EXPLAIN 注释。
4. `git commit -m "add EXPLAIN performance annotations to all complex SQL" && git push`


## D5（周五 9/26）：错题模式化归档——从 L2"记住案例"到 L3"提炼可迁移的防御规则"

> 📓 今日主课：面试 SQL（下）

---

### 🔴 认知冲突

W3D5 你学了用 GitHub Issue 归档错题——每条含"错误代码→根因→正确代码→防御规则"。这是 L2——按类型整理。你有 15 条 SQL 错题。

面试官问"你踩过哪些 SQL 坑？"——你说出了 5 个具体案例。面试官追问："从这些案例中——你有没有提炼出**可迁移的防御规则**——不只是'这次注意了'——而是'以后任何类似场景都能防住'？"

你沉默了。NOT IN + NULL 这个坑你记得很清楚。但如果下次遇到的是 `<> ALL(subquery)`——同样是 SQL 三值逻辑问题——你能识别吗？如果不能——你只防住了"完全相同的问题再现"——没有防住"同类不同形的问题"。

**L3 模式化——从 N 个具体案例中抽象出 1 条可迁移的防御规则。** 规则告诉你——"凡是出现 X 模式——必须先检查 Y"。NOT IN→检查 NULL。LEFT JOIN + 右表 WHERE→确认是不是故意的。窗口函数 ORDER BY→确认有没有显式 ROWS。这些规则**不依赖你的记忆力**——它们进入你的 SQL code review checklist——每次写 SQL 或审查 PR 时自动触发。

---

### 📖 核心原理

**每攒够 3 个同类型错题→提炼一条模式→含 6 个字段。放入 `docs/sql_mistakes.md`——这是你面试时"我有一套系统化 SQL 质量保障体系"的证据。**

### 模式 1: NOT IN + NULL（三值逻辑）

- **触发条件**：子查询/列表中可能存在 NULL 值
- **错误示例**：`WHERE user_id NOT IN (SELECT user_id FROM blacklist)`——黑名单有 NULL→整查询返回空。不是返回 NULL——返回空集（0 行）。空集比 NULL 更危险——NULL 你会注意到——空集可能被当成"正常——没有符合条件的数据"
- **根因**：NOT IN = `<> ALL(...)`。SQL 三值逻辑（TRUE/FALSE/UNKNOWN）——任何值与 NULL 比较 = UNKNOWN——WHERE UNKNOWN 不返回任何行
- **正确写法**：①子查询加 `WHERE col IS NOT NULL` ②改用 `NOT EXISTS (SELECT 1 FROM blacklist b WHERE b.user_id = orders.user_id)`——NOT EXISTS 是相关子查询——直接比较两个值——不受 NULL 影响
- **防御规则**：凡是 NOT IN 子查询——必须先确认子查询结果无 NULL。code review 搜索 `NOT IN`——检查子查询是否考虑了 NULL

### 模式 2: LEFT JOIN + 右表 WHERE（静默变 INNER JOIN）

- **触发条件**：LEFT JOIN 之后在 WHERE 中对右表列加过滤条件
- **错误示例**：`LEFT JOIN users ON ... WHERE users.level='VIP'`——把 LEFT JOIN 变成了 INNER JOIN——因为无匹配行产生 users.level=NULL——WHERE 条件过滤了 NULL
- **根因**：WHERE 在 JOIN 之后执行。LEFT JOIN 为无匹配行生成 NULL——WHERE 条件要求 `level='VIP'`——NULL 不满足——这些行被静默删除了
- **正确写法**：①条件放在 ON 子句中——`AND users.level='VIP'` ②`WHERE (users.level='VIP' OR users.level IS NULL)`
- **防御规则**：任何 LEFT JOIN 之后——检查 WHERE 是否含右表列过滤。有→确认"这是故意的还是无意的"。故意缩小结果集→改用 INNER JOIN 语义明确。无意→条件移到 ON 子句

### 模式 3: 窗口函数无 frame（D3 的 ROWS/RANGE）

- **触发条件**：窗口函数含 ORDER BY 但无显式 ROWS/RANGE
- **错误示例**：`SUM() OVER (PARTITION BY user_id ORDER BY order_date)`——默认 RANGE——同天订单批量累计
- **根因**：SQL 标准默认 RANGE——数据分析需要 ROWS。且默认在不同数据库间不同
- **正确写法**：显式 `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`（或你需要的 frame）
- **防御规则**：窗口函数含 ORDER BY → 必须含 ROWS 或 RANGE。code review 搜索 `OVER (`——检查下一行是否含 `ROWS` 或 `RANGE`

### 模式 4: COUNT(\*) vs COUNT(column)——静默的行数差异

- **触发条件**：SELECT 子句中同时出现 `COUNT(*)` 和 `COUNT(column)`——或从一种切换到另一种而未检查语义差异
- **错误示例**：`SELECT COUNT(referral_code) AS referred_users FROM users`——期望统计"被推荐注册的用户数"。但 `referral_code` 列中——未通过推荐注册的用户该列值为 NULL——`COUNT(referral_code)` 静默排除了所有这些行——返回的不是"全表行数"——是"referral_code 不为 NULL 的行数"
- **根因**：`COUNT(*)` 统计行数（含 NULL）。`COUNT(column)` 统计该列**非 NULL 值的个数**——自动跳过 NULL。两者在没有 NULL 时结果相同——在有 NULL 时静默不同——而 NULL 往往是"数据质量差"的信号（该填但没填）——你静默丢掉了这些行
- **正确写法**：确认你要的是"行数"还是"某列有值的行数"。如果是"行数"——用 `COUNT(*)` 或 `COUNT(1)`。如果是"某列有值的行数"——用 `COUNT(column)`——但需要确认"column 为 NULL 是否合理"——如果 column 不该有 NULL——先修复数据质量——再 COUNT
- **防御规则**：凡是 COUNT(column)——必须先确认该列 NULL 的含义——并在注释中说明。code review 看到 COUNT(非主键列)→检查"为什么不是 COUNT(*)"和"NULL 代表什么"
- **真实案例**：面试题——"users 表 100 行，referral_code 列 20 个 NULL——`SELECT COUNT(*)` 和 `SELECT COUNT(referral_code)` 结果差多少？"回答 100 vs 80。面试官追问"如果这些 NULL 代表'没有推荐码的用户'——COUNT(referral_code) 是'有推荐码的用户数'——语义不一样——不是谁对谁错——是你需要知道你在 COUNT 什么"

### 模式 5: 隐式类型转换——JOIN ON varchar = integer——性能杀手

- **触发条件**：JOIN ON 子句中两边列的数据类型不一致（如 orders.user_id 是 VARCHAR，users.id 是 INTEGER）
- **错误示例**：`SELECT * FROM orders JOIN users ON orders.user_id = users.id`——orders.user_id 是 VARCHAR(32)——users.id 是 INTEGER。MySQL 隐式将两边的值都转为 DOUBLE 来比较——索引失效——`type=ALL`——全表扫描
- **根因**：MySQL 的隐式类型转换规则——当 VARCHAR 和 INTEGER 比较时——MySQL 将两者都转为 DOUBLE——索引列被函数"包裹"了——索引失效。Hive 的行为不同——它不做隐式转换——直接报错或返回空结果——但更难排查——因为不会报语法错误——只是"查不出来"
- **正确写法**：①建表时统一数据类型——orders.user_id 应该和 users.id 类型一致——INT 就都 INT——VARCHAR 就都 VARCHAR ②如果类型确实不同——显式 CAST：`ON orders.user_id = CAST(users.id AS VARCHAR(32))`——但要注意——CAST 在左边也会导致左边索引失效——最安全的做法是统一建表时的类型
- **防御规则**：凡是 JOIN ON——必须检查两边列的数据类型是否一致。不一致→在建表/ETL 层面统一——不在查询层面 CAST。code review 检查 DDL——所有 JOIN 的外键列是否和主键列类型一致
- **真实案例**：鲜果多——orders 表是从 ERP 导出的——user_id 存成 VARCHAR（因为 ERP 系统用字符串 ID）——users 表是内部系统——id 是 INTEGER。JOIN 效率极低——修复是在 ODS 到 DWD 的清洗层统一类型——`CAST(user_id AS INTEGER)`——所有下游查询自动受益

---

### 🔗 从模式到检查清单——把防御规则变成自动化

上面 5 条模式不是让你"每次写 SQL 时在脑中逐条回忆"——那是不可靠的。它们的归宿是你的 **SQL Code Review Checklist**——一份写在项目文档中的清单——每次自己审查 SQL（或在 PR review 时）——逐条对照——自动化搜索：

```bash
# 自动检查——不是替代人脑——是让大脑不需要记住"搜索什么"
grep -rn "NOT IN" src/sql/          # 检查 NOT IN 子查询是否含 NULL 处理
grep -rn "LEFT JOIN" src/sql/       # 检查 WHERE 是否含右表列过滤
grep -rn "OVER (" src/sql/          # 检查窗口函数是否含 ROWS/RANGE
grep -rn "COUNT(" src/sql/          # 检查 COUNT(column)——确认 column NULL 含义
grep -rn "ON.*=" src/sql/           # 检查 JOIN ON 两边类型——需结合 DDL 检查
```

**这份 Checklist 是你的"外置大脑"——它不依赖你的记忆力——每次审查自动触发。** 三个月后你回来改一条 SQL——你不需要回忆"W9D5 教了 5 个模式"——你打开 Checklist——逐条 grep——10 分钟内完成审查。这才是 L3 工程化——规则不依赖人——规则依赖系统。

在你提交每一条 SQL PR 时——跑这 5 条 grep——把输出贴在 PR description 中——告诉 reviewer"我已经逐项自查并通过"。这个行为在面试中是一个有力的信号——"我不只写 SQL——我有一个系统化的代码质量保障机制"。

---

### 🏢 鲜果多案例

鲜果多"月活跃用户"SQL 用了 NOT IN——某月 blacklist 表里被误加了一条 NULL（管理员手误删了一个用户但没清干净关联数据）——整个月 MAU = 0。运营总监问"这个月没有活跃用户？"——你排查 3 小时——最终找到那一条 NULL——它通过 NOT IN 把全部用户都"否定"了。

如果你当时有 L3 防御规则——"凡是 NOT IN——先确认子查询无 NULL"——你写那条 SQL 时会加 `WHERE user_id IS NOT NULL`——这个事故根本不会发生。**防御规则的价值不是"事后排查更快"——是"事前就不会发生"。**

---

### ✍️ 动手练习

1. 打开 GitHub Issues——SQL 标签——同类错误 ≥ 3 个→提炼一条模式。
2. 创建 `docs/sql_mistakes.md`——至少 3 条模式——每条含 6 字段（触发条件/错误示例/根因/正确写法/防御规则/真实案例）。
3. `git commit -m "add SQL mistake pattern archive with 3+ defensive rules (L3)" && git push`


---

## D6（周六 9/27）：周项目——用 D1-D5 标准审查所有现有 SQL，逐条过五道检查，补齐所有缺口

### 🎯 今日任务

不是写新代码——是**用本周标准逐条审查你所有现有 SQL**。今天的产出不是一行新 SQL——是一份"SQL 代码规范审计报告"——每条 SQL 过五道检查——通过/不通过（标注原因和修复方案）。

### 审计流程——打开你项目中的每条重要 SQL，逐一对照：

**检查 1：CTE 注释完整吗？**

打开 SQL 文件——每遇到一个 CTE（WITH 子句中的定义）——检查前三行注释是否含"做什么/粒度/为什么"。如果不含→标注"缺少粒度声明——从 GROUP BY 子句推导需要 30 秒——加上注释只需 3 秒"——补上。

特别注意——粒度声明和 GROUP BY 是否一致？不一致→这是 bug——标注"粒度声明和 GROUP BY 不一致——需要修正注释或修正 SQL"。

**检查 2：双源验证通过了吗？**

重要 SQL（含聚合/去重/JOIN/窗口函数）——是否通过双源验证？没有→今天至少补 1 条。打开原始数据——关掉 SQL 窗口——用 pandas 独立实现——跑 `validate_sql_against_pandas()`。通过→标注"已验证"。不通过→标注差异根因（两个实现做了什么不同假设？）。

**检查 3：窗口函数 frame 显式吗？**

搜索 `OVER (`——检查每个窗口函数是否在 `ORDER BY` 之后包含 `ROWS` 或 `RANGE`。裸 ORDER BY → 标注"缺少显式 frame——默认 RANGE——同天多行时静默错误"——补上 `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`。

**检查 4：EXPLAIN 注释存在吗？**

复杂 SQL（≥ 3 层 CTE 或含 JOIN 或含子查询）——上方是否有 EXPLAIN 注释块？没有→跑 EXPLAIN——把 type/rows/总成本/当前耗时/数据量增长预估写入注释。特别是 `type=ALL` 的地方——必须标注优化方案。

**检查 5：错题模式 ≥ 3 条吗？**

打开 `docs/sql_mistakes.md`——是否有 ≥ 3 条模式？不够→打开 GitHub Issues——SQL 标签——找出同类错误——提炼模式——写入——每条含 6 字段。

### 审计完成后——三件事：

**1. 在鲜果多 README 中加"SQL 代码规范"章节——列出这五条标准——新同事写 SQL 前先读这五条。**

不是"建议"——是"写入代码前必须确认的清单"。每一条不是"你觉得好不好"——是"你验证了吗"。

```markdown
## SQL 代码规范（5 条——写入代码前必须逐项确认）

1. CTE 每层第一行注释: "粒度: 一行 = xxx"——不写粒度=让接手的人脑内编译 GROUP BY
2. 关键 SQL 必须双源验证(pandas 独立实现)——不是翻译——是独立思路——差异记录"两个实现的不同假设"
3. 窗口函数含 ORDER BY 必须含显式 ROWS 或 RANGE——不依赖任何数据库的默认
4. 复杂 SQL(≥3 层 CTE/含 JOIN/含子查询)上方含 EXPLAIN 注释块——type/rows/耗时/优化方案——给未来自己的性能上下文
5. sql_mistakes.md 包含 ≥5 条模式——每条含触发条件/根因/防御规则——新同事接手时先读完再写 SQL

违反以上任一条的 SQL 不允许合并到主分支。
```

**2. 更新 `Makefile`——加一个 `sql-review` target。**

不是"手动 grep"——是"make sql-review 一键检查"。手动 grep 你会忘——Makefile 不会。

```makefile
# SQL Code Review——自动检查 5 条工程规范
sql-review:
	@echo "=== SQL Engineering Review ==="
	@echo ""
	@echo "1. CTE 是否含粒度声明?"
	@grep -rn "WITH" src/sql/ --include="*.sql" -l | while read f; do \
		echo "  $$f: $$(grep -c '粒度' "$$f" || echo 0) 条粒度声明"; \
	done
	@echo ""
	@echo "2. 窗口函数是否显式指定 ROWS/RANGE?"
	@grep -rn "OVER (" src/sql/ --include="*.sql" | grep -v "ROWS\|RANGE" | grep "ORDER BY" || echo "  ✅ 所有窗口函数显式指定了 frame"
	@echo ""
	@echo "3. NOT IN 是否含 NULL 处理?"
	@grep -rn "NOT IN" src/sql/ --include="*.sql" | grep -v "IS NOT NULL\|NOT NULL" || echo "  ✅ 所有 NOT IN 含 NULL 处理或已确认安全"
	@echo ""
	@echo "4. 复杂 SQL 是否含 EXPLAIN 注释?"
	@grep -rn "CTE\|JOIN\|子查询" src/sql/ --include="*.sql" -l | while read f; do \
		grep -q "EXPLAIN\|Seq Scan\|Index Scan" "$$f" || echo "  ⚠️ $$f: 缺少 EXPLAIN 注释"; \
	done
	@echo ""
	@echo "5. sql_mistakes.md 模式数?"
	@grep -c "^### 模式" docs/sql_mistakes.md 2>/dev/null || echo "  ⚠️ docs/sql_mistakes.md 不存在——请创建并录入 ≥5 条模式"
	@echo ""
	@echo "=== Review Complete ==="
```

然后把它加到你的 CI pipeline 中——每次 push 自动跑 `make sql-review`。**如果 CI 红了——不是因为"代码跑不动"——是因为"代码不够工程化"。** 这是一种新的"测试"——不是测"对不对"——是测"好不好维护"。面试时你把这个 make target 展示给面试官——他知道你不是在背"SQL 规范五条"——你把它变成了**自动执行的检查**。这就是工程师和"会写 SQL 的人"之间的差异。

**3. 创建 SQL Code Review Checklist 模板——以后每次 review PR 时直接用：**

```markdown
## SQL Code Review Checklist（每次 PR 审查时逐项打勾）

### CTE 分层注释
- [ ] 每条 CTE 前三行注释含: 做什么 / 粒度 / 为什么(如有设计决策)
- [ ] 粒度声明和 GROUP BY 一致（不一致是 bug——不是"注释错了"就是"SQL 错了"）
- [ ] 子查询嵌套深度 ≤ 2 层（超过→必须用 CTE 重构）

### 双源验证
- [ ] 关键 SQL(含聚合/去重/JOIN/窗口函数)通过双源验证——或标注"差异根因为两个实现做了不同假设——已确认 SQL 的假设是正确口径"
- [ ] 容差设为 0.1%——浮点差异不应触发"验证失败"

### 窗口函数
- [ ] 每个 `OVER (ORDER BY ...)` 显式含 `ROWS` 或 `RANGE`
- [ ] 累计/移动类窗口函数默认用 ROWS——数据分析极少需要 RANGE

### EXPLAIN 注释
- [ ] 复杂 SQL 上方含 EXPLAIN 注释块: type / rows / 总成本 / 当前耗时 / 数据量增长预估 / 优化方案
- [ ] `type=ALL` 的地方必须标注优化方案（建什么索引/加什么分区）

### 错题防控
- [ ] NOT IN 子查询确保无 NULL——或改用 NOT EXISTS
- [ ] LEFT JOIN + 右表 WHERE——确认条件在 ON 还是 WHERE（是否故意的）
- [ ] COUNT(column)——确认 column 的 NULL 含义——是否应该用 COUNT(*)
- [ ] JOIN ON 两边列类型一致——不一致在建表/ETL 层面统一

### 命名
- [ ] CTE 名有意义（不是 a/b/c）
- [ ] 列别名有意义（不是 col1/col2）
```

`git commit -m "W9 audit: all SQL passes 5-point engineering review —— CTE annotated, dual-verified, window frames explicit, EXPLAIN documented, mistake patterns archived"`


## D7（周日 9/28）：W9 审计——闭卷 SQL 工程规范 + 模拟面试三问 + 完整答案分析

### 📝 闭卷自测——三道题，每道都要能闭卷回答

**Q1**：SQL CTE 分层注释的"每层三要素"是哪三个？为什么"粒度"是这三要素中最有价值也最容易被忽略的？新同事接手你的 SQL——没有粒度注释和有粒度注释——理解时间的差异是多少？

> **参考答案**
>
> 三要素：**做什么**（一句话——不是翻译 SQL 语法——是"这个中间结果是什么，给谁用的"）、**粒度**（一行代表什么——SQL 中最难追溯的信息——必须从 GROUP BY 子句推导）、**为什么**（关键设计决策——DISTINCT/LEFT JOIN/过滤条件放在这一层而不是上层——的原因）。
>
> 粒度最有价值——因为它是 SQL 代码中**唯一不能从语法直接读出的信息**。任何其他信息（列名、数据类型、聚合函数）都能从代码中直接看到。唯独"一行代表什么"——你需要从 GROUP BY 子句反向推导——这是"编译原理"不是"代码阅读"——大脑的负担完全不同。
>
> 没有粒度注释：新同事看 `GROUP BY user_id, DATE_TRUNC('month', order_date)`——需要在脑中将 SQL 语法翻译为"一行 = 一个用户在一个自然月"——约 20-30 秒（如果 SQL 很长——需要向上翻到 GROUP BY——可能打断阅读流——重新定位——再来 10 秒）。有粒度注释：读注释第一行——3 秒。**差距约 10 倍。**
>
> **常见偏差**：说"三要素是做什么、怎么做、为什么"——"怎么做"是代码本身的内容——不是注释的职责。注释不应该翻译代码——注释应该补充代码不能表达的信息（粒度、设计决策）。

**Q2**：双源验证的"三步"是哪三步？每一步发现的问题根因分别是什么？为什么"翻译 SQL→pandas"不叫双源验证？面试官如果追问"你做的双源验证和直接把 SQL 翻译成 pandas 有什么区别"——你怎么回答？

> **参考答案**
>
> 三步：**行覆盖**（外连接——找出"只在一边存在"的行）→**列对齐**（两边列名是否一致）→**数值容差**（浮点精度差异不应算失败）。
>
> 每步定位不同根因：行覆盖→口径差异（WHERE 条件/去重逻辑不一样——一个排除退款一个没排除）。列对齐→字段映射不一致（列名拼写/大小写）。数值容差→浮点精度/NULL 处理/聚合顺序差异。
>
> "翻译"不叫双源验证——因为翻译时你看着 SQL 逻辑用 pandas 语法"翻译"——你已经在脑中复制了 SQL 的假设。SQL 里假设了"status 只有英文 cancelled"——你翻译到 pandas 时也写了 `df['status'] == 'cancelled'`——你复制了同一个 bug。**两个实现共享同一个假设——即使假设是错的——两个实现都错得一样——验证会通过——但结论是错的。**
>
> 独立验证 = 关掉 SQL 窗口——只看着业务需求（"计算 GMV——排除取消和退款订单"）——用 pandas 从零实现。你不会复制 SQL 的假设——因为你根本看不到它们。你只会根据业务需求做出自己的判断——如果你的判断和 SQL 作者的判断不同（如你对"退款"的理解是 `status=='refunded'` 而 SQL 作者用了 `status='cancelled'`——英文混中文的逻辑）——这个差异会被双源验证发现——这就是独立验证的价值。
>
> **常见偏差**：说"翻译也有价值——至少验证了语法正确"——语法正确不是你关心的——业务逻辑正确才是。翻译验证的是"我有没有抄错"——独立验证验证的是"我的假设本身有没有错"。

**Q3**：`ROWS` 和 `RANGE` 在数据分析场景中——当 ORDER BY 列有重复值时——累计值的行为差异是什么？为什么不能依赖数据库的默认行为？如果你在面试中给面试官展示你写的 SQL——他问"你为什么这里写了 ROWS"——你怎么回答？

> **参考答案**
>
> ROWS：逐物理行累计——第 1 行→第 2 行→第 3 行——各自独立。RANGE：同值同组——ORDER BY 列值相同的所有行被视为同一逻辑行——一起处理。
>
> 同一天 3 个订单（金额 100/200/300）——ROWS 累计：100→300→600——RANGE 累计：三个都是 600。差异：RANGE 不是"算错了"——是它对"当前行"的定义和你的预期不同——它把三行视为一行。
>
> 不能依赖默认——因为 PostgreSQL/MySQL/SQL Server 默认 RANGE——Hive 默认 ROWS——同一个 SQL 跨数据库迁移——行为静默改变。而且数据分析场景 99% 需要 ROWS——"通用默认"不等于"你的场景的合理默认"。
>
> 面试回答："我显式写 ROWS 有两个原因。第一——SQL 默认 RANGE 在数据分析场景中几乎总是错误的——同一天多行数据会被错误地批量处理。第二——PostgreSQL 和 Hive 的默认不同——我不希望我的 SQL 在跨平台迁移时静默改变行为。显式写 ROWS 不是'更规范'——是'防止默认依赖 bug'。我在我的所有窗口函数上都强制执行这条规则——code review 时搜索 `OVER (` 检查是否含 ROWS/RANGE。"

**Q4**：EXPLAIN 的 type=ALL 和 type=index 有什么区别？为什么看到 type=ALL 必须标注优化方案？如果你面试时被要求现场分析一条慢查询——你会从哪三个字段入手？

> **参考答案**
>
> type=ALL = 全表扫描——每一行都读了——没有用任何索引。type=index = 全索引扫描——读了整个索引树而不是整个表——在索引包含所需全部列时比 ALL 快——但仍然扫描了整个索引——数据量大时同样不可接受。两者的区别：ALL 读的是数据文件（行数据）——index 读的是索引文件（只含索引列）——index 通常比 ALL 快但仍在"全扫描"类别——不是"点查"。
>
> 看到 type=ALL 必须标注优化方案——因为全表扫描的时间随数据量线性增长。10 万行时 0.8s 的查询——1000 万行时 80s。不标注优化方案 = 给未来的自己埋了一个"定时炸弹"——当数据量增长时静默变慢——没有人知道"曾经它很快"——因为 EXPLAIN 注释没有留下来。
>
> 现场分析慢查询从三个字段入手：**type**（访问方式——是不是 ALL）、**rows**（预估扫描行数——和实际数据量对比——差距 > 10 倍=统计信息过期）、**Extra**（额外信息——Using temporary / Using filesort 表示需要建索引）。这三个字段能定位 80% 的慢查询根因——不需要深入看执行计划的每一个节点。
>
> **常见偏差**：说"type=ALL 一定要优化"——不全对。如果表只有几百行（如配置表）——全表扫描比索引更快——因为索引需要两次 IO（索引→数据文件）——全表扫描只需要一次。区分的关键是 rows——扫描行数少=全表扫描可接受——扫描行数多=必须优化。

**Q5**：你现在在鲜果多维护着 2000 行 SQL。三个月后你离职了——新同事接手。你留下的"SQL 工程规范体系"包括哪五个部分？每个部分解决了新同事的什么问题？如果只给你 60 秒向新同事解释这个体系——你说什么？

> **参考答案**
>
> 五个部分：**CTE 分层注释**（新同事 3 分钟理解全貌而不是 30 分钟逐层推导）→**双源验证**（新同事不用"信任你的 SQL"——他可以直接跑验证——两个独立实现一致=可以信任）→**窗口函数显式 frame**（新同事不会因为"不知道默认行为"而静默算错——ROWS 写在那——行为确定）→**EXPLAIN 注释**（新同事知道"在数据量 X 时耗时 Y 是正常的"——不会因为慢而花一下午排查"是不是代码有问题"）→**错题模式归档**（新同事在写 SQL 前读完 5 条模式——你的坑他不会重踩——不是"经验传承"——是"防御规则标准化"）。
>
> 60 秒解释："这份代码库里每条复杂 SQL 上方都有分层注释——先读注释再读代码——注释告诉你每层产出什么。重要 SQL 我都做了双源验证——SQL 结果和 pandas 独立计算结果一致——你可以信任。所有窗口函数显式写了 ROWS——不会有隐含的 RANGE 默认行为坑。慢查询的 EXPLAIN 分析我写在注释里了——数据量增长后你知道在哪加索引。我踩过的 SQL 坑提炼成了 5 条防御规则——在 docs/sql_mistakes.md——写完新 SQL 后对着检查——我的坑你不会再踩。"
>
> **常见偏差**：说"代码有注释"——不够。注释是"点"——体系是"面"。新同事不需要"自己翻代码找注释"——他需要"知道从哪开始、按什么顺序看、每个部分解决什么问题"。你的体系是他接手项目的"用户手册"——不是"代码注释的合集"。

### 🔧 本周补漏

- **3/3** 正确：W9 过关——SQL 工程规范的五个维度你都理解了——不是"背过了"——是理解了"为什么"——能从"为什么"推导出"怎么做"
- **1-2/3** 正确：重读写错的题对应的 D 天——重新做一次动手练习——这次"先写注释再写 SQL"（D1）/ "关掉 SQL 窗口独立实现"（D2）/ "亲手跑 ROWS vs RANGE 对比实验"（D3）
- **0/3** 正确：回到 D1——重写 CTE 注释——这是 SQL 工程化的地基。然后顺着 D2→D3→D4→D5 重做——每一道动手练习不可跳过——因为这些练习是"理解"和"知道"之间的桥梁

---

> 📌 W9 完成。现在你写的每一条复杂 SQL——都有 CTE 分层注释（含粒度声明——别人不需要从 GROUP BY 推导）、都经过双源验证（不是翻译——是独立实现——两个独立思路得到相同结论）、窗口函数都显式指定了 ROWS（不会因为默认 RANGE 静默出错）、EXPLAIN 分析留在了注释里（给自己和新同事留下了性能上下文）、踩过的每个坑都提炼成了可迁移的防御规则（不只是"这次注意"——是"以后类似场景自动防住"）。这不是"SQL 写得更好看了"——这是"SQL 的维护成本从小时级降到了秒级——信任成本从'我需要验证你的 SQL'降到了'你的 SQL 自带验证'"。