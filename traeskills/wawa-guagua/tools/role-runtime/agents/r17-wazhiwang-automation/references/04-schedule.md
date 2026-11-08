# 参考层 04 —— 定时与批处理（one-off-operations / compositional-workflows）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/productivity/skills/task-management/SKILL.md
>


> 来源：n8n-io__n8n `packages/@n8n/instance-ai/skills/one-off-operations` +
> `compositional-workflows`
> 角色：R17 蛙织网 · S04 schedule 的确定性口径来源。

## 第一层 · 方法论

定时与批处理是自动化的「心跳」：定时同步、日报、提醒、对账、补偿任务。n8n
的调度器支持两类：**cron**（表达式）与 **interval**（固定间隔分钟）。无论哪种，
两条铁律：

1. **时区显式声明**：不写 timezone 的调度在不同环境跑出不同触发时刻，是生产
   事故高发区。
2. **跨 run 状态靠持久表，不靠内存**：日报/摘要必须**读回历史行**（从 Data
   Table 查上一周期数据），不能在单次 run 的内存变量里编摘要——因为每次 run
   是独立进程，内存不跨 run 存活。

批处理则要处理**部分失败**：一批 N 条数据，可能 45 条成功、5 条失败。失败批次
必须有**补偿声明**（compensation）或**人工恢复路径**（handoff），否则失败就
永久丢失。

## 第二层 · 可执行口径（判据 | 口径 | 取值来源）

| 判据 | 口径 | 取值来源 |
|---|---|---|
| 调度类型 | cron/interval/manual 三选一 | n8n scheduleTrigger |
| cron 段数 | 5 或 6 段 | cron 表达式规范 |
| interval 下限 | ≥ 1 分钟 | n8n interval 最小粒度 |
| timezone | 非空 | 时区显式声明铁律 |
| 日报读回 | kind ∈ {daily,digest,report} 时 read_back=True | n8n 跨 run 状态 |
| 批次 id | 非空且唯一 | 批处理幂等 |
| 批次状态 | pending/running/succeeded/failed/partial/dead_letter/retrying | R17 阈值 |
| 失败补偿 | 失败批必须有 compensation 或 handoff | n8n 恢复路径 |

## 第三层 · 已验证算例

**干净调度**：
```
schedule_type=cron, cron="0 9 * * 1-5", timezone=Asia/Shanghai, kind=daily, read_back=True
```
门禁：cron 5 段 + 时区非空 + daily 类已读回历史行 → PASS。

**脏调度**：
```
schedule_type=interval, interval_minutes=0, timezone=Asia/Shanghai, kind=daily, read_back=False
```
门禁：`interval_minutes=0 < 1` + `daily 类未声明 read_back` → FAIL。

**脏批处理**：
```
batches=[{batch_id: b1, item_count: 50, status: failed}]，无 compensation
```
门禁：`失败批 b1 无补偿/人工恢复路径` → FAIL。

## 第四层 · 实战踩坑

1. **cron 段数 5 与 6 都合法**：5 段是标准 `分 时 日 月 周`，6 段多一个「秒」。
   只校验 5 段会把秒级 cron 误杀。
2. **interval=0 不是「立即执行」而是死循环**：0 分钟的间隔会让调度器疯狂触发，
   必须拦。下限设 1 分钟。
3. **`failed` 之外还有 `partial` 和 `dead_letter`**：部分失败和进死信队列的批次
   同样需要补偿路径，不能只查 `failed`。
4. **read_back 是布尔门禁不是文本**：用 `data.get("read_back") is True` 严格判，
   别用 `if data.get("read_back")`（字符串 `"false"` 也是真值会误放行）。
