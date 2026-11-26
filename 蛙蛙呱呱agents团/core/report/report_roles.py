# -*- coding: utf-8 -*-
"""core/report_roles —— 角色适配层：20 个角色、195 个技能，哪些能进报告、输出什么 claim。

上一版只标了 4 个角色（r06/r19/r05/r04），报告里能用的证据面很窄。
这一层把「角色 → 技能 → 动作」逐条分类，并给出三件事：

1. **能不能进报告**：`eligible`。会被写操作/红线条目挡掉（支付、部署、签约、
   删除、凭据），这些即使有数字也不许进报告；
2. **输出什么 claim**：按技能族给 claim 模板（统计量/成本/转化/合规/定性）；
3. **哪个纲领用它**：`theses`，让方法注册表能按报告类型挑角色证据。

分类是「规则 + 人工覆盖」：
- 规则看技能名与描述的关键词（见 `CATEGORY_RULES`）；
- `OVERRIDES` 对报告关键技能做人工修正（例如 r15.tco 只能进链路/商品，不进调研）。

产出 `configs/report_capabilities.json`，供 `guagua.py report capabilities` 查看，
也供文档生成覆盖率表。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core import skill_graph

TEAM = Path(__file__).resolve().parents[2]
# 运行期产物写到 workspace（agents 目录在沙箱/只读安装位下不可写）
CATALOG = Path(os.environ.get(
    "DSH_REPORT_CATALOG",
    str(TEAM.parent / "workspace" / "_configs" / "report_capabilities.json")))

# --------------------------------------------------------------------------- #
# 20 个角色的报告定位（人工）
# --------------------------------------------------------------------------- #
ROLE_REPORT: Dict[str, Dict[str, Any]] = {
    "r01": {"name": "蛙全局", "title": "CEO / 编排", "enters": True,
            "contributes": "报告出具、结论收口、决策卡", "theses": ["*"]},
    "r02": {"name": "蛙排布", "title": "COO", "enters": True,
            "contributes": "SOP 与关键控制点、排期与验收", "theses": ["operations", "people"]},
    "r03": {"name": "蛙守线", "title": "CFO / 合规", "enters": True,
            "contributes": "三表勾稽、税务边界、合同红线", "theses": ["operations", "store"]},
    "r04": {"name": "蛙挑刺", "title": "独立评审", "enters": True,
            "contributes": "物料清点、三级证据链（PASS/FAIL）", "theses": ["*"]},
    "r05": {"name": "蛙深远", "title": "研究", "enters": True,
            "contributes": "证据台账、规模测算、情景", "theses": ["research", "marketing"]},
    "r06": {"name": "蛙得清", "title": "数据分析", "enters": True,
            "contributes": "描述/趋势/相关/回归/显著性/质量", "theses": ["*"]},
    "r07": {"name": "蛙得明", "title": "产品", "enters": True,
            "contributes": "需求优先级、验收标准", "theses": ["product"]},
    "r08": {"name": "蛙建成", "title": "MVP", "enters": False,
            "contributes": "原型与切片（无稳定数字）", "theses": []},
    "r09": {"name": "蛙稳码", "title": "工程", "enters": False,
            "contributes": "实现与测试（不作报告证据）", "theses": []},
    "r10": {"name": "蛙成美", "title": "设计", "enters": False,
            "contributes": "视觉与物料（定性）", "theses": []},
    "r11": {"name": "蛙点题", "title": "内容", "enters": True,
            "contributes": "标题/长文/笔记（定性 claim）", "theses": ["marketing"]},
    "r12": {"name": "蛙引流", "title": "增长", "enters": True,
            "contributes": "漏斗、ROI、激活、渠道", "theses": ["growth", "marketing"]},
    "r13": {"name": "蛙客成", "title": "客成", "enters": True,
            "contributes": "健康分、续约、VOC", "theses": ["support"]},
    "r14": {"name": "蛙交易", "title": "交易", "enters": True,
            "contributes": "订单三态、退款、选品", "theses": ["sku", "store"]},
    "r15": {"name": "蛙供应", "title": "供应链", "enters": True,
            "contributes": "TCO、报价、库存、履约", "theses": ["operations", "chain", "sku", "store"]},
    "r16": {"name": "蛙人事", "title": "人事", "enters": True,
            "contributes": "招聘漏斗、人效、薪酬带宽", "theses": ["people"]},
    "r17": {"name": "蛙织网", "title": "自动化", "enters": False,
            "contributes": "集成与重试（不作报告证据）", "theses": []},
    "r18": {"name": "蛙数仓", "title": "数据工程", "enters": True,
            "contributes": "质量六维、血缘、口径", "theses": ["*"]},
    "r19": {"name": "蛙智模", "title": "模型工程", "enters": True,
            "contributes": "评估、置信区间、回归门禁", "theses": ["*"]},
    "r20": {"name": "蛙值守", "title": "SRE", "enters": True,
            "contributes": "SLO、故障、备份演练", "theses": ["sre"]},
}

# --------------------------------------------------------------------------- #
# 技能族分类：关键词 → (category, claim, eligible, theses)
# --------------------------------------------------------------------------- #
CATEGORY_RULES: List[Tuple[str, Tuple[str, ...], Dict[str, Any]]] = [
    ("mutate", ("deploy", "execute", "pay", "refund", "delete", "approve", "sign",
                "send", "publish", "rotate", "revoke", "release", "cancel",
                "执行", "支付", "退款", "删除", "审批", "签署", "发布", "上线"),
     {"claim": "不允许：写操作/不可逆", "eligible": False}),
    ("security", ("credential", "secret", "password", "kyc", "aml", "audit",
                  "凭据", "密钥", "密码", "合规"),
     {"claim": "不允许：红线/凭据类", "eligible": False}),
    ("meta", ("manifest", "demo", "test", "harness", "contract", "case",
              "clarify", "evolve", "run", "自检", "演示", "用例", "契约"),
     {"claim": "仅门禁/自检，不进正文", "eligible": False}),
    ("decision", ("decide", "decision", "boardroom", "intent", "decompose",
                  "redteam", "red team", "决策", "拆解"),
     {"claim": "任务卡/决策卡/反方质询", "eligible": True, "theses": ["*"]}),
    ("eval", ("evaluation", "eval", "monitor", "drift", "trace", "modelcard",
              "registry", "tracking", "benchmark", "评测", "监控"),
     {"claim": "评估结果/置信区间/回归门禁", "eligible": True, "theses": ["*"]}),
    ("research", ("research", "sizing", "scenario", "industry", "competitor",
                  "tam", "ledger", "evidence", "台账", "规模", "情景"),
     {"claim": "证据台账/规模测算/情景", "eligible": True,
      "theses": ["research", "marketing"]}),
    ("ops", ("process", "schedule", "handoff", "capacity", "sop",
             "排期", "交接", "流程"),
     {"claim": "SOP/排期/验收口径", "eligible": True,
      "theses": ["operations", "people"]}),
    ("dataops", ("elt", "transform", "pipeline", "incremental", "catalog",
                 "lineage", "血缘", "管道"),
     {"claim": "管道/血缘/口径门禁", "eligible": True, "theses": ["*"]}),
    ("stat", ("describe", "explore", "correlate", "regression", "anova", "ttest",
              "chi2", "abtest", "power", "elasticity", "causal", "did", "matched",
              "rdd", "time_series", "segment", "rfm", "funnel", "cohort",
              "quality", "semantics", "profile", "stats",
              "趋势", "相关", "回归", "显著", "分群"),
     {"claim": "统计量（n/均值/斜率/p 值/效应量）", "eligible": True,
      "theses": ["*"]}),
    ("cost", ("tco", "quote", "rfq", "supplier", "safety-stock", "fulfill",
              "inventory", "procurement", "cost",
              "成本", "报价", "库存", "履约"),
     {"claim": "单位成本/排序/覆盖率", "eligible": True,
      "theses": ["operations", "chain", "sku", "store"]}),
    ("commerce", ("order", "payment", "selection", "pricing", "cart",
                  "订单", "支付", "选品", "定价"),
     {"claim": "订单/退款/选品指标", "eligible": True,
      "theses": ["sku", "store", "growth"]}),
    ("growth", ("roi", "activation", "diagnose", "pipeline", "churn", "health",
                "qbr", "voc", "campaign", "attribution",
                "投放", "漏斗", "留存", "续约", "渠道"),
     {"claim": "转化/ROI/留存/健康分", "eligible": True,
      "theses": ["growth", "marketing", "support"]}),
    ("support", ("ticket", "sla", "complaint", "nps", "csat", "客服", "工单", "满意度"),
     {"claim": "履约/满意度/工单", "eligible": True, "theses": ["support"]}),
    ("content", ("brief", "longform", "xhs", "copy", "ad", "content", "title",
                 "文案", "标题", "笔记"),
     {"claim": "定性（标题/结构/合规），不带数字", "eligible": True,
      "theses": ["marketing"]}),
    ("product", ("prd", "rice", "northstar", "roadmap", "story",
                 "需求", "优先级", "路线图"),
     {"claim": "优先级/验收标准", "eligible": True, "theses": ["product"]}),
    ("people", ("hiring", "attendance", "perf", "payroll", "capacity",
                "招聘", "人效", "薪酬", "编制"),
     {"claim": "招聘/人效/编制", "eligible": True, "theses": ["people"]}),
    ("sre", ("slo", "backup", "drill", "incident", "alert", "restore",
             "可用性", "备份", "故障", "演练"),
     {"claim": "SLO/MTTR/RTO", "eligible": True, "theses": ["sre"]}),
    ("finance", ("healthcheck", "statement", "cash", "budget", "cfo", "tax",
                 "三表", "现金", "预算", "税"),
     {"claim": "勾稽/现金/预算偏差", "eligible": True,
      "theses": ["operations", "store"]}),
    ("design", ("vi", "ui", "imgops", "design", "brand", "layout",
                "视觉", "品牌", "版式"),
     {"claim": "定性（合规/一致性）", "eligible": False}),
]

# 报告关键技能的人工修正（规则分错或需要更精确的语境）
OVERRIDES: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("r06", "rootcause"): {"claim": "贡献分解/帕累托", "theses": ["*"]},
    ("r06", "metrics"): {"claim": "指标树与口径", "theses": ["*"]},
    ("r06", "domain"): {"claim": "领域方法注册与后端门禁", "theses": ["research"]},
    ("r07", "metrics"): {"claim": "北极星与指标口径", "theses": ["product", "growth"]},
    ("r12", "ltv-cac"): {"claim": "LTV/CAC 与回本周期", "theses": ["growth", "marketing"]},
    ("r12", "selfmedia"): {"claim": "自媒体数据看板", "theses": ["marketing"]},
    ("r13", "crm"): {"claim": "客户分层与触达", "theses": ["support"]},
    ("r02", "knowledge"): {"claim": "知识库与 SOP 沉淀", "theses": ["operations", "people"]},
    ("r02", "portfolio"): {"claim": "项目组合与容量", "theses": ["operations", "people"]},
    ("r05", "business"): {"claim": "商业模式与单元经济", "theses": ["research", "store"]},
    ("r15", "tco"): {"claim": "到店单位成本与排序", "theses": ["chain", "operations", "sku"]},
    ("r05", "sizing"): {"claim": "TAM/SAM/SOM 与双口径方差", "theses": ["research"]},
    ("r05", "research"): {"claim": "证据台账（claim→source）", "theses": ["*"]},
    ("r06", "rootcause"): {"claim": "贡献分解/帕累托", "theses": ["*"]},
    ("r12", "diagnose"): {"claim": "漏斗与渠道归因", "theses": ["growth", "marketing"]},
    ("r13", "health"): {"claim": "健康分与续约风险", "theses": ["support"]},
    ("r20", "slo"): {"claim": "可用性与错误预算", "theses": ["sre"]},
    ("r03", "cfo"): {"claim": "三表勾稽/现金勾稽", "theses": ["operations", "store"]},
    ("r16", "hiring"): {"claim": "招聘漏斗与到岗率", "theses": ["people"]},
    ("r04", "artifact"): {"claim": "物料清点（PASS/FAIL）", "theses": ["*"], "gate": True},
    ("r18", "quality"): {"claim": "质量六维得分", "theses": ["*"], "gate": True},
    ("r19", "eval-ci"): {"claim": "Wilson 置信区间", "theses": ["*"]},
}


# 角色名/职称唯一出处是 core/base/registry.py（2026-11-17 归一，防旧花名漂移）
def _sync_identity() -> None:
    try:
        from core.base.registry import ROLES
    except Exception:  # noqa: BLE001
        return
    for role in ROLES:
        if role["id"] in ROLE_REPORT:
            ROLE_REPORT[role["id"]]["name"] = role["name"]


_sync_identity()


def _classify_skill(role: str, skill: Dict[str, Any]) -> Dict[str, Any]:
    text = f"{skill.get('skill', '')} {skill.get('desc', '')}".lower()
    cat, rule = "general", {"claim": "未命中规则，暂不进报告", "eligible": False}
    for name, keys, r in CATEGORY_RULES:
        if any(k.lower() in text for k in keys):
            cat, rule = name, r
            break
    out = {
        "role": role, "skill": skill.get("skill", ""),
        "actions": skill.get("actions") or [],
        "category": cat, "claim": rule["claim"],
        "eligible": bool(rule.get("eligible", False)),
        "theses": list(rule.get("theses") or []),
        "reason": "规则命中 " + cat,
    }
    ov = OVERRIDES.get((role, skill.get("skill", "")))
    if ov:
        out.update({k: v for k, v in ov.items() if k != "gate"})
        out["gate"] = bool(ov.get("gate"))
        out["reason"] = "人工覆盖"
    return out


def classify() -> Dict[str, Any]:
    rows = skill_graph.load()
    items = [_classify_skill(r["role"], r) for r in rows]
    by_role: Dict[str, Dict[str, int]] = {}
    for it in items:
        s = by_role.setdefault(it["role"], {"skills": 0, "eligible": 0,
                                            "actions": 0, "eligible_actions": 0})
        s["skills"] += 1
        s["actions"] += max(1, len(it["actions"]))
        if it["eligible"]:
            s["eligible"] += 1
            s["eligible_actions"] += max(1, len(it["actions"]))
    for role, meta in ROLE_REPORT.items():
        s = by_role.setdefault(role, {"skills": 0, "eligible": 0,
                                      "actions": 0, "eligible_actions": 0})
        s.update({"name": meta["name"], "title": meta["title"],
                  "enters": meta["enters"], "contributes": meta["contributes"],
                  "theses": meta["theses"]})
    return {
        "schema": "dsh.report_capabilities/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "counts": {
            "roles": len(ROLE_REPORT),
            "skills": len(items),
            "actions": sum(max(1, len(i["actions"])) for i in items),
            "eligible_skills": sum(1 for i in items if i["eligible"]),
            "eligible_actions": sum(max(1, len(i["actions"]))
                                    for i in items if i["eligible"]),
        },
        "roles": by_role,
        "items": items,
    }


def write_catalog(cat: Optional[Dict[str, Any]] = None) -> Path:
    cat = cat or classify()
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cat, f, ensure_ascii=False, indent=1)
    return CATALOG


def load_catalog() -> Dict[str, Any]:
    if CATALOG.exists():
        try:
            return json.loads(CATALOG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return classify()


def coverage_table(cat: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cat = cat or load_catalog()
    rows = []
    for role in sorted(cat["roles"]):
        s = cat["roles"][role]
        rows.append({"role": role, "name": s.get("name", ""),
                     "title": s.get("title", ""),
                     "skills": s["skills"], "eligible": s["eligible"],
                     "actions": s["actions"],
                     "eligible_actions": s["eligible_actions"],
                     "rate": round(s["eligible"] / max(1, s["skills"]) * 100, 0),
                     "enters": s.get("enters", False)})
    return rows


def role_evidence(cat: Dict[str, Any], thesis: str,
                  limit: int = 12) -> List[Dict[str, Any]]:
    """某类纲领可用的角色证据（技能级）。"""
    out = []
    for it in cat["items"]:
        if not it["eligible"]:
            continue
        if thesis in (it.get("theses") or []) or "*" in (it.get("theses") or []):
            out.append(it)
    return out[:limit]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="report_roles")
    ap.add_argument("--write", action="store_true", help="写 configs/report_capabilities.json")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--thesis", default=None)
    a = ap.parse_args(argv)
    cat = classify()
    if a.write:
        p = write_catalog(cat)
        print(f"wrote {p}")
    if a.json:
        print(json.dumps(cat, ensure_ascii=False, indent=1)[:6000])
        return 0
    c = cat["counts"]
    print(f"角色 {c['roles']} / 技能 {c['skills']} / 动作 {c['actions']}；"
          f"可进报告技能 {c['eligible_skills']} / 动作 {c['eligible_actions']}")
    for r in coverage_table(cat):
        print(f"  {r['role']} {r['name']:<4} 技能 {r['eligible']:>2}/{r['skills']:<2}"
              f" 动作 {r['eligible_actions']:>2}/{r['actions']:<2} "
              f"{'进' if r['enters'] else '不进'}报告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
