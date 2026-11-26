# -*- coding: utf-8 -*-
"""报告产线隐私扫描：凭据/个人信息不得进入 claims、manifest、报告。

为什么单独一条门禁：
    `check_project_boundary.py` 只保证「团内没有项目资产」，
    不检查项目资产里有没有密钥、手机号、身份证、Cookie、登录态。
    这类泄漏一旦写进 claims/manifest，会被渲染进 HTML 并被分发。

判据（高置信、低误报）：
    - 常见密钥前缀：sk- / AKIA / ghp_ / xox[baprs]-
    - 键值对：password/passwd/secret/token/api_key/cookie = 六个字符以上
    - 中国大陆手机号、18 位身份证
    - 占位符（***、<...>、${...}、your_、example）自动放行

用法：
    python scripts/check_report_privacy.py <文件或目录> [...]
    python scripts/check_report_privacy.py            # 默认扫 <repo>/../projects
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

SKIP_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf", ".zip", ".xlsx",
            ".xls", ".csv", ".woff", ".woff2", ".ttf", ".ico", ".svg"}

PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("密钥前缀", re.compile(r"\b(?:sk-[A-Za-z0-9_\-]{16,}|AKIA[0-9A-Z]{16}"
                            r"|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,})\b")),
    ("键值对", re.compile(r"(?i)\b(?:password|passwd|pwd|secret|token|api[_\-]?key"
                          r"|access[_\-]?key|cookie|authorization)\b\s*[:=]\s*"
                          r"[\"']?([^\s\"',:}]{6,})")),
    ("手机号", re.compile(r"(?<![\d.])1[3-9]\d{9}(?![\d.])")),
    ("身份证", re.compile(r"(?<![\d.])\d{17}[\dXx](?![\d.])")),
)

ALLOW = ("***", "****", "<", "${", "your_", "your-", "example", "xxx",
         "changeme", "placeholder", "none", "null", "env:")


def _allowed(value: str) -> bool:
    v = value.strip().lower()
    if not v:
        return True
    if any(a in v for a in ALLOW):
        return True
    # 占位手机号/编号：数字种类 <=2（如 13000000000、11111111111）
    digits = [c for c in v if c.isdigit()]
    return bool(digits) and len(set(digits)) <= 2


def scan_text(text: str) -> List[Tuple[str, int, str]]:
    hits: List[Tuple[str, int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, pat in PATTERNS:
            for m in pat.finditer(line):
                sample = m.group(1) if m.groups() else m.group(0)
                if _allowed(sample):
                    continue
                hits.append((name, lineno, m.group(0)[:40]))
    return hits


def _iter_files(targets: Iterable[Path]) -> Iterable[Path]:
    for t in targets:
        if t.is_file():
            yield t
        elif t.is_dir():
            for p in t.rglob("*"):
                if not p.is_file() or p.suffix.lower() in SKIP_EXT:
                    continue
                if p.name in ("raw.json",) or {"data", "runtime-data"} & set(p.parts):
                    continue
                yield p


REPORT_ASSETS = ("out/claims_merged.json", "out/report/report.html",
                 "out/report/report.md", "out/report/manifest.json")


def _report_assets(targets: Iterable[Path]) -> Iterable[Path]:
    for t in targets:
        base = Path(t)
        for rel in REPORT_ASSETS:
            p = base / rel
            if p.is_file():
                yield p
        for p in (base / "cards").rglob("claims.json"):
            if p.is_file():
                yield p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--report-assets", action="store_true",
                    help="只扫报告资产（claims/报告/manifest），不扫原始数据")
    a = ap.parse_args(argv)
    targets = [Path(x) for x in a.paths] or [ROOT.parent / "projects"]
    gen = _report_assets(targets) if a.report_assets else _iter_files(targets)
    files = [p for p in gen if p.exists()]
    bad = 0
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(text) > 3_000_000:
            continue
        hits = scan_text(text)
        if not hits:
            continue
        bad += len(hits)
        for name, lineno, sample in hits[:5]:
            print(f"[privacy] {p}:{lineno} {name} :: {sample}")
    if bad:
        print(f"[privacy] FAIL 命中 {bad} 处；凭据/个人信息不得进入报告资产")
        return 1
    if not a.quiet:
        print(f"[privacy] PASS 扫描 {len(files)} 个文件，无高置信泄漏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
