# -*- coding: utf-8 -*-
"""校验 SKILL.md / 工程说明里的示例输入路径是否存在。

只检查含目录的显式路径（如 examples/orders.csv），跳过 <占位符>、纯文件名、
URL、通配符和运行期生成的 workspace/ 路径。退出码 1 = 有缺失。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
PAT = re.compile(r"--(?:input|data|series|semantic)\s+([A-Za-z0-9_./\\-]+\.(?:csv|json|xml|txt))")
SKIP = re.compile(r"[<>*$]|^https?://|^[A-Za-z]:\\")


def docs() -> list[tuple[Path, Path]]:
    out = []
    for role in sorted(TEAM.glob("r[0-9][0-9]-*")):
        for rel in ("SKILL.md", "references/engineering-notes.md"):
            p = role / rel
            if p.is_file():
                out.append((p, role))
    for name in ("README.md", "使用指南.md"):
        p = TEAM / name
        if p.is_file():
            out.append((p, TEAM))
    return out


def main() -> int:
    missing = []
    for path, base in docs():
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in PAT.finditer(line):
                raw = m.group(1).replace("\\", "/")
                if SKIP.search(raw) or "/" not in raw:
                    continue
                if raw.startswith("workspace/"):
                    continue  # 运行期生成，不作为固定夹具
                cands = [base / raw, TEAM / raw] + list(TEAM.glob(f"*/{raw}"))
                if any(c.exists() for c in cands):
                    continue
                missing.append((path.relative_to(TEAM), i, raw))
    if missing:
        print(f"缺失示例文件 {len(missing)} 处：")
        for p, i, raw in missing:
            print(f"  {p}:{i}  {raw}")
        return 1
    print(f"示例路径校验通过：{len(docs())} 份文档，无缺失")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
