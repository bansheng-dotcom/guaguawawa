# 分层、物化与测试写法（pipeline-modeling）

> 被 §3、§5、§7 按需引用。版本：v2.0.0（项目自建，v1）

---

## 一、三层分工（越界就会让管道变慢且难维护）

| 层 | 只做 | 绝不做 | 默认物化 |
|---|---|---|---|
| `staging` | 对齐上游、重命名、类型转换、去重 | 聚合、业务逻辑、跨表 Join | `view` |
| `intermediate` | 中间聚合、连接、业务逻辑 | 直接给业务方消费 | `view` / `ephemeral` |
| `mart` | 面向分析/应用的最终宽表 | 跨域大 Join、复杂计算 | `table` |

**判断规则**：如果一张模型的输出会被人直接拿去画图，它就在 mart；
如果它只被其它模型引用，它就是 intermediate。

---

## 二、物化策略选择

| 物化 | 适合 | 代价 | 常见误用 |
|---|---|---|---|
| `view` | staging、轻量中间层 | 每次查询都重算 | mart 用 view → 报表慢 |
| `table` | mart、重计算 | 全量重建耗时 | staging 用 table → 构建爆炸 |
| `incremental` | 大表按时间追加 | 需要去重键 + 回填 | 无去重键 → 重复行 |
| `ephemeral` | 纯 SQL 片段复用 | 不进库、不可查 | 当 mart 用 → 无法排查 |

**铁律**：全部用 `table` 是最常见的性能事故来源——构建时间随模型数指数增长。

---

## 三、四类测试（前三类必须覆盖）

```json
{
  "model": "fct_orders",
  "tests": [
    {"type": "unique", "column": "order_id"},
    {"type": "not_null", "column": "order_id"},
    {"type": "accepted_values", "column": "status", "values": ["pending", "paid", "canceled"]},
    {"type": "relationships", "column": "user_id", "to": "dim_users.user_id"}
  ]
}
```

| 类型 | 必加位置 | 漏了会怎样 |
|---|---|---|
| `unique` | 每张 mart 主键 | 行数翻倍，指标全错 |
| `not_null` | 主键 + 业务必需字段 | 分组出现"未知"桶 |
| `accepted_values` | 所有枚举字段 | 上游加新值，报表静默多一行 |
| `relationships` | 有外键的模型 | 孤儿行，Join 后丢数据 |

### 为什么 `unique` 必须配 `not_null`

多数 SQL 里 `unique` 允许多个 NULL 共存——主键可以有多个空值还"通过"唯一性测试。
**两个测试一起加才算真的唯一。**

---

## 四、DAG 与依赖

| 检查 | 规则 |
|---|---|
| 无环 | 依赖图必须是 DAG；出现环说明设计有误 |
| 显式 | 依赖写在模型定义里，不靠"恰好先跑" |
| 方向 | staging → intermediate → mart；**不允许反向** |
| 扇出控制 | 单个 intermediate 被 10+ mart 依赖时考虑拆分 |

**隐式依赖的危险**：靠执行顺序"碰巧能跑"的管道，一旦加并行或改调度就会挂，
而且挂得毫无线索。

---

## 五、增量与回填

```json
{
  "model": "fct_events",
  "materialization": "incremental",
  "unique_key": ["event_id"],
  "strategy": "merge",
  "lookback_days": 3
}
```

| 要素 | 要求 |
|---|---|
| `unique_key` | 必填；merge/delete+insert 都靠它去重 |
| `strategy` | `append`（只追加）/ `merge`（更新）/ `delete+insert`（重算窗口） |
| `lookback_days` | 迟到数据窗口；没有它，晚到的事件永远进不来 |
| 回填方案 | 历史数据怎么补、补哪个区间、影响哪些下游 |

**没有回填方案的增量模型不许上生产**——出错时你无法修复，只能全量重跑。

---

## 六、与门禁的对应关系

| 门禁 | 覆盖哪一节 | 判不了什么 |
|---|---|---|
| `harness.py model` | §二 物化白名单、粒度字段 | 判不了分层是否合理 |
| `harness.py test` | §三 测试类型与枚举值 | 判不了测试是否加在正确字段上 |
| `harness.py dag` | §四 无环与依赖声明 | 判不了业务依赖该不该存在 |

> 门禁保证"定义合法、图无环、测试在"，**保证不了"数据是对的"**。
> 数据本身的质量归 `r06` 的 `data-validation`。
