# R08 蛙建成 · 厚度自述（T12 Tier C：补机制）

> 按升级方案 §16「厚度包」与 §17.1 T12 逐项自述。只写能被命令复核的事实。

## 1. 知识层

| 项 | 现状 |
|---|---|
| 领域参考 | 10 篇 / 37.1KB（切片 MVP、脚手架 Spec、落地页 H5、SaaS/邮件、跨平台原型、设计令牌、QA 交接等） |
| 来源 | 每篇列公开方法来源（MVP 切片、12-factor、渐进式交付、canary/rollback）与适用边界 |
| 误用说明 | 每篇有「误用反例」；对应门禁在 `harness.py` 与 `skills/s07_qa.py` |
| 能力卡 | `references/capabilities/`：html-report-presentation、miniapp-builder、office-plugin、ppt-generator、rapid-prototype |

## 2. 生产层

| # | 模块 | 输入 | 产出 |
|---|---|---|---|
| 1–7 | `skills/s01..s07` | 切片/脚手架/落地页/SaaS/原型/设计/QA | 实现工件与门禁结论 |
| 8 | `skills/s08_deck.py`、`s10_miniapp.py`、`s11_office.py` | 交付诉求 | 演示/小程序/文档 |
| 9 | `local_actions.py` | 本地骨架 | 文件存在性与越界检查 |
| 10 | **`deploy_rollback.py`（T12 新增）** | manifest + 本地 state 目录 | `state.json`/`history.json` + 2 份 HTML |

`deploy_rollback.py` 用本地文件态模拟发布：版本锁、幂等部署、健康检查、自动/人工回滚。

## 3. 证据层

| 类型 | 位置 | 说明 |
|---|---|---|
| 可部署 MVP | `golden/deploy-e2e.json` | 3 个文件（index.html/app.js/styles.css）+ 版本锁摘要 |
| 发布历史 | `run_e2e` 的 `history` | 5 条：deployed / noop / auto_rolled_back / deployed / rolled_back |
| 黄金报告 | `golden/*.html` | 交付包、回滚记录 |

## 4. 门禁层

| 错误码 | 判据 | 失败后果 |
|---|---|---|
| `D01_NO_ROLLBACK_PLAN` | `rollback.plan` 至少 1 步 | 拒绝发布 |
| `D02_VERSION_LOCK` | 版本不得低于当前（除 `allow_rollback`） | 拒绝；回滚走 rollback |
| `D03_HEALTHCHECK_FAILED` | 所有检查 actual == expect | 自动回滚并报失败 |
| `D05_VERSION_DIGEST_MISMATCH` | 同版本同摘要 | 拒绝（防同号不同包） |
| `D06_PATH_ESCAPE` | 文件名不得越界 | 拒绝发布 |

## 5. 回归层

| 类型 | 位置 | 数量 |
|---|---|---|
| 机制单测（pytest） | `tests/test_mechanism.py` | 8 条（摘要/E2E/回滚计划/降级/摘要漂移/健康失败/误用/HTML） |
| 角色端到端 | `run_tests.py` §T12 | 7 条 |
| 黄金成品 | `golden/*.html` | 2 份 |
| 误用反例 | `misuse/*.json` | 2 份（无回滚 / 版本锁漂移） |
| 全量 | `python run_tests.py` | 77 / 77 |

## 6. 最近真实运行

- 时间：2026-11-27
- 命令：`python r08-wajiancheng-mvp/run_tests.py`
- 结果：通过 77 / 77，全绿
- 机制：`python deploy_rollback.py goldens` → E2E 五步 `ok=true`
- 呈现：`python scripts/check_report_presentation.py r08-wajiancheng-mvp/golden/*.html` → 2/2 PASS

## 7. 已知边界

- 部署对象是本地静态文件，不接真实 CDN/容器编排；
- 健康检查用 `actual/expect` 模拟，不真发 HTTP 请求；
- 回滚只保留一层 `previous` 快照，不支持多级历史回滚；
- 版本比较按数字段元组，不做预发布（rc/beta）语义排序。
