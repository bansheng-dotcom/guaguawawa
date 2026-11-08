# S08 广告 / KYC-AML / 投资风控
> 蒸馏自: 补充技能/01-当前能力域/anthropics__financial-services/kyc-screener/SKILL.md
>


## 方法论（来源 kyc-screener 规则引擎 + AML / KYC / advertising-compliance /
private-placements / conflicts-of-interest）

### KYC 规则引擎（risk.kyc）

**六因子评级**（每因子封顶）：jurisdiction(2) / applicant_type(2) /
ownership_opacity(2) / pep(3) / sanctions(3) / source_of_funds(2)

| 总分 | 评级 |
|---|---|
| ≤ 2 | low |
| ≤ 4 | medium |
| ≥ 5 | high |

**处置决策**（永不直接批准）：
- sanctions ≥ 3 → decline-recommend
- sanctions ≥ 2 或 pep = 3 → escalate-edd
- 文档缺失或 UBO ≥25% 未核实 → request-docs
- 其余 low/medium → clear

- CIP 四要素：姓名 / 生日 / 地址 / 识别号
- 受益所有权：≥25% 股权的所有人 + 1 名控制人须识别核实
- 记录留存 5 年（销户后）
- 高风险客户 EDD + 高管批准

### AML 交易监测（risk.aml）

| 触发 | 义务 | 时钟 |
|---|---|---|
| 现金（含同类）单日 > $10,000 | CTR | 15 天 |
| 已知嫌疑人可疑交易 ≥ $5,000 | SAR | 30 天 |
| 无嫌疑人可疑交易 | SAR | 60 天 |
| 持续可疑活动 | SAR 续报 | 每 90 天 |
| OFAC 命中冻结 | 冻结报告 | 10 个工作日 |

- **结构化拆分红旗**：同日多笔现金、单笔均 < $10,000 且合计 ≥ $9,000
- AML 计划四支柱：内部政策 / 培训 / 独立测试（每 1–2 年）/ 指定合规官
- **禁止 tipping-off**（向客户泄露申报）
- 记录留存 5 年

### 广告合规（risk.adreview，SEC Marketing Rule）

- 毛业绩必须与净业绩**同等显著**配对展示
- 业绩期间须为标准化 1 / 5 / 10 年
- 假设 / 回测业绩必须明确标注假设性质与局限
- 推荐与背书三披露：客户身份 / 补偿 / 冲突
- 30 日内零售受众 > 25 人 → 使用前预批
- 广告留存 5 年（前 2 年易获取）；不得含保证收益/保本措辞

### 私募与合格投资者（private-placements）

- 合格投资者：收入 $200k（个人）/$300k（夫妻）连续两年 + 当年合理预期，
  或净资产 $1M（剔除住所，不通胀调整）
- 506(b)：≤35 非合格 + 禁一般性招揽；506(c)：须合理核实
- Form D / 5123：首售后 15 天
- pay-to-play：捐款后 2 年禁收报酬；FINRA 礼物 $100/人/年

## 已验证算例（run_tests.py T12，已对拍）

- **kyc 六因子**：`examples/risk_kyc.json` → `risk_score=5`、
  `rating=high`、`disposition=escalate-edd`、`approved=false`（永不直接批准）、
  `missing_docs` 含 `tax_id`。
  补全文档后同场景 → `disposition=clear`、`ok=true`。
- **aml structuring**：同日多笔现金均 <$10,000 且合计 ≥$9,000 →
  `alerts[0].type=structuring`、`filings_due=[{form:SAR}]`。
- **aml CTR**：单笔现金 $10,500 → `filings_due[0].form=CTR`、
  `deadline_days=15`。
- **adreview**：`examples/risk_adreview.json` →
  `net_return.ok=false`（缺净业绩）、`period.ok=false`（3 年非标准化期间）、
  `hypo_label.ok=false`（假设业绩未标注）、`retail_preapproval.ok=false`
  （>25 人未预批）、`no_guarantee.ok=true`；含「保本保收益」措辞 → 触发
  保证词禁用 → `ok=false`。

## 实战踩坑

- KYC **永不直接批准**：评级 low 也只输出 clear（放行建议），
  最终批准权在人工——把 clear 当「已批准」是越权。
- 结构化拆分看**合计**不看单笔：单笔都合规但同日合计逼近 $10,000
  才是真红旗，只查单笔会漏。
- 广告「毛业绩与净业绩同等显著」是硬要求，只给毛业绩不断言净业绩
  同样不合格；回测/假设业绩不标注局限也是拦。
