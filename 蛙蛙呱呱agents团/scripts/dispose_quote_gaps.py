# -*- coding: utf-8 -*-
"""12 条 quote gap 的自动处置清单（P13）。

不伪造 quote；只把缺口分成：
    void       反爬/不可复现 → 标 void，不算命中也不算失败
    downgrade  页面没有引用值 → 降级为观察/假设，不进头条
写 data/quote_gap_disposition.json，供 R05/R06 后续换源或降级。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ANTI_BOT = {"S15", "S17", "S18"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dispose_quote_gaps")
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    base = Path(a.project) / "data"
    gaps = json.loads((base / "quote_gaps.json").read_text(encoding="utf-8-sig"))
    items = []
    for g in gaps.get("gaps") or []:
        sid = str(g.get("id"))
        action = "void" if sid in ANTI_BOT else "downgrade"
        items.append({
            "id": sid,
            "action": action,
            "owner": "r05" if action == "void" else "r06",
            "reason": g.get("reason") or "",
            "next": ("找历史快照/替代页；找不到就标 void"
                     if action == "void" else
                     "换同规格同周期来源；换不到把相关断言降级为观察"),
        })
    out = {
        "schema": "dsh.quote_gap_disposition/v1",
        "total": len(items),
        "void": sum(1 for x in items if x["action"] == "void"),
        "downgrade": sum(1 for x in items if x["action"] == "downgrade"),
        "items": items,
        "strict": "未补 quote 前 report build --quote-mode strict 仍会阻断",
    }
    p = Path(a.out) if a.out else base / "quote_gap_disposition.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "path": str(p), "total": out["total"],
                      "void": out["void"], "downgrade": out["downgrade"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
