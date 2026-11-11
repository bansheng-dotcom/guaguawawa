# R12 蛙引流 · 增长运营官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/marketing/campaign-plan/SKILL.md
>


把「设计并验证可量化、可归因、可循环的增长系统」做成**本地可运行、可确定性校验**的角色 Agent。外部分析平台、广告投放、邮件发送及真实归因未接入，相关动作标记 simulated/blocked；可用 local-metric-check 对本地输入复算指标。
不真调 API / 不真投广告，而是把「该定什么口径、什么约束、什么证据」落成白名单 + 确定性算术 + 门禁。已引入真实执行层，不再仅仅是门禁校验。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 增长诊断与基线 | `diagnose` | `diagnose` / `unit` | 北极星一主一辅 + 漏斗五阶段枚举 + PMF 信号；LTV/CAC/回收期实算 |
| 增长循环与自然获客 | `loops` | `flywheel` / `content` | 飞轮五环闭环 + 内容渠道白名单 + 循环要素齐备 |
| 冷启动与外联 | `outreach` | `coldemail` / `sequence` | 冷邮件四要素 + AI 腔禁词 + 发送前合规 + 序列 3-5 封逐封新增价值 |
| 红人与合作增长 | `partner` | `influencer` / `comarketing` | 达人分级 + 披露合规 + 反刷量 + 联合营销五要素 |
| ASO 与发布 | `launch` | `aso` / `ph` | 标题/副标题上限 + 六维加权评分 + 发布清单 + 三阶段 |
| 付费投放与 CRO | `paid` | `media` / `cro` | 投放四要素 + ROI 实算 + 实验三件套 + 显著性门槛 |
| 激活留存推荐 | `retention` | `activation` / `referral` | aha 时刻 + 流失预警阈值 + K 因子实算 + 双边激励 |
| 归因与 RevOps | `revops` | `attribution` / `roi` | 归因模型枚举 + 去重口径 + 埋点字段 + CAC/LTV/回收期/ROI 实算 |
| 自媒体运营 | `selfmedia` | `daily` / `probe` | 多平台看板 + 日报结论规则 + 数据接入探测（如实降级） |

## 协作契约

- **inputs**：`content_draft` + `product`
- **outputs**：`growth_plan` + `channel_assets`
- 意图路由（`agent.py run --task`）：TAM/归因/CAC/LTV/ROI → revops；红人/达人/合作 → partner；
  ASO/应用商店/PH → launch；投放/付费/CRO → paid；冷邮件/外联/序列 → outreach；
  留存/激活/推荐/K 因子 → retention；飞轮/自然获客 → loops；日报/自媒体/看板 → selfmedia；
  兜底 → `diagnose/diagnose`。

## 运行

```bash
python agent.py manifest                      # 契约 + 9 技能清单
python agent.py diagnose diagnose --input examples/diagnose.json
python agent.py revops roi --input examples/roi.json
python agent.py harness runlog --n 5
python agent.py contract list
python agent.py case list
python run_tests.py                            # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **投放策略**归本角色 R12；**内容改写与发布清单**归 R11 蛙点题。
- **CRM 商机 / 续约 / 客服**归 R13 蛙客成，本角色只负责获客与培育线索。
- **数据口径**（统计显著性、埋点口径）交 R06；**市场数据采集**交 R05。
- **红线（不可越）**：
  1. **不刷单**——不产刷量/刷单/买粉/代刷/伪造评价/水军方案。
  2. **不伪造评价**——不生成假好评、机器点赞、互粉等误导性增长。
  3. **不未经授权采集个人信息**——涉及采集手机号/爬取个人信息/私信轰炸必须声明授权。

## 确定性校验口径

- 干净数据 → `ok=true` / exit 0；脏数据（非法枚举 / 刷单词 / 未授权采集 / 缺披露 / 算术不闭合）→ `ok=false` / exit 1。
- `probe`（selfmedia）恒 `ok=true`，缺数据只反映在 `status=blocked`（如实降级，探测非门禁）。
- 对抗评审五检查：`contract` / `no_fake_growth` / `privacy_gate` / `scope_boundary` / `concrete_artifact`。

---

## 外部能力（可选，见 references/external/）

以下外部能力（Trae 插件 / WorkBuddy 技能）的入口文档已拷入 `references/external/`，深层 references 与脚本仍以登记源目录为准：

- `marketing-toolkit` · 营销全链路工具箱（技能；消费方：r11, r10）

就绪状态：`python guagua.py capabilities --role r12 --probe`；
MCP 类需要 MCP 客户端接入，本团队 CLI 不直连。
