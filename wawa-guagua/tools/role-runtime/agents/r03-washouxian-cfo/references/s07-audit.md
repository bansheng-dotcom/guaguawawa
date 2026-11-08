# S07 认证与审计留痕
> 蒸馏自: 补充技能/01-当前能力域/JoelLewis__finance_skills/books-and-records/SKILL.md
>


## 方法论（来源 books-and-records 17a-4 + compliance-os audit_simulator /
evidence_pool_generator）

### 三层留存（SEC 17a-4）

| 层 | 年限 | 记录类型 |
|---|---|---|
| six_years | 6 年 | blotters、总账、明细账、客户账户记录、财务报表、持仓记录、合伙协议 |
| three_years | 3 年 | 通信、订单备忘录、合规程序、雇佣申请、书面协议、检查报告 |
| lifetime | 终身 | 章程文件、会议记录簿、股票证书簿 |

- **前 2 年记录须易于获取**（readily accessible）
- 电子存储二选一：WORM（一次写多次读）或具备审计轨迹的系统；
  外加第三方访问代理的年度承诺函
- IA（投资顾问）5 年；投诉记录 4 年（FINRA 4513）

### 模拟审计（audit.mockaudit）

severity 分布目标带（分布失真 = 测试深度不足）：

| severity | 目标 |
|---|---|
| observation | ≥ 40% |
| minor | 20–30% |
| major | 15–25% |
| critical | ≤ 15% |

- 所有 major/critical 必须有 owner（follow-up 最低 major）
- 控制点须映射到注册主题：access_control / change_management /
  risk_assessment / monitoring / vendor_management / incident_response /
  data_governance

### 证据池（audit.evidence）

每个控制点至少 1 条证据，每条证据四要素：
`control`（对应控制点）/ `artifact`（文档/截图/命令输出）/
`collected_at`（采集时间）/ `collector`（采集人）。

证据防篡改存档（WORM/审计轨迹）；跨框架复用（见 S06 跨框架映射）。

### 监管报送时钟（regulatory-reporting 摘要）

- ADV 年度修订 90 天；手册交付 120 天；临时修订 30 天
- Form PF 按 AUM 门槛分频（$1.5B/$1B/$2B/$150M → 60/15/120 天）
- 触发事件 72 小时报告（NAV 20% 损失 / 5% 保证金追加）

## 已验证算例（run_tests.py T11，已对拍）

- **retention**：`examples/audit_retention.json` → `violation_count=3`
  （3 条记录留存期不符 17a-4 三年层/六年层）。
- **lifetime 豁免**：章程/会议记录簿/股票证书簿属终身保存层 →
  `ok=true`（不受 6 年层约束，别误判违规）。
- **mockaudit**：`examples/audit_mockaudit.json` → `total=10`，
  `severity_pct.observation≥0.40`、`severity_pct.critical≤0.15`
  （分布失真=测试深度不足）。
- **evidence**：`examples/audit_evidence.json` → `gap_count=1`，
  缺口为缺 `collector` 字段（证据四要素 control/artifact/collected_at/
  collector 缺一即 gap）。

## 实战踩坑

- 留存层别一刀切：lifetime 层的文档比 six_years 要求更严，误套 6 年层
  会漏判；前 2 年「易获取」是额外要求，只存 WORM 但不可即取仍不合格。
- 模拟审计的 severity 分布是**门禁**：全报 critical 或全 observation
  都判失真——分布反映测试是否真的分层探查。
- 证据池的价值在跨框架复用（见 S06 映射）：同一 access_control 证据
  同时满足多框架，重复采集浪费且易不一致。
