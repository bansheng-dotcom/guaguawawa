# Workflow Triage

> 用途：记录本轮把散落 md 文件重新归类的判断。原则是以 workflow/subagent 为主体，散文件只作为 references、templates 或注册表存在。

## 1. 处理原则

| 判断 | 动作 |
| --- | --- |
| 已有 workflow 能完整覆盖 | 融合进该 workflow 的 `references/` 或 `templates/`，根目录删除旧入口 |
| 不能被已有 workflow 覆盖，但属于 PM 核心能力 | 新建目录化 workflow |
| 只是输出格式 | 放入所属 workflow 的 `templates/` |
| 只是偏好或复盘格式 | 放入 `user/` 或 `experience/` |
| 价值不确定 | 说明用途，等用户决定是否保留 |

## 2. 本轮新建为正式 workflow 的能力

| Workflow | 为什么不能直接删 | 能带来什么 |
| --- | --- | --- |
| `controller` | 没有其他 workflow 负责“先理解、少追问、路由、选最小产物” | 防止总控把所有任务都跑成重流程 |
| `pm-thinking` | PRD/需求报告都发生在方向较清楚之后，不能替代早期质问 | 提供轻量 grill-me 能力，少问但能把想法推进 |
| `report-production` | `project-briefing` 只解决项目汇报，不覆盖所有正式报告 | 处理报告类型、证据、视觉和本地轻量能力边界 |
| `project-briefing` | 普通报告流程不能覆盖“理解项目 + 理解用户 + 辅助决策 + 归档” | 让汇报更有人感，给选项利弊和归档位置 |
| `demand-management` | PRD 报告不等于正式开发输入 | 统一需求编号、需求卡、下游文件和协作复核状态 |

## 3. 本轮融合掉的旧入口

| 原文件 | 融入位置 | 说明 |
| --- | --- | --- |
| `PM轻量反应与工作流选择.md` | `workflows/controller/references/light-reaction-guide.md` | 成为 controller 的参考规则 |
| `PM总控路由流程.md` | `workflows/controller/references/pm-routing-guide.md` | 成为 controller 的路由参考 |
| `PM质问与思考流程.md` | `workflows/pm-thinking/references/pm-thinking-guide.md` | 成为 pm-thinking 的方法参考 |
| `PM报告生产流程.md` | `workflows/report-production/references/report-production-guide.md` | 成为 report-production 的报告质量参考 |
| `项目理解与汇报流程.md` | `workflows/project-briefing/references/project-briefing-guide.md` | 成为 project-briefing 的人感汇报参考 |
| `需求管理与协作审核流程.md` | `workflows/demand-management/references/demand-management-guide.md` | 成为 demand-management 的正式需求管理参考 |
| `PRD到执行需求融合流程.md` | `workflows/demand-management/references/prd-to-execution-guide.md` | 成为 PRD 转执行包的参考 |
| `外部PM框架融合流程.md` | `workflows/prd-report/references/external-framework-fusion-guide.md` | 不再单独触发，作为 PRD 报告的参考材料 |
| `腾讯产品法产品决策流程.md` | `workflows/product-strategy/references/tencent-product-decision-flow.md` | 不再作为根流程，作为产品战略/判断参考 |

## 4. 待用户决定

当前没有必须单独等待你审批的散 md。

如果你希望进一步瘦身，下一轮可以决定是否把 `report-production` 和 `project-briefing` 合并；我目前建议先不合并，因为一个管“报告生产质量”，一个管“项目理解和决策沟通”。
