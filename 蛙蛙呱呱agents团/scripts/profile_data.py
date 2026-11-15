# -*- coding: utf-8 -*-
"""把数据画像导出成 JSON，交给模型（我）选主表/主指标。

用法：
    python scripts/profile_data.py --data <项目>/data --out <项目>/data/profile.json
模型读 profile.json → 写 focus.json（table/measure/dimension/reason/confidence）
→ python guagua.py reason --role r06 --focus focus.json ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.data_profile import profile_dir  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    prof = profile_dir(a.data)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(prof, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}  tables={len(prof['tables'])}")
    for t in prof["tables"]:
        print(f"  {Path(t['file']).name:34s} rows={t['rows']:>4}  time={t['time']}  "
              f"measures={t['measures']}  dims={t['dimensions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
