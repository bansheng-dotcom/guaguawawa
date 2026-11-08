> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/operations/capacity-plan/SKILL.md

# 模块2 · 容量与委派





>








> 整合自 anthropics__knowledge-work-plugins 的 operations/capacity-plan


> 与 productivity/task-management。


> 核心主张：**容量不是感觉，是加权账**——紧急任务带权重，


> 单项目占比有红线，超 8 小时的活不派整块。





## 2.1 加权负载（s02/check）





负载公式：`weighted = committed + urgent × 1.2`。


紧急任务天然带 20% 的上下文切换税，假装它和普通任务等价是排期失真的第一来源。





单项目红线：任何单一项目负载占比 > 50% 即 CRITICAL——


一个人被一个项目吃掉一半以上，说明缺人或缺范围裁剪，二选一。





已验证算例：蛙二 committed=30h + urgent=2h×1.2 = **32.4h** 加权。


超 `capacity` 上限即过载拦下。





## 2.2 派工门禁（s02/delegate）





派出去之前四查：


1. **>8h 必拆**——超 8 小时的任务直接派是「甩锅式委派」，先 `split`；


2. **blocked_by ≤ 2**——前置依赖超过 2 个的任务派出去只会干等，


   先解依赖或推迟派发；


3. **must_read ≤ 3**——要读的材料超过 3 份，说明背景交代不清；


4. **key_results ≥ 1**——没有关键结果的委派 = 没有验收标准，


   验收时会扯皮。





## 2.3 口径恒等拆分（s02/split）





拆分公式：`n = ceil(hours / 8)`，`base = round(hours / n, 2)`，


最后一份吸收取整误差：`Σ子任务 = 原任务`（口径恒等）。





已验证算例：20h → n=3 → **6.67 + 6.67 + 6.66 = 20.00**（Σ 恒等），


最大子任务 ≤8h；6h → 无需拆分。恒等式在 run_tests 有专项断言——


拆分前后工作量对不上，是排期黑洞的常见成因。





## 2.4 容量-排期联动





`capacity/check` 的结果直接进 `schedule/sprint`：过载的人不进排期池，


先减负载再排。harness 的 `verify` 综合门禁把两步串起来：


WBS 过白名单 → sprint 排日历 → capacity 查加权，


任何一步 FAIL 整链 FAIL。





## 2.5 实战踩坑





- 「紧急×1.2」的权重是**加在负载上**，不是加在工时上——


  2h 紧急任务算 2.4h 负载，但别把它拆成 2.4h 的任务卡。


- 单项目红线看的是**占比**不是绝对值：20h/30h 超红线，


  40h/100h 不超。


- `round(h/n, 2)` 的银行家舍入在极端值会有 ±0.01 误差，


  所以最后一份用减法兜底而不是也做 round。


- 紧急权重、8h 上限、红线百分比以 `experience/thresholds.json → capacity`


  为准，改口径不改代码。
