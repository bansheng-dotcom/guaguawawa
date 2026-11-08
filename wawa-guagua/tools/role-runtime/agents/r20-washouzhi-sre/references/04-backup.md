# 04 · 加密增量备份口径（backup）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/productivity/skills/memory-management/SKILL.md
>


> 技能：`backup` ｜ 动作：`backup`（备份仓结构）、`snapshot`（快照清单/保留策略）
> 来源：restic__restic（repository、snapshot、keep_* 保留策略、加密仓、排除规则、增量去重）

## 第一层：方法论

备份层定义**备份什么、存哪里、怎么保留、怎么加密**。把这段做成确定性校验的
价值，不在于"备得更满"，而在于**让未加密的仓库和找不到唯一来源的快照进不了
恢复流程**——一个 encrypted=false 的备份仓，等于把数据明文裸奔；一份 id 重复
的快照清单，等于恢复时不知道该信谁。

三条方法论：

1. **备份仓是「恢复的地基」，不是「占空间的副本」**。本角色只校验备份仓与
   快照清单结构是否成立，不实际执行 restic 备份、不持有仓库密码（红线 1：
   凭据绝不出现在产出）。
2. **加密是硬要求**。restic 默认加密，未声明 `encrypted=true` 的备份仓不可信。
   这不是可选项，是备份能进恢复流程的前提。
3. **快照必须有唯一可定位的来源**。snapshot_id 唯一 + ≥1 份，恢复才能"恢复
   到哪一份"讲清楚。id 重复 = 恢复目标模糊。

**本角色只校验备份仓与快照清单，不执行备份/恢复/删除**。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| repo | 非空字符串 | 备份仓路径 |
| encrypted | 必须为 true | 加密声明 |
| excludes | 字符串列表（每项非空） | 排除规则 |
| snapshots | ≥ `backup.min_snapshots`（默认 1） | 快照清单 |
| 每快照 | 含 snapshot_id/ts 两字段 | 快照结构 |
| snapshot_id | 唯一 | 快照去重 |
| retention_policy | ∈ `backup.retention_policies`（keep_last/hourly/daily/weekly/monthly/yearly） | 保留策略枚举 |

**阈值单一真源**：`backup.retention_policies` / `backup.min_snapshots` 以
`experience/thresholds.json` 的 `backup` 段为准。

## 第三层：已验证的算例

**算例 A（干净备份仓）**：`examples/backup.json`
```
repo=/backups/repo / encrypted=true / excludes=["/tmp","/cache"]
```
repo 非空、加密声明、排除规则为字符串列表 → `ok=true`，`verdict=PASS`。

**算例 B（脏备份仓）**：`examples/backup_dirty.json`
```
repo="" / encrypted=false / excludes=["/tmp"]
```
BLOCKER ×2：`backup.repo` 空 + `backup.encrypted` 未加密。加密是硬要求。

**算例 C（快照清单）**：`examples/snapshot.json` vs `snapshot_dirty.json`
```
snapshots=[{snap-001},{snap-002}] + retention_policy=keep_daily → PASS
snapshots=[{snap-001},{snap-001}]                               → id 重复，FAIL
```
快照 id 必须唯一。`snapshot_id` 回写首快照 id，`snapshot_count` 回写 2。

## 第四层：实战踩坑

1. **encrypted 判据用 `is True` 而非 truthy**。`encrypted="yes"`、`encrypted=1`
   都会被 `is True` 拦下。上游序列化把布尔写成字符串是高频坑（R07 踩坑），
   这里用严格布尔只认真 true。

2. **excludes 判据拆两条：`isinstance(list)` + 每项非空字符串**。`excludes=[]`
   是合法的（不排除任何东西），`excludes="[/tmp]"`（字符串）不合法——一个
   字符串会被误当成单个路径，排除逻辑失效。

3. **snapshot_id 回写首快照 id，snapshot_count 回写数量**。`concrete_keys`
   同时含 `repo`/`snapshot_id`/`snapshot_count`，保证快照产出过得了评审的
   concrete_artifact 检查（R15 教训：concrete_keys 绝不能含 ok/checks）。

4. **retention_policy 缺失不拦，出现但越界才拦**。`policy is not None` 才进
   判据。这是为了兼容"上游只给快照清单不给保留策略"的协作场景——保留策略
   可选，但给了就必须在白名单里。

5. **min_snapshots 外置但默认 1**。restic 一个仓库至少该有 1 份快照才有意义。
   若某案例需要"至少 3 份"（如合规要求），改案例级 thresholds 即可，判据
   自动跟随——这就是 T9 阈值外置的价值。
