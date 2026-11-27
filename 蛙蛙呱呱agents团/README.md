# 蛙蛙呱呱agents团 · 包内导航

> **完整手册在仓根**：[`../README.md`](../README.md)（20 角色详解、协作流水线、版本记录）。
> 本文件只做一件事：让你在包内 60 秒找到入口。**不重复角色正文**——双写必漂移（2026-11-17 体检结论）。

---

## 这是什么

一个可本地运行、可审计、可编排的「一人公司 OS」：20 个角色，每个角色有确定性 `agent.py` 与门禁；
执行角色只交 `claims.json` / `result.json`，报告由 R01 统一出具，R04 独立验收。

| 想知道 | 读 |
|---|---|
| 谁负责什么、向谁汇报、边界 | [`docs/_entry/ORG.md`](docs/_entry/ORG.md) |
| 任务怎么展开、移交、编排 | [`docs/_entry/PROTOCOL.md`](docs/_entry/PROTOCOL.md) |
| 报告写什么、怎么判合格 | [`REPORT-STANDARD.md`](REPORT-STANDARD.md) |
| 报告产线地图（拆卡默认 / A 数据 / B 应急） | [`docs/REPORT-LINES.md`](docs/REPORT-LINES.md) |
| 拆卡与防代写（nonce / 签名 / 收卡校验） | [`docs/REPORT-DISPATCH.md`](docs/REPORT-DISPATCH.md) |
| 新角色怎么接入报告产线 | [`docs/_entry/REPORT-BRIDGE-GUIDE.md`](docs/_entry/REPORT-BRIDGE-GUIDE.md) |
| 跨宿主入口（agents.md 标准） | [`AGENTS.md`](AGENTS.md) |
| 20 个角色的完整定义（宿主直接加载） | [`agent-packs/agents/`](agent-packs/agents/) |
| 技能层规格 / 升级路线 | [`docs/SKILL-LAYER-SPEC.md`](docs/SKILL-LAYER-SPEC.md) · [`docs/SKILL-MD-UPGRADE-PLAN.md`](docs/SKILL-MD-UPGRADE-PLAN.md) |
| 文档现行/历史索引 | [`docs/README.md`](docs/README.md) |

---

## 60 秒上手

```bash
cd 蛙蛙呱呱agents团

python guagua.py doctor                  # 环境 + 20 角色体检
python guagua.py roles                   # 花名册
python guagua.py info r06                # 某个角色的契约
python guagua.py call r06 --help         # 它的全部子命令
python guagua.py call r06 semantics validate --input examples/semantic_model.json

python guagua.py plan "停车场一年营收最大化"   # R01 拆任务卡
python guagua.py status
python guagua.py dispatch --all
```

---

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

## 包内结构

```
guagua.py              统一入口（roles/info/call/plan/dispatch/report/…）
chat.py                知识注入 Prompt
core/                  注册表、协议、工作区、报告产线（report_cli/dispatch/card_issue/card_plan/dor）、图表引擎
shared/                跨角色共享（role_runtime / methods / capabilities / mcp）
r01-… r20-…            20 个角色（agent.py + skills/ + harness + tests + references）
configs/               rXX.yaml（职责/原则）+ report_card_spec / report_flow / report_coverage
agent-packs/           宿主可直接加载的 20 份角色卡 + plugin.json
avatars/               21 张角色头像（唯一源）
docs/                  规格、SOP、路线图（现行/历史见 docs/README.md）
交付/                  拆卡/协作/报告升级 SOP 与模板；仅 generic_semantics_v1.yaml 是代码依赖
tests/                 pytest 单测 + 回归 + prompt 回归 + evals 夹具（不是缓存）
scripts/               CI 门禁、preflight、生成器、Trae 镜像同步
```

> 头像只有 `avatars/` 一份源；`agent-packs/avatars/` 由 `scripts/gen_agent_packs.py` 生成。

---

## 四条铁律

1. 一个任务一个 owner——「共同负责」等于没人负责。
2. 生成与校验分离——谁生产谁不验收，验收归 `r04-watiaoci-reviewer`。
3. 不可逆动作必须创始人签字——裁员/关停/签合同/动资金不接受口头豁免。
4. 报告只有一个作者（R01）且只加方法不加章节——执行角色只交 `claims.json`；新增章节先扩契约。

---

## 提交前自检

见 [`AGENTS.md`](AGENTS.md) 的「提交前自检（全绿才算完）」。
最少这三条：

```bash
python -m pytest tests -q -p no:cacheprovider
python scripts/preflight.py --dir <项目>
python scripts/sync_trae_skill.py --check
```
