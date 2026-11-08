# S05 隐私与数据安全
> 蒸馏自: 补充技能/01-当前能力域/JoelLewis__finance_skills/privacy-data-security/SKILL.md
>


## 方法论（来源 privacy-data-security：Reg S-P / Reg S-ID / GDPR 口径）

### 数据流映射（privacy.map）

每条个人数据流必须有：合法基础 + 留存期 + 跨境机制。

- GDPR 六类合法基础：consent / contract / legal_obligation /
  vital_interests / public_task / legitimate_interest
- 跨境传输机制：adequacy / SCC / BCR / derogation

### 隐私通知（Reg S-P）

- 初始隐私通知：建立客户关系**当时**送达（非"合理时间"）
- 年度通知：每 12 个月一次
- FAST Act 网站张贴替代邮寄须同时满足：仅共享例外项（248.14/15 列举的
  5 类处理类业务）+ 政策未变
- 向非关联第三方共享 NPI 前必须先提供**退出（opt-out）机会**与合理时间

### 数据主体请求（privacy.dsr）

- 六类请求：access / rectification / erasure / portability / restriction /
  objection
- GDPR 响应时钟 30 天；完成的请求须有身份验证 + 完成时间戳

### 泄露双时钟

- NY DFS：72 小时内通知监管
- 2024 Reg S-P 修正案：敏感信息泄露 ≤30 天通知受影响个人
- 供应商合同须含 24–72 小时违约通知条款

### 最小化与访问（privacy.minimize）

- 字段级：每字段必须有收集目的；标记非必要的必须停采
- 敏感字段双态加密 + 传输 TLS ≥1.2
- 访问审查至少每年一次；特权账户更频繁
- 到期数据须安全销毁（物理粉碎/密码学擦除）并留痕

### 身份盗窃预防（Reg S-ID）

合理设计的 Identity Theft Prevention Program：识别红旗模式 + 应响应程。

## 已验证算例（run_tests.py T10，已对拍）

- **map**：`examples/privacy_map.json` 某数据流缺合法基础 → `ok=false`。
- **dsr**：`examples/privacy_dsr.json` → `overdue=[dsr-2]`
  （超 30 天响应时钟）→ `ok=false`。
- **breach 双时钟**：某事件 `breach_dfs`（80 小时 > 72 小时）→ `ok=false`；
  `breach_notice`（3.3 天 ≤ 30 天）→ `ok=true`。两个时钟独立判定，
  一个超一个不超要分别报。
- **minimize**：某数据流含非必要字段 / `access_review` 距上次 13 个月
  （>12）→ 该项 `ok=false`。

## 实战踩坑

- 双时钟最易混：DFS 72 小时是**通知监管**，Reg S-P 30 天是**通知个人**，
  漏掉任一时钟都算 fail；早期只算一个导致合规漏报。
- 合法基础不是「有就行」：consent 场景缺撤回机制、legal_obligation
  场景对不上具体法条，都判不合格。
- 「到期销毁」必须留痕，否则算未完成——数据删了但无销毁记录，
  审计时无法证明已删。
