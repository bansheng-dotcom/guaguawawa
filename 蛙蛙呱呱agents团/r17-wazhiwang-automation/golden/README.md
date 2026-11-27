# R17 黄金样本：自动化成功链 + 失败/重放链

> 由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `automation-success.html` | integration.workflow → retry.retry → audit.runlog | `workflow.json` / `retry.json` / `runlog.json` | 节点/连接/触发器、无明文密钥；重试上限/超时/幂等/死信；执行日志可追溯 |
| `automation-replay.html` | retry.errorflow → audit.audit → audit.runlog | `errorflow.json` / `audit.json` / `runlog.json` | Error Trigger 已发布且按目标挂载；六要素证据齐备；失败可复现 |

## 怎么重新生成

```bash
python r17-wazhiwang-automation/golden/build_golden.py
```

## 验收

```bash
python r17-wazhiwang-automation/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`retry_unbounded.json` 触发 `retry.max_retries`；
  `retry_no_dead_letter.json` 触发 `retry.dead_letter`。

## 说明

- 重放生产流属高风险动作，必须人工决策；本包只校验证据链；
- 凭据走环境变量/密钥管理，绝不出现在工件。
