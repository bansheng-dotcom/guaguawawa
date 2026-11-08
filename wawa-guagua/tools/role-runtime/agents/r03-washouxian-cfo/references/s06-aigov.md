# S06 AI 治理与披露
> 蒸馏自: 补充技能/01-当前能力域/alirezarezvani__claude-skills/compliance-os/SKILL.md
>


## 方法论（来源 compliance-os framework_selector / audit_simulator + EU AI Act 口径）

### 适用框架决策树（aigov.frameworks）

| 框架 | binding | 触发 |
|---|---|---|
| GDPR | legal | 处理欧盟数据主体的个人数据 |
| ISO 27001 | contract | 企业客户 / 认证需求 |
| SOC 2 | contract（依赖 ISO 27001） | 美国企业客户 SaaS |
| ISO 42001 | voluntary（依赖 ISO 27001） | 开发或部署 AI |
| EU AI Act | legal（依赖 ISO 42001） | AI 面向欧盟市场/用户 |
| HIPAA | legal | 处理 PHI |
| FDA QSR | legal | 医疗器械软件 |
| NIS2 | legal（依赖 ISO 27001） | 欧盟关键实体 |
| NIST CSF | voluntary | 美国政府客户 |

排序规则：legal → contract → voluntary；被选框架的依赖必须同时入选
（合规是一棵依赖树，不是清单）。

### AI 系统四级分类（aigov.aiclassify，EU AI Act）

1. **prohibited（禁止）**：社会评分、实时生物识别（执法）、
   职场情绪推断、无差别面部抓取 → 直接下线
2. **high（高风险）**：招聘筛选、信用评分、教育录取、基本服务、
   执法、移民边境、生物分类 → 须合规评定 + 人类监督
3. **limited（有限/透明义务）**：与人交互或生成内容 → 须披露
4. **minimal（最小）**：其余

### 披露四要素（aigov.disclose）

1. 披露 AI 身份（交互式 AI 须会话开始即披露）
2. 生成内容标识
3. 人工监督点
4. 申诉渠道

### 跨框架映射（compliance-os）

控制点可跨框架复用：access_control 同时映射 ISO 27001 / SOC 2 /
ISO 42001 / GDPR / NIST CSF / NIS2 / HIPAA——一份证据多框架用，
统一证据清单降低认证成本（证据池见 S07）。

## 已验证算例（run_tests.py T11，已对拍）

- **frameworks 依赖树**：`examples/aigov_frameworks.json` →
  `legal_frameworks=2`（GDPR + EU AI Act 均 legal）。选 EU AI Act 必须
  同时选其依赖 ISO 42001，选 ISO 42001 又依赖 ISO 27001——
  **被选框架的依赖必须同时入选**，否则 `ok=false`。
- **aiclassify**：招聘筛选场景 → `level=high`（高风险，须合规评定+人类监督）；
  社会评分/实时生物识别 → `level=prohibited` → `ok=false`（直接下线）。
- **disclose**：`examples/aigov_disclose.json` 四要素齐全 → `ok=true`。

## 实战踩坑

- 合规是**依赖树不是清单**：只选 EU AI Act 不带 ISO 42001/27001，
  框架链断裂，认证白做——frameworks 动作会明确报缺失依赖。
- prohibited 不是「整改后可用」：命中即下线，没有缓解路径。
- 披露四要素缺一不可，尤其「人工监督点」和「申诉渠道」最易漏——
  只披露「本内容是 AI 生成」不满足四要素。
