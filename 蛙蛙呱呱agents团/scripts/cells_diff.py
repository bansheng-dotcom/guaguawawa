# -*- coding: utf-8 -*-
"""scripts/cells_diff.py —— 三套 cells→claims 读数对账（P5-5 双写期）。

用法：
    python scripts/cells_diff.py --project <项目目录>
退出码：0 一致；1 有差异或缺键。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import cells_unified  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    a = ap.parse_args(argv)
    res = cells_unified.compare(Path(a.project), write=True)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
