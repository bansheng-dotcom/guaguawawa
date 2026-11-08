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

## 编排（R01 的 run_task 路由）

```
意图「停车场一年营收最大化」
  → R01 拆解：
      1. R07 出策略假设（定价/套餐/时段/会员）
      2. R06 用历史数据 + A/B 验证假设 → 产出 analysis_material_pack
      3. R08 组装成 HTML 方案报告
      4. R04 复核门禁
  → 产物回 workspace/artifacts/{task_id}/
```

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
