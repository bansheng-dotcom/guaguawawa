# 模块B · 跨角色任务拆解与编排
> 蒸馏自: 补充技能/alirezarezvani__claude-skills/ceo-advisor.md
>


> 整合自 gsd-core 的 Phase Loop、wshobson/agents 的任务分解、claude-skills 的编排协议。
> 核心主张：**编排器必须瘦**；一个文件/一个职能只有**一个 owner**；一切带终止条件。

## B1. 编排总循环（GSD 五相环，防上下文腐化）

`Discuss → Plan → Execute → Verify → Ship`，每 Phase 走一遍：
Discuss 防「基于错误假设规划」；Plan 防「执行坏设计」；Execute 防串扰；Verify 防「交付跑偏」；
Ship 收口归档。

- **编排器只做四件事**：加载上下文 → 派发正确角色 → 回收结果 → 更新状态。不干重活、不写产出、
  不替执行者判断。
- **每角色干净上下文**：只给该角色需要的工件，不喂全历史（上下文隔离核心）。

## B2. 任务卡/WBS 模板（单一主责 + 接口契约）

```
## 任务 <名>
### 目标  1-2 句要构建什么
### 拥有文件  独占文件清单
### 需求  具体交付 1..n
### 接口契约  导出:<本流提供> / 导入:<从别流消费>
### 验收标准  - [ ] 可验证准则
### 明确不做
```

切法：**垂直切片**（按用户流）优先；按层（数据→业务→API）仅天然分层时用。

## B3. 角色职责边界（单一主责 DRI）

- 一个文件一个 owner；共享文件由 lead 持有并顺序应用他人改动。
- 一个职能一个 owner；「共同负责」＝没人负责。
- 界面契约先行：角色交界处先定类型/接口再动工。
- 分工：研究者(并行)→综合者→规划者→检查者(≤3 轮修订)→执行者(波内并行)→验证者；
  每角色只授最小工具权限。

## B4. 依赖管理与编排模式

- 依赖图 `blockedBy/blocks`；最小化依赖链深度；检测消除循环；沿关键路径排序。
- 波次并行（Wave）：无依赖→第 1 波并行；依赖第 1 波→第 2 波。
- 并发安全：共享状态写用原子锁（O_EXCL 锁文件，陈旧锁 10s 清除）。

## B5. 路由判定矩阵（意图→角色）

| 信号 | 路由 |
|---|---|
| burn/runway/fundraise/LTV/CAC | CFO |
| pipeline/win rate/quota | CRO |
| roadmap/PMF/JTBD/北极星/kill | CPO |
| cadence/OKR/scorecard/DRI | COO |
| 2+ 角色信号 | boardroom |
| 无法命中 | 先六问再路由 |

（本角色用关键字路由矩阵 `ROUTING` 落地，可替换为 LLM 规划器。）

## B6. 委派、验收与终止条件

- 委派协议 `[INVOKE:role|问题]`；回复必含 关键发现(一行)+支撑数据+置信度+一句 caveat。
- **死循环防护（硬规则）**：禁止自调用；**最大调用深度=2**；禁止闭环；每跳带调用链。
- 独立验收（Verify）：查需求覆盖、决策覆盖、目标对齐三缺一即不过。
- **验收 = 已完成定义**：完成≠无报错，而＝「所建=所规划=所决定」。
- 终止条件：成功标准全命中→收口；杀死标准触发→强制终止转复盘。
## 已验证算例（run_tests.py S02，已对拍）

- 任务卡负例：`owners=["r06","r07"]`（双主责）+ `non_goals=[]` → `ok=false`——「共同负责=没人负责」直接拦。
- 波次编排：t3 blockedBy [t1,t2] → 2 波（t1/t2 并行第 1 波）；构造 t1←t3←t1 环 → `cycle` 非空 + CRITICAL，退出码非 0。
- 路由：「帮我分析数据并修 Bug」→ 命中 r06+r09 → `boardroom=true`。

## 实战踩坑

- 循环检测必须在波次划分之前：有环时拓扑分层会死循环，先 DFS 三色标记截停。
- 依赖深度上限（max_wave_depth=6）与六段门禁字段以 `experience/thresholds.json → decompose` 为准。
- `decompose/route` 的 20 角色信号矩阵与编排器 `agent.py ROUTING` 同源维护，新增角色必须两处同步。

## 跨部门任务拆解 (Decompose Wave)
- **战略时间线 (Stage-adaptive time horizons)**：
  - Seed/Pre-PMF: 3 / 6 / 12 个月
  - Series A: 6 / 12 / 24 个月
  - Series B+: 1 / 3 / 5 年
- **波次规划 (Wave Planning)**：
  1. Keep the lights on (保底运营)
  2. Protect the core (防守核心业务)
  3. Grow the core (扩张核心业务)
  4. Fund new bets (探索创新业务)
- **任务卡 (Task Card) 生成规范**：明确目标 (Objective) -> 指定主理角色 (Owner) -> 指定协助角色 (Support) -> 前置依赖 (Dependencies)。
