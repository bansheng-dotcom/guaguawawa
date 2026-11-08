# 05 · 恢复演练口径（restore）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/skills/runbook/SKILL.md
>


> 技能：`restore` ｜ 动作：`restore`（恢复请求）、`drill`（恢复演练记录）
> 来源：restic__restic（restore 语义：file/directory/snapshot/config）+ R20 恢复演练纪律

## 第一层：方法论

恢复层定义**恢复什么、能否恢复、演练证据是什么**。把这段做成确定性校验的价值，
不在于"恢复得更快"，而在于**让无源快照的恢复请求和没证据的成功声明进不了生产**
——一个 snapshot_id 为空的恢复请求等于凭空恢复；一条 `result=success` 却没
checksum 的演练记录等于自我安慰。

三条方法论：

1. **备份存在 ≠ 恢复成功**（能力全景 R20 边界原话）。本角色只校验恢复请求
   结构与演练记录是否成立，不实际执行 restic restore、不声称"一定能恢复"。
   恢复能力必须靠演练出证据才算数。
2. **恢复必须指向真实快照**。snapshot_id 为空 = 无源恢复，直接拦。
3. **"声明成功"必须有可验证证据**。`result=success` 必须带 checksum 一致性
   证据 + `restored_count>0`。声明成功却无文件数/校验和 = 不可信。

**本角色只校验恢复请求与演练记录，不执行恢复**。

## 第二层：可执行口径

| 判据 | 口径 | 取值来源 |
|---|---|---|
| restore_id | 非空字符串 | 恢复请求标识 |
| target | ∈ `restore.restore_targets`（file/directory/snapshot/config） | 恢复目标枚举 |
| snapshot_id | 非空（指向真实快照） | 源快照 |
| 授权声明 | authorized/drill/approver/handoff 任一非空 | 红线 2：不擅自恢复生产 |
| drill_id | 非空字符串 | 演练标识 |
| restored_count | > 0 | 恢复文件数（证据） |
| result | ∈ {success, failure} | 演练结果 |
| checksum_match（success） | 非空或 true | 校验和一致性证据 |

**阈值单一真源**：`restore.restore_targets` 以 `experience/thresholds.json` 的
`restore` 段为准。

## 第三层：已验证的算例

**算例 A（干净恢复请求）**：`examples/restore.json`
```
rst-001 / target=snapshot / snapshot_id=snap-002 / authorized=true
```
target 白名单、源快照非空、授权声明 → `ok=true`，`verdict=PASS`。

**算例 B（脏恢复请求）**：`examples/restore_dirty.json`
```
rst-001 / target=snapshot / snapshot_id="" / authorized=false
```
BLOCKER ×2：`restore.snapshot` 源快照空 + `restore.authorized` 未授权。

**算例 C（演练记录）**：`examples/drill.json` vs `drill_dirty.json`
```
drill-001 / restored_count=150 / result=success / checksum_match=true → PASS
drill-001 / restored_count=0   / result=success / checksum_match=false → FAIL
```
restored_count 必须 >0；result=success 必须带 checksum 证据。

## 第四层：实战踩坑

1. **授权声明是四选一，不是四选全**。`authorized`/`drill`/`approver`/`handoff`
   任一非空即视为"已声明授权"。这是为了让"演练"场景（drill）与"正式恢复"
   场景（authorized+approver）共用同一判据。判据写 `bool(...) or bool(...)`
   的或运算，不是与。

2. **checksum 判据也认"非空字符串"**。`checksum_match="sha256:abcd..."` 和
   `checksum_match=true` 都放行——因为上游可能给校验和值而非布尔。但
   `checksum_match=false`（显式假）会被拦：声明 success 却给假证据，更可疑。

3. **restored_count 用 `c._num` 而非 `int`**。上游给 `"150"`（字符串）也能
   通过——`_num` 做浮点转换。但 `restored_count=0` 归 0，被 `>0` 判据拦。
   这是 R07 类型松绑教训在 R20 的复现。

4. **drill 的 result=failure 不触发 checksum 判据**。失败演练记录的是"为什么
   失败"，不需要 checksum。判据写在 `if result == "success"` 条件里。

5. **restore 与 drill 是两个独立动作**。restore 是"准备恢复"的请求校验（前置
   授权），drill 是"演练结果"的记录校验（事后证据）。两者组合起来才是完整
   的恢复纪律：先授权、再演练、出证据。
