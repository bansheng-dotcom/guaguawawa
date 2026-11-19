#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐卡预检：用产线同一套判据检查单张 claims.json（不渲染、不合并）。

用法：
    python _check_card.py <claims.json> [...]
"""
from __future__ import annotations

import json
import sys
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from compile_agent_report import build_pack, build_draft  # noqa: E402


def check_one(p: Path) -> dict:
    claims = json.loads(p.read_text(encoding="utf-8-sig"))
    pack = build_pack(claims)
    draft = build_draft(claims)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump({"draft": draft, "pack": pack}, f, ensure_ascii=False)
        tmp = f.name
    proc = subprocess.run(
        [sys.executable, str(ROOT / "r01-waquanju-ceo" / "agent.py"),
         "interpret", "sections", "--input", tmp],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        res = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {"file": p.name, "ok": False, "raw": proc.stdout[-800:] + proc.stderr[-800:]}
    return {"file": str(p), "ok": res.get("ok"), "errors": res.get("errors"),
            "checks": {c["id"]: c.get("ok") for c in res.get("checks") or []}}


def main(argv):
    for a in argv:
        r = check_one(Path(a))
        print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
