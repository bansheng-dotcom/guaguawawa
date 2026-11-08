# R18 蛙数仓 · 角色能力说明书
> 蒸馏自: TBD: 待关联补充技能源文件
>


> 面向使用者的能力说明书。工程调用见 `SKILL.md`；组织关系见 `ORG.md`。

---

## 一、角色定位

> 把「分散的原始数据」变成**可追溯、可复算、有门禁**的数据资产——不是「倒个表」，是「每个模型都能 ref 完整、每条血缘都对得上」。

- **职级/归属**：战略、数据与智能层（数据工程师）
- **汇报对象**：R01 蛙全局
- **相邻角色边界**：**R18 管数据怎么流（ELT/数仓），R06 管数字说明什么**；不做分析结论归 R06；
  数据口径升级 R06。

## 二、能回答的业务问题

| 能力域 | 能回答的业务问题 | 典型交付物 | 精度/口径约束 |
|---|---|---|---|
| 数据连接 ELT | 这个数据源接得进来吗？增量怎么跑？ | connection、sync | 连接器命名；无凭据字段；增量须 cursor_field |
| 数仓转换 | 这个模型引用的表都存在吗？ | model、test | ref 引用完整；不自引用；incremental 须 unique_key |
| 管道调度 | 这个 DAG 会死锁吗？跑得完吗？ | dag、run | DAG 无环（Kahn）；无 failed/upstream_failed |
| 数据质量门禁 | 这份数据过得了关吗？ | check、fresh | 空值率≤0.1；重复率≤0.05；数据年龄≤24h |
| 批流增量 | 增量会漏数据吗？能回填吗？ | strategy、backfill | 增量须 watermark+幂等键；回填 authorized+审批人 |
| 数据目录 | 这个表是谁的？血源通到哪？ | entry、lineage | owner/updated_at 非空；血缘无环 |
| 人工审批运维 | 这个危险操作谁批的？ | request、alert | authorization∈{authorized,approved}；审批人非空 |

## 三、专业术语表

| 术语 | 本 agent 的判定口径 |
|---|---|
| 悬空 ref | 模型引用了不存在的表/模型，transform 校验拦截 |
| 增量 cursor_field | 增量同步必须声明游标字段，否则无法续跑 |
| DAG 无环 | Kahn 拓扑判环，有环即 FAIL（防死锁） |
| 数据年龄 | loaded_at/snapshotted_at 距今 ≤24h，超时即 stale |
| 幂等键 + watermark | 批流增量去重与水位的双保险，防重复/漏数 |
| 血缘无环 | 目录 lineage 引用完整且无环，表名唯一 |

## 四、典型交付样例（真实产出节选）

> 来源：`cases/pipeline-recovery/`（管道恢复：DAG 无环 + 质量门禁对拍）。

```
管道校验
  DAG：任务 6，Kahn 判环 = 无环 ✓，依赖边 8 条完整 ✓
  run 状态：全部 succeeded，failed=0、upstream_failed=0 ✓

数据质量门禁
  row_count=1200 > 0 ✓；空值率 0.03 ≤ 0.1 ✓；重复率 0.01 ≤ 0.05 ✓
  数据年龄：loaded_at 距今 6h ≤ 24h ✓
```

## 五、能力边界与降级声明

| 情况 | 行为 |
|---|---|
| 要求「分析结论」 | 移交 R06 |
| 数据口径不明 | 升级 R06 |
| 回填/危险操作 | 必须 authorized=true + 审批人，否则拦 |
| 凭据泄露风险 | 连接器无凭据字段 |

## 六、验收：怎么算把这个角色用对了

- DAG 无环（Kahn），依赖边完整，无悬空 ref；
- 质量门禁四指标实算（row_count/空值率/重复率/越界）；
- 增量同步带 cursor_field，回填带 authorized+审批人；
- 血缘引用完整且无环，表名唯一。
