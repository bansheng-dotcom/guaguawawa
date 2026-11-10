# Team 编排：跨域方案（示例 · 营收最大化）

> 本文是一个**编排实例**。组织架构见 `ORG.md`，三种协同模式见 `PROTOCOL.md`，
> 汇报规范见 `REPORT-STANDARD.md`，机器可读契约见 `core/`。

## 角色分工（以「营收最大化方案」为例）

| 阶段 | 角色 | 交付 | 交接端口 |
|---|---|---|---|
| ① 策略假设 | R07 蛙得明（产品经理） | 定价/套餐/时段/会员方案假设 + 待验证指标 | `strategy_hypotheses` |
| ② 数据验证 | R06 蛙得清（数据分析师） | 历史营收归因 + A/B 检验结果 | `analysis_report` |
| ③ 可视化/实现 | R08 蛙建成（MVP/可视化） | HTML 方案报告 / 落地页 | `html_report` |
| ④ 评审 | R04 蛙挑刺（评审官） | pass/fail + 门禁复核 | `critique_report` |

## 编排（R01 的 plan / run）

```bash
# 1) 生成任务卡：命中「营收/收入/利润 + 最大化/优化/提升」时走四段场景链
python r01-waquanju-ceo/agent.py plan --intent "停车场一年营收最大化"
# → {"planned": 4, "owners": ["r07", "r06", "r08", "r04"]}

# 2) 按依赖执行：自动交接上游产物 + 逐卡验收
python r01-waquanju-ceo/agent.py run --all
# 或单卡执行（owner 非 r01 时自动转发给对应角色）
python r01-waquanju-ceo/agent.py run --task <task_id>
```

| 机制 | 行为 |
|---|---|
| `plan` | 普通意图按 `skills/s02_decompose.py::ROUTE_MATRIX` 关键词矩阵打分，按命中数排成依赖链；命中业务优化场景时改用 R07→R06→R08→R04 四段链，并为每段挂 `examples/` 示例输入，保证可直接 `run` 演示 |
| `run --all` | 只执行 `deps` 全部 done 的待办卡；执行前 `_hydrate_inputs` 把上游产物目录（`artifacts/{id}`、`artifacts/run-{id}`）里的 json/md/html/csv/txt 追加进下游 `inputs` |
| 显式输入优先 | 任务卡已用 `note="input=<path>"` 钉住输入时不再自动追加，避免上游文件抢在显式输入前面 |
| 状态判定 | 子进程退出码不可靠（缺输入/需澄清时可能仍为 0），编排器以任务卡最终 `status` 为准；failed 会阻断下游依赖 |
| 验收 | 每张 done 卡独立跑 `verify_task`，产物存在即通过 |
| 异构交接边界 | 自动交接只“搬文件”，不转换 schema。评审判据包、PRD→实现规格这类结构化交接，需要在任务卡里显式提供，或由适配器转换（示例链中 R04 用 `examples/criteria_review.json` 做外置判据演示） |

端到端实战演示（不依赖 LLM、确定性产出 HTML）：`python scripts/run_parking_lot_case.py`。

## 关键约束

- **谁生成谁负责**：R07 出「假设」，R06 只「验证假设」不发明方案，R08 只「渲染」不新增分析声明。
- **生成与校验分离**：R06 的生成层（6 角色契约）负责写，`harness/contract/review` 负责关笼子。
- **跨角色失败路由**：R06 验证推翻 R07 假设 → 回 R07 改假设，不硬凑结论（移交协议见 `PROTOCOL.md` 模式 B）。

---

## 入口索引

| 问题 | 读哪份 |
|---|---|
| 谁负责什么、向谁汇报、与谁交接 | `ORG.md` |
| 任务怎样展开、下发、移交、编排 | `PROTOCOL.md` |
| 汇报写什么、什么文笔、什么排版 | `REPORT-STANDARD.md` |
| **全角色商业分析与决策级报告出具标准（必读）** | `docs/SOP_BUSINESS_ANALYSIS_AND_REPORTING.md` |
| **智能体能力升级方法论（体检→对标→硬化→注入→闭环→沉淀）** | `docs/SOP_AGENT_META_UPGRADE.md` |
| 机器可读的角色注册表 | `core/registry.py` |
| 端口/任务卡/事件字段契约 | `core/protocol.py` |
| 共享 HTML 报告渲染器 | `core/report_renderer.py` |
| **通用专业报告生成器（全 20 角色统一调用）** | `shared/report_generator.py` |
