# -*- coding: utf-8 -*-
"""把 Trae / WorkBuddy 技能目录打成可分发的 zip。

排除运行期与缓存：workspace、repo_python_xuexi、projects、__pycache__、
.pytest_cache、.cache、.git、node_modules、*.pyc、*.log、*.zip。

用法：
  python scripts/package_skill_targets.py
  python scripts/package_skill_targets.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import zipfile
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱")
DIST = ROOT / "dist"

TARGETS = [
    ("wawa-guagua-trae-skill.zip", "wawa-guagua",
     ROOT / "traeskills" / "wawa-guagua"),
    ("wawa-company-os-workbuddy.zip", "wawa-company-os",
     ROOT / "workbuddy专家团" / "wawa-company-os"),
]

EXCLUDE_DIRS = {"workspace", "repo_python_xuexi", "projects", "__pycache__",
                ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache",
                ".git", ".venv", "node_modules", "real_check"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".log", ".tmp", ".swp", ".zip")


def commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def build(src: Path, out: Path, name: str) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    count = raw = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(src)
            if any(part in EXCLUDE_DIRS for part in rel.parts[:-1]):
                continue
            if p.name in {".DS_Store", "Thumbs.db"} or p.suffix in EXCLUDE_SUFFIX:
                continue
            z.write(p, f"{name}/{rel.as_posix()}")
            count += 1
            raw += p.stat().st_size
        info = {"name": name, "packed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "git_commit": commit(), "files": count,
                "note": "workspace/repo_python_xuexi 等运行期目录未打包"}
        z.writestr(f"{name}/PACKAGE_INFO.json",
                   json.dumps(info, ensure_ascii=False, indent=2))
    tmp.replace(out)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    return {"path": str(out), "files": count,
            "raw_mb": round(raw / 1024 / 1024, 1),
            "zip_mb": round(out.stat().st_size / 1024 / 1024, 1),
            "sha256_16": sha}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    for filename, name, src in TARGETS:
        if not src.exists():
            print(f"[skip] {name}: 源不存在 {src}")
            continue
        if args.check:
            print(f"[check] {name}: {src}")
            continue
        r = build(src, DIST / filename, name)
        print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
