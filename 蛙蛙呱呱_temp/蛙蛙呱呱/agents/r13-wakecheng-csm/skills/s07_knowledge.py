# -*- coding: utf-8 -*-
"""S07 服务知识与升级 —— 能力域 7。

整合 chatwoot__chatwoot 的 `canned_response.rb`（short_code + content 复用问答）+
`kbase.rb`（知识库）+ `article.rb`（帮助文章）。把「FAQ 与升级」转成确定性校验：
FAQ 三件套、答案长度下限、重复检测（Jaccard 相似度）、升级单四要素（symptom/
repro/impact/owner_route）、升级路由白名单（r07 产品/r09 工程/r03 合规/r02 流程）、
问题证据（source + quote）。

关键立场：升级必须有证据，不能只转「客户说有问题」——每张升级单都要挂
source（数据/工单来源）与 quote（可追溯原文）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "knowledge"
DESC = "服务知识与升级：faq/escalation"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("faq", help="校验 FAQ 知识库")
    a.add_argument("--input", required=True)
    b = act.add_parser("escalation", help="校验升级单")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "faq":
        return _validate_faq(data)
    if args.action == "escalation":
        return _validate_escalation(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_faq(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    kth = c.load_thresholds()["knowledge"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", faq_count=0)

    faqs = data.get("faqs")
    if not isinstance(faqs, list) or not faqs:
        return c.result([_ck(False, "faqs 必须是非空列表", "knowledge.list")],
                        ok=False, verdict="FAIL", faq_count=0)

    missing = [f.get("question") for f in faqs if isinstance(f, dict)
               and any(not str(f.get(k, "")).strip() for k in kth["faq_required"])]
    checks.append(_ck(not missing, f"FAQ 三件套齐备（缺 {missing or '无'}）",
                      "knowledge.faq_fields"))

    short_answers = [f.get("question") for f in faqs if isinstance(f, dict)
                     and len(str(f.get("answer", ""))) < kth["min_answer_chars"]]
    checks.append(_ck(not short_answers,
                      f"答案 ≥ {kth['min_answer_chars']} 字（过短 {short_answers or '无'}）",
                      "knowledge.answer_len"))

    # 重复检测：两两 Jaccard > duplicate_similarity
    dups: List[str] = []
    qs = [str(f.get("question", "")) for f in faqs if isinstance(f, dict)]
    for i in range(len(qs)):
        for j in range(i + 1, len(qs)):
            if c.jaccard(qs[i], qs[j]) > kth["duplicate_similarity"]:
                dups.append(f"#{i}<->#{j}")
    checks.append(_ck(not dups, f"无重复 FAQ（相似 {dups or '无'}）",
                      "knowledge.duplicate"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    faq_count=len(faqs),
                    narrative=f"FAQ {len(faqs)} 条、重复 {len(dups)} 对")


# --------------------------------------------------------------------------- #
def _validate_escalation(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    kth = c.load_thresholds()["knowledge"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", escalation_count=0)

    missing = [k for k in kth["escalation_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"升级单四要素齐备（缺 {missing or '无'}）",
                      "knowledge.escalation_fields"))

    route = data.get("owner_route")
    ok_route = route in kth["escalation_routes"]
    checks.append(_ck(ok_route, f"升级路由={route!r} 在白名单 {kth['escalation_routes']}",
                      "knowledge.route"))

    # 问题证据：source + quote 双要素
    evidence = data.get("evidence")
    ok_ev = isinstance(evidence, dict) and all(
        str(evidence.get(k, "")).strip() for k in kth["evidence_required"])
    checks.append(_ck(ok_ev, "问题证据（source + quote）齐备", "knowledge.evidence"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    escalation_count=1, route=route,
                    narrative=(f"升级单「{data.get('symptom', '?')}」→ {route}"))
