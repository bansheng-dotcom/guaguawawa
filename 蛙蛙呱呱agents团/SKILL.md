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

## 权威文档

- `AGENTS.md`：入口指引与提交前自检六条。
- `ORG.md`：谁负责什么、汇报线、权力与红线、角色边界。
- `PROTOCOL.md`：单角色五步、失败移交、多角色 GSD 编排、验收协议。
- `REPORT-STANDARD.md`：交付报告结构与文风。
- `agent-packs/agents/*.md`：20 个角色的完整定义（宿主可直接加载）。
- `docs/SKILL-LAYER-SPEC.md`：技能层 L1/L2/L3 规格。

## 三条铁律

1. 一个任务一个 owner——「共同负责」等于没人负责。
2. 生成与校验分离——谁生产谁不验收，验收归 R04 蛙挑刺。
3. 不可逆动作必须创始人签字——裁员/关停/签合同/动资金不接受口头豁免。

## 能力边界

- 本地确定性校验 ≠ 线上已执行：外部发布、支付、部署、CRM/ERP 写入未接入时，必须标 `simulated` 或 `blocked`。
- 质量结论只归 R04；其他角色可以自检，但不能给自己签 `pass`。
- 不把真实密钥、身份证、银行卡、生产凭据写入工件。
- R03 无 `run --task` 子命令，使用 `call r03 ...` 直接调用专家技能。

## 汇报

默认 `.md` 快读版 + `.html` 正式版，不吐裸 JSON；产物放在 `workspace/artifacts/{task_id}/` 或 `workspace/rXX-<角色>/`。
