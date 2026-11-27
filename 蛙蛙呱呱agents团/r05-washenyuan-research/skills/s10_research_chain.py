# -*- coding: utf-8 -*-
"""chain 技能：8 段研究链的 CLI 外壳（scope/source/collect/verify/triangulate/size/compete/report/run/audit）。

用法：
    python agent.py chain run --fixture fixtures/pet_smart_hardware.json --out-dir artifacts/chain
    python agent.py chain report --fixture fixtures/pet_smart_hardware.json
    python agent.py chain audit --out-dir artifacts/chain
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

from research_chain import audit as chain_audit
from research_chain import run_fixture

NAME = "chain"
DESC = "8 段研究链：scope→source→collect→verify→triangulate→size→compete→report"

ACTIONS = {
    "scope": "拆解决策问题（5–8 子问题 + MECE）",
    "source": "建立源地图（一手/二手/三手）",
    "collect": "落证据台账（七要素 + 三要素）",
    "verify": "逐条验证（回抓/复算/偏见/时效）",
    "triangulate": "合成结论（置信度 + 矛盾记录）",
    "size": "双口径测算 + p10/p50/p90",
    "compete": "5 家 × 8 维矩阵 + battlecard + 五力 + 份额",
    "report": "研究简报（结论先行 + 证据附录 + 边界）",
    "run": "一条命令跑完 8 段并写 manifest",
    "audit": "复核 sha256 与全部门禁",
}

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FIXTURE = os.path.join(_HERE, "fixtures", "pet_smart_hardware.json")
DEFAULT_OUT = os.path.join(_HERE, "artifacts", "chain")


def add_parser(sub) -> None:
    """注册 chain 技能及 10 个子命令（与 ACTIONS 同序）。"""
    sp = sub.add_parser(NAME, help=DESC)
    acts = sp.add_subparsers(dest="action", required=True)
    for name, help_text in ACTIONS.items():
        ap = acts.add_parser(name, help=help_text)
        ap.add_argument("--fixture", default=None, help="研究链夹具 JSON")
        ap.add_argument("--input", default=None, help="兼容统一 --input 传夹具")
        ap.add_argument("--out-dir", default=None, help="产物目录")
        ap.add_argument("--seed", type=int, default=None, help="蒙特卡洛种子")


def _resolve(args) -> tuple:
    fixture = getattr(args, "fixture", None) or getattr(args, "input", None) or DEFAULT_FIXTURE
    out_dir = getattr(args, "out_dir", None) or DEFAULT_OUT
    seed = getattr(args, "seed", None)
    return fixture, out_dir, seed


def _stage_output(art: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
    """把阶段工件展开为契约可校验的 CLI 结果。"""
    gate = art.get("gate") or {}
    out = dict(art)
    out.update({
        "ok": bool(gate.get("ok")),
        "verdict": "PASS" if gate.get("ok") else "FAIL",
        "checks": gate.get("checks") or [],
        "out_dir": out_dir,
    })
    if art.get("artifact") == "research_plan":
        out["subquestion_count"] = len(art.get("subquestions") or [])
        out["mece_ok"] = bool((art.get("mece") or {}).get("mutually_exclusive")
                              and (art.get("mece") or {}).get("collectively_exhaustive"))
    elif art.get("artifact") == "source_map":
        summary = art.get("summary") or {}
        out["candidate_count"] = summary.get("candidate_count", 0)
        out["type_count"] = summary.get("type_count", 0)
    elif art.get("artifact") == "evidence_ledger":
        out["evidence_count"] = len(art.get("entries") or [])
    elif art.get("artifact") == "verification":
        summary = art.get("summary") or {}
        out["verified_count"] = summary.get("verified", 0)
        out["unverified_count"] = summary.get("unverified", 0)
    elif art.get("artifact") == "synthesis":
        summary = art.get("summary") or {}
        out["conclusion_count"] = summary.get("conclusion_count", 0)
        out["contradiction_count"] = summary.get("contradiction_count", 0)
    elif art.get("artifact") == "sizing":
        mc = art.get("monte_carlo") or {}
        out["tam_top"] = (art.get("top_down") or {}).get("tam")
        out["tam_bottom"] = (art.get("bottom_up") or {}).get("tam")
        out["tam_p50"] = mc.get("p50")
    elif art.get("artifact") == "competition":
        out["competitor_count"] = len(art.get("competitors") or [])
        out["dimension_count"] = len(art.get("dimensions") or [])
    elif art.get("artifact") == "research_report":
        out["appendix_count"] = len(art.get("ledger_evidence_ids") or [])
        out["conclusion_count"] = len(art.get("conclusions") or [])
    return out


def run(args) -> Dict[str, Any]:
    """执行单个阶段 / 全链 / 审计；退出码由调用方按 ok 决定。"""
    action = str(getattr(args, "action", "run"))
    fixture, out_dir, seed = _resolve(args)

    if action == "audit":
        result = chain_audit(out_dir)
        return {"artifact": "chain_audit", "ok": bool(result.get("ok")),
                "verdict": result.get("verdict", "FAIL" if not result.get("ok") else "PASS"),
                "checks": result.get("checks") or [], "failed": result.get("failed") or [],
                "research_id": result.get("research_id"), "out_dir": out_dir}

    if not os.path.isfile(fixture):
        return {"ok": False, "verdict": "FAIL", "checks": [],
                "error": "fixture not found: %s" % fixture}

    kwargs = {"seed": seed} if seed is not None else {}
    manifest = run_fixture(fixture, out_dir, **kwargs)
    if action == "run":
        checks = [c for s in manifest.get("stages") or []
                  for c in ([{"id": "stage:%s" % s.get("stage"), "ok": bool(s.get("gate")),
                              "detail": ",".join(s.get("gate_failed") or [])}])]
        checks += (manifest.get("cross_checks") or {}).get("checks") or []
        return {"artifact": "chain_run", "ok": bool(manifest.get("ok")),
                "verdict": manifest.get("grade") == "A" and "PASS" or "FAIL",
                "checks": checks, "failed": [c["id"] for c in checks if not c["ok"]],
                "manifest": manifest, "stage_count": len(manifest.get("stage_order") or []),
                "out_dir": out_dir}

    path = os.path.join(out_dir, "%s.json" % action)
    if not os.path.isfile(path):
        return {"ok": False, "verdict": "FAIL", "checks": [],
                "error": "unknown chain action: %s" % action}
    with open(path, "r", encoding="utf-8-sig") as f:
        art = json.load(f)
    return _stage_output(art, out_dir)


def main(argv=None) -> int:
    """独立运行入口（供调试；正式入口仍是 agent.py）。"""
    parser = argparse.ArgumentParser(prog="s10_research_chain")
    sub = parser.add_subparsers(dest="cmd", required=True)
    add_parser(sub)
    args = parser.parse_args(argv)
    out = run(args)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
