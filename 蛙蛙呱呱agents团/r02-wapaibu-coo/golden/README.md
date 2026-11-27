# R02 黄金成品（golden）：重试/死信报告 + 流程复盘

两份 HTML 由 `workflow_engine.py` 真跑一遍「143 份副本收敛」工作流后导出；
`golden/workflow-run.json` 是同一轮运行的机器可读产物（首轮 + 重放）。

```bash
cd r02-wapaibu-coo
python workflow_engine.py goldens                 # 重建两份 HTML + workflow-run.json
python agent.py wf run    --input <policy+tasks.json>
python agent.py wf replay --input golden/workflow-run.json
python workflow_engine.py check --case misuse/unbounded-retry.json
```

| 文件 | 内容 | 验收点 |
|---|---|---|
| `coo-retry-dlq.html` | 重试与死信：终态表、指数退避序列、死信队列、重放结果 | 成功/失败/重放三态齐；退避 2/4/8/16s 封顶 60s；死信全部有幂等键 |
| `coo-process-retro.html` | 流程复盘：143 份副本收敛前后对比、浪费与根因、行动项 | 数字与升级方案 §6.1 一致（143→9、28,278→4,014 行） |
| `workflow-run.json` | 首轮 + 重放两次运行结果 | 重放后 `dead_letters_open=[]`，阻塞任务自动恢复 |

## 夹具（确定性）

`DEMO_TASKS`：extract → map（重试 1 次）→ rewrite → verify（重试 3 次）→ publish（4 次全失败进死信）→ notify（阻塞）。
首轮 `outcome=failed`；`replay` 后 `publish` 重放成功、`notify` 自动恢复，全链成功。

## 误用样本（misuse/）

| 文件 | 故意违规 | 期望错误码 |
|---|---|---|
| `unbounded-retry.json` | `max_retries=999` + `retry_forever=true` | `W01_UNBOUNDED_RETRY` |
| `lost-dead-letter.json` | 任务失败但死信队列为空 | `W02_DEAD_LETTER_LOST` |
