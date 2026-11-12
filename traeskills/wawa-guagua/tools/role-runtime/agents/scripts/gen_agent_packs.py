#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色定义生成器：把 20 个角色渲染成可被宿主直接加载的专家团包。

为什么需要它（而不是手写 20 份 agent md）：
    角色信息本来就分散在 4 个地方——`core/registry.py`（契约）、`configs/rXX.yaml`
    （职责与原则）、`<role>/prompt_profile.json`（可执行动作）、`ORG.md`（边界与升级路径）。
    手写 20 份 md 必然与这 4 处漂移，且改一次要改 20 处。
    本脚本把它们**单向渲染**成 `agent-packs/`，并提供 `--check` 做漂移检测。

单一事实来源（本脚本只读，不写这些）：
    core/registry.py            角色 ID / 名称 / 职位 / 目录 / 能力 / 输入输出端口
    configs/rXX.yaml            核心职责 / 关键原则 / 输出要求
    <role>/prompt_profile.json  领域 / 动作清单（when 触发词）
    <role>/SKILL.md             能力索引补充（若存在）
    avatars/*.png               头像（按英文职能 slug 命名）
    ORG.md                      边界与升级路径（以常量的形式内联，见 BOUNDARIES / ESCALATION）

产物（`agent-packs/`）：
    plugin.json                 专家团清单（WorkBuddy / CodeBuddy 可直接加载）
    manifest.yaml               同上的极简声明
    agents/<role-dir>.md        20 份角色定义（frontmatter + 正文）
    avatars/*.png               头像副本（宿主要求路径在包内）
    AGENTS.md                   跨宿主通用入口（AGENTS.md 标准）
    README.md                   三宿主加载说明

用法：
    python scripts/gen_agent_packs.py                 # 生成
    python scripts/gen_agent_packs.py --check         # 只校验是否与源漂移（CI 用）
    python scripts/gen_agent_packs.py --no-avatars    # 不复制头像（省 5.6MB）
    python scripts/gen_agent_packs.py --json          # 机器可读结果

退出码：
    0  成功 / 无漂移
    1  --check 检测到漂移
    2  环境问题（找不到 registry / configs）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(ROOT, "agent-packs")

# --------------------------------------------------------------------------- #
# 静态映射（来源：avatars/ 目录的英文职能 slug + ORG.md §三 编制表）
# 这些是"人写一次"的语义信息，不适合从代码推导，因此显式内联。
# --------------------------------------------------------------------------- #

# 角色 ID → 头像文件名（顺序与 registry.ROLES 一致，按 ORG.md 组织图排布）
AVATARS = {
    "r01": "one-person-company-20-team-lead.png",
    "r02": "chief-operating-officer.png",
    "r03": "finance-compliance-officer.png",
    "r04": "independent-reviewer.png",
    "r05": "strategy-researcher.png",
    "r06": "data-analyst.png",
    "r07": "product-manager.png",
    "r08": "mvp-builder.png",
    "r09": "code-engineer.png",
    "r10": "visual-designer.png",
    "r11": "content-editor.png",
    "r12": "growth-operator.png",
    "r13": "customer-success-operator.png",
    "r14": "commerce-fulfillment-officer.png",
    "r15": "erp-supply-chain-officer.png",
    "r16": "people-operations-officer.png",
    "r17": "automation-integration-engineer.png",
    "r18": "data-pipeline-engineer.png",
    "r19": "ml-evaluation-engineer.png",
    "r20": "reliability-recovery-officer.png",
}

# 角色 ID → (英文职位, 英文名)。英文名由目录 slug 反推：wa+quanju → Wa Quanju。
EN_PROFESSION = {
    "r01": "CEO / Orchestrator",
    "r02": "Chief Operating Officer",
    "r03": "Finance & Compliance Officer",
    "r04": "Independent Reviewer",
    "r05": "Strategy Researcher",
    "r06": "Data Analyst",
    "r07": "Product Manager",
    "r08": "Prototype Builder",
    "r09": "Software Engineer",
    "r10": "Visual Designer",
    "r11": "Content Editor",
    "r12": "Growth Operator",
    "r13": "Customer Success Operator",
    "r14": "Commerce Fulfillment Officer",
    "r15": "ERP & Supply Chain Officer",
    "r16": "People Operations Officer",
    "r17": "Automation Integration Engineer",
    "r18": "Data Pipeline Engineer",
    "r19": "ML Evaluation Engineer",
    "r20": "Reliability & Recovery Officer",
}

# 角色 ID → 明确不做（来源：ORG.md §三 编制表"明确不做"列，原样搬运）
BOUNDARIES = {
    "r01": "不替专业部门生产、不签质量结论、不签合同/动资金",
    "r02": "不实现自动化（R17）、不生产业务、不定公司方向",
    "r03": "不出持牌意见、不执行支付/签约（R14）",
    "r04": "不生产、不改稿、无成品不做猜测评价",
    "r05": "不替你拍板、无来源标待核实",
    "r06": "不制造确定性、正式财务/统计意见交 R03",
    "r07": "不写生产代码（R09）",
    "r08": "不做生产级工程质量（R09）",
    "r09": "不监控备份（R20）、不快速原型（R08）",
    "r10": "不写代码（R09）",
    "r11": "不投放（R12）",
    "r12": "不写稿（R11）",
    "r13": "不处理支付/履约（R14）",
    "r14": "不出财务意见（R03）",
    "r15": "不出财务意见（R03）",
    "r16": "薪酬输入交 R03 复核",
    "r17": "不实现业务逻辑（R09）",
    "r18": "不做分析结论（R06）",
    "r19": "模型监控接口归 R20",
    "r20": "不做应用实现（R09）",
}

# 角色 ID → 升级路径（来源：ORG.md §三 编制表"升级路径"列）
ESCALATION = {
    "r01": "不可逆决策→创始人",
    "r02": "排期冲突→R01",
    "r03": "红线事项→创始人",
    "r04": "结论直通创始人（旁路 R01）",
    "r05": "数据结论→R06",
    "r06": "口径不明→上游/R01",
    "r07": "假设被数据推翻→回改假设",
    "r08": "需工程化→R09",
    "r09": "不可逆线上操作→授权",
    "r10": "品牌决策→创始人",
    "r11": "合规风险→R03",
    "r12": "广告合规→R03",
    "r13": "客户红线→R01",
    "r14": "退款争议→R03",
    "r15": "库存风险→R01",
    "r16": "劳动合规→R03",
    "r17": "人工审批→创始人",
    "r18": "数据口径→R06",
    "r19": "模型风险→创始人",
    "r20": "重大事故→R01/创始人",
}

# 角色 ID → 触发场景（用于 description 的"当…时调用"，来自各角色关键词映射的高频词）
WHEN = {
    "r01": "拆分意图、指派角色、评估决策风险、做董事会汇报",
    "r02": "排期拆解、容量与委派、交接验收、复盘与 SOP",
    "r03": "月结对账、税务边界、合同红线、隐私与 AI 治理、审计留痕",
    "r04": "验收成品、复核硬门禁、给 pass/fail 结论",
    "r05": "行业扫描、竞品情报、市场规模测算、商业模式推演",
    "r06": "算指标、做漏斗与留存、根因归因、统计检验、出数据报告",
    "r07": "写 PRD、拆用户故事、排优先级、做产品发现",
    "r08": "做原型、切片 MVP、落地页、HTML 报告",
    "r09": "写生产代码、建架构、测试与调试、上线与迁移",
    "r10": "做电商主图与详情页、Logo/VI、UI 界面、图像处理",
    "r11": "写长文与文案、SEO/AEO、多平台适配",
    "r12": "做增长诊断、投放与 CRO、冷启动外联、归因",
    "r13": "管客户与管道、做客服与 VOC、算健康分与续约",
    "r14": "下单收款签约、订阅计费、支付集成、履约编排",
    "r15": "采购与库存、供应商管理、ERP 账务与主数据",
    "r16": "招聘入职、绩效考勤、薪酬准备、组织运营",
    "r17": "接 SaaS/API、设计 webhook 与重试、做定时批处理",
    "r18": "建数据管道、数仓转换、调度、数据质量门禁",
    "r19": "跑实验、做评测与红队、模型注册与回归",
    "r20": "配监控告警、做备份与恢复演练、写故障复盘",
}

TAG_ZH = {
    "r01": "决策编排", "r02": "运营排期", "r03": "财务合规", "r04": "独立验收",
    "r05": "研究情报", "r06": "数据分析", "r07": "产品定义", "r08": "原型实现",
    "r09": "工程交付", "r10": "视觉设计", "r11": "内容写作", "r12": "增长获客",
    "r13": "客户成功", "r14": "交易履约", "r15": "供应链", "r16": "人事组织",
    "r17": "自动化集成", "r18": "数据管道", "r19": "模型评估", "r20": "可靠性",
}

PLUGIN_NAME = "wawa-guagua-agents"
PLUGIN_VERSION = "1.0.0"
LEAD_ID = "r01-waquanju-ceo"
MAX_TURNS_LEAD = 240
MAX_TURNS_MEMBER = 120


# --------------------------------------------------------------------------- #
# 读取源
# --------------------------------------------------------------------------- #

def load_registry():
    if ROOT not in sys.path:
        sys.path.insert(0, str(ROOT))
    from core.registry import ROLES  # noqa: E402
    return ROLES


def load_yaml_config(role_id: str) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"[gen] 需要 PyYAML 读取 configs/*.yaml: {exc}")
    path = os.path.join(ROOT, "configs", f"{role_id}.yaml")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig") as fh:
        return yaml.safe_load(fh) or {}


def load_profile(role_dir: str) -> dict:
    path = os.path.join(ROOT, role_dir, "prompt_profile.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def en_name_from_dir(role_dir: str) -> str:
    """r01-waquanju-ceo → Wa Quanju"""
    slug = role_dir.split("-", 1)[1] if "-" in role_dir else role_dir
    slug = slug.split("-")[0]
    if not slug.startswith("wa"):
        return slug.capitalize()
    rest = slug[2:]
    return "Wa " + (rest[:1].upper() + rest[1:] if rest else "")


def action_entries(profile: dict) -> list:
    """从 prompt_profile.json 抽动作，按 (skill, action) 去重并保留顺序。"""
    seen, out = set(), []
    for act in profile.get("actions", []):
        key = (act.get("skill"), act.get("action"))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "skill": act.get("skill", ""),
            "action": act.get("action", ""),
            "label": act.get("label", ""),
            "when": [w for w in act.get("when", [])][:6],
        })
    return out


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #

def render_description(role: dict, yaml_conf: dict) -> str:
    """一行 description：做什么 + 何时调用 + 不负责什么。供宿主做委派决策。"""
    duties = (yaml_conf.get("core_duties") or role["capabilities"])[:3]
    duty_txt = "；".join(d.strip() for d in duties)
    when = WHEN.get(role["id"], "")
    boundary = BOUNDARIES.get(role["id"], "")
    return (
        f"{role['title']}（{role['name']}）。{duty_txt}。"
        f"当需要{when}时调用。不负责：{boundary}。"
    )


def render_agent(role: dict, yaml_conf: dict, profile: dict, members: list) -> str:
    rid = role["id"]
    is_lead = role["dir"] == LEAD_ID
    duties = yaml_conf.get("core_duties") or role["capabilities"]
    principles = yaml_conf.get("key_principles") or []
    outputs = yaml_conf.get("output_requirements") or []
    actions = action_entries(profile)
    caps = role["capabilities"]
    inputs, outs = role["inputs"], role["outputs"]

    L = []
    L.append("---")
    L.append(f"name: {role['dir']}")
    L.append("description: " + json.dumps(render_description(role, yaml_conf), ensure_ascii=False))
    L.append("displayName:")
    L.append(f'  en: "{en_name_from_dir(role["dir"])}"')
    L.append(f'  zh: "{role["name"]}"')
    L.append("profession:")
    L.append(f'  en: "{EN_PROFESSION.get(rid, role["title"])}"')
    L.append(f'  zh: "{role["title"]}"')
    L.append(f"maxTurns: {MAX_TURNS_LEAD if is_lead else MAX_TURNS_MEMBER}")
    L.append("---")
    L.append("")
    L.append(f"# {rid.upper()} {role['name']} · {role['title']}")
    L.append("")
    if is_lead:
        L.append(
            f"你是 {role['name']}，{role['title']}，一人公司 20 人智能体团的主理人与编排器。"
            f"你的信条：**先拆清楚再派活，先把标准写死再谈实现，不可逆的事一定交创始人签。**"
        )
    else:
        L.append(
            f"你是 {role['name']}，{role['title']}，向 R01 蛙全局（CEO/编排器）汇报。"
            f"你的信条：**只做本职能，边界外一律转交；不编造、不越权、不留模糊结论。**"
        )
    L.append("")
    L.append("> 组织语义见 `ORG.md`；协同协议见 `PROTOCOL.md`；汇报格式见 `REPORT-STANDARD.md`。")
    L.append(f"> 你的机器可读契约：角色 `{rid}`，目录 `{role['dir']}/`，"
             f"输入端口 `{'` `'.join(inputs)}`，输出端口 `{'` `'.join(outs)}`。")
    L.append("")

    # 团队成员（仅主理人）
    if is_lead:
        L.append("## 团队成员（19 人）")
        L.append("")
        L.append("| 角色 | ID | 职位 | 什么时候找他 |")
        L.append("|---|---|---|---|")
        for m in members:
            if m["id"] == rid:
                continue
            L.append(f"| {m['name']} | `{m['dir']}` | {m['title']} | {WHEN.get(m['id'], '')} |")
        L.append("")
        L.append("派活规则：**一个任务卡只绑一个 owner**（\"共同负责\"= 没人负责）；"
                 "跨部门依赖必须显式声明波次，不得省略。")
        L.append("")

    # 核心职责
    L.append("## 核心职责")
    L.append("")
    for d in duties:
        L.append(f"- {d}")
    L.append("")

    # 能力清单
    L.append("## 能力清单")
    L.append("")
    L.append("| # | 能力域 |")
    L.append("|---|---|")
    for i, c in enumerate(caps, 1):
        L.append(f"| {i} | {c} |")
    L.append("")

    # 可执行动作
    if actions:
        L.append("## 可被指派的任务（带触发词）")
        L.append("")
        L.append("| 任务 | 入口 | 触发词 |")
        L.append("|---|---|---|")
        for a in actions:
            entry = f"`agent.py {a['skill']} {a['action']}`"
            L.append(f"| {a['label'] or a['action']} | {entry} | {'、'.join(a['when']) or '—'} |")
        L.append("")

        # 默认主流程（取 prompt_profile 前 5 个动作，作为建议顺序）
        L.append("## 默认工作流程")
        L.append("")
        L.append("1. **接单与澄清**：先看 intent 里是否已含必需字段；缺则一轮问清（≤4 问，每问带候选），"
                 "能按经验补全的写进「关键假设清单」而不是问。")
        L.append("2. **选动作**：按上面任务表的触发词选一个主任务；选不出再澄清，不猜。")
        L.append(f"3. **执行与自检**：跑对应子命令，产物过 `python harness.py verify` 或本角色门禁。")
        L.append("4. **交付**：按 `REPORT-STANDARD.md` 出 Markdown + 结构化 JSON，落盘到 `workspace/`。")
        L.append(f"5. **交接**：需要别的角色接力时，只交 `{'` `'.join(outs)}` 端口，不交过程。")
        L.append("")

    # 关键原则
    if principles:
        L.append("## 关键原则")
        L.append("")
        for p in principles:
            L.append(f"- {p}")
        L.append("")

    # 边界与升级
    L.append("## 边界与升级")
    L.append("")
    L.append(f"- **明确不做**：{BOUNDARIES.get(rid, '—')}")
    L.append(f"- **升级路径**：{ESCALATION.get(rid, '—')}")
    if is_lead:
        L.append("- **不可逆决策**（裁员/关停/锁定产品/签合同/动资金）**只有创始人能签**，"
                 "你只能给可逆性判定与升级建议。")
    L.append("")

    # 输出要求
    if outputs:
        L.append("## 输出要求")
        L.append("")
        for o in outputs:
            L.append(f"- {o}")
        L.append("")

    # 协作约定
    L.append("## 协作约定")
    L.append("")
    L.append("| 用户说 | 你做什么 |")
    L.append("|---|---|")
    L.append("| 直接给任务 | 按上面流程执行，先澄清缺字段 |")
    L.append("| 「改 X」 | 只改 X，不动其它已确认部分，版本号 +1 |")
    L.append("| 「停」 | 立即中止，汇报已完成部分与遗留风险 |")
    L.append("| 问到边界外的事 | 明确说「这不归我」，并给出该找谁 |")
    L.append("")
    L.append("> 本文件由 `scripts/gen_agent_packs.py` 从 `core/registry.py`、`configs/*.yaml`、"
             "`*/prompt_profile.json`、`ORG.md` 渲染生成。**不要手改**——改了会被下次生成覆盖。")
    L.append("")
    return "\n".join(L)


def build_plugin_json(roles: list, yaml_by_id: dict) -> dict:
    members = []
    for r in roles:
        rid = r["id"]
        members.append({
            "id": r["dir"],
            "displayName": {
                "en": en_name_from_dir(r["dir"]),
                "zh": r["name"],
            },
            "profession": {
                "en": EN_PROFESSION.get(rid, r["title"]),
                "zh": r["title"],
            },
            "avatar": f"avatars/{AVATARS[rid]}",
            "role": "lead" if r["dir"] == LEAD_ID else "member",
            "description": render_description(r, yaml_by_id.get(rid, {})),
        })

    return {
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": (
            "One-person-company 20-role agent team with a CEO orchestrator: "
            "decision governance, strategy & data, product & engineering, marketing, "
            "commerce operations, and reliability, each with deterministic gates."
        ),
        "author": {"name": "蛙蛙呱呱", "email": "noreply@localhost"},
        "agents": [f"./agents/{r['dir']}.md" for r in roles],
        "expertType": "team",
        "agentName": LEAD_ID,
        "teamInfo": {
            "leadAgent": LEAD_ID,
            "memberAgents": [r["dir"] for r in roles if r["dir"] != LEAD_ID],
        },
        "displayName": {"en": "Wawa Guagua Agents Team", "zh": "蛙蛙呱呱agents团"},
        "profession": {"en": "One-Person Company Team", "zh": "一人公司智能体团"},
        "displayDescription": {
            "en": ("20 specialists under one CEO orchestrator: intent decomposition, "
                   "decision gating, research & analysis, product & engineering, "
                   "growth & content, commerce & supply chain, and reliability — "
                   "every deliverable passes a deterministic gate."),
            "zh": ("CEO 主理人统管 20 个专家：意图拆解、决策闸门、研究分析、产品工程、"
                   "增长内容、交易供应链、自动化可靠性；每类交付物都过确定性门禁。"),
        },
        "avatar": "avatars/team.png",
        "categoryId": "01-Business",
        "defaultInitPrompt": {
            "zh": "帮我判断一件事该不该做，并给出能签字的决策卡",
            "en": "Help me decide whether to do something, with a signable decision card.",
        },
        "tags": [
            {"en": "Decision Gate", "zh": "决策闸门"},
            {"en": "Multi-Agent Orchestration", "zh": "多角色编排"},
            {"en": "Deterministic Gates", "zh": "确定性门禁"},
        ],
        "quickPrompts": [
            {"zh": "这个定价该不该调？给我一张能签字的决策卡",
             "en": "Should we change pricing? Give me a signable decision card."},
            {"zh": "帮我做一套电商主图与详情页方案",
             "en": "Produce an e-commerce main-image and detail-page plan."},
            {"zh": "分析这份订单数据，找出漏斗卡在哪",
             "en": "Analyze this order data and find where the funnel leaks."},
        ],
        "plugin": PLUGIN_NAME,
        "members": members,
    }


def build_manifest() -> str:
    return (
        f"name: {PLUGIN_NAME}\n"
        f'version: "{PLUGIN_VERSION}"\n'
        "type: expert\n"
    )


def build_agents_md(roles: list) -> str:
    """AGENTS.md 放在角色团根目录（不是 agent-packs/ 里）。

    原因：它引用的 ORG.md / PROTOCOL.md / docs/ 都在根目录。
    放进子目录会让所有相对路径差一级——这是实测踩到的坑。
    """
    L = [
        "# AGENTS.md · 蛙蛙呱呱agents团",
        "",
        "> 本文件面向所有支持 [AGENTS.md](https://agents.md) 标准的编码/办公智能体。",
        "> 它只做入口指引，**权威内容在别处**——不在此重复，避免双写漂移。",
        "",
        "## 这是什么",
        "",
        f"一个由 CEO 主理人编排的 {len(roles)} 人专家团，每个角色都有确定性门禁。",
        "",
        "## 从哪里读",
        "",
        "| 想知道 | 读 |",
        "|---|---|",
        "| 谁负责什么、向谁汇报、与谁交接 | `ORG.md` |",
        "| 任务怎样展开、下发、移交、编排 | `PROTOCOL.md` |",
        "| 汇报写什么、什么文笔、什么排版 | `REPORT-STANDARD.md` |",
        "| 每个角色的完整定义（宿主可直接加载） | `agent-packs/agents/*.md` |",
        "| 专家团清单 / 成员与头像 | `agent-packs/plugin.json` |",
        "| 技能层规格（怎么写出合格 SKILL.md） | `docs/SKILL-LAYER-SPEC.md` |",
        "| 技能层升级路线 | `docs/SKILL-MD-UPGRADE-PLAN.md` |",
        "",
        "## 怎么调用",
        "",
        "```bash",
        "python guagua.py roles                     # 看 20 个角色",
        "python guagua.py info r06                  # 看某个角色的契约",
        "python guagua.py call r06 --help           # 看它能做什么",
        "python guagua.py skills                    # 看已升级的技能包",
        "python guagua.py plan \"你的经营目标\"         # 让 R01 拆任务卡",
        "```",
        "",
        "## 三条铁律",
        "",
        "1. **一个任务一个 owner**——「共同负责」等于没人负责。",
        "2. **生成与校验分离**——谁生产谁不验收，验收归 `r04-watiaoci-reviewer`。",
        "3. **不可逆动作必须创始人签字**——裁员/关停/签合同/动资金不接受口头豁免。",
        "",
        "## 提交前自检（六条，全绿才算完）",
        "",
        "```bash",
        "python guagua.py check                     # 20 角色入口不回归",
        "python scripts/check_skill_gate.py         # 技能包门槛 + 黄金快照无退化",
        "python scripts/audit_skill_layer.py --check-refs   # SKILL.md 结构分 + 悬空指针",
        "python scripts/gen_agent_packs.py --check  # 专家团包与源无漂移",
        "python scripts/check_threshold_consistency.py      # 跨卡阈值一致（单一出处）",
        "python scripts/sync_dsh_skills.py --check  # DSH 技能镜像无分叉（否则模型读旧技能）",
        "```",
        "",
        "## 改这份文件之前",
        "",
        "不要手改。它由 `scripts/gen_agent_packs.py` 从 `core/registry.py`、`configs/*.yaml`、",
        "`*/prompt_profile.json`、`ORG.md` 渲染生成；改源，再跑：",
        "",
        "```bash",
        "python scripts/gen_agent_packs.py",
        "python scripts/gen_agent_packs.py --check   # 确认无漂移",
        "```",
        "",
    ]
    return "\n".join(L)


def build_readme(roles: list) -> str:
    lead = next(r for r in roles if r["dir"] == LEAD_ID)
    L = [
        "# 蛙蛙呱呱agents团 · 专家团包（agent-packs）",
        "",
        "> 由 `scripts/gen_agent_packs.py` 从 `core/registry.py`、`configs/*.yaml`、",
        "> `*/prompt_profile.json`、`ORG.md` 单向渲染生成。**不要手改。**",
        "",
        f"## 内容",
        "",
        f"- `plugin.json` — 专家团清单，`{len(roles)}` 个成员，主理人 `{lead['name']}`（`{LEAD_ID}`）",
        f"- `manifest.yaml` — 极简声明（`type: expert`）",
        f"- `agents/*.md` — {len(roles)} 份角色定义（frontmatter + 正文）",
        f"- `avatars/*.png` — 头像副本（宿主要求路径在包内）",
        "- 角色团根目录的 `AGENTS.md` — 跨宿主通用入口（不在本目录内，因它引用根目录的 `ORG.md`/`docs/`）",
        "",
        "## 三种宿主的加载方式",
        "",
        "| 宿主 | 怎么用 |",
        "|---|---|",
        "| **WorkBuddy / CodeBuddy** | 整个 `agent-packs/` 作为 plugin 目录导入；"
        "入口 `plugin.json`，团员在 `agents/` |",
        "| **Claude Code** | 把 `agents/*.md` 复制或软链到 `.claude/agents/`，文件名即子代理名 |",
        "| **通用（AGENTS.md 标准）** | 宿主按 nearest-file 规则读取 `AGENTS.md`，由它指向权威文档 |",
        "",
        "## 重新生成",
        "",
        "```bash",
        "python scripts/gen_agent_packs.py            # 生成 / 覆盖",
        "python scripts/gen_agent_packs.py --check    # 只校验是否与源漂移（CI 用）",
        "```",
        "",
        "## 成员一览",
        "",
        "| ID | 代号 | 职位 | 明确不做 |",
        "|---|---|---|---|",
    ]
    for r in roles:
        L.append(f"| `{r['dir']}` | {r['name']} | {r['title']} | {BOUNDARIES.get(r['id'], '—')} |")
    L.append("")
    L.append("> 边界与升级路径的权威说明见 `ORG.md` §三 编制表。")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# 写盘 / 校验
# --------------------------------------------------------------------------- #

def build_all(out_dir: str, with_avatars: bool = True) -> dict:
    roles = load_registry()
    yaml_by_id = {r["id"]: load_yaml_config(r["id"]) for r in roles}
    missing = [r["id"] for r in roles if r["id"] not in AVATARS]
    if missing:
        raise SystemExit(f"[gen] 缺少头像映射: {missing}")
    for r in roles:
        if r["id"] not in EN_PROFESSION:
            raise SystemExit(f"[gen] 缺少英文职位: {r['id']}")

    files = {}       # relpath（相对 out_dir）-> bytes
    root_files = {}  # relpath（相对 ROOT）-> bytes

    plugin = build_plugin_json(roles, yaml_by_id)
    files["plugin.json"] = (json.dumps(plugin, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    files["manifest.yaml"] = build_manifest().encode("utf-8")
    files["README.md"] = build_readme(roles).encode("utf-8")
    # AGENTS.md 必须放在角色团根目录：它引用的 ORG.md / docs/ 都在那里
    root_files["AGENTS.md"] = build_agents_md(roles).encode("utf-8")

    for r in roles:
        txt = render_agent(r, yaml_by_id.get(r["id"], {}),
                           load_profile(r["dir"]), roles)
        files[f"agents/{r['dir']}.md"] = txt.encode("utf-8")

    return {"files": files, "root_files": root_files, "roles": roles,
            "with_avatars": with_avatars}


def write_files(out_dir: str, payload: dict, with_avatars: bool) -> int:
    files = payload["files"]
    for rel, data in sorted(files.items()):
        path = os.path.join(out_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
    for rel, data in sorted(payload.get("root_files", {}).items()):
        with open(os.path.join(ROOT, rel.replace("/", os.sep)), "wb") as fh:
            fh.write(data)
    n_avatar = 0
    if with_avatars:
        av_dir = os.path.join(out_dir, "avatars")
        os.makedirs(av_dir, exist_ok=True)
        for fname in sorted(set(AVATARS.values()) | {"team.png"}):
            src = os.path.join(ROOT, "avatars", fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(av_dir, fname))
                n_avatar += 1
    return n_avatar


def check_drift(out_dir: str, payload: dict) -> list:
    """返回漂移列表 [(relpath, 原因)]。"""
    drift = []
    pairs = [(rel, data, os.path.join(out_dir, rel.replace("/", os.sep)))
             for rel, data in payload["files"].items()]
    pairs += [(rel, data, os.path.join(ROOT, rel.replace("/", os.sep)))
              for rel, data in payload.get("root_files", {}).items()]
    for rel, data, path in sorted(pairs):
        if not os.path.isfile(path):
            drift.append((rel, "缺失"))
            continue
        with open(path, "rb") as fh:
            disk = fh.read()
        if disk != data:
            drift.append((rel, "内容与源不一致"))
    return drift


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="生成 20 人专家团包（plugin.json + agents/*.md）")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出目录（默认 agent-packs/）")
    ap.add_argument("--check", action="store_true", help="只校验是否与源漂移，不写盘（CI 用）")
    ap.add_argument("--no-avatars", action="store_true", help="不复制头像")
    ap.add_argument("--json", action="store_true", help="输出机器可读结果")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    payload = build_all(args.out, with_avatars=not args.no_avatars)
    roles = payload["roles"]

    if args.check:
        drift = check_drift(args.out, payload)
        if args.json:
            print(json.dumps({"ok": not drift,
                              "drift": [{"file": f, "reason": r} for f, r in drift],
                              "count": len(payload["files"])}, ensure_ascii=False, indent=2))
        else:
            print("蛙蛙呱呱 · 专家团包漂移检查")
            print("=" * 64)
            print(f"应有文件 {len(payload['files'])} 份｜输出目录 {os.path.relpath(args.out, ROOT)}")
            if drift:
                print(f"\n漂移 {len(drift)} 处：")
                for f, reason in drift[:20]:
                    print(f"  [{reason}] {f}")
                if len(drift) > 20:
                    print(f"  ... 另有 {len(drift) - 20} 处")
                print("\n执行 `python scripts/gen_agent_packs.py` 重新生成。")
            else:
                print("\n无漂移：磁盘内容与 4 处事实来源一致。")
        return 1 if drift else 0

    n_avatar = write_files(args.out, payload, with_avatars=not args.no_avatars)
    lead = next(r for r in roles if r["dir"] == LEAD_ID)
    if args.json:
        print(json.dumps({"ok": True, "out": os.path.relpath(args.out, ROOT),
                          "files": len(payload["files"]), "avatars": n_avatar,
                          "members": len(roles), "lead": lead["dir"]},
                         ensure_ascii=False, indent=2))
    else:
        print("蛙蛙呱呱 · 专家团包生成")
        print("=" * 64)
        print(f"输出目录 : {os.path.relpath(args.out, ROOT)}")
        print(f"角色定义 : {len(roles)} 份（agents/*.md）")
        print(f"清单文件 : plugin.json / manifest.yaml / AGENTS.md / README.md")
        print(f"头像副本 : {n_avatar} 张")
        print(f"主理人   : {lead['name']}（{LEAD_ID}）")
        print("\n下一步：")
        print("  python scripts/gen_agent_packs.py --check     # 确认无漂移")
        print("  python guagua.py check                        # 确认原工程未受影响")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
