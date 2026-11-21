# -*- coding: utf-8 -*-
"""R04 验收输入派生校验：三份输入必须由产物派生（sha 对得上）。

用法：
    python scripts/check_r04_inputs.py --dir out
    python scripts/check_r04_inputs.py --dir out --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import r04_derive  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="报告产物目录（含 report.html 与 r04_*.json）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = r04_derive.check(a.dir)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if res["ok"]:
            print(f"PASS  派生关系成立  {a.dir}  sha={res['artifact_sha256'][:12]}")
        else:
            print(f"FAIL  {a.dir}")
            for p in res.get("problems") or []:
                print(f"      - {p}")
            print("      修法：python guagua.py report run-line … 重出报告，"
                  "r04 输入由产线自动派生，不要手写")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
