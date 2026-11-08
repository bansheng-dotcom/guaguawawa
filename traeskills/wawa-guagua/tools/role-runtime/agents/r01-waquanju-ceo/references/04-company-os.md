# 模块D · 公司治理与运营系统（Company OS）
> 蒸馏自: 补充技能/alirezarezvani__claude-skills/ceo-advisor.md
>


> 整合自 c-level-advisor 的 company-os、coo-advisor 的 ops_cadence、chief-of-staff 的 routing。
> 核心主张：**一个有效 OS 的六大组件缺一不可；记分卡 ≤15 个指标，看到红线只看红**。

## D1. 六大组件

1. **责任图**：一人一职能 owner（buck stops with one），无共享所有权，季度重审。
2. **记分卡**：5–15 个周度指标，每项有 owner + **数值目标**（非区间），红黄绿不写段落；
   周会只讨论红项。反例：40 个 KPI＝看数而非管数。
3. **会议节奏**：日站会 15min（只阻塞）；周领导层 L10 90min；月部门复盘；季度 1–2 天定 Rocks；
   年度 2–3 天定 1/3 年愿景。
4. **问题解决 IDS**（Identify→Discuss→Solve，单议题 ≤15min）：定真问题→限时讨论→一个 owner
   +一个动作+一个到期日。
5. **Rocks（90 天优先）**：每人 3–7 个，**二元**（done/not done，无「60% 完成」）。
6. **沟通节奏**：月全员书面 + 季 all-hands + 周领导面板 + 月董事会 memo + 每次发布客户说明。
   默认能分享就分享。

**OS 选型**：10–250 人运营混乱→EOS/Traction；高增长需层层下达→Scaling Up；假设驱动→OKR 原生；
扁平高自治→Holacracy；都不配→自定义杂交。

## D2. 周度 L10 议程（固定）

好新闻 5' → 记分卡 5'(仅红) → Rock 进度 5' → 客户/员工头条 5' → 问题清单 IDS 60' → 上期待办 5'
→ 收尾 5'(给会议打分 1–10，怎么到 10)。

## D3. 唯一事实来源（Single Source of Truth）

- **company-context.md**：公司现状，被 office-hours/brief/boardroom 自动加载。
- **STATE.md**：当前在哪个 Phase、活跃里程碑、哪些完成/待办——任何角色先读 STATE 再行动。
- 工件链（CONTEXT→RESEARCH→PLAN→SUMMARY→VERIFICATION）跨会话存续：**交接工件而非交接记忆**。
- 信息流：Async 为默认，sync 为例外；会前预读，未读无发言权。

## D4. 决策日志（两阶段留痕）

**两层记忆**：Layer1 原始议事录（全部辩论，**永不自动加载**，仅创始人显式调取，90 天归档）；
Layer2 已批准决策（唯一自动回灌未来的层，**append-only**）。

```
## [日期] — [议题标题]
**决策:** [一句]  **Owner:**  **Deadline:**
**理由:** 为何胜过替代
**用户覆写:** 若创始改建议——何因
**否弃:** - [提案] — [原因] [DO_NOT_RESURFACE]
**待办:** - [ ] ... — Owner — Due — Review
**取代/被取代:**
```

- 写前必查冲突：DO_NOT_RESURFACE 违规 / 同主题结论矛盾 / 动作归属歧义。
- `DO_NOT_RESURFACE` 硬执行：被否提案重提→BLOCKED；重开须创始人明说 reopen。

## D5. 复盘 Retro（闭环）

触发：90 天查点 / 杀死标准触发 / 决策被推翻 / 季度全量。对**预承诺标准**打分（WIN/PARTIAL/LOSS/
MIXED）；回访被保留的异议；假设审计；过程教训。LOSS 新增 boardroom 或 brief。
## 已验证算例（run_tests.py S05/S06/S07，已对拍）

- OS 门禁：删掉 `ids` 组件 + Rocks 状态写「60% 完成」→ `ok=false`（六组件缺一 + 非二元判定双双拦截）。
- 记分卡：`target="10-20"`（区间目标）+ 绿项（NPS）进议程 → fail——目标必须数值、议程只看红。
- IDS：缺 owner + `timebox_min=40` → fail（单议题 ≤15min）。
- 冷却锁四分支：pricing 20/60 天重议→拒绝；70/60 天→允许；杀死标准触发→允许；`founder_release=true` 但未留痕→CRITICAL。
- 决策日志：被否提案（DO_NOT_RESURFACE）重提 → CRITICAL 拦截；声明 `supersedes` → 放行；理由=复述决策 → fail。
- 复盘：事后补标准（pre_committed=false）打 LOSS 且未闭环 → fail。
- 董事会：miss 无归因 + 求助缺「向谁要什么」→ fail；陪练单视角+替创始人拍板（final_decision）→ fail。

## 实战踩坑

- 每人 Rocks 数量下限最初按「总量」写，跑样张才暴露应为「每人 3-7」——per-owner 统计，示例数据也得按 owner 攒够 3 个。
- 决策日志 `rationale` 门禁要同时判「非空 + 不等于 decision」：只判长度时「复述结论」能蒙混过关。
- 记分卡数量（5-15）、Rocks（3-7）、冷却锁天数（募资30/定价60/pivot90/裁员30）以 `experience/thresholds.json → companyos` 为准。

## 公司治理与组织操作系统 (Company OS)
- **文化与底线**：企业文化是当 CEO 不在场时员工的行为准则。
- **冷却锁 (Freeze Lock)**：
  - 项目资源超支或目标发生严重漂移时，CEO 应触发“冷却锁”，冻结执行动作，强制进入复盘。
- **核心记分卡 (Scorecard)**：监控 3-5 个跨部门北极星指标，而非陷入无限数据。
- **利益相关者顺位**：1.客户 2.团队 3.董事会/投资者 4.合作伙伴。
