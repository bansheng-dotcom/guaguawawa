# R08 黄金成品（golden）：MVP 交付包 + 回滚记录

两份 HTML 由 `deploy_rollback.py` 在临时目录真跑一遍「本地文件态 E2E」后导出；
`golden/deploy-e2e.json` 是同一轮的五步结果与发布/回滚历史。

```bash
cd r08-wajiancheng-mvp
python deploy_rollback.py goldens                       # 重建两份 HTML + deploy-e2e.json
python deploy_rollback.py e2e                           # 只看五步结果
python deploy_rollback.py check --case misuse/deploy-no-rollback.json
```

| 文件 | 内容 | 验收点 |
|---|---|---|
| `mvp-delivery-pack.html` | 交付包：发布物、版本锁+摘要、健康检查、回滚计划 | 3 个文件可部署；同版本同摘要幂等；坏版本被 D03 拦下 |
| `mvp-rollback-record.html` | 回滚记录：发布/幂等/自动回滚/重发/人工回滚时间线 | 时间线 5 条；版本锁摘要与磁盘重算一致 |
| `deploy-e2e.json` | 机器可读的五步结果 | `ok=true`；`rollback` 后 `check_health` 通过 |

## E2E 五步（本地文件态）

1. 首次发布 `mvp-1.1.0` → `deployed`；
2. 重复发布同版本 → `noop`（幂等，不重写文件）；
3. 发布 `mvp-1.2.0` 且健康检查 500 → `auto_rolled_back`，`release/` 恢复 v1.1.0；
4. 修复后发布 `mvp-1.2.0` → `deployed`；
5. 人工回滚 → `rolled_back`，版本锁 = `mvp-1.1.0`。

## 误用样本（misuse/）

| 文件 | 故意违规 | 期望错误码 |
|---|---|---|
| `deploy-no-rollback.json` | 回滚计划为空直接发布 | `D01_NO_ROLLBACK_PLAN` |
| `version-lock-drift.json` | 用 deploy 把版本从 1.1.0 退回 0.9.0 | `D02_VERSION_LOCK` |
