# STRIDE 威胁建模与 OWASP ASVS：从「扫漏洞」到「证明没漏」

> 适用角色：R09 工程官；对应工程链第 7 段 `security`，并与 `api` 错误码联动。

## 1. 来源

- Microsoft, *The STRIDE Threat Model*（2002 起）：把威胁分为 Spoofing、
  Tampering、Repudiation、Information disclosure、Denial of service、
  Elevation of privilege 六类。
- Adam Shostack, *Threat Modeling: Designing for Security*（2014）：提出
  「资产—信任边界—威胁—缓解」四步法，强调威胁建模先于代码。
- OWASP ASVS（Application Security Verification Standard）4.0.3 / 5.0：
  按 V1–V14 给出可验证的安全要求与 L1–L3 等级。
- OWASP Top 10 2021：常见 Web 风险清单，可作为 ASVS 的入门子集。
- NIST SP 800-218（SSDF）：把安全活动嵌入软件开发生命周期的实践集合。

## 2. 适用边界

适合：

- 有明确资产（账号、笔记、订单、密钥）与信任边界的网络服务；
- 需要向客户或审计方证明「我们检查过什么」的交付；
- 依赖较多、存在供应链风险的工程。

不适合 / 需裁剪：

- 完全离线、无多用户、无敏感数据的单机脚本：可只保留依赖与密钥扫描，
  但必须在安全清单里写明裁剪理由，不能默认「不需要」；
- 把 ASVS 当渗透测试替代品：ASVS 是要求清单，不能证明不存在未知漏洞；
- 把 STRIDE 当漏洞扫描器：它产出的是威胁与缓解设计，不是 CVE 列表。

## 3. 方法：资产 → 边界 → 威胁 → 缓解 → 验证

1. **列资产**：凭据、个人数据、业务数据、管理能力、构建产物。
2. **画信任边界**：浏览器/网关/应用/数据库/运维脚本之间跨越即边界。
3. **逐类过 STRIDE**：每一类至少写一条真实威胁，禁止「无此类威胁」一句话带过。
4. **写缓解**：缓解必须是可实施的控制（服务端取 owner、长度上限、审计日志、
   最小权限），而不是「注意安全」。
5. **对 ASVS**：至少 6 项，全部 pass，等级不低于 L2；每条要求要能指向实现或测试。
6. **扫依赖与密钥**：依赖扫描 high 必须为 0；密钥扫描泄漏必须为 0；
   扫描工具名与结果都要落盘，便于复核。

## 4. 仓内落点

`eng_chain/security.py` 的门禁：

| 门禁 | 检查内容 | 失败级别 |
|---|---|---|
| `security:stride` | S/T/R/I/D/E 六类齐全，且每条威胁有缓解 | CRITICAL |
| `security:asvs` | ASVS ≥6 项全 pass，等级 ≥L2 | CRITICAL |
| `security:no_high` | 依赖扫描 high = 0 | CRITICAL |
| `security:no_leaked_secrets` | 密钥扫描 leaked = 0 | CRITICAL |
| `security:error_codes` | 安全清单覆盖全部 API 错误码 | CRITICAL |

`runner.py` 再做跨段一致：API 错误码集合必须等于安全清单集合。这样
「接口新增 403 但安全评审没更新」会直接阻断发布。

## 5. 误用反例

| 反例 | 后果 | 拦截门禁 |
|---|---|---|
| 六类威胁只写「无」 | 建模流于形式，真实威胁未识别 | `security:stride` |
| 缓解写成「加强安全意识」 | 无法实施、无法验证 | `security:stride` |
| ASVS 全 pass 但无实现证据 | 审计时无法自证 | 人工评审 + `security:asvs` |
| 只扫依赖，不扫密钥 | 硬编码 token 进仓库 | `security:no_leaked_secrets` |
| 依赖出现 high 仍发布 | 已知漏洞直接上线 | `security:no_high` |
| 接口错误码与安全清单不一致 | 越权错误无人处理 | `security:error_codes` |
| 用一次漏洞扫描代替威胁建模 | 设计层缺陷永远扫不出来 | `security:stride` |

## 6. 检查清单

- [ ] 每个资产都至少出现在一条威胁里；
- [ ] 每条威胁的缓解能指向代码、配置或测试；
- [ ] 越权读取/写入各有一条威胁与缓解；
- [ ] 错误响应不包含堆栈、SQL、密钥；
- [ ] 依赖锁定且 high = 0；密钥扫描 leaked = 0；
- [ ] ASVS 条目与实现文件能对上，等级写明 L2 或 L3；
- [ ] 安全清单与 API 错误码集合完全一致。
