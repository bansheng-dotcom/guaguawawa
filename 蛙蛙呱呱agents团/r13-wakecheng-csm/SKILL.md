# R13 蛙客成 · 客户成功与销售运营官
> 蒸馏自: 补充技能/01-当前能力域/anthropics__knowledge-work-plugins/sales/SKILL.md
>


把「客户从线索到续约的全生命周期运营」做成**本地可运行、可确定性校验**的角色 Agent。增加 `local-crm-csv` 仅对本地导出 CSV 清洗、去重和计算漏斗；不写入 CRM 或发送任何消息。
不真连 CRM / 不真发消息，而是把「该定什么口径、什么约束、什么证据」落成白名单 +
确定性算术 + 门禁。

来源仓库：`twentyhq__twenty`（CRM 对象与销售阶段）、`chatwoot__chatwoot`（会话/SLA/CSAT）、
`formbricks__formbricks`（问卷题型与 NPS 三桶）。

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 客户与联系人管理 | `crm` | `person` / `company` | 人员必填 + 生命周期枚举 + 渠道白名单 + 时间线时序单调；公司↔人员↔商机引用完整 |
| 销售管道 | `pipeline` | `pipeline` / `opp` | 七阶段枚举 + 加权管道值 Σ(金额×阶段概率) + 停滞识别 + 客户集中度 HHI |
| 销售活动与跟进 | `activity` | `activity` / `log` | 活动类型白名单 + 承诺三件套 + 逾期日差实算 + 开放商机活动覆盖 |
| 全渠道客服 | `support` | `inbox` / `ticket` | 渠道/状态枚举 + 首响 ≤240min + 解决 ≤48h + 重开率 ≤0.15 + CSAT 均值 ≥4.0 + 私有备注隔离 |
| 客户反馈与 VOC | `voc` | `survey` / `voc` | 官方 17 种题型白名单 + NPS 三桶实算（P≥9 / D≤6）+ 样本量 10 + 响应率 ≥0.1 + 主题词频 |
| 客户健康与续约输入 | `health` | `health` / `risk` | 四维加权健康分（30/25/25/20）+ 风险分带 + 单维崩坏一致性 + 续约候选双门槛 |
| 服务知识与升级 | `knowledge` | `faq` / `escalation` | FAQ 三件套 + 答案 ≥40 字 + Jaccard 去重；升级四要素 + 路由白名单 + 证据双要素 |
| 客户运营自动化接口 | `automation` | `automation` / `probe` | 需求卡六要素 + 触发/字段类型白名单 + 敏感字段禁入 + 高危动作审批点；实现探测如实降级 |

共 **8 技能 / 16 动作**（15 个门禁 + 1 个 probe）。

## 协作契约

- **inputs**：`lead` + `order_status`
- **outputs**：`crm_record` + `voc`
- 意图路由（`agent.py run --task`）：FAQ/知识库/升级单 → knowledge；自动化/需求卡 → automation；
  NPS/问卷/反馈/VOC → voc；健康/续约/流失 → health；客服/工单/收件箱 → support；
  跟进/活动/逾期 → activity；管道/商机/停滞/预测 → pipeline；兜底 → `crm/person`。

## 运行

```bash
python agent.py manifest                      # 契约 + 8 技能清单
python agent.py pipeline pipeline --input examples/pipeline.json
python agent.py support inbox --input examples/inbox.json
python agent.py health health --input examples/health.json
python agent.py automation probe
python agent.py harness pipeline --input examples/pipeline.json
python agent.py contract list
python agent.py case list
python verify_loop.py                          # 30 行闭环矩阵
python run_tests.py                            # 一键验收，期望 ALL GREEN
```

## 边界（角色分工与红线）

- **投放策略 / 广告预算**归 R12；**路线图优先级**归 R07；**定价与合同条款**归 R03/R02。
- **统计推断、显著性、因果**归 R06；本角色只做确定性加权与阈值判断。
- **自动化实现（n8n/Webhook/重试）**归 R17；本角色只产出需求卡（触发/条件/字段/审批点/审计）。
- **退款、折扣、赔偿、定制开发承诺**一律不擅自答应——需要时写 handoff 交 R03/R02。
- **红线（不可越）**：
  1. 不擅自承诺退款、赔偿、终身免费或保证效果。
  2. 不未经授权导出客户数据、批量导出手机号、爬取个人信息。
  3. 不把凭据（password/api_key/token/secret）写进自动化字段映射。

## 确定性校验口径

- 干净数据 → `ok=true` / exit 0；脏数据（枚举越界 / 算术不闭合 / 缺归因 / 缺证据 /
  敏感字段 / 单维崩坏）→ `ok=false` / exit 1。
- `probe`（automation）恒 `ok=true`，R17 未落地只反映在 `status=blocked`（如实降级，探测非门禁）。
- 对抗评审五检查：`contract` / `unauthorized_promise` / `scope_boundary` / `privacy_gate` /
  `concrete_artifact`；失败按类别 route 回 writer 或 controller。
- 阈值全部外置在 `experience/thresholds.json`，改口径不改代码；案例可再覆盖
  （如 `pipeline-rescue` 把停滞阈值收紧到 10 天）。
