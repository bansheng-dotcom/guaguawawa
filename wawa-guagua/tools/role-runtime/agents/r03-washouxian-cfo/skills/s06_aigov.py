# -*- coding: utf-8 -*-
"""S06 AI 治理与披露（能力域 6）。

来源：alirezarezvani__claude-skills compliance-os
（framework_selector.py 确定性决策树：GDPR/ISO 27001/SOC 2/ISO 42001/
EU AI Act/HIPAA/FDA QSR/NIS2/NIST CSF 的触发条件、binding 排序、依赖边；
audit_simulator 控制点→主题映射）+ EU AI Act 四级风险分类口径。

决策树与触发条件为确定性规则，全部平移为可测逻辑。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "aigov"
DESC = "AI 治理与披露：frameworks/aiclassify/disclose"

# 适用框架决策树（移植 framework_selector.select_frameworks）
_FRAMEWORK_RULES = [
    {"id": "GDPR", "binding": "legal", "deps": [],
     "trigger": lambda p: p.get("processes_personal_data")
     and p.get("eu_data_subjects"),
     "why": "处理欧盟数据主体的个人数据"},
    {"id": "ISO 27001", "binding": "contract", "deps": [],
     "trigger": lambda p: p.get("enterprise_clients")
     or p.get("security_certification_needed"),
     "why": "企业客户或认证需求要求 ISMS"},
    {"id": "SOC 2", "binding": "contract", "deps": ["ISO 27001"],
     "trigger": lambda p: p.get("us_enterprise_clients")
     or p.get("saas_revenue"),
     "why": "美国企业客户 SaaS 交付的通行鉴证"},
    {"id": "ISO 42001", "binding": "voluntary", "deps": ["ISO 27001"],
     "trigger": lambda p: p.get("ai_development") or p.get("ai_deployed"),
     "why": "开发或部署 AI 系统的 AIMS 基线"},
    {"id": "EU AI Act", "binding": "legal", "deps": ["ISO 42001"],
     "trigger": lambda p: p.get("ai_deployed")
     and (p.get("eu_market") or p.get("eu_users")),
     "why": "面向欧盟市场/用户部署 AI 系统"},
    {"id": "HIPAA", "binding": "legal", "deps": [],
     "trigger": lambda p: p.get("processes_phi"),
     "why": "处理受保护健康信息"},
    {"id": "FDA QSR", "binding": "legal", "deps": [],
     "trigger": lambda p: p.get("medical_device_software"),
     "why": "软件构成医疗器械"},
    {"id": "NIS2", "binding": "legal", "deps": ["ISO 27001"],
     "trigger": lambda p: p.get("essential_services") and p.get("eu_market"),
     "why": "欧盟关键实体网络安全指令"},
    {"id": "NIST CSF", "binding": "voluntary", "deps": [],
     "trigger": lambda p: p.get("us_government_clients"),
     "why": "美国政府客户要求网络安全框架"},
]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("frameworks", "适用治理框架决策树（legal→contract→voluntary）"),
                 ("aiclassify", "AI 系统风险分级（禁止/高/有限/最小）"),
                 ("disclose", "AI 披露与透明度最小集校验")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"frameworks": _frameworks, "aiclassify": _aiclassify,
          "disclose": _disclose}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _frameworks(data: Any) -> Dict[str, Any]:
    profile = data.get("profile", {}) or {}
    checks: List[Dict[str, Any]] = []
    selected: List[Dict[str, Any]] = []
    for fr in _FRAMEWORK_RULES:
        if fr["trigger"](profile):
            selected.append({"framework": fr["id"], "binding": fr["binding"],
                             "why": fr["why"], "deps": fr["deps"]})
    if not selected:
        checks.append(c.ck(False, "未命中任何治理框架（profile 过于稀疏？）",
                           "selection", "HIGH"))
    binding_rank = {"legal": 0, "contract": 1, "voluntary": 2}
    order = sorted(selected, key=lambda x: binding_rank[x["binding"]])
    # 依赖检查：被选框架的依赖必须也被选（SOC2→ISO27001 等）
    selected_ids = {s["framework"] for s in selected}
    for s in selected:
        for dep in s["deps"]:
            if dep not in selected_ids:
                checks.append(c.ck(False,
                                   f"{s['framework']} 依赖 {dep} 但未选入",
                                   "dependency", "HIGH",
                                   framework=s["framework"], missing=dep))
    # 合规义务排序：legal 必须排在 roadmap 首位
    roadmap = [x["framework"] for x in order]
    legal = [x["framework"] for x in order if x["binding"] == "legal"]
    checks.append(c.ck(bool(legal) or bool(selected),
                       f"适用框架 {roadmap or '无'}", "frameworks", "OK"))
    if legal:
        checks.append(c.ck(roadmap[0] in legal,
                           f"法定框架优先：{legal} 排最前",
                           "binding_first", "HIGH"
                           if roadmap[0] not in legal else "OK"))
    return c.result(checks, selected=selected, roadmap=roadmap,
                    legal_frameworks=legal,
                    next="legal 缺口优先补；voluntary 可排期")


# --------------------------------------------------------------------------- #
def _aiclassify(data: Any) -> Dict[str, Any]:
    """EU AI Act 四级分类：禁止实践 > 高风险用途 > 有限（透明）> 最小。"""
    th = c.load_thresholds()["aigov"]
    system = data.get("system", {}) or {}
    practices = [str(x) for x in (system.get("practices", [])
                                  or [system.get("practice", "")]) if x]
    checks: List[Dict[str, Any]] = []
    hits_prohibited = [p for p in practices
                       if p in th["prohibited_practices"]]
    hits_high = [p for p in practices if p in th["high_risk_flags"]]
    if hits_prohibited:
        level = "prohibited"
    elif hits_high:
        level = "high"
    elif system.get("interacts_with_humans") or system.get("generates_content"):
        level = "limited"
    else:
        level = "minimal"
    if level == "prohibited":
        checks.append(c.ck(False, f"命中禁止实践 {hits_prohibited}，"
                                  f"不得部署", "ai_level", "CRITICAL",
                           level=level))
    elif level == "high":
        checks.append(c.ck(bool(system.get("conformity_assessment"))
                           and bool(system.get("human_oversight")),
                           f"高风险 AI（{hits_high}）须已完成合规评定"
                           f"且有人类监督安排", "ai_level", "CRITICAL"
                           if not (system.get("conformity_assessment")
                                   and system.get("human_oversight"))
                           else "OK", level=level))
    else:
        checks.append(c.ck(True, f"风险分级 {level}", "ai_level", "OK",
                           level=level))
    if level not in th["risk_levels"]:
        checks.append(c.ck(False, f"非法分级 {level}", "ai_level", "CRITICAL"))
    return c.result(checks, level=level,
                    level_rank=th["risk_levels"].index(level) if level
                    in th["risk_levels"] else -1,
                    prohibited_hit_count=len(hits_prohibited),
                    high_risk_hit_count=len(hits_high),
                    practice_count=len(practices),
                    prohibited_hits=hits_prohibited, high_risk_hits=hits_high,
                    next="prohibited 直接下线；high 补评定与监督再上线")


# --------------------------------------------------------------------------- #
def _disclose(data: Any) -> Dict[str, Any]:
    """AI 披露最小集：披露 AI 身份 / 生成内容标识 / 人工监督点 / 申诉渠道。"""
    th = c.load_thresholds()["aigov"]
    disclosure = data.get("disclosure", {}) or {}
    checks: List[Dict[str, Any]] = []
    if not disclosure:
        checks.append(c.ck(False, "disclosure 为空", "structure", "CRITICAL"))
        return c.result(checks, next="补披露四要素")
    for f in th["disclosure_required_fields"]:
        ok = bool(disclosure.get(f))
        checks.append(c.ck(ok, f"披露要素「{f}」" + ("齐全" if ok else "缺失"),
                           "disclosure_field", "HIGH" if not ok else "OK",
                           field=f))
    # 与用户交互的 AI 必须在会话开始时披露身份
    if disclosure.get("disclose_interaction"):
        ok = bool(disclosure.get("disclose_at_start"))
        checks.append(c.ck(ok, "交互式 AI 须在会话开始即披露",
                           "disclose_timing", "HIGH" if not ok else "OK"))
    required = th["disclosure_required_fields"]
    complete = sum(1 for f in required if disclosure.get(f))
    return c.result(checks, disclosure_complete=f"{complete}/{len(required)}",
                    disclosure_complete_count=complete,
                    required_count=len(required),
                    next="四要素齐全后随版本发布并留档")
