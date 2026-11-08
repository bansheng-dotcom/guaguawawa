# 04 用户RFM分群

---

## 一、白话理解

### 社区团购需要一个"用户分层模型"

你有2.7万个下单用户——不可能每个人都一视同仁。你需要知道：
- 谁是**高价值用户**（多给优惠券，别让他跑了）
- 谁是**流失风险**（赶紧发push/优惠券拉回来）
- 谁是**高频低价值**（只买引流品薅羊毛的）

RFM就是最经典的答案：

| 维度 | 含义 | 社区团购的对应 |
|------|------|--------------|
| **R**ecency | 最近一次购买距现在多久？ | 昨天买过=高粘性；7天没买=可能跑了 |
| **F**requency | 买了多少次？ | 30天内下单10次=每日采买型用户 |
| **M**onetary | 花了多少钱？ | 总消费200元 vs 20元 |

**社区团购的RFM跟电商不一样：** 团购是高频低客单价（每天买菜），所以R的阈值更短（3-7天而非电商的30天）、F的阈值更高（≥8次而非≥4次）。

### 一个直观例子

```
用户A: 昨天买过(R=1天) + 买了10次(F=10) + 花了250元(M=250) → 高价值用户
用户B: 14天没买(R=14天) + 买了1次(F=1) + 花了15元(M=15) → 流失风险
```

用户A下次打开APP应该看到专属优惠券。用户B应该收到push"你常买的西红柿今天特价！"

---

## 二、SQL拆解

打开 [run_all.py](../run_all.py)，找到 `analysis_03_rfm`。这个SQL比较长，分3个CTE：

### CTE 1: user_rfm — 计算每个用户的R/F/M原始值

```sql
WITH user_rfm AS (
    SELECT
        o.user_id,
        julianday('2025-07-01') - julianday(MAX(o.order_date)) as recency_days,
        COUNT(DISTINCT o.order_id) as frequency,
        ROUND(SUM(o.total_amount), 2) as monetary,
        COUNT(DISTINCT o.order_date) as active_days
    FROM orders o
    GROUP BY o.user_id
)
```

**julianday()** 是SQLite的日期函数，返回"从公元前4714年11月24日以来经过的天数"。两个日期相减 = 相隔天数。在其他SQL方言中：
- MySQL: `DATEDIFF('2025-07-01', MAX(order_date))`
- PostgreSQL: `'2025-07-01'::date - MAX(order_date)::date`

### CTE 2: rfm_scored — 把R/F/M值转成1-4分

```sql
CASE WHEN recency_days <= 3 THEN 4   -- 3天内买的=最高R分
     WHEN recency_days <= 7 THEN 3
     WHEN recency_days <= 14 THEN 2
     ELSE 1 END as r_score,

CASE WHEN frequency >= 8 THEN 4      -- 买了8次以上=最高F分
     WHEN frequency >= 4 THEN 3
     WHEN frequency >= 2 THEN 2
     ELSE 1 END as f_score,

CASE WHEN monetary >= 200 THEN 4     -- 花了200以上=最高M分
     WHEN monetary >= 100 THEN 3
     WHEN monetary >= 50 THEN 2
     ELSE 1 END as m_score
```

**阈值怎么定？** 看数据的分位数来确定——不是拍脑袋。代码中用分位数来设定阈值（比如R得分4对应最近3天内购买，这应该对应Top 25%的用户）。

### CTE 3: rfm_segments — 基于R/F/M分数组合定义分层

```sql
CASE
    WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN '高价值用户'
    WHEN r_score >= 3 AND f_score >= 2 THEN '活跃用户'
    WHEN r_score >= 2 AND f_score >= 2 THEN '潜力用户'
    WHEN r_score <= 2 AND f_score <= 2 THEN '流失风险'
    WHEN f_score >= 3 THEN '高频率低价值'
    ELSE '低价值用户'
END as segment
```

**为什么不直接用R+F+M总分？** 因为一个R=4(最近买过)但F=1(只买了一次)的用户和一个R=1但F=4的用户，总分相同但行为完全不同。用CASE WHEN可以定义"有意义的组合"而非机械求和。

---

## 三、输出解读

```
segment      user_count  avg_recency  avg_frequency  avg_monetary
高价值用户        1,388          4.2            4.9        138.59
活跃用户          8,178          4.3            2.9         58.97
高频率低价值        321         17.5            4.2         95.92
潜力用户          6,004         10.7            2.9         63.36
低价值用户        1,442          4.5            1.0         22.39
流失风险          9,564         19.2            1.5         32.90
```

**关键洞察：**
- **流失风险35.6%** — 超过1/3的用户处于流失边缘！平均19天没买过。**需要运营介入**（push推送/优惠券/爆品提醒）
- **高价值用户仅5.2%** — 贡献了最多的GMV，需要重点维护（专属客服群？提前内测新功能？）
- **高频率低价值**（321人）— 买了频繁（F=4.2）但消费金额不高（M=96）。可能是"薅羊毛型"用户——只买引流品和特价品。

---

## 四、面试怎么讲

**面试官："怎么做用户分层？"**

> "我用RFM模型。在社区团购场景下，RFM的阈值跟电商不一样——团购高频低客单价，所以R的阈值按天算（≤3天是最高分，≤7天其次），F的阈值比电商高（≥8单是最高分）。
>
> 我的做法是三步：第一，从订单表聚合每个用户的R(最近购买天数)、F(订单数)、M(消费总额)；第二，根据分位数把R/F/M分成1-4分；第三，用CASE WHEN定义5-6个分层——比如高价值(R≥3,F≥3,M≥3)、流失风险(R≤2,F≤2)、高频率低价值(F≥3但消费不高)。
>
> 在美团优选的分析中，分层结果：5%高价值用户、30%活跃用户、35%流失风险——这个35%是我们的重点召回对象。"

---

## 五、动手练习

1. 修改R/F/M的分数阈值（比如recency从3/7/14改成2/5/10），看分层结果怎么变
2. 加入城市等级维度——一线城市的"高价值用户"占比更高吗？
3. 写SQL找出"流失风险"用户里客单价最高的100个人——这些是曾经花过钱但现在不来了的，最值得召回

---

[← 上一篇: 03 漏斗分析](03-漏斗分析.md) | [下一篇: 05 留存复购 →](05-留存复购.md)
