> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/incident-response/SKILL.md

# 模块4 · 复盘与事故分析





>








> 整合自 anthropics__knowledge-work-plugins 的 engineering/incident-response


> 与 runbook、operations/risk-assessment。


> 核心主张：**事故的价值取决于复盘的诚实度**——


> severity 定级、升级时限、根因、闭环窗四件事都有确定口径。





## 4.1 事后复盘门禁（s04/postmortem）





- **severity / urgency 1-5 分制**：越界即拦；sev≥4 属重大事故；


- **sev≥4 必须 30 分钟内升级**（`escalated_within` 事件在时限内），


  没升级事件的重大事故记录直接 FAIL（已验证负例）；


- **根因非空**：没有根因的事后报告 = 起尸报告，只有现象没有认知；


- **时间线单调**：事故时间线倒序/乱序即拦；


- **行动项**：每条带 `owner + due`，闭环窗 7 天——


  超窗未闭环的复盘在下次 `retro/action` 里变 CRITICAL。





## 4.2 五维打分（s04/grade）





预承诺标准打分五维：**目标 / 计划 / 执行 / 复盘 / 团队**。


每维达标与否对照事前写的标准，三态裁决：


- 全过 → `PASS`；


- 部分未达标 → `PARTIAL`（已验证算例：仅一维未达标）；


- **LOSS 未闭环 → FAIL**——输了还不上门禁补作业，


  同样的坑会再踩一次。





## 4.3 行动项追踪（s04/action）





- 过期行动项 = CRITICAL，不是 WARN——复盘的产出过期作废，


  等于白复盘；


- 汇总 `closure_rate`（闭环率），低于阈值的项目群在


  portfolio/status 里一起亮黄。





## 4.4 复盘与流程的闭环





复盘行动项里「补 SOP」类条目 → process/sop 固化成控制点；


「入库知识」类条目 → knowledge/entry 登记带指纹。


复盘不是终点站，是流程与知识两个能力域的供血源头。





## 4.5 实战踩坑





- severity 定级**就高不就低**：拿不准 3 还是 4 时按 4 处理——


  按 4 就会触发 30 分钟升级门禁，宁可多升不可漏升。


- 根因写「人为失误」不算根因——继续问「为什么会让人为失误发生」，


  起码问到流程/设计层。


- 五维打分的标准必须**事前写**（R01 decisionlog 的预承诺标准），


  事后补标准 = 自己给自己打分。


- 升级时限、闭环窗、severity 上限以 `experience/thresholds.json → retro`


  为准，本文不手抄数值。
