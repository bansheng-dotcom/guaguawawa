# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/html-report-presentation/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 2/2`（含 1 个反例）。版本：v2.0.0

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 报告标题为空 | `report.title` | ✅ exit=1（`tests/report-fail.json`） |
| MU-02 | `meta` 缺 audience / purpose | `report.meta` | ✅ exit=1（同上） |
| MU-03 | 章节 <3 或某章无 summary | `report.chapters` / `report.chapter` | ✅ exit=1（同上） |
| MU-04 | 核心论点 <3 | `report.thesis` | ✅ exit=1（同上） |
| MU-05 | 来源 <3 或某条无 label | `report.sources` / `report.source.label` | ✅ exit=1（同上） |

## 二、门禁抓不到，靠 §6 自检

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-06 | 背景写三页才出结论 | 决策者读不到重点 | §6 结论先行 |
| MU-07 | 论点无法被证伪 | 是口号不是论点 | §6 反驳条件 |
| MU-08 | 来源写"公开资料显示" | 无法核 | §6 具名来源 |
| MU-09 | 编造来源凑数 | 失信，比少写更糟 | §7 EX-10 |
| MU-10 | 没看打印预览 | 分页切断表格 | §6 打印检查 |
| MU-11 | 一份报告给所有人看 | 没有为读者写 | §6 audience 检查 |

> **纪律**：报告的价值不在篇幅，在"决策者读完能做哪个决定"。
