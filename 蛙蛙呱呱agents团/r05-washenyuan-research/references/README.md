# R05 蛙深远 · references 索引（能力卡）

> 一个角色的 references 目录分四类：**方法（怎么想）**、**能力（能做什么）**、
> **技能拆解（s01–s07）**、**工程注记（怎么接）**。这张卡只做目录与验收口径。

## 目录

| 文件/目录 | 是什么 | 什么时候读 |
|---|---|---|
| `method-pack.md` | 六段方法包：决策问题 / 问题树 / 假设与证伪 / 证据分级 / 方法与陷阱 / 输出契约 | 写研究方案或结论前必读 |
| `00-capability-charter.md` | 角色能力宪章：边界、不做什么、交给谁 | 接新任务前对边界 |
| `capabilities/` | 每项能力一张 `SKILL.md`（十节技能包） | 执行某个具体技能时 |
| `s01/`–`s07/` | 七个技能的方法拆解与样例 | 需要看"上次怎么做的" |
| `engineering-notes.md` | 工程注记：路径、命令、常见故障 | 跑不通时 |

## 验收

```bash
python scripts/audit_method.py --all        # 方法包 100 分制，≥80 才可用
python scripts/audit_method_depth.py        # 深度探针：方法/可执行/数据三层
python scripts/audit_skill_layer.py         # 技能包结构分与悬空指针
```

## 红线

- 方法包审计 <80：不得用于对外交付。
- 每条假设必须有**杀死标准**；没有证伪条件的假设不算假设。
- 至少 2 个竞争解释；只有一个解释的结论只能写成"待验证"。
- 输出契约四件套（claim / evidence / confidence / falsifier）缺一不进首页。
