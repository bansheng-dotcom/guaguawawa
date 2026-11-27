# -*- coding: utf-8 -*-
"""S13 增长链 —— 七段可复算流水线（diagnose → … → mmm）。

动作：
  diagnose / experiment / attribution / retention / paid / selfmedia / mmm
  单段跑并落盘；run 一条命令跑全链；audit 复核工件 sha256 与跨段一致性。
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from . import _common as c

ROLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROLE not in sys.path:
    sys.path.insert(0, ROLE)

from growth_chain import (attribution, diagnose, experiment, mmm, paid,  # noqa: E402
                          retention, runner, selfmedia)

NAME = "growth_chain"
DESC = "七段增长链：诊断/实验/归因/留存/付费/自媒体/MMM + 一键跑链 + 审计"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    def single(name: str, help_text: str) -> Any:
        sub = act.add_parser(name, help=help_text)
        sub.add_argument("--input", required=True)
        sub.add_argument("--out", default="")
        return sub

    d = single("diagnose", "指标树 + 漏斗 + 异常检测")
    d.add_argument("--metric", default="revenue")
    single("experiment", "两比例功效 / 样本量 / 预注册")
    a = single("attribution", "首触/末触/多触 + 增量")
    a.add_argument("--evidence", default="")
    a.add_argument("--budget-total", type=float, default=100000.0)
    a.add_argument("--causal-claim", action="store_true")
    single("retention", "队列矩阵 + 留存曲线 + 激活/推荐")
    pd = single("paid", "CAC / LTV / 回收月 / 贡献毛利")
    pd.add_argument("--payback-max", type=float, default=18.0)
    sm = single("selfmedia", "平台导出规范化 + 看板 + 三态日报")
    sm.add_argument("--platform", default="")
    mm = single("mmm", "adstock + 饱和 + ridge + 留出 + 贡献 CI")
    mm.add_argument("--decay", type=float, default=0.5)
    mm.add_argument("--ridge-lambda", type=float, default=1.0)
    mm.add_argument("--holdout-r2-min", type=float, default=0.5)

    r = act.add_parser("run", help="一条命令跑 7 段并产出 manifest")
    r.add_argument("--spec", required=True)
    r.add_argument("--out-dir", required=True)
    au = act.add_parser("audit", help="复核工件 sha256 与跨段一致性")
    au.add_argument("--dir", required=True)


def _checks(gate: Dict[str, Any], stage: str) -> List[Dict[str, Any]]:
    return [{"ok": x["ok"], "msg": f"{x['name']}：{x.get('detail', '')}",
             "dim": f"growth.{stage}",
             "sev": "OK" if x["ok"] else "BLOCKER"} for x in gate.get("checks", [])]


def run(args) -> Dict[str, Any]:
    action = args.action
    if action == "run":
        manifest = runner.run(args.spec, args.out_dir)
        return c.result(_checks(manifest["gate"], "run"), ok=manifest["ok"],
                        artifact=manifest, manifest=manifest,
                        artifact_path=os.path.join(args.out_dir,
                                                   "growth_manifest.json"))
    if action == "audit":
        audit = runner.audit(args.dir)
        return c.result(_checks(audit, "audit"), ok=audit["ok"],
                        artifact=audit["artifact"], audit=audit,
                        artifact_path=os.path.join(args.dir, "growth_manifest.json"))

    stage_map = {
        "diagnose": lambda: diagnose.build(args.input),
        "experiment": lambda: experiment.build(args.input),
        "attribution": lambda: attribution.build(
            args.input, evidence_path=args.evidence or None,
            budget_total=args.budget_total, causal_claim=args.causal_claim),
        "retention": lambda: retention.build(args.input),
        "paid": lambda: paid.build(args.input, payback_max=args.payback_max),
        "selfmedia": lambda: selfmedia.build(args.input,
                                             platform=args.platform or None),
        "mmm": lambda: mmm.build(args.input, decay=args.decay,
                                 ridge_lambda=args.ridge_lambda,
                                 holdout_r2_min=args.holdout_r2_min),
    }
    if action not in stage_map:
        return {"error": f"未知动作: {action}", "ok": False, "checks": []}
    artifact = stage_map[action]()
    out = args.out or os.path.join(ROLE, "artifacts", f"{action}.json")
    c.write_json(out, artifact)
    return c.result(_checks(artifact["gate"], action),
                    ok=artifact["gate"]["ok"], artifact=artifact,
                    artifact_path=os.path.abspath(out), action=action)
