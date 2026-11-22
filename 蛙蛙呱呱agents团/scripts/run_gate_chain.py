# -*- coding: utf-8 -*-
"""scripts/run_gate_chain.py —— 一条门禁链的 CLI 入口（SOP S6）。

用法：
    python scripts/run_gate_chain.py --dir <项目> [--out <输出目录>] [--html <报告>]
输出：JSON 到 stdout，并写 <out>/gate_chain.json。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import gate_chain  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="项目目录（含 plan/）")
    ap.add_argument("--out", default="", help="输出目录（含 contract.json）")
    ap.add_argument("--html", default="", help="报告 html（跑 L4）")
    a = ap.parse_args()

    res = gate_chain.run(a.dir, a.html or None, a.out or None)
    out = Path(a.out) if a.out else Path(res["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "gate_chain.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
