#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「蛙蛙呱呱agents团」打成可分发的 zip（可重复执行）。

规则：
    * 排除生成物：workspace/、__pycache__/、.pytest_cache/、*.pyc、*.log；
    * 保留：agent-packs、docs、configs、scripts、shared、core、20 个角色目录；
    * 压缩包里额外写一份 PACKAGE_INFO.json（版本、时间、git commit、文件数）。

用法：
    python scripts/make_package.py
    python scripts/make_package.py --out D:/dist/guagua.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent                      # 蛙蛙呱呱agents团/
ROOT = TEAM.parent                      # 仓库根
DEFAULT_OUT = ROOT / "蛙蛙呱呱agents团.zip"

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                "workspace", ".git", ".venv", "node_modules"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".log", ".tmp", ".swp", ".zip")


def git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def build(out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    count = 0
    raw = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dirpath, dirnames, filenames in os.walk(TEAM):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
            for fn in sorted(filenames):
                if fn in EXCLUDE_NAMES or fn.endswith(EXCLUDE_SUFFIX):
                    continue
                p = Path(dirpath) / fn
                try:
                    if p.stat().st_size > 80 * 1024 * 1024:   # 单文件超过 80MB 跳过
                        continue
                except OSError:
                    continue
                z.write(p, p.relative_to(ROOT).as_posix())
                count += 1
                raw += p.stat().st_size
        info = {
            "name": TEAM.name,
            "packed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "git_commit": git_commit(),
            "files": count,
            "raw_bytes": raw,
            "note": "workspace/ 等生成物未打包；解压后直接 python guagua.py check",
        }
        z.writestr("PACKAGE_INFO.json", json.dumps(info, ensure_ascii=False, indent=2))
    tmp.replace(out)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    return {"path": str(out), "files": count,
            "raw_mb": round(raw / 1024 / 1024, 1),
            "zip_mb": round(out.stat().st_size / 1024 / 1024, 1),
            "sha256_16": sha}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="打包蛙蛙呱呱agents团")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    res = build(Path(args.out))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
