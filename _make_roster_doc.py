import pathlib
import sys

sys.path.insert(0, '.')
from core import roster  # noqa: E402

r = roster.build()
t = r['totals']
lines = [
    '# 蛙蛙呱呱专家团 · 名册（20 人）',
    '',
    '> 生成式名册：`core/roster.py` 从 20 个角色目录现场读取（身份 + 技能动作 + 技能包）。',
    f'> 专家 {r["count"]} 人｜可进报告 {t["report_roles"]} 人｜技能动作 {t["actions"]} 个｜技能包 {t["skills"]} 个',
    '',
    '| # | 角色 | 姓名 | 职务 | 目录 | 动作 | 技能包 | 进报告 | 主责能力 |',
    '|---|---|---|---|---|---|---|---|---|',
]
for rid, v in r['roles'].items():
    caps = '、'.join(v['capabilities'][:3])
    lines.append(
        f"| {rid} | {v['name']} | {v['title']} | `{v['dir']}` | "
        f"{len(v['actions'])} | {len(v['skills'])} | "
        f"{'是' if v['enters_report'] else '否'} | {caps} |")

lines += [
    '',
    '## 名册在哪（三处，用途不同）',
    '',
    '| 位置 | 是什么 | 谁在用 |',
    '|---|---|---|',
    '| `core/registry.py::ROLES` | **手写身份表**（id/name/title/dir/status/capabilities/inputs/outputs），20 条 | 系统启动、加载角色、判断谁进报告 |',
    '| `core/roster.py` | **生成式完整名册**（身份 + `prompt_profile.json` 的动作 + `skills/` 技能包） | 发任务卡、反查「谁能干这件事」 |',
    '| `r01-…` ~ `r20-…` 20 个目录 | **专家团本体**：`agent.py`、`prompt_profile.json`、`skills/`、`tests/` | 每个角色真正干活的地方 |',
    '',
    '## 怎么查',
    '',
    '```bash',
    'python -m core.roster                    # 20 行总览',
    'python -m core.roster --who 市场规模      # 反查谁能干',
    'python guagua.py roles                   # 20 个角色入口',
    'python guagua.py info r05                # 某个角色的契约',
    '```',
    '',
    '## 20 人的分工（按报告相关性）',
    '',
    '| 段 | 角色 |',
    '|---|---|',
    '| 编排与评审 | r01 蛙全局（CEO 编排）、r04 蛙挑刺（独立评审） |',
    '| 研究与分析 | r05 蛙深远（战略研究）、r06 蛙得清（数据分析） |',
    '| 商业与交易 | r03 蛙守线（财务合规）、r12 蛙引流（增长）、r13 蛙客成（客户）、r14 蛙交易（履约）、r15 蛙供应（供应链） |',
    '| 产品与内容 | r07 蛙得明（产品）、r11 蛙点题（内容） |',
    '| 组织与运营 | r02 蛙排布（COO）、r16 蛙人事 |',
    '| 工程（不产报告） | r08 MVP、r09 代码、r10 设计、r17 自动化 |',
    '| 数据与可靠性 | r18 蛙数仓、r19 蛙智模、r20 蛙值守 |',
]
pathlib.Path('交付/专家团名册-20人.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines[:8]))
print('...')
print('written 交付/专家团名册-20人.md')
