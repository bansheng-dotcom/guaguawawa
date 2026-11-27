# AGENTS.md · 蛙蛙呱呱agents团

> 本文件面向所有支持 [AGENTS.md](https://agents.md) 标准的编码/办公智能体。
> 它只做入口指引，**权威内容在别处**——不在此重复，避免双写漂移。

## 这是什么

一个由 CEO 主理人编排的 20 人专家团，每个角色都有确定性门禁。

## 从哪里读

| 想知道 | 读 |
|---|---|
| 谁负责什么、向谁汇报、与谁交接 | `ORG.md` |
| 任务怎样展开、下发、移交、编排 | `PROTOCOL.md` |
| 汇报写什么、什么文笔、什么排版 | `REPORT-STANDARD.md` |
| 报告产线（唯一出具人 R01） | `REPORT-BRIDGE-GUIDE.md` · `docs/REPORT-LINES.md` |
| 项目边界（工具 vs 项目资产）、brief 契约 | `docs/REPORT-LINES.md` · `使用指南.md` |
| 专家团改了什么、什么时候改的 | `CHANGELOG.md` |
| 每个角色的完整定义（宿主可直接加载） | `agent-packs/agents/*.md` |
| 专家团清单 / 成员与头像 | `agent-packs/plugin.json` |
| 技能层规格（怎么写出合格 SKILL.md） | `docs/SKILL-LAYER-SPEC.md` |
| 技能层升级路线 | `docs/SKILL-MD-UPGRADE-PLAN.md` |
| 术语口径（任务卡 / ClaimCard / 格子 / 职责键） | `docs/GLOSSARY.md` |
| 入口清单（对外一个入口，其余内部） | `docs/ENTRYPOINTS.md` |
| 门禁索引（每个 check 的消费者） | `docs/GATES.md` |

## 怎么调用

```bash
python guagua.py roles                     # 看 20 个角色
python guagua.py info r06                  # 看某个角色的契约
python guagua.py call r06 --help           # 看它能做什么
python guagua.py skills                    # 看已升级的技能包
python guagua.py prompt --role r06 --intent "你的问题"   # 唯一提示词入口（chat 已废弃）
python guagua.py project init ../projects/<slug> --industry "你的行业"   # 项目资产建在团外
python guagua.py plan "你的经营目标"         # 让 R01 拆任务卡
python guagua.py report "你的问题" --dir <项目> --out <目录>   # v11 唯一入口：一条命令出报告（可加 --pdf）
python guagua.py report check --html <报告>                    # 验收成品（三层质检）
python guagua.py run --intent "你的经营目标"                    # 不确定走哪条？先让路由器给建议（--execute 才执行）
# 旧 run / pack / produce / research / --thesis 已退役；诊断用 capabilities / plan
# 完整入口与产线地图见 docs/REPORT-LINES.md
```

### 不确定用哪个入口

| 你要做的事 | 用哪条 |
|---|---|
| 只跑一个角色的一个技能 | `guagua.py call <角色> ...`（要留痕加 `--as-task`） |
| 多角色协作完成经营任务 | `guagua.py plan "..."` → `dispatch` |
| 已有干净数据、要出报告 | `guagua.py report "..." --dir <项目> --out <目录>` |
| 多角色交卡后出报告 | `run-line --source cards --claims <merged.json>` |

`guagua.py run ...` 默认只打印建议命令，不执行；确认后加 `--execute`。

## 项目边界（工具 vs 项目资产）

专家团是**工具**，项目是**资产**，两者物理隔离：

- 项目资产（数据/知识快照/brief/卡/claims/报告）只写 `<PROJECT_ROOT>`；
  默认 `<repo>/projects/<slug>`，可用 `--project` 或 `GUAGUA_PROJECT` 覆盖；
- 专家团内不出现任何项目字段、项目文件、过程产物；写团内一律被守卫拒绝；
- 运行临时物（事件/锁/trace）只写 `GUAGUA_WORKSPACE`（默认 `<repo>/workspace`）；
- 任务卡与 expert_brief 合成 `CardBundle`：卡管 owner/deps/inputs/outputs/
  non_goals，brief 管 must_answer/standards/evidence_rules/acceptance_checks；
  验收只由 brief 派生，卡里不写 acceptance 明细。

## 四条铁律

1. **一个任务一个 owner**——「共同负责」等于没人负责。
2. **生成与校验分离**——谁生产谁不验收，验收归 `r04-watiaoci-reviewer`。
3. **不可逆动作必须创始人签字**——裁员/关停/签合同/动资金不接受口头豁免。
4. **报告只有一个作者（R01）且只加方法不加章节**——执行角色只交 `result.json`；新能力进 `core/analysis_methods.py` 或 `report_framework` 维度；新增章节须先扩 `core/report_kernel/contract.py` 的契约并过 CI。

## 提交前自检（全绿才算完）

```bash
python guagua.py check                     # 20 角色入口不回归
python scripts/ci_report_checks.py         # 报告产线：run-line + 门禁 + 图型 + 风格
python scripts/ci_upgrade_checks.py        # 方法与评测：方法包 / 评测回归 / 技能结论
python scripts/check_skill_gate.py         # 技能包门槛 + 黄金快照无退化
python scripts/audit_skill_layer.py --check-refs --min 75   # 技能卡 ≥75 分 + 悬空指针 0
python scripts/gen_agent_packs.py --check  # 专家团包与源无漂移
python scripts/gen_experts.py --check      # 专家卡与方法库无漂移（防 phantom 方法）
python scripts/check_convergence.py --baseline .convergence-baseline.json   # 收敛门禁只许下降
python scripts/check_threshold_consistency.py      # 跨卡阈值一致（单一出处）
python scripts/sync_dsh_skills.py --check  # DSH 技能镜像无分叉（否则模型读旧技能）
python scripts/check_prompt_system.py     # 意图目录/画像/回归三项一致
python scripts/check_third_party_licenses.py   # 第三方许可状态（分发前加 --strict）
python scripts/check_project_boundary.py   # 团内无项目资产（projects/briefs/claims/report）
python scripts/check_brief_contract.py     # expert_brief v2 七层 / 五门槛 / 18 条上限
python scripts/check_report_isolation.py   # 报告层不读知识库、不读 brief
python scripts/check_role_tests.py         # 20 角色 run_tests.py 全绿（端到端验收）
python -m pytest tests -q -p no:cacheprovider   # 根目录单测
```

## 改这份文件之前

不要手改。它由 `scripts/gen_agent_packs.py` 从 `core/base/registry.py`、`configs/*.yaml`、
`*/prompt_profile.json`、`ORG.md` 渲染生成；改源，再跑：

```bash
python scripts/gen_agent_packs.py
python scripts/gen_agent_packs.py --check   # 确认无漂移
```
