# W29：SQL 面试冲刺（2/9 — 2/15）

> 🎯 **本周目标**：SQL 面试不是"再刷一遍题"——是你已经刷过 200+ 题的基础上（W1-W28 的主课学习），用工程化思维重新组织你的 SQL 知识——窗口函数模板化、错题模式回顾、代码审查体系化。学完这周，面试官让你手写 SQL——你不是回忆题型，是调用模板。
>
> 📎 **本周主课**：SQL 面试冲刺——面试 SQL/连续登录/留存/漏斗/Gap/递归
>
> 🏢 **本周场景**：你在面试。面试官在白板上写了一个业务场景——"计算每个用户连续活跃的最大天数"。你的手开始写 CTE。不是因为这道题你刷过——是因为你的大脑里有一个模板，你知道这类问题统一用 `ROW_NUMBER() - dense_rank` 差值法。

---

## D1（周一 2/9）：SQL 代码审查——用 git log 回顾你的 SQL 进化


---

---

### SQL 面试自我介绍——三段式进化——30 秒版

面试官:"你写了多久 SQL——你的 SQL 水平怎么样？"

> "7 个月——我的 SQL 经历了三个阶段的进化——你可以在我的 GitHub commit history 中看到。第一阶段(W3-W5)——子查询嵌套——能用就行。第二阶段(W9)——CTE 分层注释标准——每层标注粒度。第三阶段(W12 以后)——EXPLAIN 注释+数据质量验证+双源验证——每条 SQL 上方有性能分析和验证逻辑。你可以在我的 src/sql/ 目录看到现在的风格。"

面试官追问——CTE 分层注释举例: "比如 GMV 计算 SQL——我分三层 CTE——cleaned_orders(清洗层——粒度:一行=一个有效订单)、user_monthly(聚合层——粒度:一行=一个用户在一个月)、city_monthly(输出层——粒度:一行=一个城市在一个月)。每层第一行注释写粒度——这是 SQL 中最难追溯的信息——有了粒度注释——接手的人不需要从 GROUP BY 推导——读注释 3 秒就知道每层产出什么。"

用 git log 搜索 SQL 进化: git log --oneline --grep="SQL"——git log --oneline --all -- src/sql/——git diff <W3commit> <W12commit> -- src/sql/——这些命令能展示你的 SQL 风格的确实化了——面试时如果有屏幕共享——直接展示 diff——比口头描述有力 10 倍。


---

---

### SQL 面试自我介绍——三段式——30 秒版

**面试官:"你写了多久 SQL——你的 SQL 水平怎么样？"**

**你的回答:**

> "我写了 7 个月 SQL——我的 SQL 风格经历了三个阶段的进化——你可以在我的 GitHub commit history 中看到。第一阶段(W3-W5)——子查询嵌套——能用就行——'让 SQL 跑通'。第二阶段(W9)——CTE 分层注释标准——每层标注粒度——'让 SQL 能被读懂'。第三阶段(W12 以后)——EXPLAIN 注释+数据质量验证+双源验证——'让 SQL 能被信任'。你可以在我的 src/sql/ 目录看到现在的风格——每条复杂 SQL 上方有 CTE 分层注释、性能分析、数据验证逻辑。"

**面试官追问:"CTE 分层注释——能举个例子吗？"**

> "比如一条 GMV 计算 SQL——我分成三层 CTE——cleaned_orders(清洗层——粒度:一行=一个有效订单)、user_monthly(聚合层——粒度:一行=一个用户在一个月)、city_monthly(输出层——粒度:一行=一个城市在一个月)。每层第一行注释写'粒度:一行=xxx'——这是 SQL 中最难追溯的信息——有了粒度注释——接手的人不需要从 GROUP BY 子句反向推导——读注释 3 秒就知道每层产出什么。"

> 📓 今日主课：SQL 面试——面试 SQL 六大模式

---

### 🔴 认知冲突

面试官问"你写了多久 SQL？"——你说"7 个月"——然后面试官追问"你的 SQL 在这 7 个月里有什么变化？"

如果你只能回答"更熟练了"——这等于没答。你应该能说："我 W3 时候的 SQL 是子查询套子查询——你可以在我的 git log 里看到。W9 之后我统一用 CTE 分层注释标准——你可以看到从 commit abc123 开始我的 SQL 风格变了。"

**问题**：Git 不只是代码的版本控制——它是你学习过程的档案。怎么用 `git log` 找到你的"成长节点"？

---

### 📖 核心原理

**用 `git log` 搜索你的 SQL 进化：**

```bash
# 找到所有和 SQL 相关的 commit
git log --oneline --grep="SQL"

# 找到你第一次用 CTE 的 commit（W9D1）
git log --oneline --all -- src/sql/

# 对比 W3 的 SQL（子查询嵌套）和 W12 的 SQL（CTE 分层）——差异化在你的 git history 里是可见的
git diff <W3的commit> <W12的commit> -- src/sql/
```

**面试回答模板**（30 秒）：
> "我写了 7 个月 SQL。我的 SQL 风格经历了三个阶段的进化——你可以在我的 GitHub commit history 中看到。第一阶段（W3-W5）是能用就行——子查询套子查询。第二阶段（W9）开始用 CTE 分层注释标准——每层标注粒度。第三阶段（W12 以后）加入了 EXPLAIN 注释和数据质量验证——每行 SQL 上方有性能分析和数据验证逻辑。你可以在我的 `src/sql/` 目录看到现在的风格。"

---

### ✍️ 动手练习

1. 跑 `git log --oneline --all -- src/sql/`——列出你 SQL 相关的 commit 历史。
2. 找到至少 3 个"风格变化"节点——每个节点标注你当时学了什么导致风格变化。
3. 在个人笔记里写"我的 SQL 面试自我介绍"——含三段式演进。

---

## D2（周二 2/10）：窗口函数——闭卷写出 6 种模板


---

---

### 6 种窗口函数模板——完整代码 + 面试要点

**模板 1: 排名——ROW_NUMBER vs RANK vs DENSE_RANK**

```sql
SELECT user_id, order_date, amount,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date) AS rn,
       RANK()       OVER (PARTITION BY user_id ORDER BY amount DESC) AS rank_val,
       DENSE_RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) AS dense_val
FROM orders;
-- 关键: ROW_NUMBER 无并列——每行唯一序号。RANK 有并列——跳号(1,2,2,4)。DENSE_RANK 有并列——不跳号(1,2,2,3)
```

**模板 2: 连续——差值法（Gap-and-Island）**

```sql
WITH numbered AS (
    SELECT user_id, login_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM logins
),
grouped AS (
    SELECT user_id, login_date,
           login_date - rn * INTERVAL '1 day' AS grp
    FROM numbered
)
SELECT user_id, MIN(login_date) AS start_date, MAX(login_date) AS end_date,
       COUNT(*) AS consecutive_days
FROM grouped
GROUP BY user_id, grp
HAVING COUNT(*) >= 3  -- 至少连续 3 天
ORDER BY consecutive_days DESC;
-- 面试要点: 能解释"为什么 date - rn 恒定 = 连续"——不能只背代码
```

**模板 3: 移动平均——ROWS 必须显式写**

```sql
SELECT order_date, amount,
       AVG(amount) OVER (ORDER BY order_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7d
FROM daily_sales;
-- 关键: ROWS 显式写——默认是 RANGE——数据缺失日期时行为不同
-- ROWS: 物理行——最近 7 行。RANGE: 逻辑值——最近 7 天(可能只有 3 行)
```

**模板 4: 累计——ROWS UNBOUNDED PRECEDING**

```sql
SELECT user_id, order_date, amount,
       SUM(amount) OVER (PARTITION BY user_id ORDER BY order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumsum
FROM orders;
-- 面试追问: "为什么显式写 ROWS——不写会怎样？"
-- A: SQL 默认 RANGE——同天多订单时累计值全相同——数据分析师几乎总要 ROWS
```

**模板 5: 前后比较——LAG/LEAD**

```sql
SELECT user_id, order_date, amount,
       LAG(amount, 1, 0) OVER (PARTITION BY user_id ORDER BY order_date) AS prev_amount,
       amount - LAG(amount, 1) OVER (PARTITION BY user_id ORDER BY order_date) AS diff,
       LEAD(amount, 1) OVER (PARTITION BY user_id ORDER BY order_date) AS next_amount
FROM orders;
-- LAG(column, offset, default)——第三个参数是默认值——不指定则第一行返回 NULL
```

**模板 6: 占比——ratio_to_report**

```sql
SELECT city, SUM(amount) AS city_gmv,
       SUM(amount) * 100.0 / SUM(SUM(amount)) OVER () AS pct_of_total,
       SUM(amount) * 100.0 / SUM(SUM(amount)) OVER (PARTITION BY DATE_TRUNC('month', order_date)) AS pct_of_month
FROM orders
GROUP BY city, DATE_TRUNC('month', order_date);
-- 面试要点: SUM(SUM(amount)) OVER ()——窗口函数和 GROUP BY 的嵌套——面试高频
```

> 📓 今日主课：窗口函数面试——ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD/SUM OVER

---

### 📖 核心原理

**窗口函数不是"背语法"——是"6 种问题模式 + 6 种解法模板"。**

| 模式 | 一句话问题 | 模板 | 常见陷阱 |
|------|----------|------|---------|
| **排名** | "每个分组里排第几？" | `ROW_NUMBER() OVER (PARTITION BY X ORDER BY Y)` | RANK vs DENSE_RANK——有并列时行为不同 |
| **连续** | "最大的连续天数？" | `date - ROW_NUMBER()` 差值法 | 别忘了按 user_id 分区 |
| **移动平均** | "最近 N 天的平均值？" | `AVG() OVER (ROWS N-1 PRECEDING)` | 必须显式写 ROWS——默认是 RANGE |
| **累计** | "截至当天的累计值？" | `SUM() OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)` | 同日期多行时 ROWS vs RANGE 行为不同 |
| **前后比较** | "今天和昨天比？" | `LAG(col, 1) OVER (PARTITION BY X ORDER BY date)` | LAG 默认值——不指定则第一行返回 NULL |
| **占比** | "这个值在分组里占百分之几？" | `col / SUM(col) OVER (PARTITION BY X)` | 分母为 0 |

**每个模板——你能闭卷写出来吗？** 今天的目标——6 个模板每个闭卷手写一遍。

---

### ✍️ 动手练习

1. 闭卷——不看任何参考资料——手写 6 个窗口函数模板（每个 3-5 行 SQL）。
2. 对照你的笔记检查——每个模板的常见陷阱都写对了吗？
3. 在 `docs/sql_templates.md` 中整理成速查表——面试前一天看这页就够了。

---

## D3（周三 2/11）：Gap-and-Island + 连续登录——面试最高频题型


---

---

### 连续登录变体训练——面试官可能怎么换皮

面试官不会直接说"写一个连续登录的 SQL"——会换皮:

**变体 1:** "找出连续 7 天都有消费的用户。"——解法:把 login_date 换成 order_date——WHERE amount>0——完全相同。

**变体 2:** "找出连续签到超过 30 天的用户。"——解法:把 login_date 换成 checkin_date——逻辑完全相同。

**变体 3:** "找出连续 3 个月 GMV 增长的用户。"——解法:先用 LAG 比较本月和上月——如果增长则标记为 1——然后对标记做差值法。

**变体 4:** "找出 GMV 连续 5 天超过 100 万的日期段。"——解法:WHERE amount>1000000——然后对满足条件的日期做差值法。

面试官追问——同天多条记录会不会有问题: "会！同天多条登录——ROW_NUMBER 为同一天生成不同 rn——差值法失效。解法——最内层加 DISTINCT——SELECT DISTINCT user_id, login_date FROM logins——确保每用户每天只有一行。这就是为什么生产级 SQL 的 CTE 第一层通常是去重——面试时如果你能主动说出这个局限——面试官会加分。"


---

---

### 连续登录——完整面试演练——从手写 SQL 到解释原理到变体

**面试官:"写一个 SQL——计算每个用户连续活跃的最大天数。"**

**你的手写 SQL(闭卷):**

```sql
WITH numbered AS (
    SELECT user_id, login_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM logins
),
grouped AS (
    SELECT user_id, login_date,
           login_date - rn * INTERVAL '1 day' AS grp
    FROM numbered
),
consecutive AS (
    SELECT user_id, grp, COUNT(*) AS days,
           MIN(login_date) AS start_date, MAX(login_date) AS end_date
    FROM grouped
    GROUP BY user_id, grp
)
SELECT user_id, MAX(days) AS max_consecutive_days
FROM consecutive
GROUP BY user_id
ORDER BY max_consecutive_days DESC;
```

**面试官追问:"为什么差值法有效——用自己的话解释。"**

> "如果登录日期是连续的——比如 1 号、2 号、3 号——ROW_NUMBER 也是 1、2、3——date - rn = 12月31号——三行的差值相同——聚合后属于同一组。如果日期断开——比如 1 号、2 号、5 号——ROW_NUMBER 是 1、2、3——date - rn 分别是 12月31号、12月31号、1月2号——不再是同一个值——自然形成新的分组。差值法把'连续'这个逻辑概念——转化成了'差值的相等性'——SQL 的 GROUP BY 就能处理了。"

**面试官追问:"这个 SQL 有什么局限——如果用户一天登录了两次——会不会有问题？"**

> "会！如果有同一天多条登录记录——ROW_NUMBER 会为同一天生成不同的 rn——差值法失效——同一用户被错误地拆成了多个'连续段'。解法——在最内层加 DISTINCT——`SELECT DISTINCT user_id, login_date FROM logins`——确保每个用户每天只有一行。这就是为什么生产级 SQL 的 CTE 第一层通常是去重。"

**变体 1——连续消费(amount>0 替代 login):** 把 login_date 改成 order_date——加 WHERE amount > 0——逻辑完全相同。

**变体 2——连续活跃 >= 7 天:** 在 consecutive CTE 后加 HAVING COUNT(*) >= 7。

**变体 3——连续增长(GMV 连续 N 天增长):** 用 LAG 比较今天和昨天——不是差值法——是 LAG+条件累积。

> 📓 今日主课：Gap-and-Island——连续登录/连续活跃/连续消费

---

### 📖 核心原理

**连续登录 = 所有面试题里出现频率最高的窗口函数题。核心公式——差值法：**

```sql
-- 连续登录天数
WITH numbered AS (
    SELECT user_id, login_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM logins
),
grouped AS (
    SELECT user_id, login_date,
           login_date - CAST(rn AS INTERVAL) AS grp_date  -- 连续的日期会落入同一组
    FROM numbered
)
SELECT user_id, COUNT(*) AS consecutive_days
FROM grouped
GROUP BY user_id, grp_date
ORDER BY consecutive_days DESC
LIMIT 1;
```

**为什么差值法有效？** 如果日期是连续的（1号、2号、3号）——ROW_NUMBER 也是连续的（1、2、3）——差值 `date - rn` 恒定。一旦日期断开（1号、2号、5号）——rn 仍然是 1、2、3——但 `date - rn` 不再恒定——自然形成了新的分组。

---

### ✍️ 动手练习

1. 闭卷手写连续登录 SQL。
2. 在注释里解释"为什么差值法有效"——用你自己的话，不是背的。
3. 变体：连续消费（`amount > 0` 替换 `login`）、连续活跃 7 天（`HAVING COUNT(*) >= 7`）。

---

## D4（周四 2/12）：ETL 面试——数据清洗/去重/拉链表/SCD


---

---

### ETL 面试——SCD Type2 SQL 版本闭卷

面试官:"写一个 SCD Type2 的 SQL——追踪用户等级变化。"

```sql
WITH today AS (
    SELECT user_id, user_level, CURRENT_DATE AS snapshot_date FROM users
),
yesterday AS (
    SELECT * FROM dim_user_scd WHERE is_current = 1
),
changes AS (
    SELECT
        COALESCE(t.user_id, y.user_id) AS user_id,
        CASE
            WHEN y.user_id IS NULL THEN 'NEW'
            WHEN t.user_id IS NULL THEN 'DELETED'
            WHEN t.user_level != y.user_level THEN 'UPDATED'
            ELSE 'UNCHANGED'
        END AS change_type,
        t.user_level AS new_level, y.user_level AS old_level
    FROM today t
    FULL OUTER JOIN yesterday y ON t.user_id = y.user_id
    WHERE y.user_id IS NULL          -- 新用户
       OR t.user_id IS NULL          -- 消失
       OR t.user_level != y.user_level  -- 有变化
)
SELECT * FROM changes;
```

面试官追问:"四种情况分别怎么处理？"

> "新用户(y IS NULL)——INSERT 新行——start_date=今天——end_date=9999-12-31——is_current=1。无变化(UNCHANGED)——保留昨天的行——不操作。有变化(UPDATED)——UPDATE 旧行(end_date=昨天, is_current=0)——INSERT 新行(start_date=今天, is_current=1)。消失的用户(t IS NULL)——UPDATE 旧行(end_date=昨天, is_current=0)。"

**ETL 面试加分点——主动提数据质量:** "在生产环境中——每个 CTE 后面我会跑一个 COUNT(*) 验证——确认行数在合理范围内。比如——新用户+有变化+消失的用户总数——应该等于'需要更新的行数'。如果对不上——ETL 中途出了问题——告警——不回滚——人工介入。"


---

---

### SCD Type2 的 SQL 实现——闭卷写出

```sql
-- SCD Type2: 用户等级变化的拉链表——闭卷手写
-- 核心逻辑: 今天快照 vs 昨天拉链表(is_current=1) -> 四种情况

WITH today_snapshot AS (
    SELECT user_id, user_level, CURRENT_DATE AS snapshot_date
    FROM users
),
yesterday_scd AS (
    SELECT * FROM dim_user_scd WHERE is_current = 1
)
-- 情况 1: 新用户（今天有——昨天没有）-> INSERT 新行(start_date=今天, end_date=9999-12-31, is_current=1)
-- 情况 2: 无变化（今天和昨天的 user_level 相同）-> 保留昨天的行——不操作
-- 情况 3: 有变化（今天和昨天的 user_level 不同）-> UPDATE 昨天的行(end_date=昨天, is_current=0) + INSERT 新行(start_date=今天, end_date=9999-12-31, is_current=1)
-- 情况 4: 消失的用户（昨天有——今天没有）-> UPDATE 昨天的行(end_date=昨天, is_current=0)

SELECT
    COALESCE(t.user_id, y.user_id) AS user_id,
    CASE
        WHEN y.user_id IS NULL THEN 'NEW'
        WHEN t.user_id IS NULL THEN 'DELETED'
        WHEN t.user_level != y.user_level THEN 'UPDATED'
        ELSE 'UNCHANGED'
    END AS change_type,
    t.user_level AS new_level,
    y.user_level AS old_level
FROM today_snapshot t
FULL OUTER JOIN yesterday_scd y ON t.user_id = y.user_id
WHERE y.user_id IS NULL                          -- 新用户
   OR t.user_id IS NULL                          -- 消失的用户
   OR t.user_level != y.user_level;              -- 有变化的用户
```

**面试时——面试官问"你做过拉链表吗"——你不能只说"做过"——你说——"我用 FULL OUTER JOIN 对比今天的快照和昨天的拉链表——识别四种情况——新用户/无变化/有变化/消失的用户。有变化的用户——关闭旧行(end_date=昨天, is_current=0)——开启新行(start_date=今天, is_current=1)。我的鲜果多项目用 Python 实现过 SCD Type2——如果你要看代码——在 src/data/scd_type2.py。"**

> 📓 今日主课：ETL SQL——去重/拉链表/SCD Type2

---

### 📖 核心原理

**ETL 面试题——不只是"会写 SQL"，是"会写能放在生产环境中跑的 SQL"。**

关键点：
- 去重逻辑写在 CTE 注释里——面试官需要知道你理解"什么算重复"
- SCD Type2 拉链表——W11D4 用 Python 实现了——现在闭卷写出 SQL 版本
- 数据质量——每个 CTE 后面有验证步骤（`COUNT(*)`）

---

### ✍️ 动手练习

1. 闭卷写出 SCD Type2 的 SQL 版本。
2. 在 `docs/sql_templates.md` 中加入 ETL 模板章节。

---

## D5（周五 2/13）：SQL 错题最终回顾——你犯过的每一个错误都是一道面试题


---

---

### SQL 错题库——完整 5 坑 + 防御规则

**面试官:"你踩过什么 SQL 坑——怎么防止再犯？"**

**你的完整回答(含 5 个坑——每个 15 秒):**

> "我踩过 5 个经典 SQL 坑——每个我都在 GitHub 的 SQL 错题库中记录了。(1)NOT IN + NULL——子查询有 NULL 时整查询返回空——解法用 NOT EXISTS。(2)LEFT JOIN + 右表 WHERE——LEFT JOIN 变成 INNER JOIN——解法把条件放在 ON 子句中。(3)窗口函数不带 ROWS——默认 RANGE——同天多行累计值相同——解法显式写 ROWS BETWEEN。(4)COUNT(column) vs COUNT(*)——COUNT(column) 静默排除 NULL——导致行数对不上——解法用 COUNT(*) 或注释说明。(5)隐式类型转换——JOIN ON varchar=integer——索引失效——解法建表时统一类型。"
>
> "我把这 5 个坑写进了我的 SQL Code Review Checklist——每次 review PR 时逐项打勾。另外——我在 CI 中加了自动扫描——grep NOT IN/grep LEFT JOIN.*WHERE——如果有潜在的坑——CI 会警告。工具会忘——checklist+自动化不会。"

**面试官追问:"这些坑你是怎么系统化管理的？"**

> "三重防护。(1)SQL Code Review Checklist——每次 PR review 逐项打勾——5 个坑每个有对应的检查项。(2)CI 自动扫描——grep 搜索 NOT IN/LEFT JOIN.*WHERE/OVER(*ORDER)——如果发现潜在的坑——CI 输出警告——不阻止合并——但提醒 reviewer。(3)错题库(GitHub Issues)——每个坑是一个 Issue——含错误代码/根因/正确写法/防御规则。新同事入职时——先读完这 5 个 Issue——我的坑 TA 不会再踩。"


---

---

### SQL 错题库——面试时脱口而出的 5 个经典坑

**面试官问"你踩过什么 SQL 坑"——你的回答——5 个坑——每个 15 秒——含错误+根因+解法:**

**坑 1: NOT IN + NULL——整查询返回空**

错误: `WHERE user_id NOT IN (SELECT user_id FROM blacklist)`——blacklist 有 NULL->返回空集。
根因: NOT IN = <> ALL——任何值与 NULL 比较 = UNKNOWN——WHERE UNKNOWN 不返回行。
解法: 子查询加 `WHERE user_id IS NOT NULL`——或改用 `NOT EXISTS`。

**坑 2: LEFT JOIN + 右表 WHERE——变成 INNER JOIN**

错误: `LEFT JOIN users ON ... WHERE users.level='VIP'`——无匹配行->users.level=NULL->WHERE 过滤 NULL。
根因: WHERE 在 JOIN 之后执行——LEFT JOIN 为无匹配行生成 NULL——WHERE 条件过滤了 NULL。
解法: 条件放在 ON 子句中——或 `WHERE (users.level='VIP' OR users.level IS NULL)`。

**坑 3: 窗口函数无 ROWS——默认 RANGE——同天累计值全相同**

错误: `SUM() OVER (PARTITION BY user_id ORDER BY order_date)`——不带 ROWS。
根因: SQL 默认 RANGE——同天订单被一起累计。
解法: 显式 `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`。

**坑 4: COUNT(column) vs COUNT(*)——静默的行数差异**

错误: `SELECT COUNT(referral_code) FROM users`——期望统计用户数。
根因: COUNT(column) 不计算 NULL——referral_code 为 NULL 的用户被静默排除。
解法: COUNT(*) 统计行数——或注释说明"此 COUNT 排除了 NULL——这是有意的因为..."

**坑 5: 隐式类型转换——JOIN ON varchar = integer——索引失效**

错误: `JOIN users ON orders.user_id = users.id`——orders.user_id 是 VARCHAR——users.id 是 INTEGER。
根因: MySQL 隐式转换——索引失效->全表扫描。Hive 直接报错或返回空。
解法: 建表时统一类型——或在 ETL 层 CAST。

**面试官听完 5 个坑——追问"你怎么防止这些坑再犯"——你回答——"我把这 5 个坑写进了我的 SQL Code Review Checklist——每次 review PR 时逐项打勾——工具会忘——checklist 不会。"**

> 📓 今日主课：SQL 错题回顾

---

### 📖 核心原理

**打开你的 GitHub Issues（SQL 标签）——这些是你 7 个月踩过的坑。今天一一回顾——确保每个坑你知道为什么错、面试官追问"你踩过什么 SQL 坑"时你能脱口而出 5 个。**

你的回答："我在 GitHub 上维护了一个 SQL 错题知识库——目前有 N 条。面试时如果问到'你踩过什么坑'——我会说 NOT IN + NULL（结果为空）、窗口函数 ROWS vs RANGE（累计值对不上）、LEFT JOIN + WHERE 右表条件（变成了 INNER JOIN）..."

---

### ✍️ 动手练习

1. 打开 GitHub Issues——SQL 标签——有多少条？
2. 每条过一遍——如果某条你看到标题就回忆不起来具体内容——把 Issue 打开重读。

---

## D6（周六 2/14）：周项目——SQL 模拟面试


---

---

### SQL 模拟面试 10 题——闭卷手写——5 分钟/题

**题 1:** 城市 GMV 排名——并列排名相同——不跳号。(DENSE_RANK)

**题 2:** 用户累计消费——按时间排序。(SUM OVER ROWS UNBOUNDED PRECEDING)

**题 3:** 连续登录 >= 7 天。(差值法——ROW_NUMBER + date - rn + GROUP BY + HAVING)

**题 4:** 7 天移动平均 GMV。(AVG OVER ROWS 6 PRECEDING——显式写 ROWS)

**题 5:** 每天 GMV 和前一天差值。(LAG——注意第一行返回 NULL——设默认值)

**题 6:** 每个城市 GMV 占比 > 10%。(SUM OVER / SUM OVER PARTITION——窗口函数嵌套)

**题 7:** SCD Type2——用户等级拉链表。(FULL OUTER JOIN——四种情况——CASE WHEN)

**题 8:** 留存率——Cohort 分析。(自 JOIN——COUNT(DISTINCT)——按注册月分组)

**题 9:** 每用户最高消费订单。(ROW_NUMBER + WHERE rn=1——注意 RANK 会返回多条并列)

**题 10:** 漏斗分析——浏览->加购->下单。(CTE 分层——COUNT DISTINCT——转化率)

评分——10 题——每道 10 分——>= 80 = SQL 面试就绪。不到 80——重练。


---

---

### SQL 模拟面试——10 道高频题——每道闭卷手写 5 分钟

**模拟面试规则:** 白板或纯文本编辑器(无语法高亮)——每道题 5 分钟——超时就停——对答案。

**题 1:** 计算每个城市的 GMV 排名——并列时排名相同——不跳号。(DENSE_RANK)

**题 2:** 计算每个用户的累计消费金额——按时间排序。(SUM OVER ROWS)

**题 3:** 找出连续登录 >= 7 天的用户。(差值法)

**题 4:** 计算每天 GMV 的 7 天移动平均。(AVG OVER ROWS 6 PRECEDING)

**题 5:** 计算每天 GMV 和前一天 GMV 的差值。(LAG)

**题 6:** 找出每个城市 GMV 占比超过 10% 的日期。(SUM OVER / SUM OVER PARTITION)

**题 7:** SCD Type2——用户等级变化拉链表。(FULL OUTER JOIN)

**题 8:** 留存率——每个 cohort 在注册后第 N 天的留存。(自 JOIN + COUNT)

**题 9:** 找出每个用户消费金额最高的一笔订单。(ROW_NUMBER + WHERE rn=1)

**题 10:** 漏斗分析——计算从浏览到加购到下单的转化率。(CTE + COUNT DISTINCT)

**评分——10 题——每道 10 分——>= 80 分 = SQL 面试准备就绪。** 不到 80 分——重练——直到闭卷全对。

找一个朋友（或自己对镜子）——让对方给你出 5 道 SQL 题。在白板（或纯文本编辑器——没有语法高亮）上手写。每道题限时 5 分钟。

---

## D7（周日 2/15）：W29 审计


---

---

### W29 SQL 面试交付物清单

- [ ] docs/sql_templates.md——含 6 个窗口函数模板+连续登录+SCD Type2——每个含面试要点+常见陷阱
- [ ] SQL Code Review Checklist——含 5 个错题模式的防御规则+CI 自动扫描
- [ ] SQL 面试自我介绍——三段式——30 秒——已录音回听——精炼到 <= 30 秒
- [ ] 6 个窗口函数模板——全部闭卷可写——每个模板知道关键陷阱
- [ ] 连续登录 SQL——闭卷可写——能解释"为什么差值法有效"——知道同天多记录的坑
- [ ] SCD Type2——闭卷可写 SQL 版本——四种情况分别处理
- [ ] 5 个 SQL 错题——每个能说清错误/根因/解法/防御规则
- [ ] SQL 模拟面试——10 题——闭卷——>= 80 分

**W29 面试速查卡——30 秒版:**

> "我的 SQL 面试准备涵盖四个核心领域。(1)6 个窗口函数模板——排名/连续/移动平均/累计/前后比较/占比——全部闭卷可写。(2)连续登录——差值法——能闭卷写+解释原理+知道变体和局限。(3)5 个 SQL 经典坑——NOT IN+NULL/LEFT JOIN+WHERE/窗口无ROWS/COUNT陷阱/隐式类型转换——每个有错误/根因/解法/防御规则。(4)我的 SQL 风格经历了三个阶段——子查询嵌套->CTE分层注释->EXPLAIN+数据验证——你可以在我的 GitHub commit history 中看到。"


---

---

### W29 SQL 面试速查卡——全部闭卷可答

**Q1:** 6 个窗口函数模板——全部闭卷可写——每个模板的关键陷阱都知道？

**Q2:** 连续登录 SQL——闭卷可写——能解释"为什么差值法有效"？

> 如果日期连续(1,2,3)——ROW_NUMBER 也是(1,2,3)——date - rn 恒定。一旦日期断开(1,2,5)——rn 仍是(1,2,3)——date - rn 不再恒定——自然形成新分组。

**Q3:** SCD Type2——闭卷可写 SQL 版本——四种情况分别怎么处理？

**Q4:** 能说出 >= 5 个 SQL 错题 + 根因 + 解法？

**Q5:** 面试官问"你的 SQL 在 7 个月里有什么变化"——你的三段式回答？

> 第一阶段(W3-W5): 子查询嵌套——能用就行。第二阶段(W9): CTE 分层注释——每层标注粒度。第三阶段(W12+): EXPLAIN 注释+数据质量验证——每行 SQL 上方有性能分析和验证逻辑。你可以在我的 GitHub commit history 中看到这三个阶段。

### W29 工程化交付物清单

- [ ] docs/sql_templates.md——含 6 个窗口函数模板 + 连续登录 + SCD Type2——每个含面试要点
- [ ] SQL Code Review Checklist——含 5 个错题模式的防御规则
- [ ] SQL 面试自我介绍——三段式——30 秒——已录音回听

- 6 个窗口函数模板——全部闭卷可写？
- 连续登录——闭卷可写并解释原理？
- SCD Type2——闭卷可写 SQL 版本？
- 能说出 ≥ 5 个 SQL 错题 + 根因？
