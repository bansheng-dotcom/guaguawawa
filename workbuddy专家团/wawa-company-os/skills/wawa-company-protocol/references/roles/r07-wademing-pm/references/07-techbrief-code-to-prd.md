# 模块G · 技术翻译与代码反推需求（S07）
> 蒸馏自: 补充技能/product-manager/SKILL.md 及相关 workflow
>


## 一、方法论

什么时候用：要把「工程能做什么/代码里有什么」翻译成「产品语言」，或反过来从代码/UI
反推出需求结构时。核心是**翻译不越界**——产品只做语言转换，工程实现交 R09、视觉交 R10。

- **技术翻译（Technical Brief）五模块**：用户影响 / 前端影响 / 后端影响 / Agent 影响
  （输入·输出·工具·记忆·停止条件）/ 失败兜底（谁查 / 怎么恢复 / 人工处理）。
- **UI Brief 五模块**：页面目标 / 信息架构 / 用户动作 / 状态（空态·加载·成功·失败·
  权限）/ 审查重点。
- **代码反推需求（Code → PRD）**：逐页（概述/布局/字段清单/交互逻辑/接口依赖）+
  接口（区分已接入/未接入，必填 method/path/business_logic）。
- **发布门禁（Release Gate）**：三个时刻（阶段完成 / 推送部署分支 / 生产 promotion），
  任一阻断项即 no-go。

## 二、可执行口径（与 skills/s07_techbrief.py 逐字对齐）

阈值一律以 `experience/thresholds.json` 为准，键名如下：

| 校验 | 读 thresholds.json 键 | 判读 |
|---|---|---|
| 技术五模块 | `techbrief.tech_modules`（5 枚举） | 缺任一 → BLOCKER |
| 失败兜底 | 无阈值（固定） | who_investigates/recovery/manual_handling 俱全 |
| UI 五模块 | `techbrief.ui_modules`（5 枚举） | 缺任一 → BLOCKER |
| UI 状态 | 代码内固定 5 态 | empty/loading/success/failure/permission 俱全 |
| 代码反推页面 | 无阈值（固定） | pages 非空，每页 name+overview，字段 name+type |
| 代码反推接口 | 无阈值（固定） | method+path+business_logic 俱全 |
| 发布门禁 | 无阈值（固定） | status ∈ pass/ok/yes/go 通过；fail/block/blocked/no 阻断 |

输出键（contracts.py `techbrief` 契约）：`ok`、`checks` + 动作专属：
- `techbrief` → `modules`
- `uibrief` → `ui_modules`、`states_required`
- `codetoprd` → `page_count`、`api_count`
- `releasegate` → `decision`、`blocker_count`、`check_count`

## 三、已验证算例（只写 run_tests.py 真实跑过的数字）

| 算例 | 输入 | 结果 |
|---|---|---|
| 技术五模块 | `examples/techbrief.json`（5 模块 + failure 三字段） | ok=true |
| UI Brief | 5 模块 + 5 状态 | ok=true |
| 代码反推 | 1 页（1 字段）+ 1 接口 | ok=true |
| 发布门禁 go | 2 项 pass | ok=true，decision=go |
| 发布门禁阻断 | 1 项 security block | ok=false，decision=no-go |

## 四、实战踩坑

1. **技术翻译的「降级不越界」是契约，不是口头**：`techbrief` 只做产品语言翻译，
   若文本出现「生产级/高可用/CI-CD」却未声明 `handoff` 交接，review 的 scope_boundary
   （对齐 R08 的 concrete_artifact/scope_boundary）会判 FAIL——本角色边界写进
   SKILL.md「工程实现交 R09」。
2. **UI 状态是硬 5 态**：`_uibrief` 要求 states 含 empty/loading/success/failure/
   permission 五个 key，缺一个就 BLOCKER——即使业务页面「没有权限态」也要显式标
   `permission: false` 之类占位，别漏。
3. **接口要区分「已接入/未接入」**：`_codetoprd` 对 apis 只强制 method/path/
   business_logic 三字段，但 reference 层要求「区分已接入/未接入」——这是软约束，
   靠 review 兜底，代码层不硬拦。
4. **发布门禁 status 匹配大小写不敏感**：`str(status).lower()` 后匹配，写 `PASS`/
   `Pass` 都认；但 `pending`/`unknown` 既不算 pass 也不算 blocker，会被静默忽略——
   判读时留意「没覆盖到的状态」不会被算进 blocker_count。
