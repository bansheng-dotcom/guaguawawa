# -*- coding: utf-8 -*-
"""咨询项目 CLI：start / submit / sign / advance / status / render / check。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.consulting import checks, workbook  # noqa: E402
from shared.consulting.stages import STAGES  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start")
    s.add_argument("--id", required=True)
    s.add_argument("--client", required=True)
    s.add_argument("--decision", required=True)
    s.add_argument("--partner", default="r01")
    s.add_argument("--lead", default="r05")
    s.add_argument("--deadline", default="")

    sb = sub.add_parser("submit")
    sb.add_argument("--id", required=True)
    sb.add_argument("--stage", type=int, required=True)
    sb.add_argument("--input", required=True)

    sg = sub.add_parser("sign")
    sg.add_argument("--id", required=True)
    sg.add_argument("--stage", type=int, required=True)
    sg.add_argument("--by", required=True)

    ad = sub.add_parser("advance")
    ad.add_argument("--id", required=True)

    st = sub.add_parser("status")
    st.add_argument("--id", required=True)

    rd = sub.add_parser("render")
    rd.add_argument("--id", required=True)

    ck = sub.add_parser("check")
    ck.add_argument("--stage", type=int, required=True)
    ck.add_argument("--input", required=True)

    ns = ap.parse_args()
    try:
        if ns.cmd == "start":
            wb = workbook.start(ns.id, ns.client, ns.decision, ns.partner, ns.lead, ns.deadline)
            print(f"已创建 {ns.id}，当前阶段 {wb['current_stage']}；工作簿：{workbook.path_of(ns.id)}")
        elif ns.cmd == "submit":
            payload = json.loads(Path(ns.input).read_text(encoding="utf-8"))
            r = workbook.submit(ns.id, ns.stage, payload)
            print(f"阶段 {r['stage']} {'通过' if r['ok'] else '未通过'}")
            for e in r["errors"]:
                print("  -", e)
            return 0 if r["ok"] else 1
        elif ns.cmd == "sign":
            print(workbook.sign(ns.id, ns.stage, ns.by))
        elif ns.cmd == "advance":
            print(workbook.advance(ns.id))
        elif ns.cmd == "status":
            for r in workbook.status(ns.id):
                print(f"{r['stage']} {r['name']:<8} {r['status']:<12} 签字={r['signed_by'] or '—'}")
                for e in r["errors"]:
                    print("   -", e)
        elif ns.cmd == "render":
            print("已生成：", workbook.render_md(ns.id))
        elif ns.cmd == "check":
            payload = json.loads(Path(ns.input).read_text(encoding="utf-8"))
            errs = checks.check(ns.stage, payload)
            print("通过" if not errs else "未通过")
            for e in errs:
                print("  -", e)
            return 0 if not errs else 1
    except workbook.WorkbookError as exc:
        print(f"失败：{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
