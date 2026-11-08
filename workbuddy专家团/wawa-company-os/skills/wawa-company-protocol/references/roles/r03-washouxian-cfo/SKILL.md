# R03 蛙守线（CFO / 财务合规官）
> 蒸馏自: 补充技能/01-当前能力域/anthropics__financial-services/month-end-closer/SKILL.md
>


> 八能力域：报表月结 / CFO 经营诊断 / 税务边界 / 合同政策 / 隐私数据安全 /
> AI 治理 / 审计留痕 / 广告-KYC-AML 风控。
> 红线：只出内部建议与确定性校验，永不出具持牌意见（正式法律/审计意见），
> 永不直接批准开户（approved 恒 False），永不代签 controller sign-off。

## 运行

```bash
python agent.py <skill> <action> --input <json>
```

输出：stdout 单行 `__AGENT_RESULT__ {json}`（含 ok / checks / 量化字段 / next）。

## 技能总览（8 技能 × 3 动作）

| 技能 | 动作 | 干什么 |
|---|---|---|
| financial | rollforward | 资产负债表账户平衡门禁（X+A+B−C−D+E+F=Y） |
| financial | recon | GL↔子账对账（六桶/容差 0.01/归因/匹配率≥95%） |
| financial | variance | 差异注解门禁（max(5%×基数,下限) + 收入/人力/现金必评） |
| cfo | runway | 月度现金模拟 + 决策触发器（9/6/4/3 个月）+ burn multiple |
| cfo | unitecon | LTV/CAC/回本/LTV:CAC（≥3 达标）+ 队列 churn 反推 |
| cfo | healthcheck | 三表勾稽恒等式（资产=负债+权益 / 现金勾稽 / 毛利） |
| tax | iso | ISO 合格处置（2 年/1 年）+ AMT 交叉（26%/28%, 免税额 137k） |
| tax | rmd | RMD 计算（Uniform 除数表）+ 消费税 25%/10% |
| tax | safeharbor | 预估税安全港（90%/100%/110%）+ RSU 预扣缺口（22%/37%） |
| contract | scan | 12 条红线规则扫描（severity/why/redline） |
| contract | policy | 政策字段门禁（purpose/scope/owner/周期/enforcement 可执行） |
| contract | redline | 整改跟踪（CRITICAL/HIGH 必闭合，接受风险须审批人） |
| privacy | map | 数据流合法基础/跨境机制/隐私通知（初始+年度 12 月） |
| privacy | dsr | DSR 30 天时钟 + 泄露双时钟（DFS 72h / 个人 30 天） |
| privacy | minimize | 字段级最小化 + 敏感字段加密 + 访问审查（≤12 月） |
| aigov | frameworks | 适用框架决策树（GDPR/ISO27001/SOC2/ISO42001/EU AI Act…） |
| aigov | aiclassify | AI 系统四级分类（prohibited/high/limited/minimal） |
| aigov | disclose | AI 披露四要素（身份/内容标识/人工监督/申诉渠道） |
| audit | retention | 17a-4 三层留存（6 年/3 年/终身）+ 前 2 年可获取 + WORM |
| audit | mockaudit | 模拟审计 severity 分布（obs≥40%, critical≤15%） |
| audit | evidence | 证据池（control/artifact/collected_at/collector） |
| risk | kyc | 六因子评级（低≤2/中≤4/高）+ 处置建议（永不 clear 越权） |
| risk | aml | CTR（>$10k/15 天）/SAR（≥$5k/30 天）/结构化拆分检测 |
| risk | adreview | 净业绩配对/1-5-10 年期间/假设标注/背书三披露/预批门 |

## 输入契约

`python contracts.py [skill [action]]` 打印 24 个动作的 JSON Schema；
`examples/` 下有全部通过契约的样例输入。

## 测试与验收

```bash
python run_tests.py     # 全量断言（目标全绿）
python verify_loop.py   # 24 动作「跑到绿」循环（契约×执行×结构×评审门）
```

## 阈值外置（T9）

所有法定数字与口径在 `experience/thresholds.json`：
AMT 免税额、RMD 除数表、CTR/SAR 门槛、留存年限、severity 目标带、
runway 触发器、LTV:CAC 门槛等。**改口径不改代码。**

## 意图路由

`agent.route(text)` 关键词路由：月结/对账→financial，runway/烧钱→cfo，
ISO/AMT/RMD→tax，合同/条款→contract，隐私/DSR→privacy，AI 治理→aigov，
审计/留存→audit，KYC/AML/广告→risk。

## 案例（T8）

- `cases/month-end-close/` 月结对账：recon→rollforward→healthcheck 同根因归因
- `cases/kyc-onboarding/` KYC 尽调：评级→处置建议→AML 结构化红旗

## 参考

- `references/s01-financial.md` … `references/s08-risk.md`（各能力域方法论）

## 来源

- anthropics__financial-services（month-end-closer / gl-reconciler /
  statement-auditor / kyc-screener）
- JoelLewis__finance_skills（compliance 系列 / wealth-management 税务 /
  financial-statements / return-calculations）
- alirezarezvani__claude-skills（cfo-advisor / compliance-os /
  general-counsel-advisor）
