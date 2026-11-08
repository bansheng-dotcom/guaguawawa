# good_summaries（好算例摘要：已验证）

- v1 脏证据：hooks 声明 "never blocks, always exits 0" → STRENGTH-001；
  快照 passed=true、checks 含 lint/test 而 signals 只有 lint → STRENGTH-007。
  2 个 error、0 个 warning → 评分 70、tier at-risk、verdict FAIL。
- v2 修复后：钩子改为真阻断表述，signals 补齐 test 运行记录 → 0 命中，
  评分 100、tier solid、verdict PASS。
- 「not evaluable 不是 pass」：证据空/无区段 → verdict NOT_EVALUABLE、ok=false。
