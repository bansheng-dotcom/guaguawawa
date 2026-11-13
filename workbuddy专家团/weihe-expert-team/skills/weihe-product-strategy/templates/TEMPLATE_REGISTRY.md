# Template Registry

> 用途：登记模板归属。`templates/` 根目录不再堆放具体模板；具体模板放回使用它的 workflow、user 或 experience 目录。

## 归属表

| 模板 | 当前路径 | 归属 | 用途 |
| --- | --- | --- | --- |
| PRD 人机翻译模板 | `workflows/prd-report/templates/prd-human-machine-template.md` | `prd-report` | 把用户语言转成 PRD 草稿和机器可执行说明 |
| 产品发现到 PRD 融合模板 | `workflows/prd-report/templates/product-discovery-to-prd-template.md` | `prd-report` | 外部 PM 框架、样例 PRD、本地 PRD 的融合对照 |
| PRD 红队与预演失败模板 | `workflows/prd-report/templates/prd-red-team-premortem-template.md` | `prd-report` | 攻击承重假设、预演失败和发布门禁 |
| 用户故事与测试场景模板 | `workflows/acceptance-test/templates/user-story-test-scenario-template.md` | `acceptance-test` | User Story、Job Story、WWA、测试场景 |
| 产品需求提交模板 | `workflows/demand-management/templates/product-requirement-submit-template.md` | `demand-management` | 正式需求卡 |
| 协作能力复核确认模板 | `workflows/demand-management/templates/collaboration-capability-review-template.md` | `demand-management` | 记录协作能力复核状态，不绑定具体 agent |
| 人类可读汇报模板 | `workflows/project-briefing/templates/human-readable-briefing-template.md` | `project-briefing` | 用户能看懂、能决策的项目汇报 |
| 设计产出审阅模板 | `workflows/ui-brief/templates/design-output-review-template.md` | `ui-brief` | PM 初审设计/前后端/Agent 产出是否满足产品目标 |
| 腾讯产品法审查清单 | `workflows/product-strategy/references/tencent-product-review-checklist.md` | `product-strategy` | 产品判断和方案审查清单；它是参考，不是输出模板 |
| 用户偏好记录模板 | `user/templates/user-preference-record-template.md` | `user` | 记录跨项目用户偏好 |
| 经验卡模板 | `experience/templates/experience-card-template.md` | `experience-rag` | 把可复用产品判断、纠错、偏好和协作规则提炼成 RAG 经验卡 |
| 纠错复盘模板 | `experience/templates/correction-retrospective-template.md` | `experience` | 记录纠错、下次规则和适用范围 |

## 使用规则

- 先看 workflow 的 `workflow.yaml`，再读取对应 `templates/`。
- 模板不能绕过 workflow 单独使用。
- 新模板必须有唯一归属；如果多个 workflow 都会用，优先放到更上游的 workflow 或拆成参考规则。
- 偏好和纠错不属于报告模板，分别进入 `user/` 和 `experience/`。
