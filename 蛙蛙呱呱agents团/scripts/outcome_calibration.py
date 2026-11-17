# -*- coding: utf-8 -*-
"""月度结果校准（P9）：读台账，写 JSON + Markdown；没有到期数据就写 NO_DUE_DATA。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import outcome_ledger as ol  # noqa: E402

DEFAULT_OUT = ROOT.parent / "workspace" / "outcomes"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="outcome_calibration")
    ap.add_argument("--path", default=None, help="ledger.json；默认 workspace/outcomes/ledger.json")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="输出目录")
    ap.add_argument("--month", default=None, help="YYYY-MM；默认今天所在月")
    a = ap.parse_args(argv)
    cal = ol.calibrate(path=a.path, month=a.month)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"calibration_{cal['month']}.json"
    mp = out / f"calibration_{cal['month']}.md"
    jp.write_text(json.dumps(cal, ensure_ascii=False, indent=2), encoding="utf-8")
    s = cal["summary"]
    lines = [
        f"# 结果校准 {cal['month']}",
        "",
        f"- 台账总数：{s['total']}；open：{s['open']}；逾期：{s['overdue']}",
        f"- 命中率：{s['hit_rate'] if s['hit_rate'] is not None else '—（无到期数据）'}",
        f"- 判决：**{cal['verdict']}**",
        f"- 说明：{cal['note']}",
        "",
        "## 回填清单",
        "",
        *([f"- `{i}`" for i in cal["due_unreviewed"]] or ["- 无逾期未回填"]),
        "",
    ]
    mp.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(jp), "md": str(mp),
                      "verdict": cal["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
