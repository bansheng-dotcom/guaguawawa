# 门禁索引（GATES）

> 由 `python scripts/gates_index.py --write` 生成，禁止手改。
> 状态：CI=进 CI；GATES=configs/gates.yaml 引用；INDIRECT=被其它脚本调用；MANUAL=显式登记（只能手工跑）；未登记=没有消费者。

## 汇总

| 状态 | 数量 |
|---|---:|
| CI | 21 |
| GATES | 1 |
| INDIRECT | 10 |
| MANUAL | 1 |
| 未登记 | 0 |

## 脚本

| 脚本 | 状态 | 证据 | 用途 |
|---|---|---|---|
| `check_analysis_chain.py` | CI | ci_report_checks / ci_upgrade_checks | R06 分析链门禁：六段工件齐全、哈希/门禁/跨段一致。 |
| `check_business_terms.py` | CI | ci_report_checks / ci_upgrade_checks | 业务词隔离门禁（方案 §3.6 / P1-7）。 |
| `check_chart_edges.py` | CI | ci_report_checks / ci_upgrade_checks | charts_pro 边界门禁：空数据 / 零域 / 负值 / 长标签 / 超多类别。 |
| `check_chart_fail_if_missing.py` | CI | ci_report_checks / ci_upgrade_checks | 图表必绘门禁。 |
| `check_chart_report_embed.py` | CI | ci_report_checks / ci_upgrade_checks | 兼容入口：ci_report_checks 仍调本文件名；实际校验 charts_pro。 |
| `check_claim_trace.py` | CI | ci_report_checks / ci_upgrade_checks | 结论可追门禁：正文每个数字必须回到 material pack。 |
| `check_conclusions.py` | CI | ci_report_checks / ci_upgrade_checks | 结论层审计：跑评测集里的技能，检查每个结果都有 conclusion（或明确 blocked）。 |
| `check_convergence.py` | CI | ci_report_checks / ci_upgrade_checks | 收敛门禁：同一件事不许被第二次新建。 |
| `check_dead_code.py` | CI | ci_report_checks / ci_upgrade_checks | 「每个文件都要能说清谁在用」的可执行版本。 |
| `check_doc_consistency.py` | CI | ci_report_checks / ci_upgrade_checks | 文档一致性检查：报告的产线版本与步骤在多个入口文档里必须一致。 |
| `check_engine_variants.py` | CI | ci_report_checks / ci_upgrade_checks | 引擎台账门禁（T0 的“止血”版本）。 |
| `check_gate_lock.py` | CI | ci_report_checks / ci_upgrade_checks | 门禁脚本锁：改门禁必须是显式动作，且留下提交痕迹。 |
| `check_move_cards.py` | CI | ci_report_checks / ci_upgrade_checks | 校验 Move 卡片：让「学习」有可判定的入口。 |
| `check_r04_inputs.py` | CI | ci_report_checks / ci_upgrade_checks | R04 验收输入派生校验：三份输入必须由产物派生（sha 对得上）。 |
| `check_report_flow.py` | CI | ci_report_checks / ci_upgrade_checks | 唯一报告门禁（2026-11-15 产线收敛后 / 2026-11-20 收紧）：只看 HTML 成品，不看是谁画的。 |
| `check_report_presentation.py` | CI | ci_report_checks / ci_upgrade_checks | 呈现层门禁（v12 / T9）。 |
| `check_report_privacy.py` | CI | ci_report_checks / ci_upgrade_checks | 报告产线隐私扫描：凭据/个人信息不得进入 claims、manifest、报告。 |
| `check_report_style.py` | CI | ci_report_checks / ci_upgrade_checks | 报告字体门禁：全篇禁用斜体，标题/表头/图注不得用衬线体。 |
| `check_role_packs.py` | CI | ci_report_checks / ci_upgrade_checks | 校验 20 个角色领域包：书、方法、指标、决策、远见、误判、章节。 |
| `check_role_thickness.py` | CI | ci_report_checks / ci_upgrade_checks | 20 角色厚度地板（T1）。 |
| `check_skill_integration.py` | CI | ci_report_checks / ci_upgrade_checks | 校验「领域方法 → 现有技能」的接入率，防止另起一套。 |
| `check_content.py` | GATES | configs/gates.yaml | 内容哈希（变更台账的底层工具）。 |
| `check_brief_contract.py` | INDIRECT | 被 gen_agent_packs.py 调用 | brief 契约门禁：expert_brief v2 的七层 / 五门槛 / 18 条上限不许回退。 |
| `check_charts_pro.py` | INDIRECT | 被 check_chart_edges.py 调用 | charts_pro 门禁：每型都有样例、都能渲染、别名可解析。 |
| `check_project_boundary.py` | INDIRECT | 被 check_report_privacy.py、gen_agent_packs.py 调用 | 项目边界门禁：专家团里不许出现项目资产。 |
| `check_prompt_system.py` | INDIRECT | 被 gen_agent_packs.py 调用 | P2.2 统一门禁：一条命令跑完提示词系统的全部 CI 检查。 |
| `check_report_isolation.py` | INDIRECT | 被 gen_agent_packs.py 调用 | 报告层隔离门禁：报告层只读证据，不读知识库、不读 expert_brief。 |
| `check_report_layout.py` | INDIRECT | 被 check_gate_lock.py、check_report_flow.py 调用 | 报告版式出厂检查（不关心报告是谁画的，只看 HTML 结果）。 |
| `check_role_tests.py` | INDIRECT | 被 gen_agent_packs.py 调用 | 20 角色端到端验收：逐个执行 `<role>/run_tests.py`，任一非 0 即失败。 |
| `check_skill_gate.py` | INDIRECT | 被 gen_agent_packs.py 调用 | 技能层 CI 门禁：升级门槛 + 黄金快照回归。 |
| `check_third_party_licenses.py` | INDIRECT | 被 gen_agent_packs.py 调用 | 第三方许可状态门禁。 |
| `check_threshold_consistency.py` | INDIRECT | 被 gen_agent_packs.py 调用 | 跨卡阈值一致性检查：防止同一概念在不同 SKILL.md 里被定义成不同数值。 |
| `check_gates.py` | MANUAL | 由 core/report/report_cli.py 的 gates 子命令在运行时调用 | 出口闸：G1 口径 + G2 台账 + G3 图表。 |

## configs/gates.yaml

| gate | 实现 / 阈值 |
|---|---|
| `caliber` | threshold=0.2 impl=core.cells_claims.audit_cards |
| `content` | golden_corpus=baselines/golden_corpus.json tool=scripts/check_content.py |
| `chart` | registry=core.report_theme.charts_pro.spec.RENDERERS |
