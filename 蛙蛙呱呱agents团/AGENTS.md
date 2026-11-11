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
| 每个角色的完整定义（宿主可直接加载） | `agent-packs/agents/*.md` |
| 专家团清单 / 成员与头像 | `agent-packs/plugin.json` |
| 技能层规格（怎么写出合格 SKILL.md） | `docs/SKILL-LAYER-SPEC.md` |
| 技能层升级路线 | `docs/SKILL-MD-UPGRADE-PLAN.md` |

## 怎么调用

```bash
python guagua.py roles                     # 看 20 个角色
python guagua.py info r06                  # 看某个角色的契约
python guagua.py call r06 --help           # 看它能做什么
python guagua.py skills                    # 看已升级的技能包
python guagua.py plan "你的经营目标"         # 让 R01 拆任务卡
```

## 三条铁律

1. **一个任务一个 owner**——「共同负责」等于没人负责。
2. **生成与校验分离**——谁生产谁不验收，验收归 `r04-watiaoci-reviewer`。
3. **不可逆动作必须创始人签字**——裁员/关停/签合同/动资金不接受口头豁免。

## 提交前自检（六条，全绿才算完）

```bash
python guagua.py check                     # 20 角色入口不回归
python scripts/check_skill_gate.py         # 技能包门槛 + 黄金快照无退化
python scripts/audit_skill_layer.py --check-refs   # SKILL.md 结构分 + 悬空指针
python scripts/gen_agent_packs.py --check  # 专家团包与源无漂移
python scripts/check_threshold_consistency.py      # 跨卡阈值一致（单一出处）
python scripts/sync_dsh_skills.py --check  # DSH 技能镜像无分叉（否则模型读旧技能）
```

## 改这份文件之前

不要手改。它由 `scripts/gen_agent_packs.py` 从 `core/registry.py`、`configs/*.yaml`、
`*/prompt_profile.json`、`ORG.md` 渲染生成；改源，再跑：

```bash
python scripts/gen_agent_packs.py
python scripts/gen_agent_packs.py --check   # 确认无漂移
```
