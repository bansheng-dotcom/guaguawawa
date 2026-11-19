# 蛙蛙呱呱agents团 · 包内导航

> **完整手册在仓根**：[`../README.md`](../README.md)（20 角色详解、六条流水线、版本记录）。
> 本文件只做一件事：让你在包内 60 秒找到入口。**不重复角色正文**——双写必漂移（2026-11-17 体检结论）。

---

## 这是什么

一个可本地运行、可审计、可编排的「一人公司 OS」：20 个角色，每个角色有确定性 `agent.py` 与门禁；
执行角色只交 `result.json`，报告由 R01 统一出具。

| 想知道 | 读 |
|---|---|
| 谁负责什么、向谁汇报、边界 | [`ORG.md`](ORG.md) |
| 任务怎么展开、移交、编排 | [`PROTOCOL.md`](PROTOCOL.md) |
| 报告写什么、怎么判合格 | [`REPORT-STANDARD.md`](REPORT-STANDARD.md) |
| 新角色怎么接入报告产线 | [`REPORT-BRIDGE-GUIDE.md`](REPORT-BRIDGE-GUIDE.md) |
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

python guagua.py report "…" --dir <项目> --out <目录>   # 报告主线（等价 report run-line）
```

---

## 包内结构

```
guagua.py              统一入口（roles/info/call/plan/dispatch/report/…）
chat.py                知识注入 Prompt
core/                  注册表、协议、工作区、报告产线、图表引擎
shared/                跨角色共享（role_runtime / methods / capabilities / mcp）
r01-… r20-…            20 个角色（agent.py + skills/ + harness + tests + references）
configs/               rXX.yaml（职责/原则）+ report_policy.yaml + skill_graph.json
agent-packs/           宿主可直接加载的 20 份角色卡 + plugin.json
avatars/               21 张角色头像（唯一源）
docs/                  规格、SOP、路线图（现行/历史见 docs/README.md）
scripts/               CI 门禁、生成器、审计脚本
```

> 头像只有 `avatars/` 一份源；`agent-packs/avatars/` 由 `scripts/gen_agent_packs.py` 生成。

---

## 四条铁律

1. 一个任务一个 owner——「共同负责」等于没人负责。
2. 生成与校验分离——谁生产谁不验收，验收归 `r04-watiaoci-reviewer`。
3. 不可逆动作必须创始人签字——裁员/关停/签合同/动资金不接受口头豁免。
4. 报告只有一个作者（R01）且只加方法不加章节——执行角色只交 `result.json` + `evidence.json`；新增章节先扩契约。

---

## 提交前自检

见 [`AGENTS.md`](AGENTS.md) 的「提交前自检（全绿才算完）」。
