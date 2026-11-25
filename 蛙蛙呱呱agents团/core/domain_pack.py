# -*- coding: utf-8 -*-
"""core/domain_pack —— 业务线 → 领域编队 + 专家作战计划。

解决的问题（针对「换个业务线就不会分析」）：
旧产线只能吃「已有数据的项目」，换一条业务线就没有可挂的方法。
本模块先不碰数据，只做三件事：

1. 把业务线意图匹配到一个**行业假设**（指标树、关键问题、情景轴、数据清单）；
2. 从 20 个角色领域包里选出一个**任务编队**（谁负责哪一段、用什么方法）；
3. 输出一份**领域作战计划**：先验证什么、用什么识别策略、三种情景、
   90 天计划、这个域最容易错的四件事、数据到位后跑哪条产线。

它不编项目数字：行业基准只给区间并标注「需按项目校准」；
真正的数字等数据到位后由 `report produce` 的方法库算。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import skill_bridge

ROOT = Path(__file__).resolve().parent.parent
ROLES = ROOT / "knowledge" / "roles"

# --------------------------------------------------------------------------- #
# 行业假设：业务线 → 指标树 / 关键问题 / 情景轴 / 数据清单
#
# 2026-11-25（P1-7）：这张表本质是**数据**（行业 → 假设），不是通用逻辑。
# 已搬到 `configs/industries/*.yaml`，core 只保留「读配置 + 匹配」。
# 项目可覆盖：`<PROJECT>/configs/industries/` 会先于团内目录加载。
# --------------------------------------------------------------------------- #
INDUSTRIES_DIR = ROOT / "configs" / "industries"

_NEUTRAL = {
    "id": "generic", "name": "通用业务",
    "role_boost": {"r01": 1, "r06": 1},
    "keywords": [], "hypothesis": "先把目标拆成可验证的因果链，再找数据",
    "critical": "关键假设能否被数据证伪",
    "kpis": [], "questions": [], "scenarios": [("需求", "供给")],
    "benchmarks": {}, "data": [],
}


def _yaml(p: Path) -> Dict[str, Any]:
    try:
        import yaml
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def load_industries(extra_dirs: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """读行业包；项目目录优先（同名覆盖团内默认）。"""
    out: Dict[str, Dict[str, Any]] = {}
    for d in [INDUSTRIES_DIR] + [Path(x) for x in (extra_dirs or [])]:
        if not Path(d).is_dir():
            continue
        for p in sorted(Path(d).glob("*.yaml")):
            doc = _yaml(p)
            if not doc:
                continue
            key = str(doc.get("id") or p.stem)
            out[key] = doc
    return out or {"generic": dict(_NEUTRAL)}


INDUSTRIES: Dict[str, Dict[str, Any]] = load_industries()


def load_roles() -> Dict[str, Dict[str, Any]]:
    out = {}
    for p in sorted(ROLES.glob("r*.json")):
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        out[d["role"]] = d
    return out


def match_industry(intent: str) -> Dict[str, Any]:
    best, score = None, 0
    for key, ind in INDUSTRIES.items():
        s = sum(1 for w in ind["keywords"] if w in intent)
        if s > score:
            best, score = ind, s
    if best is None:
        best = dict(next(iter(INDUSTRIES.values())))
        best["_fallback"] = True
    return best


def score_roles(intent: str, roles: Dict[str, Dict[str, Any]],
                industry: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    boost = (industry or {}).get("role_boost") or {}
    scored = []
    for rid, r in roles.items():
        s = sum(1 for w in r.get("keywords", []) if w in intent) + boost.get(rid, 0)
        # 战略与分析是任何业务线的底座
        if rid in ("r01", "r06"):
            s += 1
        scored.append({"role": rid, "name": r["name"], "title": r["title"],
                       "domain": r["domain"], "score": s,
                       "hits": [w for w in r.get("keywords", []) if w in intent],
                       "industry_fit": rid in boost})
    scored.sort(key=lambda x: (-x["score"], x["role"]))
    picked = [x for x in scored if x["score"] > 0][:5]
    for must in ("r01", "r06"):
        if not any(x["role"] == must for x in picked):
            picked.append(next(x for x in scored if x["role"] == must))
    return picked[:5]


def _coverage_for(role_ids: List[str]) -> Dict[str, Any]:
    counts = {"exact": 0, "partial": 0, "new": 0}
    rows = []
    for rid in role_ids:
        for name, m in (skill_bridge.methods(rid) or {}).items():
            fit = m.get("fit", "new")
            counts[fit] = counts.get(fit, 0) + 1
            rows.append({"role": rid, "method": name, "fit": fit,
                         "skill": f"{m.get('skill_role', '')}.{m.get('skill', '')}".strip("."),
                         "action": m.get("action", ""),
                         "command": m.get("command", ""),
                         "note": m.get("note", "")})
    total = sum(counts.values())
    return {"total": total, **counts,
            "coverage_rate": round((counts["exact"] + counts["partial"]) / max(1, total), 4),
            "rows": rows}


def plan(intent: str) -> Dict[str, Any]:
    roles = load_roles()
    ind = match_industry(intent)
    picked = score_roles(intent, roles, ind)
    return {
        "schema": "dsh.domain_plan/v1",
        "intent": intent,
        "industry": {k: ind.get(k) for k in
                     ("name", "hypothesis", "critical", "kpis", "questions",
                      "scenarios", "benchmarks", "data")},
        "roles": [{**p, "books": roles[p["role"]]["books"],
                   "methods": [{**m, "skill": skill_bridge.info(p["role"], m["name"])}
                               for m in roles[p["role"]]["methods"]],
                   "failure_modes": roles[p["role"]]["failure_modes"],
                   "sections": roles[p["role"]]["report_sections"]}
                  for p in picked],
        "skill_coverage": _coverage_for([p["role"] for p in picked]),
        "analysis_design": [
            {"question": "变化从哪来（价/量/结构）", "method": "decompose_mix_rate",
             "needs": "两期权重与率", "level": "L1"},
            {"question": "改版/促销有没有用", "method": "ab_proportion / ab_mean",
             "needs": "随机分流 + 样本量", "level": "L3"},
            {"question": "政策/上线前后效果", "method": "did_twfe + event_study + placebo",
             "needs": "处理组/对照组 + ≥4 期", "level": "L3"},
            {"question": "定价与促销弹性", "method": "elasticity",
             "needs": "≥6 期价格与销量", "level": "L2"},
            {"question": "留存与复购", "method": "cohort_retention",
             "needs": "队列×期", "level": "L1"},
        ],
        "sprints": [
            {"window": "第 1—2 周", "goal": "补数据 + 定口径",
             "deliverable": "数据清单逐项到位；指标定义冻结"},
            {"window": "第 3—4 周", "goal": "描述与归因",
             "deliverable": "量价/结构归因 + 漏斗/队列"},
            {"window": "第 5—8 周", "goal": "因果与实验",
             "deliverable": "A/B 或 DiD + 稳健性"},
            {"window": "第 9—12 周", "goal": "策略与停止条件",
             "deliverable": "三情景 + 90 天动作 + 杀死标准"},
        ],
    }


def to_markdown(p: Dict[str, Any]) -> str:
    ind = p["industry"]
    lines: List[str] = []
    lines.append(f"# {p['intent']} · 领域作战计划（专家版）\n")
    lines.append("> 由 20 角色领域包 + 行业假设组装；不含未经核实的项目数字。")
    lines.append("> 行业基准只给区间，必须按项目校准；数据到位后再出数据报告。\n")

    lines.append("## 0. 一句话判断\n")
    lines.append(f"这条业务线的胜负手不在「做不做」，而在 **{ind['critical']}**。")
    lines.append(f"先验证：{ind['hypothesis']}。\n")

    lines.append("## 1. 任务编队（为什么是这几个角色）\n")
    lines.append("| 角色 | 能力域 | 在这条业务线负责什么 | 匹配到的词 |")
    lines.append("|---|---|---|---|")
    for r in p["roles"]:
        tag = "、".join(r["hits"]) or ("行业适配" if r.get("industry_fit") else "底座")
        lines.append(f"| {r['role']} {r['name']} | {r['domain']} | {r['title']} | {tag} |")
    lines.append("")

    lines.append("## 2. 行业假设与指标树（先定看什么）\n")
    lines.append("**关键问题**：")
    for q in ind["questions"]:
        lines.append(f"- {q}")
    lines.append("\n**指标**：" + "、".join(ind["kpis"]))
    lines.append("\n**基准（需校准）**：")
    for k, v in (ind["benchmarks"] or {}).items():
        lines.append(f"- {k}：{v}")
    lines.append("")

    lines.append("## 3. 每个角色的专家方法（怎么分析）\n")
    for r in p["roles"]:
        lines.append(f"### {r['role']} {r['name']} · {r['domain']}\n")
        for m in r["methods"]:
            lines.append(f"- **{m['name']}**：{m['formula']}（用于：{m['when']}）")
            sk = m.get("skill") or {}
            if sk.get("fit") in ("exact", "partial"):
                lines.append(f"  - 技能：`{sk['command']}`（{sk['fit']}；{sk['note']}）")
            else:
                lines.append(f"  - 新增：{sk.get('note', '现有技能无对应动作')}")
        lines.append("")

    cov = p.get("skill_coverage") or {}
    if cov:
        lines.append("## 3.5 技能接入（不是另起一套）\n")
        lines.append(f"本计划 {cov['total']} 条方法：已有技能直接做 **{cov['exact']}** 条、"
                     f"同域需扩字段 **{cov['partial']}** 条、需新增 **{cov['new']}** 条；"
                     f"接入率 {cov['coverage_rate']:.0%}。\n")
        lines.append("| 角色 | 方法 | 技能/动作 | 状态 |")
        lines.append("|---|---|---|---|")
        for row in cov["rows"]:
            where = f"`{row['skill']}{(' ' + row['action']) if row['action'] else ''}`"
            lines.append(f"| {row['role']} | {row['method']} | {where} | {row['fit']} |")
        lines.append("")
    lines.append("## 4. 分析设计（先定识别，再算数）\n")
    lines.append("| 问题 | 方法 | 需要的数据 | 最高证据等级 |")
    lines.append("|---|---|---|---|")
    for d in p["analysis_design"]:
        lines.append(f"| {d['question']} | {d['method']} | {d['needs']} | {d['level']} |")
    lines.append("\n> 没有对照组/没有前趋势，就只能到 L2，禁止写「导致/替代/驱动」。")
    lines.append("")

    lines.append("## 5. 三种情景与领先指标（远见从哪来）\n")
    ax1, ax2 = ind["scenarios"][0]
    lines.append(f"两个不确定性轴：**{ax1}** × **{ax2}**。\n")
    lines.append("| 情景 | 触发信号 | 动作 |")
    lines.append("|---|---|---|")
    lines.append(f"| 基准：{ax1}平稳、{ax2}不变 | 连续 2 期核心指标在 ±5% 内 | 按现模型扩量 |")
    lines.append(f"| 上行：{ax1}改善、{ax2}加速 | 领先指标连续 2 期超基线 10% | 加投，抢窗口 |")
    lines.append(f"| 下行：{ax1}恶化、{ax2}迁移 | 客单或复购连续 2 期下滑 | 收缩，保现金 |")
    lines.append("\n**领先指标**（比结果早 1—2 期）：")
    for r in p["roles"][:3]:
        for f in r.get("foresight", [])[:2]:
            lines.append(f"- {r['domain']}：{f}")
    lines.append("")

    lines.append("## 6. 90 天验证计划\n")
    lines.append("| 窗口 | 目标 | 交付 |")
    lines.append("|---|---|---|")
    for s in p["sprints"]:
        lines.append(f"| {s['window']} | {s['goal']} | {s['deliverable']} |")
    lines.append("\n**停止条件**：连续 2 个验证窗口核心指标未达基线，停止扩量；"
                 "因果结论在稳健性检验中不显著，撤回该结论，不换措辞硬写。")
    lines.append("")

    lines.append("## 7. 这个域最容易错的四件事\n")
    for r in p["roles"]:
        for f in r.get("failure_modes", [])[:1]:
            lines.append(f"- {r['domain']}：{f}")
    lines.append("")

    lines.append("## 8. 数据清单（拿到就能跑）\n")
    lines.append("| 表 | 字段 | 用途 |")
    lines.append("|---|---|---|")
    for t, f, u in ind["data"]:
        lines.append(f"| {t} | {f} | {u} |")
    lines.append("")

    lines.append("## 9. 数据到位后跑哪条产线\n")
    lines.append("```powershell")
    lines.append("cd \"D:\\蛙蛙呱呱\\蛙蛙呱呱agents团\"")
    lines.append(f"python guagua.py report produce --intent \"{p['intent']}\" "
                 f"--dir <项目目录> --out <输出目录>")
    lines.append("```")
    lines.append("\n方法引擎：`python -m core.analysis_lab --help`"
                 "（归因 / A/B / DiD / 弹性 / 队列）。")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="domain_pack")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    p = plan(a.intent)
    if a.json:
        text = json.dumps(p, ensure_ascii=False, indent=2)
    else:
        text = to_markdown(p)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
        if not a.json:
            jp = Path(a.out).with_suffix(".json")
            jp.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
            print(f"wrote {jp}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
