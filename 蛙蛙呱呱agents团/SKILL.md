---
name: wawaguagua-agents
description: 蛙蛙呱呱 · 20 角色智能体公司（一人公司 OS）。当用户提到「蛙蛙呱呱」「guagua」「20 角色专家团」「AI 公司」或要求按 CEO 主理人 R01 编排、把经营目标拆成任务卡、调用 R01–R20 任一角色（战略研究/数据分析/数仓/模型评估/产品/MVP/工程/设计/内容/增长/客户成功/交易/供应链/人事/自动化/SRE）做深一件事，或要求生成与校验分离、R04 独立评审、R03 合规红线复核时使用。
---

# 蛙蛙呱呱 · 20 角色智能体公司

本技能包是一个可本地运行、可审计、可编排的 AI 公司操作系统，不是普通问答。所有执行走确定性 `agent.py` 与门禁，产物落 `workspace/`。

## 何时触发

- 用户要找「蛙蛙呱呱」、CEO 主理人、20 角色专家团，或要求把经营目标拆成多角色任务卡。
- 用户要某个专业职能做深：研究、数据分析、产品、MVP、工程、设计、内容、增长、交易、供应链、人事、自动化、SRE。
- 用户要求独立验收、合规红线、失败移交、按波次编排。

## 怎么用

在本技能包根目录执行（该目录即原 `蛙蛙呱呱agents团`）：

```bash
python guagua.py roles                     # 20 角色花名册
python guagua.py info r06                  # 角色契约与入口
python guagua.py call r06 --help           # 角色支持的全部子命令
python guagua.py call r06 <子命令> ...      # 单角色执行
python guagua.py plan "经营目标"            # R01 拆任务卡
python guagua.py status                    # 查看任务依赖与状态
python guagua.py dispatch --all            # 按依赖执行并验收
python guagua.py chat --role r06 --intent "..."   # 生成知识注入 Prompt
python guagua.py doctor                    # 环境诊断 + 20 角色体检
```

`call` 规则：第一个参数是角色，其后参数原样转发给该角色的 `agent.py`。

## 报告产线 v14（拆卡线唯一默认 + 两段发卡）

分析不是写观点，是**先查源、再按卡取数、按格交付、最后合并成判断**。2026-11-23 起，拆卡线是唯一默认路线：

```bash
report clarify --intent "…" --out <项目>          # 出 12 问（R01 在对话里问用户）
report intake --dir <项目> --answer I1=…          # 记录回答（≥10 条才可签 brief）
report clarify --dir <项目> --confirm --user-said "用户原话"
report brief --dir <项目> --plan                  # 出映射表 + 卡片清单给用户看（不发卡）
report brief --dir <项目> --plan --confirm --ack-cards --user-said "用户原话"

# ① 探源卡（给 r18 蛙数仓，抄送 r05）：查清有哪些源，登记数据目录
report probe --dir <项目> --issue                 # → cards/r18/TASK.md
#   r18 回填 cards/r18/data_catalog.json（table/owner/fields/cost/freshness）

# ② 探测：需求 × 源匹配 → 生成供给方案（每格能到 L1 还是 L2）
report probe --dir <项目>                         # → plan/supply.json
#   --degrade：把无数据的格子标 unavailable

# ③ 采集卡 → 子智能体按 nonce 执行，交 cards/<role>/claims.json
report preflight --dir <项目>                     # 九项预检 P1–P9
report collect --dir <项目> --out <项目>/out       # 收卡：比 planned vs actual → claims_merged.json
report run-line --intent "…" --claims <项目>/out/claims_merged.json --out <项目>/out/report --pdf
```

**两段发卡**：第一次给 **r18 蛙数仓**查源（探源卡），第二次给执行层采数（采集卡）。
少了探源那一步，采集卡只能写"去采品牌价格"，执行层要么采不到、要么自己编。

**能力级别**：报告口径节第一条写「计划 L1 / 实际 L1」。
计划 L1 交付 L1 = 按计划交付；计划 L2 实际 L1 = 降级，必须写 `degraded_from` 与 `L2_condition`。

**人必须在环里**：12 问必须问给用户（`--by agent` 代答不算，`user_answers<10` 签不了 brief）；
澄清确认必须带 `--user-said`；发卡前必须 `--plan` 把卡片清单给用户过目，确认时带 `--ack-cards`。
没有 `coverage/issued.json` 的项目，`collect` 直接拒收（老卡只有 `--allow-legacy` 且标降级）。

| 层 | 模块 | 产物 |
|---|---|---|
| 接活 12 问 + brief 签字 | `core/intake.py` | `intake.json` / `brief.json` |
| 拆卡格网（六维 MECE） | `core/cards/card_upgrade.py` | `plan/grid.json` |
| **探源卡（给 r18）** | **`core/cards/pipeline.py`** | **`cards/r18/TASK.md`** → `data_catalog.json` |
| **可行性探测 + 供给方案** | **`core/cards/pipeline.py`** + **`core/sources/supply_plan.py`** | **`plan/supply.json`** |
| 卡就绪（DoR） | `core/dor.py` | `plan/dor.json` |
| 派活校验（nonce + 签名 + 执行者） | `core/cards/pipeline.py` | `coverage/issued.json` |
| 预检九项（P1–P9） | `scripts/preflight.py` | 退出码 / PASS-FAIL |
| 收卡整备（归一/去重/冲突/覆盖 + 能力级别） | `core/cards/pipeline.py` | `claims_merged.json` |
| 章节校验 + 渲染 | `core/report/report_flow.py` + `core/report/report_renderer.py` | `report.html` |

硬规则：**未注册 metric 拒收**；**图只许 query(raw)**；DoR 未过不发卡；brief 未签不拆卡；
**没有 nonce 的卡不收**；**降级必须带 `degraded_from` + `L2_condition`**。

## 权威文档

- `AGENTS.md`：入口指引与提交前自检清单。
- `ORG.md`：谁负责什么、汇报线、权力与红线、角色边界。
- `PROTOCOL.md`：单角色五步、失败移交、多角色 GSD 编排、验收协议。
- `REPORT-STANDARD.md`：交付报告结构与文风。
- `agent-packs/agents/*.md`：20 个角色的完整定义（宿主可直接加载）。
- `docs/SKILL-LAYER-SPEC.md`：技能层 L1/L2/L3 规格。

## 四条铁律

1. 一个任务一个 owner——「共同负责」等于没人负责。
2. 生成与校验分离——谁生产谁不验收，验收归 R04 蛙挑刺。
3. 不可逆动作必须创始人签字——裁员/关停/签合同/动资金不接受口头豁免。
4. 报告只有一个作者（R01）且只加方法不加章节——执行角色只交 `result.json`；新能力进 `core/analysis_methods.py`，`frames_*.py` 冻结。

## 能力边界

- 本地确定性校验 ≠ 线上已执行：外部发布、支付、部署、CRM/ERP 写入未接入时，必须标 `simulated` 或 `blocked`。
- 质量结论只归 R04；其他角色可以自检，但不能给自己签 `pass`。
- 不把真实密钥、身份证、银行卡、生产凭据写入工件。
- R03 无 `run --task` 子命令，使用 `call r03 ...` 直接调用专家技能。

## 汇报

默认 `.md` 快读版 + `.html` 正式版，不吐裸 JSON；产物放在 `workspace/artifacts/{task_id}/` 或 `workspace/rXX-<角色>/`。
