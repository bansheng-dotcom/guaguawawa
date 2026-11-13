# 咨询 8 阶段工作流（能力卡）

> 一句话：把一个模糊议题，推进成**可签字、可回滚、可复盘**的 8 阶段交付。
> 每阶段都有 owner、必填产物、独立 reviewer 和一条硬门禁；不过门禁不能进下一阶段。

## 8 个阶段

| # | 阶段 | owner | 必填产物 | 门禁 |
|---|---|---|---|---|
| 1 | 定义问题 | r01 | decision / decision_maker / success_metric / scope_out | partner 确认问题定义 |
| 2 | 逻辑地图 | r05 | branches / critical_branch | 分支 MECE、每条有假设、标出关键支 |
| 3 | 80/20 聚焦 | r01 | focus / excluded_reasons | 聚焦 ≤3 支、其余写明为什么不做 |
| 4 | 分析计划 | r05 | workstreams | 每条有数据源/方法/负责人/降级 |
| 5 | 执行分析 | r06 | findings / conflicts / gaps | 发现四件套、冲突单列、缺口可补 |
| 6 | 整合答案 | r05 | messages | 1—3 条信息、机制 + 竞争解释 |
| 7 | 形成建议 | r01 | options / recommendation | ≥3 选项、经济性/风险/KPI/回滚 |
| 8 | 打包交付 | r05 | deliverables / value_tracking | 摘要/正文/附录/价值追踪齐全 |

## 目录

```
shared/consulting/
  stages.py      8 阶段定义（owner / 产物 / reviewer / gate）
  checks.py      每阶段的可执行校验（MECE、四件套、3 选项…）
  workbook.py    工作簿状态机：start / submit / sign / advance / render
scripts/
  consult.py     命令行入口
  consult_audit.py  咨询深度探针
tests/
  test_consulting_workbook.py   8 阶段 happy path + 门禁拒绝
projects/consulting/<ID>/workbook.md   项目工作簿落盘（客户数据不进 git）
```

## 常用命令

```bash
python scripts/consult.py start --id FRUIT-01 --client 蛙呱呱 \
       --decision "是否做赤峰苹果直采" --partner r01
python scripts/consult.py status --id FRUIT-01
python scripts/consult.py submit --id FRUIT-01 --stage 2 --file branches.json
python scripts/consult.py sign   --id FRUIT-01 --stage 2 --by r01
python scripts/consult.py advance --id FRUIT-01
python scripts/consult.py render --id FRUIT-01
python -m pytest tests/test_consulting_workbook.py -q
```

## 红线

- 门禁是**硬**的：`checks.py` 不通过时 `advance` 必须失败，不允许"人工跳过"。
- 阶段 7 的建议必须 ≥3 个选项；只给一个方案等于替老板拍板。
- 工作簿含客户信息：`projects/consulting/` 默认不进 git（`.gitignore` 已覆盖）。
- 8 阶段走完不代表答案深：以 `evals/consulting/` 的 20 题评分为准，分数不涨就砍阶段。
