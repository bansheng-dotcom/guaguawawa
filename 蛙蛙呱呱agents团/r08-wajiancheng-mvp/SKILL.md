---
name: r08-wajiancheng-mvp
description: 产品实现官(MVP)角色技能。确定性本地输入校验及可演示工件；外部发布、生产部署和真实集成未接入，均不宣称已执行。
---

# R08 蛙建成 · 产品实现官 (MVP)
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/engineering/system-design/SKILL.md
>


把能力全景里的 **7 个能力域各自做成一个独立技能模块**（`skills/s01..s07`），
由一个薄调度器 `agent.py` 统一分发。每个技能都是纯标准库、独立可测的单元，
把「实现官的提示词/工作流」转成**确定性校验 + 门禁**，返回可 JSON 化的结果。

## Quick Start

```bash
python agent.py manifest                      # 协作契约 + 7 技能清单
python agent.py demo                          # 生成示例工件(slice/scaffold/landing/prototype)

python agent.py slice slice --input examples/slice.json      # S01 产品切片
python agent.py slice mvp --input mvp.json                   # S01 MVP 五门禁
python agent.py scaffold scaffold --input examples/scaffold.json  # S02 仓库脚手架
python agent.py scaffold spec --input spec.json              # S02 工程 Spec
python agent.py landing landing --input examples/landing.json # S03 落地页八要素
python agent.py landing form --input form.json               # S03 表单
python agent.py saas saas --input saas.json                  # S04 SaaS 脚手架
python agent.py saas email --input email.json                # S04 邮件脚手架
python agent.py prototype prototype --input examples/prototype.json  # S05 跨平台原型
python agent.py prototype screen --input screen.json         # S05 单屏
python agent.py design design --input design.json            # S06 设计系统
python agent.py design token --input token.json              # S06 Token
python agent.py qa qa --input qa.json                        # S07 质量验证
python agent.py qa handoff --input handoff.json              # S07 交接

python agent.py contract list                               # T6 7 技能机器可读契约
python agent.py contract validate --skill slice --action slice --output r.json
python agent.py review --result r.json --skill slice --action slice   # T7 对抗评审
python agent.py case list                                    # T8 案例库
python agent.py case validate --case landing-mvp
python agent.py harness slice --input slice.json            # 确定性验证器(硬门禁)
python agent.py harness verify --mvp mvp.json --qa qa.json
python agent.py run --task <task_id>                        # 协作入口
python agent.py local-check --input scaffold_inventory.json # 只读验收本地项目文件存在性
```

## 能力域 → 技能模块

| # | 能力域 | 子命令 | 真实执行的动作 | 整合自 |
|---|---|---|---|---|
| S01 | 产品切片MVP | `slice slice/mvp` | artifact_type 七类白名单 + slices 可验证假设 + MVP 五门禁 | makerskills |
| S02 | Spec转仓库 | `scaffold scaffold/spec` | 六类 stack + 目录树含入口 + 文件清单 + 鉴权合法 | makerskills |
| S03 | 落地页H5 | `landing landing/form` | 八要素 + 佐证≥3 + 五项技术约束 + 表单端点 | makerskills |
| S04 | SaaS邮件脚手架 | `saas saas/email` | 页面≥2 路由 + 鉴权 + 邮件模板/退订 | makerskills |
| S05 | 跨平台原型 | `prototype prototype/screen` | 六结构键 + feature 四层 + 平台白名单 + 单屏三件套 | flutter |
| S06 | 组件设计实现 | `design design/token` | tokens 三分类 + components 状态 + 主色/scale | makerskills |
| S07 | 质量验证交接 | `qa qa/handoff` | 五检查状态 + 无障碍 + 交接四要素 | makerskills |

## 协作契约

- **inputs**：`prd`（产品需求文档）、`ui_brief`（UI 简要）。
- **outputs**：`mvp`（可运行 MVP）、`page_assets`（页面资产）。
- 结果以一行 `__AGENT_RESULT__ {json}` 输出，供编排器以子进程方式消费。
- 协作入口 `run --task` 按**意图关键词 → 技能+动作**确定性路由（见 `_INTENT_ROUTES`），
  产物 `{skill}.json` 与 `mvp_report.md` 写回 `workspace/artifacts/{task_id}/`。

## 关键纪律（保留自 reference，校验环不丢）

1. 五门禁硬校验：MVP 缺 assumption/mvp/experiment/criteria/handoff 任一 gate 即 FAIL。
2. 枚举白名单外置：所有 stack/auth/平台/token 分类 从 thresholds.json 读，不硬编码。
3. 技术约束即契约：落地页五项技术约束任一 False 即 FAIL，不降级用重框架。
4. 吐多少由契约锁死：`contract validate` 用 JSON Schema 校验每次产出，不符即 FAIL。
5. 空泛/占位拦截：`review` 点名「待定/TODO/占位」无具体产物 → FAIL。
6. 不越界到生产工程：出现「生产级/CI-CD/灾备」且未声明 handoff → scope_creep FAIL。

## 边界

R08 做 MVP/跨端/页面可演示实现；生产工程·CI/CD·可靠性交 R09/R20；
视觉还原交 R10；后端真实支付/订阅交 R14；表单真实收集交 R13/R17。

## 详细参考（7 个模块）

- [模块A 产品切片与 MVP](references/01-slice-mvp.md)
- [模块B Spec 转仓库](references/02-scaffold-spec.md)
- [模块C 落地页与 H5](references/03-landing-h5.md)
- [模块D SaaS 与邮件脚手架](references/04-saas-email.md)
- [模块E 跨平台原型](references/05-prototype-cross-platform.md)
- [模块F 组件与设计实现](references/06-design-token.md)
- [模块G 质量验证与交接](references/07-qa-handoff.md)
