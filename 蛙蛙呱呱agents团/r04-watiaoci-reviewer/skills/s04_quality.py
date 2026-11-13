# -*- coding: utf-8 -*-
"""s04 独立质量评价（quality）：critique / converge 两动作。

口径来源：Intense-Visions__harness-engineering · harness-verification（Iron Law：
完成声明必须有本会话新鲜证据；报告禁词 should/probably/seems to/I believe）
与 harness-soundness-review（findings schema + 收敛循环）。
- critique：三查——①claims 文本禁词扫描 ②完成型 claim 必须有非空 evidence_refs，
  否则 not_verified ③绝对词需 evidence 支撑；findings 按 soundness schema 输出，
  error 阻断签发。
- converge：总 issue 数不再下降即 converged（终止收敛循环）。
阈值：thresholds.json → quality.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "quality"
DESC = "独立质量评价：critique（禁词/证据链/绝对词三查 + soundness findings）与 converge（总 issue 不再下降即收敛）"

ACTIONS = {
    "critique": "对工作产品的 claims 做禁词、证据链、绝对词三查，error 阻断签发",
    "converge": "对照两轮 findings 总数，不再下降即 converged 终止循环",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ap = act.add_parser("critique", help=ACTIONS["critique"])
    ap.add_argument("--input", required=True)
    ap = act.add_parser("converge", help=ACTIONS["converge"])
    ap.add_argument("--input", required=True, help="第一轮 findings JSON")
    ap.add_argument("--compare", required=True, help="第二轮 findings JSON")


# --------------------------------------------------------------------------- #
# critique
# --------------------------------------------------------------------------- #
def _find_hedge(text: str, hedge_words: List[str]) -> List[str]:
    low = text.lower()
    return [w for w in hedge_words if w in low]


def _critique_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["quality"]
    claims = data.get("claims") or []
    checks: List[Dict[str, Any]] = []
    if not claims:
        checks.append(c.ck(False, "claims 为空，无完成声明可核", "quality:claims", "CRITICAL"))
    findings: List[Dict[str, Any]] = []
    claims_checked: List[Dict[str, Any]] = []
    fid = 0

    for cl in claims:
        cid = str(cl.get("id") or "")
        text = str(cl.get("text") or "")
        kind = str(cl.get("kind") or "completion")
        refs = [str(r) for r in (cl.get("evidence_refs") or []) if str(r).strip()]
        problems: List[str] = []

        hedges = _find_hedge(text, th["hedge_words"])
        for w in hedges:
            fid += 1
            problems.append(f"hedge:{w}")
            findings.append({
                "id": f"Q-{fid:03d}", "check": "hedge_language", "title": "使用推测措辞",
                "detail": f"claim {cid} 含禁词 {w!r}（完成声明只能写 verified / not verified）",
                "severity": "error", "autoFixable": False,
                "suggestedFix": "改为「verified: <证据>」或「not verified: <缺失>」",
                "evidence": [f"claim {cid}: {text[:60]}"],
            })
        if kind == "completion" and not refs:
            fid += 1
            problems.append("not_verified")
            findings.append({
                "id": f"Q-{fid:03d}", "check": "completion_without_evidence",
                "title": "完成声明无证据",
                "detail": f"claim {cid} 是完成型声明但没有非空 evidence_refs（Iron Law）",
                "severity": "error", "autoFixable": False,
                "suggestedFix": "补本会话新鲜证据引用后重报",
                "evidence": [f"claim {cid}: evidence_refs 为空"],
            })
        absolutists = _find_hedge(text, th["absolutist_words"])
        if absolutists and not refs:
            fid += 1
            problems.append(f"absolutist:{absolutists[0]}")
            findings.append({
                "id": f"Q-{fid:03d}", "check": "absolutist_without_evidence",
                "title": "绝对词无证据支撑",
                "detail": f"claim {cid} 含绝对词 {absolutists[0]!r} 且无 evidence_refs",
                "severity": "error", "autoFixable": False,
                "suggestedFix": "要么补证据，要么把绝对表述改为可验证的具体范围",
                "evidence": [f"claim {cid}: {text[:60]}"],
            })
        verified = not problems
        claims_checked.append({
            "id": cid, "text": text, "kind": kind,
            "evidence_refs": refs,
            "status": "verified" if verified else "not_verified",
            "problems": problems,
        })

    error_count = sum(1 for f in findings if f["severity"] == "error")
    warning_count = sum(1 for f in findings if f["severity"] == "warning")
    verdict = "PASS" if error_count == 0 else "FAIL"
    for cl in claims_checked:
        checks.append(c.ck(cl["status"] == "verified",
                           f"{cl['id']}: {cl['status']}" + (f"（{'/'.join(cl['problems'])}）"
                                                            if cl["problems"] else ""),
                           f"quality:{cl['id']}",
                           "OK" if cl["status"] == "verified" else "CRITICAL"))
    out = c.result(checks,
                   claims_checked=claims_checked,
                   findings=findings,
                   error_count=error_count,
                   warning_count=warning_count,
                   verdict=verdict,
                   next="0 error：可签发" if verdict == "PASS"
                        else "error 阻断签发：生产方按 suggestedFix 修改后重评",
                   )
    out["ok"] = out["ok"] and verdict == "PASS"
    return out


def critique(data: Dict[str, Any]) -> Dict[str, Any]:
    return _critique_core(data)


# --------------------------------------------------------------------------- #
# converge
# --------------------------------------------------------------------------- #
def _count_findings(data: Dict[str, Any]) -> int:
    findings = data.get("findings")
    if isinstance(findings, list):
        return len(findings)
    if isinstance(findings, int):
        return int(findings)
    return -1


def _converge_core(v1: Dict[str, Any], v2: Dict[str, Any]) -> Dict[str, Any]:
    t1 = _count_findings(v1)
    t2 = _count_findings(v2)
    checks: List[Dict[str, Any]] = []
    if t1 < 0 or t2 < 0:
        checks.append(c.ck(False, "findings 字段缺失或非法（须为非负数组或计数）",
                           "quality:converge", "CRITICAL"))
        converged = None
        verdict = "INVALID"
    else:
        converged = t2 >= t1
        verdict = "CONVERGED" if converged else "ITERATING"
        checks.append(c.ck(True, f"v1={t1} v2={t2} → {verdict}（总 issue 不再下降即收敛）",
                           "quality:converge", "OK", **{"converged": converged}))
    out = c.result(checks,
                   v1_count=t1, v2_count=t2,
                   delta=t2 - t1 if (t1 >= 0 and t2 >= 0) else None,
                   converged=converged,
                   verdict=verdict,
                   next="终止收敛循环：当前发现已收敛" if converged
                        else "issue 仍在下降：继续下一轮评审-修复循环",
                   )
    out["ok"] = out["ok"] and t1 >= 0 and t2 >= 0
    return out


def converge(v1: Dict[str, Any], v2: Dict[str, Any]) -> Dict[str, Any]:
    return _converge_core(v1, v2)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "critique":
        return critique(data)
    if args.action == "converge":
        v2 = c.load_json(args.compare)
        return converge(data, v2)
    raise SystemExit(f"未知动作：{args.action}")
