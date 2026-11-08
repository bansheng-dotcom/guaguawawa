# s07 迁移 CI/CD 安全（ops）方法论

来源沉淀：`KarmenLoop__fullstack-web-delivery`（部署生命周期）+ `wshobson__agents`。

## 一、方法论（什么时候用、核心口径）

迁移与安全回答「怎么安全地上生产」。两个动作：
- `migration`：迁移步骤 + 回滚计划，**不可逆操作需授权**。
- `security`：依赖 CVE 与泄露密钥审计。

核心红线（R09 边界）：**不可逆线上操作需授权**；**无回滚计划的迁移不做**。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

不可逆操作词、CVE 严重度、泄露密钥上限外置：
`ops.irreversible_ops/cve_severities/max_leaked_keys`。
（验证链：`experience/thresholds.json → _common.load_thresholds() → s07_ops.migration/security`）

**migration 校验规则**：
- steps 为空 → `ops:migration_steps` CRITICAL。
- 步骤 operation 含不可逆词（drop/truncate/force_push…）且未授权 → `ops:irreversible_auth` CRITICAL。
- rollback_plan 为空 → `ops:rollback` CRITICAL。

**security 校验规则**：
- dependencies 为空 → `ops:dependencies` CRITICAL。
- CVE severity 不在枚举 → `ops:cve_severity` HIGH。
- CVE 为 critical/high → `ops:cve_high` CRITICAL。
- 泄露密钥 > 0 → `ops:leaked_keys` CRITICAL。

**输出键**：migration → `step_count / irreversible_found / rollback_steps / verdict / next`；
security → `dependency_count / cve_counts / leaked_key_count / verdict / next`。

## 三、已验证算例（run_tests.py 全绿，非新编）

`examples/ops_migration.json`（3 可逆步+授权+2 回滚步）：irreversible_found=[]，verdict=PASS。
`examples/ops_security.json`（2 依赖 0 泄露，仅 medium CVE）：leaked_key_count=0，verdict=PASS。
脏夹具 `ops_migration_dirty.json`：drop+truncate 未授权 → irreversible_found 非空，ok=false；
`ops_security_dirty.json`：critical CVE + 1 泄露密钥 → ok=false。

## 四、实战踩坑（真拦下来的教训）

- **不可逆判定要做子串匹配**：`drop table users` 要能命中 drop/truncate 词根，
  大小写不敏感，否则换个写法就绕过。
- **泄露密钥 1 条就是 CRITICAL**：max_leaked_keys=0，任何泄露都不允许，
  不能设容错。
