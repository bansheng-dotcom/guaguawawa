# W10：Hive 与大数据工程（9/29 — 10/5）

> 🎯 **本周目标**：大数据和小数据的工程差异不是"Hive 语法和 MySQL 不太一样"。它们是两种完全不同的设计哲学——OLAP vs OLTP、Schema on Read vs Schema on Write、分布式文件 vs B+Tree、分区（目录跳过）vs 索引（B+Tree 查找）。学完这周，你能解释"为什么相同的 SQL 在 Hive 上要写成不同的风格"、理解分区裁剪的本质（不是索引查找——是目录跳过——在 SQL 编译阶段就知道哪些目录不需要读）、用 Python 模拟 Shuffle 过程理解数据倾斜的根因（不只是"加盐"——是理解为什么 hash 分配导致了负载不均）。本周还有一个硬性工程任务——全项目命名审计——消灭所有 `x`/`d`/`tmp`/`df1`。
>
> 📎 **本周主课**：Hive 从入门到实战——Hive 架构/HQL/分区分桶/数据倾斜/Hive 调优/Spark 入门
>
> 🏢 **本周鲜果多剧情**：鲜果多的订单数据从 10 万行涨到了 5000 万行。pandas 单机跑不动了——内存不够（DataFrame 比 CSV 大 5-10 倍）、速度太慢（单核 CPU 被你的 for 循环卡死）。公司把数据迁移到了 Hive。你需要把之前 pandas 的分析逻辑翻译成 Hive SQL——同时应对数据倾斜（某几个大城市的订单量占了 80%——GROUP BY city 时一个 Reducer 处理了 80% 的数据）、分区设计（按什么字段分区才能让 90% 的日常查询只扫一个分区）、文件治理（每天导入产生几千个小文件——查询越来越慢——但不是因为数据多了——是因为文件数多了）。

---

## D1（周一 9/29）：Hive vs MySQL——不是"语法差异表"，是"四个根本设计哲学的对立"

> 📓 今日主课：Hive 架构 + HQL vs MySQL 十大差异

---

### 🔴 认知冲突

你以为"Hive 就是 MySQL 但能处理大数据"——就像从自行车换到卡车——方向盘还是圆的，只是大了点。

然后你在 Hive 上写了一条 `UPDATE orders SET status='done' WHERE order_id=12345`——报错：`SemanticException: UPDATE is not supported`。你查了文档——Hive 不支持行级 UPDATE。你又写了一条 `SELECT * FROM orders LIMIT 10`——等了 45 秒才出结果——而在 MySQL 上这条是 0.01 秒。你还试着跑了一个 `SELECT COUNT(DISTINCT user_id) FROM orders`——跑了 3 分钟后报错：`Error: Java heap space`——你的聚合把 Reducer 的内存打爆了——因为几百个热点 key 的数据全砸到了一个节点上。

你不只是从自行车换到了卡车——你是从自行车换到了火车。方向盘没了——你面对的是铁轨、信号灯、调度站、和"火车不能急转弯"的物理约束。你不理解火车的物理原理——你还在用骑自行车的方式操作火车。

**面试官问你"Hive 和 MySQL 有什么区别"——你不能回答"语法有一点点不一样"或"Hive 不支持 UPDATE"。你需要从四个根本设计哲学的对立回答——每个对应一种"物理约束"——每个约束决定了你在 Hive 上编写 SQL 时的思维转变。**

---

### 📖 核心原理

**四个根本差异——不只是"语法对比表"——是"为什么这样设计"的物理约束：**

**差异 1：设计目的——OLAP vs OLTP。这是其他三个差异的根因。**

MySQL 是 OLTP（Online Transaction Processing）：处理在线事务。单行或少量几行的增删改查——毫秒级响应。用户下单→`INSERT INTO orders`→立刻返回——用户不能等。设计目标：**低延迟的少量操作**。

Hive 是 OLAP（Online Analytical Processing）：分析海量数据。扫描上亿行做聚合——分钟级响应。计算上月 GMV→`SELECT SUM(amount) FROM orders WHERE month='2026-08'`→企业可以等 2 分钟。设计目标：**高吞吐的大量操作**。

这个差异决定了 Hive 不做任何"降低吞吐来换取低延迟"的优化。它假设你每次查询都要扫大量数据——所以它不建 B+Tree 索引（索引会增加写入开销——降低吞吐）。它用全表扫描 + 分区裁剪 + 列式存储来加速——这些方案在高吞吐场景中远胜索引。

**差异 2：存储模型——不可变的分布式文件 vs 可原地修改的 B+Tree。**

MySQL 把数据存在 B+Tree 索引结构中——可以快速定位单行（通过主键）——并且**原地修改**那一行的数据。`UPDATE ... WHERE id=12345` 是 O(log n)——找到那一页、改那个值、写回。

Hive 把数据存在**不可变的大文件**中（HDFS 上的 ORC/Parquet 文件）。一个分区目录下有几个几 GB 的文件。要"更新一行"——Hive 必须：①读取整个文件（几 GB）→②在内存中找到那一行→③修改那个值→④把整个文件写回 HDFS。这不是"不支持"——是**物理上代价大到不可接受**。

这就是为什么 Hive 用 `INSERT OVERWRITE` 而不是 `UPDATE`——它不是修一个值——而是把整个分区（或整张表）的数据全部重写。**这个差异要求你的思维从"改一行"转变为"重写一个分区"。**

**差异 3：Schema 时机——Schema on Read vs Schema on Write。**

MySQL 在**写入时**校验 Schema。你 `INSERT` 一行——类型不对——MySQL 拒绝写入。这叫 Schema on Write。

Hive 在**读取时**才解析和校验 Schema。写入时不校验——数据只是文件——放在 HDFS 上。读取时 Hive 才去读文件、解析格式。文件格式和表定义不一致→**读取时**报错。这叫 Schema on Read。

这解释了为什么 Hive 能接受各种格式的数据——但也解释了"为什么 Hive 查询突然报错说某列的类型不对"——数据源改了格式——Hive 不知道——直到你 SELECT 才暴露。

**差异 4：SQL 支持度——事务/行级操作 vs 批量/分区。**

| 能力 | MySQL | Hive | 物理约束 |
|------|-------|------|---------|
| SELECT | ✅ 毫秒 | ✅ 分钟 | OLAP 不追求低延迟 |
| INSERT | ✅ 单行 | ✅ 追加文件 | Hive 的 INSERT 是"往目录里加文件"——不是往 B+Tree 加一行 |
| UPDATE/DELETE | ✅ 原地修改 | ❌ 不支持行级 | 文件不可变——只能重写整个分区 |
| 事务(ACID) | ✅ 原生 | ⚠️ 有限支持 | 需要 ORC+分桶+高代价——不符合 OLAP 定位 |
| 索引 | ✅ B+Tree | ❌ 无 | 全表扫描在 5000 万行上可能比索引遍历更快——分区+列式存储替代索引 |

**面试标准回答（45 秒）——面试官问"Hive 和 MySQL 有什么区别？"：**

> "根本差异是设计目的不同。MySQL 是 OLTP——处理在线事务——用 B+Tree 做原地修改——追求低延迟。Hive 是 OLAP——分析海量数据——数据存在不可变的分布式文件上——不支持行级修改——用 INSERT OVERWRITE 批量重写分区。这个根本差异决定了后续所有设计选择——Schema on Read vs Write、分区代替索引、MapReduce/Tez/Spark 代替单机执行。理解这个差异后——你不会在 Hive 上试图做事务，也不会在 MySQL 上跑 TB 级聚合。"

---


---

### 📖 补充：Hive 的架构——三个核心组件决定了"为什么 Hive 查询慢"

理解 Hive 架构不是为了画架构图——是为了理解"为什么 SELECT LIMIT 10 也要等 45 秒"。

**三个核心组件——每个告诉你"延迟从哪来"：**

**1. Metastore**（元数据库——通常是 MySQL/PostgreSQL）：存储"表名对应的 HDFS 路径"、"有哪些分区"、"列的类型"。每次查询开始时——Hive 需要查 Metastore——获取"数据在哪、怎么读"。Metastore 本身不是瓶颈（查元数据是毫秒级的）——但如果你有几万个分区——加载分区列表可能需要几秒到几十秒——这是 Metastore 的性能上限。

**2. Driver**（编译器——在 HiveServer2 中运行）：接收 SQL——Parser（语法解析）-> Semantic Analyzer（语义分析——查 Metastore——表存在吗？列存在吗？）-> Logical Plan（逻辑计划——这个 JOIN 应该怎么算？）-> Physical Plan（物理计划——切多少个 Map Task？多少个 Reducer？）-> 提交到执行引擎。**这个编译过程就是"SELECT LIMIT 10 也要等 45 秒"的根因——编译开销是固定的——不随数据量变化。** MySQL 的 SELECT LIMIT 10 不需要编译——直接查 B+Tree——定位+读 10 行——毫秒级返回。Hive 必须把 SQL 完整编译为 MapReduce/Tez/Spark 作业——即使最后只需要 10 行——编译过程本身耗时 30-60 秒。

**3. 执行引擎**（MapReduce/Tez/Spark——YARN 管理资源）：真正读写 HDFS 文件的组件。每个 Map Task 启动一个 JVM——JVM 启动时间约 3-5 秒。100 个 Map Task = 300-500 秒的 JVM 启动开销。这就是 D4"小文件问题"的根源——每个小文件启动一个 Map Task——每个 Task 启动一个 JVM——而 JVM 启动时间经常大于文件读取时间。

**这个架构串联了 W10 的四个主题：**
- D2 分区裁剪 = 减少 InputSplit 数量——Driver 在编译阶段就缩减输入——不需要启动无用的 Map Task
- D3 数据倾斜 = Shuffle 阶段负载不均——一个 Reducer 被分配了太多 key——和"启动了多少 JVM"无关——是"每个 JVM 被分配了多少数据"
- D4 小文件 = Map Task 数量失控——因为每个文件启动一个 Task——每个 Task 启动一个 JVM
- D4 调优 = 在每个架构层次上找到瓶颈——Metastore 慢（分区太多）-> Driver 慢（编译复杂）-> 执行引擎慢（小文件/倾斜/Reducer 少）

### 🏢 鲜果多案例

鲜果多的订单数据迁移到 Hive 后——你发现之前 pandas 里"更新用户等级"的逻辑不能用 `UPDATE` 实现了。你在 Hive 里用 `INSERT OVERWRITE` 代替：

```sql
-- MySQL 做法（不适用于 Hive——不支持行级 UPDATE）:
-- UPDATE users SET user_level = 'gold' WHERE total_spent > 5000;

-- Hive 做法——批量重写分区——每天凌晨重写当天的用户表分区:
INSERT OVERWRITE TABLE users PARTITION (dt='2026-09-29')
SELECT user_id,
       CASE WHEN total_spent > 5000 THEN 'gold'
            WHEN total_spent > 2000 THEN 'silver'
            ELSE 'normal'
       END AS user_level,
       total_spent, register_date
FROM users WHERE dt='2026-09-28';
```

每天的分区是**一份完整的新数据**——不是"昨天 + 差异"——是"昨天全量 + 今天更新 = 今天全量"。这不是浪费存储——这是"文件不可变"的代价。但这也意味着——你可以随时回到任何一天的分区——每一天都是自包含的完整快照。**代价是存储——收益是时间旅行——这就是 OLAP 的权衡。**

---

### ✍️ 动手练习

1. 在 `docs/hive_vs_mysql.md` 中写入四个根本差异——每个配"对你日常分析工作的实际影响"：更新逻辑→INSERT OVERWRITE、行数验证→`wc -l` 而不是 `SELECT COUNT(*)`（Hive 的 COUNT 会启动 MR 作业）。
2. 练习 45 秒面试回答——录音——回听——确保从"设计目的"开始——不是从"语法差异"开始。
3. 如果你有 Hive 环境——跑 `SELECT * FROM orders LIMIT 10`——感受"为什么 LIMIT 在 Hive 上也慢"（因为 Hive 默认全表扫描——即使只要 10 行——也需要启动 MR 作业——在最后阶段截断）。对比 MySQL 的同一条查询。
4. `git commit -m "document Hive vs MySQL four paradigm differences + interview talking point" && git push`

---

### ✅ 自检反馈

**✅ 参考答案**

四个差异：OLAP vs OLTP / 文件 vs B+Tree / Schema on Read vs Write / 批量 vs 事务。Hive 不支持 UPDATE 的根因：数据存在不可变的大文件中——物理上无法原地修改单行——代价是重写整个文件。

**❓ 常见偏差**

| 偏差 | 原因 | 🔧 补救 |
|------|------|---------|
| "Hive 不支持 UPDATE——那怎么更新数据？" | INSERT OVERWRITE PARTITION——不是改一行——是重写整个分区 | 理解"文件不可变"的物理约束 |
| "Hive 有索引吗？" | 没有。分析型查询中全表扫描可能比索引遍历更快。Hive 用分区+列式存储加速 | 不要试图在 Hive 上建索引——建分区 |


---

### 📖 补充：Hive 数据类型与 NULL 处理——和 MySQL 的差异会静默改变分析结果

**Hive 的 NULL 处理——比 MySQL 更"严格"——某些看似等价的写法在 Hive 中行为不同：**

```sql
-- MySQL: 这两个等价——都排除 NULL
SELECT * FROM orders WHERE status != 'cancelled';       -- 含 NULL 的行被排除
SELECT * FROM orders WHERE status NOT IN ('cancelled');  -- 含 NULL 的行被排除

-- Hive: 行为不同——NOT IN 含 NULL 子查询时整查询返回空（和 W9D5 模式 1 一样）
-- 但 Hive 的 != NULL 的行为也可能因配置不同而不同
-- 规则: 永远显式处理 NULL——不要依赖数据库的默认 NULL 处理
SELECT * FROM orders WHERE status IS NOT NULL AND status != 'cancelled';
```

**Hive 的复杂类型——Array/Map/Struct——在 Python 中的等价物：**

| Hive 类型 | Python 等价 | 使用场景 | 示例 |
|-----------|----------|---------|------|
| `ARRAY<STRING>` | `list[str]` | 一个订单的多个标签 | `tags[0]` 取第一个标签 |
| `MAP<STRING, INT>` | `dict[str, int]` | 键值对——如属性 | `props['color']` 取颜色 |
| `STRUCT<name:STRING, age:INT>` | namedtuple / dataclass | 嵌套对象——如地址 | `address.city` 取城市 |

**这些类型在 Hive SQL 中怎么用——实战示例：**

```sql
-- ARRAY: 订单包含多个商品 ID
SELECT order_id, product_ids[0] AS first_product  -- 取数组第一个元素
FROM orders
WHERE ARRAY_CONTAINS(product_ids, 'p_67890');     -- 检查数组是否包含某值

-- MAP: 用户属性——键值对
SELECT user_id, properties['vip_level'] AS vip_level
FROM users
WHERE properties['city'] = '北京';

-- STRUCT: 地址——嵌套结构
SELECT user_id, address.city, address.province
FROM users
WHERE address.province = '广东省';
```

**面试中如果你能解释 Hive 复杂类型的使用场景——面试官知道你不仅会写 HiveQL——你在用 Hive 建模半结构化数据。这是 Hive 相对 MySQL 的另一个核心优势——MySQL 的列是扁平的——Hive 的列可以嵌套、可以是数组、可以是键值对——更适合现实世界中的"不整齐"的数据（JSON 日志、埋点事件、Nested 用户属性）。**



## D2（周二 9/30）：分区裁剪——为什么 `WHERE dt='2026-09-01'` 和 `WHERE order_date='2026-09-01'` 性能差 100 倍

> 📓 今日主课：Hive 实战——分区裁剪/列式存储/MAPJOIN/动态分区

---

### 🔴 认知冲突

你写了两条查询——过滤条件完全等价——都是"9 月 1 日的数据"：

```sql
-- 查询 A: 0.8 秒
SELECT COUNT(*) FROM orders WHERE dt = '2026-09-01';

-- 查询 B: 48 秒
SELECT COUNT(*) FROM orders WHERE order_date = '2026-09-01';
```

两条差 60 倍。不是因为 `dt` 有索引而 `order_date` 没有——**Hive 根本没有索引**。不是因为 `dt` 的数据类型更好——它们都是 STRING。差 60 倍的原因是：**`dt` 是分区列——`order_date` 不是。**

分区对 Hive 来说不是"数据组织方式"——是**物理目录结构**。`WHERE dt='2026-09-01'` 告诉 Hive：只进这个目录——Hive 在 SQL 编译阶段就从 Metastore（元数据库）知道哪些目录不需要读——在启动任何 MapReduce Task 之前就缩减了输入。`WHERE order_date='2026-09-01'` 告诉 Hive：进所有 365 个分区目录、打开所有文件、逐行检查——因为 Hive 不知道 order_date 和目录的对应关系。

**你以前在 MySQL 上学到的"索引加速查询"的心智模型——在 Hive 上不适用。** Hive 不是通过"快速定位数据"来加速——而是通过"跳过不需要的数据"来加速。这两种加速方式的物理机制完全不同：索引=查询过程中减少查找开销，分区=查询开始前减少输入数据量。

---

### 📖 核心原理

**分区 = 物理目录。分区裁剪 = 目录跳过。这个机制发生在 SQL 编译阶段——在任何 Map Task 启动之前。**

```
orders 表在 HDFS 上的实际存储结构:
/user/hive/warehouse/orders/
├── dt=2026-08-31/
│   ├── part-00001.orc    ← 8月31日的订单数据（两个文件）
│   └── part-00002.orc
├── dt=2026-09-01/
│   ├── part-00001.orc    ← 9月1日的数据——WHERE dt='2026-09-01' 只读这个目录
│   └── part-00002.orc
├── dt=2026-09-02/
│   └── part-00001.orc
└── dt=2026-09-03/
    └── part-00001.orc    ← 共365个这样的目录
```

`WHERE dt='2026-09-01'` 的物理过程：
1. Hive 解析 SQL——看到 `WHERE dt='2026-09-01'`
2. 查询 Metastore——"dt 是分区列——dt='2026-09-01' 对应的 HDFS 路径是什么？"
3. Metastore 返回：`/user/hive/warehouse/orders/dt=2026-09-01/`
4. Hive 只把这个目录下的文件（`part-00001.orc`, `part-00002.orc`）映射为 MapReduce 的 InputSplit
5. 其他 364 个目录——不查询、不扫描、不存在

`WHERE order_date='2026-09-01'` 的物理过程：
1. Hive 解析 SQL——看到过滤条件
2. 查询 Metastore——"order_date 是分区列吗？"——不是
3. Hive 把**所有 365 个目录**下的所有文件映射为 InputSplit
4. 每个 Map Task 读取文件——逐行检查 order_date='2026-09-01'
5. 只有约 0.3%（1/365）的数据满足条件——但 100% 的数据都被扫描了

**分区键的选择原则——不是"哪个列数据量大就分区"——是"哪个列最常被用来过滤"：**

- ✅ 日期（`dt`）——90% 的日常查询按日期过滤："昨天"、"上月"、"Q3"
- ✅ 国家/地区——如果分析主要按地理拆分
- ❌ 用户 ID（`user_id`）——100 万个用户 = 100 万个目录 = HDFS NameNode 内存爆炸。NameNode 在内存中管理所有文件/目录的元数据——100 万个目录是物理极限
- ❌ 订单状态（`status`）——5 个值 → 5 个分区。每个分区巨大——没有裁剪效果——因为每个查询只访问其中 1-2 个分区——但那个分区本身就是全表

**面试标准回答（30 秒）——"分区为什么比索引快？"：**

> "分区不是查询优化——是存储层的目录跳过。Hive 在编译 SQL 时从 Metastore 知道哪些目录不需要读——在启动 MR 作业前缩减了输入。索引是在查询过程中加速查找——但仍然需要遍历索引结构。分区裁剪发生在更底层——直接跳过目录。分区键的选择取决于查询模式——最常被过滤的列就是分区键。"

---

### 🏢 鲜果多案例

鲜果多每天 50 万行订单——按 `dt` 分区——365 个分区。日常查询"昨天各城市 GMV"——`WHERE dt='2026-09-29'`——只扫 1 个分区（50 万行）——0.8s。"上月每天 GMV 趋势"——31 个分区——~8s。"整年 GMV"——365 个分区——~90s。

如果当初选了 `user_id` 作为分区键——"昨天各城市 GMV"这个查询必须扫描所有分区——因为 Hive 不知道"昨天"是哪些 user_id——每次查询都是全表扫描——90s 而不是 0.8s。

**分区键的选择——不是技术决策——是业务决策。你需要知道"这个团队最常怎么查数据"。

**二级分区——当一级分区不够时：每天+每个国家的查询——两个条件都需要裁剪：**

```sql
-- 一级分区: 只按 dt 分区——跨国查询"全国家汇总"时 OK——只查一天
-- 但"查一个国家的 365 天趋势"——需要扫全部 365 个分区
CREATE TABLE orders_one (order_id STRING, amount DECIMAL)
PARTITIONED BY (dt STRING);

-- 二级分区: dt + country——两种查询模式都能裁剪
-- WHERE dt='2026-09-29' AND country='CN' 只扫 1 个子目录
-- WHERE dt BETWEEN '2026-01-01' AND '2026-06-30' AND country='CN' 只扫 CN 的半年目录
CREATE TABLE orders_two (order_id STRING, amount DECIMAL)
PARTITIONED BY (dt STRING, country STRING);
```

HDFS 上的目录结构：`/orders/dt=2026-09-29/country=CN/`——二级分区 = 两级目录——每级独立裁剪。但注意——分区层级太多（3 级+）——目录数爆炸——NameNode 内存压力大——且小文件问题加剧（因为数据被切得更碎）。

**分区设计的两个反模式——在生产环境中最常见也最昂贵的错误：**

| 反模式 | 症状 | 根因 | 修复 |
|-------|------|------|------|
| **分区膨胀** | 几万个分区——Hive SHOW PARTITIONS 超时——NameNode 内存告警 | 把 user_id/order_id 设为分区键——每个用户一个分区 = 百万级目录 | 改回 dt 分区——用 ORC 的 Bloom Filter 索引加速 user_id 过滤——不需要分区 |
| **空分区陷阱** | WHERE dt='2026-09-29' 返回空结果——但数据明明已经导入 | 分区值拼写不一致：建表是 dt='2026-09-29'——写入时写成了 dt='2026-9-29'（缺前导零）——Hive 当成了不同分区 | 统一分区值的格式——用脚本校验——或建表时写死格式 |

**面试追问应对——"二级分区什么时候不加？"**
> "当二级分区的基数太大时——比如 dt+user_id——二级分区会创建数百万个子目录——HDFS NameNode 的内存承受不了。而且 Hive 的 Metastore 在加载分区列表时会超时。此时应该用排序+ORC 文件内索引（Bloom Filter）代替二级分区——索引在文件内——不需要额外目录。"
**

---

### ✍️ 动手练习

1. 用 Python 模拟分区裁剪——建 10 个目录 `data/dt=2026-09-01/` 到 `data/dt=2026-09-10/`——每个目录一个 CSV——写 `smart_read(base_dir, dt_filter)`——有过滤时只读目标目录——无过滤时读全部。
2. 对比有分区裁剪（读 1 个目录）vs 无分区裁剪（读 10 个目录）的时间——记录加速比。
3. 在代码注释里写"面试 30 秒回答——分区 vs 索引"。
4. `git commit -m "simulate Hive partition pruning with Python directory-skip demo" && git push`

---

### ✅ 自检

- `smart_read` 有过滤时只读目标目录——日志输出"扫描 1/10 目录"
- 面试回答从"目录跳过"开始——不是从"索引"开始


---

---

### 📖 分区设计的进阶模式——不只"按 dt 分区"

**模式 1：动态分区——让 Hive 自动创建分区——而不是手动 ALTER TABLE ADD PARTITION：**

```sql
-- 静态分区: 手动指定每个分区的值
INSERT OVERWRITE TABLE orders PARTITION (dt='2026-09-29')
SELECT * FROM raw_orders WHERE order_date = '2026-09-29';

-- 动态分区: Hive 根据最后一列的值自动创建分区——适合回刷历史数据
SET hive.exec.dynamic.partition=true;
SET hive.exec.dynamic.partition.mode=nonstrict;

INSERT OVERWRITE TABLE orders PARTITION (dt)
SELECT order_id, amount, user_id, order_date AS dt
FROM raw_orders;
-- Hive 自动为每个不同的 dt 值创建分区——一条 SQL 完成 365 天导入
```

**模式 2：分区修复——当你在 HDFS 上手动放了文件——但 Metastore 不知道：**

```sql
-- 场景: 同事直接把文件拷贝到 HDFS 的 /orders/dt=2026-09-30/ 目录下
-- Hive 不知道——查询这个分区的数据返回空
MSCK REPAIR TABLE orders;  -- 扫描所有 HDFS 目录——同步分区元数据到 Metastore
```

**模式 3：分区裁剪失效——在分区列上使用函数——裁剪失效：**

```sql
-- 失效: WHERE 对分区列使用了函数——Hive 无法推导目标目录
SELECT * FROM orders WHERE YEAR(dt) = 2026;  -- 全表扫描

-- 生效: WHERE 直接比较分区列——编译期就能确定目标目录
SELECT * FROM orders WHERE dt BETWEEN '2026-01-01' AND '2026-12-31';
```

**面试陷阱题——为什么 WHERE YEAR(dt)=2026 没有分区裁剪？** 分区裁剪依赖 Metastore 中的分区值（目录名 = dt=2026-09-29）。YEAR(dt)=2026 需要先计算每行的 YEAR 值再比较——Hive 在编译期不能从 YEAR(dt)=2026 推导出需要哪些目录——退化为全表扫描。解决：用 WHERE dt BETWEEN '2026-01-01' AND '2026-12-31'——直接指定目录范围。



## D3（周三 10/1）：数据倾斜——用 Python 模拟 Shuffle，理解"不只是加盐"而是"hash 分配导致负载不均"

> 📓 今日主课：数据倾斜专题——JOIN 倾斜/GROUP BY 倾斜/COUNT DISTINCT 倾斜

---

### 🔴 认知冲突

你的 Hive `GROUP BY user_id` 跑了 40 分钟还没出结果。你看了日志——199 个 Reducer 中有 198 个在 2 分钟内完成了——最后一个跑了 40 分钟还在跑。同事说"数据倾斜了——加盐吧"。你搜了"加盐"——给 key 加随机前缀——跑通了——40 分钟变成 3 分钟。但你不知道为什么——你只是复制粘贴了一个技巧。

面试官追问："加盐为什么能解决数据倾斜？它改变了 Shuffle 的哪个环节？什么类型的聚合函数不能用加盐——为什么？"——你沉默了。你用了这个技巧——但不理解它背后的分布式计算原理。

**问题**：数据倾斜不是"Hive 的 bug"——是**分布式计算中的 hash 分配机制**在数据分布极端不均时的必然结果。理解 Shuffle 三阶段（Map→Shuffle→Reduce）——你就能推导出"加盐为什么有效"和"什么时候不该用加盐"。不理解 Shuffle——加盐只是一个神秘的咒语——你不知道它什么时候会失效。

---

### 📖 核心原理

**Shuffle 三阶段——这是分布式 GROUP BY 的核心机制。理解它——你就能自己推导出加盐的原理。**

```
Map 阶段（每个 Mapper 独立运行——读自己分到的 HDFS 文件块）:
  Mapper1 读 HDFS Block 1（30% 的数据）→ 本地预聚合 → 输出 (key, partial_agg)
  Mapper2 读 HDFS Block 2（30% 的数据）→ 同上
  Mapper3 读 HDFS Block 3（40% 的数据）→ 同上

Shuffle 阶段（数据重新分配——这是整个分布式计算的瓶颈）:
  Mapper 的输出按 key 的 hash 值分配给 Reducer。
  分配规则: Reducer编号 = hash(key) % Reducer数量
  
  hash('hot_user_001') % 4 = 1  → Reducer1 收到所有 hot_user_001 的中间结果
  hash('user_12345')  % 4 = 0  → Reducer0
  hash('user_67890')  % 4 = 2  → Reducer2
  ...

Reduce 阶段（每个 Reducer 只处理自己分到的 key——最终聚合）:
  Reducer0 收到自己那批 key → 逐个最终聚合 → 输出
  Reducer1 收到自己那批 key → 同上
  Reducer2 → 同上
  Reducer3 → 同上
```

**倾斜发生在 Shuffle 阶段。** 如果 `hot_user_001` 占了全表 50% 的数据——所有 Mapper 的输出中属于这个 key 的数据——全发给 Reducer1。Reducer1 需要处理 50% 的总数据量——Reducer0、2、3 各处理约 0.5%。Reducer 0/2/3 在 2 分钟内完成——然后**空等** Reducer1 跑完。整个查询在等那个最慢的 Reducer。空等的 CPU 没有被利用——但查询耗时等于最慢的 Reducer 的耗时。

**这就是数据倾斜的物理本质——不是"某个节点慢"——是 hash 分配导致负载极度不均——所有节点在等最慢的那个。**

**加盐（Salting）的本质——破坏 hash 的"同一个 key 去同一个 Reducer"的规则：**

```sql
-- 第一阶段: 随机后缀——hot_user_001 被拆成 10 份——hash 后分散到不同的 Reducer
SELECT CONCAT(user_id, '_', CAST(FLOOR(RAND()*10) AS STRING)) AS salted_key,
       SUM(amount) AS partial_sum
FROM orders
GROUP BY CONCAT(user_id, '_', CAST(FLOOR(RAND()*10) AS STRING));

-- hot_user_001 → hot_user_001_0, hot_user_001_1, ..., hot_user_001_9
-- hash(hot_user_001_0) % 4 = 1 → Reducer1
-- hash(hot_user_001_1) % 4 = 2 → Reducer2
-- hash(hot_user_001_2) % 4 = 3 → Reducer3
-- hash(hot_user_001_3) % 4 = 0 → Reducer0
-- ...10 个后缀 → 分散到 4 个 Reducer → 每个 Reducer 处理约 12.5%（50%/4）而不是 50%

-- 第二阶段: 去掉后缀——把 10 份局部聚合结果再聚合——数据量极小——不倾斜
SELECT SPLIT(salted_key, '_')[0] AS user_id,
       SUM(partial_sum) AS total_amount
FROM stage1_result
GROUP BY SPLIT(salted_key, '_')[0];
-- 每个 key 现在只有 10 行（10 份局部结果）→ 第二阶段数据量极小 → 不倾斜
```

**加盐的代价**：第一阶段输出的 key 数量变多（hot_user_001 变成了 10 个不同的 key）→ Shuffle 数据量略增。但对于热点 key 来说——从"一个 Reducer 处理 50%"变成"分散到多个 Reducer"——收益远大于代价。

**什么时候不能用加盐？——聚合函数不可拆分时：**

- `SUM(amount)` → 可拆分——局部 SUM + 全局 SUM = 全局 SUM ✅
- `COUNT(user_id)` → 可拆分——局部 COUNT + 全局 SUM = 全局 COUNT ✅
- `AVG(amount)` → 可拆分——局部 SUM+局部 COUNT → 全局 SUM/全局 COUNT = 全局 AVG ✅（但要同时算 SUM 和 COUNT）
- **`COUNT(DISTINCT user_id)` → 不可拆分**——局部去重 + 全局去重 ≠ 全局去重。同一个 user_id 可能被随机后缀拆到两个桶——局部 COUNT DISTINCT 各算了 1 次——第二阶段不能简单求和——需要用 HyperLogLog 近似算法 ❌
- **`MEDIAN(amount)` → 不可拆分**——局部中位数 + 全局中位数 ≠ 全局中位数。需要把所有数据汇集到一个节点才能算精确中位数 ❌

---

### 🏢 鲜果多案例

鲜果多"超级大客户"——某连锁餐厅——每天几百笔批发订单——占全表 15% 的订单量。Hive `GROUP BY user_id` 算客单价时——这个客户的 user_id 导致一个 Reducer 处理了 15% 的数据——查询 1 小时。你判断：①热点 key 存在 ②需要 AVG(amount)——可拆分但需要同时算 SUM 和 COUNT。你用了两阶段聚合——第一阶段 SUM+COUNT 按 salted_key——第二阶段 SUM(partial_sum)/SUM(partial_count)=全局 AVG。加了 10 个盐值——1 小时→3 分钟。**不是"加盐这个技巧好"——是"你理解了 Shuffle——知道瓶颈在哪——知道 AVG 可以用 SUM/COUNT 拆分——选择了正确的方案"。**

---

### ✍️ 动手练习

1. 用 Python 模拟 Shuffle + 数据倾斜：构造 10 万行——1 个热点 key 占 50%——4 个 Reducer（hash 分配）——计算每个 Reducer 的负载（行数和占比）。画柱状图——最不平衡的 Reducer 处理 50%——其他 3 个各 ~0.5%。
2. 在同一脚本中实现加盐——对比加盐前后的负载分布。画柱状图——4 个 Reducer 各约 12.5%。
3. 验证——如果聚合是 `np.median` 而不是 `np.sum`——加盐后的结果和直接聚合一样吗？不一样——因为中位数不可拆分——这就是"什么时候不能用加盐"。
4. 在注释画 ASCII Shuffle 图——标注"热点 key 全进同一个 Reducer"的路径和"加盐后分散到多个 Reducer"的路径。
5. `git commit -m "simulate Hive data skew + salting with Python Shuffle demo + unsplittable agg verification" && git push`


## D4（周四 10/2）：Hive 调优——原理驱动的参数调优 + 小文件治理

> 📓 今日主课：Hive 调优——EXPLAIN/小文件/JOIN 策略/并行度

---

### 🔴 认知冲突

你的 Hive 查询越来越慢——但数据量没有显著增长。排查发现——不是数据多了——是**文件数多了**。每天导入的数据产生了几千个小文件（每个几 MB）——Hive 为每个小文件启动一个 Map Task——启动 Task 本身的开销（几秒）比读文件内容（< 1 秒）还大。你被"小文件"困住了——不是因为你的 SQL 写得不好——是因为你不知道"小文件合并"这个开关。

**问题**：Hive 调优不是"背参数"。每个参数对应一个特定的系统瓶颈——你理解瓶颈是什么——该调哪个参数自然就知道了。反过来——背了参数但不理解瓶颈——你不知道什么时候该调。

---

### 📖 核心原理

**四个最常见瓶颈 + 对应参数 + 为什么有效：**

| 瓶颈 | 症状 | 参数 | 为什么有效 |
|------|------|------|----------|
| **Reducer 太少** | CPU 利用率低——查询慢 | `mapreduce.job.reduces` | 设置得 >= 合理值——经验: total_bytes/256MB |
| **小文件太多** | 查询启动慢——Map Task 数远超合理值 | `hive.merge.mapfiles=true` | 合并输入小文件——减少 Map Task 数 |
| **JOIN 小表→MapJoin** | JOIN 慢——Shuffle 数据量巨大 | `hive.auto.convert.join=true` | 小表广播到所有 Mapper——JOIN 在 Map 阶段完成——不需要 Shuffle |
| **数据倾斜 JOIN** | 某个 Reducer 处理量远超其他 | `hive.optimize.skewjoin=true` | Hive 自动检测热点 key→走 D3 的分而治之路径 |

**小文件合并——不依赖参数，更要管源头。——源头治理 + 事后合并——两步走。

**源头治理——在数据写入时就防止小文件产生：**

每天的数据导入（如 Flume/Kafka→HDFS）如果每 5 分钟写一次——一天产生 288 个小文件。改为每小时写一次——一天 24 个大文件。或者用 Hive 的 Streaming 写入时设置 batch size——攒够 128MB 再写一个文件。

```python
# 源头治理——Python 模拟: 小文件合并写入
import os
from typing import List

def merge_small_files(input_dir: str, output_dir: str, target_size_mb: int = 128):
    """合并小文件到目标大小——模拟 Hive 的文件合并策略。

    Hive 参数: hive.merge.mapfiles=true 在 Map-Only 作业结束时合并小文件。
    这个函数模拟同样的逻辑——适用于你本地的 CSV/Parquet 文件管理。
    """
    files = sorted([f for f in os.listdir(input_dir) if f.endswith('.csv')])
    buffer = []
    buffer_size = 0
    batch_idx = 0

    for filename in files:
        filepath = os.path.join(input_dir, filename)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        if buffer_size + size_mb > target_size_mb and buffer:
            batch_idx += 1
            print(f'合并 batch_{batch_idx}: {len(buffer)} 个文件 -> {buffer_size:.1f}MB')
            buffer = []
            buffer_size = 0

        buffer.append(filepath)
        buffer_size += size_mb

    if buffer:
        batch_idx += 1
        print(f'合并 batch_{batch_idx}: {len(buffer)} 个文件 -> {buffer_size:.1f}MB')

    print(f'总计: {len(files)} 个小文件 -> {batch_idx} 个大文件 (减少 {(1-batch_idx/len(files))*100:.0f}%)')
    return batch_idx
```

**事后合并——定期作业——对已有小文件的表重写：**

```sql
-- Hive: 把分区内的小文件合并成大文件
-- 原理: INSERT OVERWRITE 读取所有小文件 -> 按 Hive 的合并策略写回 -> 自动合并
INSERT OVERWRITE TABLE orders PARTITION (dt='2026-09-29')
SELECT * FROM orders WHERE dt='2026-09-29';

-- 或者设置合并参数——让 Hive 在 Map-Only 作业结束后自动合并
SET hive.merge.mapfiles=true;
SET hive.merge.mapredfiles=true;       -- MapReduce 作业结束后也合并
SET hive.merge.size.per.task=256000000; -- 每个合并后文件 256MB
SET hive.merge.smallfiles.avgsize=16000000; -- 平均文件 < 16MB 时触发合并
```

**四个调优参数的深入理解——不只是"设哪个值"——是"这个参数改了什么、为什么有效"：**

| 参数 | 设什么值 | 改了什么 | 为什么有效 | 什么时候不该设 |
|------|---------|---------|----------|-------------|
| `mapreduce.job.reduces` | total_bytes / 256MB | 控制 Reducer 数量——每个处理约 256MB | Reducer 太少->单个处理太多数据->内存溢出。太多->启动开销大 | 数据量 < 1GB——1 个 Reducer 足够——设多了反而慢(启动开销) |
| `hive.merge.mapfiles=true` | true | Map-Only 作业结束后自动合并输出文件 | Map Task 的输出在写入 HDFS 前合并——减少最终文件数 | 如果输出本来就只有 1-2 个大文件——不需要额外合并步骤(开销极低——可以始终开启) |
| `hive.auto.convert.join=true` | true + `hive.mapjoin.smalltable.filesize`(默认 25MB) | 小表不进入 Shuffle——序列化后广播到所有 Mapper 内存 | JOIN 在 Map 阶段完成——不需要 Reduce——避免 Shuffle——速度数量级提升 | 小表 > 内存限制——强制 MapJoin 会导致 OOM。此时用普通 JOIN(走 Shuffle) |
| `hive.optimize.skewjoin=true` | true | Hive 自动检测热点 key->对该 key 走 D3 的分而治之路径 | 避免单个 Reducer 处理 50% 数据——自动拆解 | 数据分布天然均匀——没有倾斜——这个优化不生效(开销极小——可以始终开启) |

**调优的正确顺序——不是"一次把所有参数都设上"——而是"先定位瓶颈->再选参数"：**

1. **先看是不是小文件**——如果 Map Task 数远超文件总大小/128MB——先合并小文件。因为小文件问题不解决——后面所有调优都在浪费资源（每个 Map Task 的启动开销 > 读取数据的时间）
2. **再看 JOIN 是不是倾斜**——如果 JOIN 慢且 199/200 个 Reducer 快但 1 个慢——数据倾斜——考虑 MapJoin(小表)或 skewjoin(大表)
3. **再看 Reducer 数量是否合理**——CPU 利用率低=Reducer 太少。内存溢出=单个 Reducer 处理太多
4. **最后看数据格式**——ORC+压缩(zlib/snappy)能减少 70% 的存储和 IO——但这是存储优化——不应在 SQL 慢的时候第一反应就改格式

**面试时的完整回答——"Hive 查询慢——你怎么排查？"：**
> "我的排查顺序是四步。第一——查是不是小文件——Map Task 数远超文件总大小/128MB->合并小文件。第二——查是不是数据倾斜——看 Job 日志——199 个 Reducer 在 2 分钟内完成但 1 个跑了很久->确认热点 key->加盐或 MapJoin。第三——查 Reducer 数量——CPU 利用率低=太少——设 mapreduce.job.reduces。第四——查数据格式——CSV 改 ORC+snappy 压缩——减少 IO。每一步定位不同的瓶颈——不是一次性把所有参数设上——而是先定位再调参。"

** 源头 = 每天导入数据时不要产生小文件——合并成大文件再导入。事后 = 定期运行合并作业——`INSERT OVERWRITE ... SELECT * FROM ...`——把多个小文件读出来写回——Hive 自动合并成大文件。



## 深度扩展：ORC vs Parquet——列式存储格式的选择

> 这个补充不属于任何 D 天——但你的 Hive 工程化知识如果不包含存储格式选择——是不完整的。

**两个列式格式的核心差异——从数据分析师的视角：**

| 维度 | ORC | Parquet | 对鲜果多的影响 |
|------|-----|---------|-------------|
| 压缩率 | 更高（约 20-30% 更小）——ORC 用更精细的 stripe+index 结构 | 稍低——但够用 | 5000 万行订单——ORC 约 3GB——Parquet 约 4GB——差异在 TB 级才显著 |
| 读取速度 | 更快的全表扫描——stripe 内的 min/max 索引能跳过不需要的 stripe | 更快的列裁剪——只需要 3 列时——Parquet 只读这 3 列的数据页 | 鲜果多 GMV 日报——SELECT SUM(amount)——只需要 1 列——Parquet 可能更快 |
| 生态兼容 | Hive/Spark 原生——但非 Hadoop 生态需要额外库 | 跨语言——Python(R)/Java/Go 都能直接读写 | 你的 pandas 分析如果用 Parquet——pd.read_parquet() 零依赖 |
| 写入速度 | ORC 写入更慢——更精细的索引结构需要更多计算 | Parquet 写入更快 | 如果每天导入是瓶颈——Parquet。如果查询是瓶颈——ORC |
| 谓词下推 | 支持 min/max/bloom filter——在 stripe 级别跳过 | 支持 min/max——在 row group 级别跳过 | WHERE amount > 1000——ORC 通过 stripe stats 跳过不满足条件的 stripe |

**鲜果多的选择——不同场景用不同的格式，不是"全项目统一一个格式"：**

- **ODS 层**——CSV（或 JSON）——和源系统格式一致——不做任何转换——保持"字节级一致性"承诺
- **DWD 层**——Parquet——方便分析师用 Python 直接读——pd.read_parquet('dwd_order_detail/dt=2026-09-29/')——不用装 Hive
- **DWS/ADS 层**——ORC——日常查询多、聚合多——ORC 的 stripe 索引对聚合查询更友好——且 Hive 原生支持最好

**这个决策在面试中是一个区分点——当面试官问"你用 ORC 还是 Parquet——为什么"——你不能说"我看别人都用这个"——你要说出你的查询模式决定了选择。**

---

### 🏢 鲜果多综合案例——D1-D4 整合：四个问题，一根链

鲜果多订单数据迁移到 Hive 后——你遇到了四个问题——它们不是"四个独立的问题"——是一根链上的四个环节：

**问题 1（D1——OLAP vs OLTP）：** 你习惯了 MySQL 的 `SELECT * FROM orders LIMIT 10`——在 Hive 上等了 45 秒。你意识到 Hive 不是"慢的 MySQL"——是"另一种计算模型"。改成 `SELECT * FROM orders WHERE dt='2026-09-29' LIMIT 10`——利用分区裁剪——1.2 秒返回。

**问题 2（D2——分区设计）：** 最初的 orders 表只有 dt 一级分区。运营总监问"广东省各城市的 GMV 排名"——需要扫一年 365 个分区——Map Task 启动开销占了 50% 的耗时。加了二级分区（province）——省级查询直接裁剪到对应省目录。

**问题 3（D3——数据倾斜）：** 按城市 GROUP BY——广州和深圳占了 35% 的订单——一个 Reducer 处理 35% 的数据——查询从 2 分钟变成 15 分钟。用 D3 的加盐策略——广州拆成 10 个盐值——15 分钟降为 2.5 分钟。

**问题 4（D4——小文件）：** 每天导入的订单数据用 Flume 每 1 分钟写一个文件——一天产生 1440 个小文件。三个月后——`/orders/dt=*/` 下面有 13 万个小文件——任何查询的 Map Task 数都在千级——JVM 启动时间占了 90% 的耗时。跑了合并作业——13 万变成 365 个大文件——查询从 5 分钟降到 45 秒。

**这四个问题的共同根因：你在用 MySQL 的心智模型操作 Hive。** 理解 D1-D4 后——你不会再问"为什么 Hive 这么慢"——你问的是"瓶颈在哪——分区设计、数据倾斜、小文件、还是 MapJoin 没开"。

### 📖 补充练习：Hive 调优实战演练

1. 如果今天你有 Hive 环境——查看项目中一条慢 SQL 的 EXPLAIN 输出——定位 type、rows、和 Map Task 数。没有 Hive 环境——在 GitHub 搜索"Hive EXPLAIN"——找一个公开的 EXPLAIN 输出——练习"从 EXPLAIN 的三个关键字段反向推导瓶颈"。
2. 用 Python 模拟小文件问题的性能影响：构造一个目录含 500 个 2MB CSV——另一个目录含 1 个 1GB CSV——分别用 pandas 遍历读取——对比耗时。在注释中记录——解释"启动开销 vs 读取开销"。
3. 在 README 的性能优化章节中写一条规则："优化 Hive 查询的第一步永远是先把 EXPLAIN 跑一遍——而不是靠直觉改参数。"
4. `git commit -m "add Hive tuning drill: EXPLAIN analysis + small file overhead simulation" && git push`

## D5（周五 10/3）：全项目命名审计——消灭所有 x/d/tmp/df1/df2

> 📓 今日主课：Hive 综合实战

---

### 🔴 认知冲突

你写了 9 周的代码——`src/` 下 2000+ 行。打开任一文件——`df1`、`tmp`、`d`、`x`——这些变量名在写的时候省了 2 秒——在读的时候浪费 30 秒 × 100 次 = 50 分钟。L3 代码可读性的硬指标：**变量名必须表达"这是什么"——不依赖上下文。** `df1` 不表达任何东西——你需要看赋值语句才知道"哦——这是加载了 orders 表之后的第二个中间结果"。

### ✍️ 动手练习

1. 全局搜索：`grep -rnE '\b(x|y|z|d|d1|d2|tmp|temp|df1|df2|df3|f|proc|ret|val|obj)\b' src/ --include="*.py"`
2. 逐项改为有意义的名称。每改一处跑 `pytest tests/ -v`。
3. 搜索单字符函数名：`grep -rnE 'def [a-z]\(' src/`——全部改掉。
4. 目标：两条 grep 返回空。
5. `git commit -m "naming audit: zero bad variable or function names" && git push`


---

### 📖 命名的工程化分类——不只是"改个名字"——是"这个名字属于哪种坏味道"

变量名不是孤立的问题——每个坏名字背后是一种**思维偷懒的模式**。识别模式->一次审计消灭一类：

| 坏名字类别 | 示例 | 为什么出现 | 该改成什么 | 审计 grep |
|-----------|------|-----------|-----------|----------|
| **单字母变量** | `x`, `y`, `z`, `d`, `f` | "这个变量只在这 3 行用——不用起名字" | 即使是临时的——也表达含义：`x`->`order_id`, `d`->`raw_data` | `grep -rnE '\b[x-z]\b' src/` |
| **数字后缀** | `df1`, `df2`, `df3`, `tmp2` | "不知道叫什么——编号吧" | 编号 = 你不知道这个变量表达什么——停下来想清楚再起名：`df1`->`orders_cleaned`, `df2`->`orders_aggregated` | `grep -rnE '\b(df|tmp|temp)[0-9]+\b' src/` |
| **无意义缩写** | `proc`, `ret`, `val`, `obj` | "大家都能看懂吧" | 没有人能看懂——`proc`->`process_orders`还是`processor`？`ret`->`return_value`还是`retention_rate`？ | `grep -rnE '\b(proc|ret|val|obj|cfg|mgr|hdlr)\b' src/` |
| **类型前缀** | `str_name`, `int_age`, `list_results` | "匈牙利命名法——加类型前缀" | Python 不流行——类型在 annotation 里——不在变量名里。`str_name`->`name: str` | `grep -rnE '\b(str_|int_|float_|list_|dict_)\b' src/` |
| **过于通用** | `data`, `info`, `result`, `config` | "这就是数据——有什么问题" | "data" 不表达任何信息——每行代码都是 data。`data`->`order_records`, `result`->`monthly_gmv` | `grep -rnE '\b(data|info|result|config|item|obj|entry)\b' src/` |
| **函数名没有动词** | `def orders():`, `def daily_kpi():` | "看名字就知道是取数据" | 函数是动作——名字必须表达"做什么"——`def fetch_orders()`/`def compute_daily_kpi()` | `grep -rnE 'def [a-z_]+[^s]\(' src/`（检查无动词的函数名） |

**自动化命名审计脚本——不只是 grep——而是每次 commit 前自动跑：**

```python
#!/usr/bin/env python
"""自动化命名审计——CI 集成——每次 push 自动检查。"""
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 禁止的变量名模式——每一类对应一个具体的坏味道
FORBIDDEN_PATTERNS: List[Tuple[str, str, str]] = [
    (r'\b[x-z]\b', '单字母变量', '用完整单词代替，如 order_id 而不是 x'),
    (r'\b(df|tmp|temp)\d+\b', '数字后缀', '编号=你不知道它表达什么——想清楚再起名'),
    (r'\b(proc|ret|val|obj|cfg|hndl)\b', '无意义缩写', '用完整单词，如 processor 而不是 proc'),
    (r'\b(data|info|result|item)\b', '过于通用', '表达具体含义，如 order_records 而不是 data'),
]


def audit_naming(root_dir: str = 'src') -> List[str]:
    """扫描所有 Python 文件——报告不符合命名规范的变量名。"""
    issues = []
    for py_file in Path(root_dir).rglob('*.py'):
        content = py_file.read_text(encoding='utf-8')
        for pattern, category, fix_example in FORBIDDEN_PATTERNS:
            for match in re.finditer(pattern, content):
                line_no = content[:match.start()].count('\n') + 1
                issues.append(
                    f'{py_file}:{line_no}: [{category}] "{match.group()}" -> {fix_example}'
                )
    return issues


if __name__ == '__main__':
    issues = audit_naming()
    if issues:
        print(f'❌ 命名审计未通过: {len(issues)} 个问题')
        for issue in issues:
            print(f'  {issue}')
        sys.exit(1)
    else:
        print('✅ 命名审计通过——没有发现坏名字')
```

把这个脚本放在 `scripts/audit_naming.py`——然后在 Makefile 中加一个 target：

```makefile
naming-audit:
	python scripts/audit_naming.py src/
```

CI pipeline 中加上这一步——如果命名审计不通过——不允许合并。**命名规范不是"风格建议"——是"代码质量门禁"——自动执行——不依赖人的自觉。**

---

### 🏢 鲜果多案例

鲜果多项目——`src/` 下 2000+ 行——跑了一次命名审计——发现 47 个问题：
- 单字母变量: 12 个（`x`, `y`, `d`, `f`, `t`）
- 数字后缀: 8 个（`df1`~`df5`, `tmp1`~`tmp3`）
- 无意义缩写: 15 个（`proc`, `ret`, `val`）
- 过于通用: 12 个（`data`, `info`, `result`）

逐一修改后——新同事打开代码——不需要"猜"每个变量是什么意思。三个月后你自己回来改代码——不需要"重新理解"自己当时在想什么。**一次命名审计的投资——回收期是"每一次重读代码"。** 如果把 2000 行代码看成 2000 次读取——每次节省 5 秒——总共节省 ~3 小时。




---

## D6（周六 10/4）：周项目——Hive 思维应用到 pandas 代码，逐函数标注"大数据迁移就绪度"

### 🎯 今日任务

不是写 Hive SQL——是**用 D1-D5 的 Hive 大数据思维审查你现有的 pandas 代码**。每个数据操作标注"当前数据量下 ok——数据量超过 X 时需迁移到 Hive/Spark——为什么——迁移方案是什么"。

### 审计流程——打开你鲜果多项目的每个数据分析函数，逐一标注：

**标注 1：哪些 groupby 会成为倾斜瓶颈？**

打开 `analyze.py`——找到每个 `df.groupby(...)`——问自己：这个 groupby 的 key 可能倾斜吗？按城市分组——某几个大城市占 80% → 标注"数据倾斜风险：城市分布不均——单独处理 TOP 城市或该聚合迁移到 Hive+加盐"。按 `user_id` 分组——某个大客户占 15% → 标注"热点 key 风险——分而治之策略"。

**标注 2：哪些操作在数据量大时需要分区裁剪？**

找到每个按日期过滤的操作——如 `df[df['order_date'] >= '2026-09-01']`——标注"当前 pandas 全量扫描——数据量 > 100 万行时在 Hive 中按 dt 分区——WHERE dt='2026-09-01' 只扫一个目录"。

**标注 3：哪些中间结果应该用 Parquet 而不是 CSV？**

找到每个 `df.to_csv()` 和 `pd.read_csv()`——标注"当前数据量 CSV 可接受——超 10 万行时改为 Parquet——列式存储+压缩——读写快 5-10 倍"。

**标注 4：命名审计最终确认**

跑 D5 的两条 grep——返回空了吗？没空的今天补全。

### 审计完成后——在 README 加"大数据迁移就绪度"章节：

列一张表——"操作 → 当前数据量 → 数据量阈值 → 迁移方案"。这张表是你以后"数据量涨了——这个分析还能不能跑"的第一参考。

`git commit -m "W10 audit: annotated all pandas ops with Hive migration readiness + naming audit clean"`

---

### 📖 迁移就绪度表——不只是"标注"——是"数据量增长的应急预案"

在 README 中加一张表——每行是一个分析操作——列：操作/当前数据量/数据量阈值/迁移方案/预估迁移成本。这张表是你以后"数据涨了能不能跑"的第一参考：

| 分析操作 | 当前实现 | 当前数据量 | 瓶颈阈值 | 迁移方案 | 预估迁移成本 |
|---------|---------|----------|---------|---------|------------|
| 每日 GMV 汇总 | `df.groupby('dt').sum()` | 10万行 | 500万行（内存>8GB） | Hive: `SELECT dt, SUM(amount) FROM orders WHERE dt='${yesterday}' GROUP BY dt` | 1h（一条 SQL——不改逻辑） |
| 用户留存分析 | `df.groupby('user_id').apply(retention_logic)` | 5万用户 | 50万用户（Python apply 太慢） | Hive: 窗口函数 LAG() OVER (PARTITION BY user_id ORDER BY dt) | 2h（窗口函数等价——需验证行为一致） |
| 城市维度下钻 | `df.groupby(['city','dt']).agg(...)` | 365天×300城市 | 数据倾斜——某城市占 80% | Hive: GROUP BY city, dt——加盐策略——大城市的 key 拆成 N 份 | 3h（加盐是两阶段聚合——逻辑变化——需重新验证） |
| CSV 读写 | `pd.read_csv()`/`to_csv()` | 10万行 | 50万行（读写 > 30秒） | Parquet: `pd.read_parquet()`——列式存储+压缩——读写快 5-10 倍 | 30min（改两行代码——验证列类型兼容） |
| 循环 apply | `df.apply(lambda row: ...)` | 1万行 | 10万行（Python 循环——秒级变分钟级） | 向量化: 用 `np.where`/`df.loc` 代替 `.apply`；或迁移到 Hive UDF | 1h（改 Python 逻辑——从逐行到批量——需要重新验证正确性） |

**这张表的核心价值不是"技术方案"——是"让 PM/老板理解为什么需要迁移"。** 当 PM 问"为什么这个分析变慢了"——你打开这张表——指给他看"当前 10 万行时 2s——到了 500 万行预估 90s——我们需要迁移到 Hive"——PM 能理解"不是因为代码不好——是数据量超过了当前架构的设计假设"。




## D7（周日 10/5）：W10 审计——闭卷 Hive 四范式 + Shuffle 三阶段 + 模拟面试

### 📝 闭卷自测

**Q1**：Hive 为什么不支持 `UPDATE`？根因是四个范式差异中的哪一个？这个差异还导致了什么其他行为？

> **A**：根因是"文件不可变"（存储模型差异——分布式文件 vs B+Tree）。Hive 数据存在 HDFS 大文件中——UPDATE 单行需要读取整个文件(几GB)→修改一行→写回整个文件——物理上代价不可接受。这个差异还导致：①用 INSERT OVERWRITE 代替 UPDATE——重写整个分区 ②不支持事务——因为文件不可变 ③Schema on Read——写入时不校验——因为写入只是"放文件"。

**Q2**：用 Shuffle 三阶段（Map→Shuffle→Reduce）解释数据倾斜的根因——为什么加盐能解决？

> **A**：Shuffle 阶段——Mapper 输出按 key 的 hash 分配给 Reducer。热点 key 占了 50% 数据——hash 后全进同一个 Reducer——那个 Reducer 处理 50% 数据——其他 Reducer 空等。加盐 = 给热点 key 加随机后缀→打破 hash 的"同 key 同节点"规则→热点 key 被拆成 N 份→分散到 N 个 Reducer→负载均衡。偏差：说"加盐让数据更均匀"——没解释为什么更均匀——因为它改变了 hash 的输入——key 从 `hot_user` 变成了 `hot_user_0`/`hot_user_1`/...——hash 值不同——分配到不同 Reducer。

**Q3**：什么聚合函数不能用加盐？为什么？举两个例子。

> **A**：不可拆分的聚合函数——局部聚合结果不能简单合并得到全局结果。①COUNT(DISTINCT user_id)——同一个 user_id 被随机后缀分到两个桶→局部 COUNT DISTINCT 各算 1 次→第二阶段不能求和（会重复计算）。②MEDIAN(amount)——局部中位数和全局中位数没有简单合并公式——需要所有数据汇集到一个节点。

**Q4**：分区裁剪为什么比索引快？分区键的选择原则是什么？

> **A**：分区发生在编译阶段——Metastore 返回目标目录——Hive 只读那部分文件——不扫描其他目录。索引是在查询过程中加速——仍然需要遍历索引结构。分区键选择：最常被过滤的列 = 分区键——日常查询 WHERE 哪个列——那个列就是分区键（通常是 dt）。

**Q5**：命名审计——两条 grep 返回空了？

**Q4**：小文件问题的根因是什么？如何从 Hive 日志中判断一个查询是否被小文件拖慢了？源头治理和事后合并各自的适用场景是什么？

> **A**：根因——每天导入的数据产生大量小文件（每个几 MB）——Hive 为每个小文件启动一个 Map Task——启动开销（几秒）> 读文件内容（< 1 秒）。日志判断：Map Task 数 >> 文件总大小/128MB——比如总数据 1GB——但 Map Task 有 500 个（500 个 × 2MB/个）——说明小文件严重。正常情况下 1GB 数据只需 8 个 Map Task（128MB/个）。
>
> 源头治理 = 在数据写入 HDFS 时（Flume/Kafka/Spark Streaming）设置写入 batch size——攒够 128MB 再写——从源头杜绝小文件。事后合并 = 对已有小文件的表定期跑 INSERT OVERWRITE SELECT *——Hive 自动合并输出文件。适用场景：源头治理用于"数据流还在写入"的场景——每天的新数据。事后合并用于"历史数据已经有小文件"的场景——一次性清理。
>
> **常见偏差**：说"小文件只影响 Hive——pandas 不受影响。"——pandas 同样受影响——`pd.read_csv('data/dt=*/part-*.csv')` 读 500 个小 CSV——每个文件的 open/read/close 是独立的系统调用——比读一个 1GB 大文件慢 5-10 倍。小文件问题是分布式文件系统的通用问题——不是 Hive 特有的。

**Q5**：你的鲜果多项目被同事接手。他打开 `analyze.py`——看到 `df1`、`tmp`、`d`、`x`——他不知道"这些变量之间是什么关系"。你做了一个命名审计——这 47 个坏名字背后的心理模式是什么？如果让你给新同事一条"命名原则"——是什么？

> **A**：47 个坏名字背后的心理模式：**"现在我知道它是什么——别人也能推导出来"**——这是"知识的诅咒"——你拥有上下文（你在写什么、为什么写、写了之后下一步要干什么）——你认为这个上下文是"显而易见的"——但实际上三个月后的你和任何新同事都没有这个上下文。
>
> 命名原则：**变量名必须表达"这是什么"——不依赖任何上下文。** 检查方法：把变量名单独抽出来——不给赋值语句——不给周围代码——问一个人"这是什么"——他能答对吗？能=通过。不能=重命名。`df1` -> "一个 DataFrame。" -> 不过——你在处理"清洗过的订单"还是"聚合后的城市汇总"？名字必须区分这些。

**Q6**：你在 README 里写了一张"迁移就绪度表"——这和在代码里写注释有什么区别？为什么表比注释更有价值？

> **A**：注释散布在各个函数中——需要在 N 个文件中搜索。表在一处汇总——一眼看到所有瓶颈——方便做"迁移优先级排序"——先迁移"数据量快接近阈值"的操作。而且表是给 PM/老板看的——注释是给同事看的——两者的读者不同——表达的抽象层级不同。表是"决策工具"——注释是"解释工具"——你需要两个。

### 🔧 补漏
### 🔧 补漏

- **5/5**：W10 过关——Hive 大数据工程的核心概念内化
- **3-4/5**：重读写错的题对应的 D 天
- **≤ 2/5**：回到 D3——Shuffle 是理解数据倾斜的地基——先理解 Shuffle——后面的加盐/调优/分区都是应用

---

> 📌 W10 完成。你现在能用 Hive 的分布式思维审查任何数据分析代码——知道哪些操作在数据量大时会成为瓶颈、为什么分区设计取决于查询模式而不是数据量、数据倾斜不是"运气不好"——是 hash 分配在数据不均时的必然结果——以及加盐不是神秘咒语——是打破 hash 规则的有理解基础的工程方案。