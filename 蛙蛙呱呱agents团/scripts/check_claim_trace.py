# -*- coding: utf-8 -*-
"""scripts/check_claim_trace.py —— 结论可追门禁：正文每个数字必须回到 material pack。

用法：
    python scripts/check_claim_trace.py --report <report.html> --evidence <analysis_material_pack.json|链条目录>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "r06-wadeqing-analyst"
for p in (str(ROOT), str(ROLE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from analysis_chain.deliver import audit_trace  # noqa: E402


def _selftest() -> int:
    pack = {"numbers": {"C0-N1": {"display": "1,234元", "value": 1234}},
            "claims": [{"claim_id": "C0"}]}
    good = "<html><body><p>本期为 1,234元。</p></body></html>"
    bad = "<html><body><p>本期为 9,999元。</p></body></html>"
    ok1 = audit_trace(good, pack)["ok"]
    ok2 = audit_trace(bad, pack)["ok"]
    print(f"[{'PASS' if ok1 and not ok2 else 'FAIL'}] claim_trace selftest "
          f"good={ok1} bad_rejected={not ok2}")
    return 0 if (ok1 and not ok2) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_claim_trace")
    ap.add_argument("--report", default=None, help="报告 HTML")
    ap.add_argument("--evidence", default=None, help="material pack JSON 或链条目录")
    ap.add_argument("--selftest", action="store_true", help="内置正反例自测")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.report or not a.evidence:
        print("[FAIL] 需要 --report 与 --evidence（或 --selftest）")
        return 1
    path = a.evidence
    if os.path.isdir(path):
        path = os.path.join(path, "analysis_material_pack.json")
    if not os.path.exists(path):
        print(f"[FAIL] 缺少证据包 {path}")
        return 1
    pack = json.load(open(path, encoding="utf-8"))
    html = open(a.report, encoding="utf-8", errors="replace").read()
    trace = audit_trace(html, pack)
    if a.json:
        print(json.dumps(trace, ensure_ascii=False, indent=2))
    else:
        print(f"[{'PASS' if trace['ok'] else 'FAIL'}] 结论可追率={trace['rate']:.1%} "
              f"未追到={trace['untraced'][:10]}")
    return 0 if trace["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
