#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""禁止在代码里私自接外部生图接口。

规则（来自用户口径）：
    * 默认走提示词路线（imagegen compose / prompt_pack），不自动调外部生图 API；
    * 要接某个外部接口，必须由用户明确指定并给 Key，再单独接；
    * 因此仓库代码里**不允许**出现 text_to_image / trae-api 这类端点字符串，
      出现即视为「绕过提示词路线去偷接接口」。

扫描范围：蛙蛙呱呱agents团 下所有 .py（跳过 scripts/ 本脚本与 docs/）。
退出码：0 干净 / 1 发现违规。
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKIP_DIRS = {"workspace", "__pycache__", ".pytest_cache", "agent-packs"}

# 只在「真的带 URL」时算违规：注释里提到端点名不算私接
PATTERNS = [
    re.compile(r"https?://[^\s\"']*text_to_image", re.I),
    re.compile(r"https?://[^\s\"']*mchost\.guru", re.I),
    re.compile(r"https?://[^\s\"']*trae-api", re.I),
    re.compile(r"https?://[^\s\"']*api/ide/v1/text", re.I),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(base, fn)
            if os.path.abspath(path) == os.path.abspath(__file__):
                continue
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if any(p.search(line) for p in PATTERNS):
                    hits.append((os.path.relpath(path, ROOT), i, line.strip()[:90]))

    print("外部生图接口私接检查（默认只走提示词）")
    print("=" * 66)
    print(f"扫描 .py 完成｜违规 {len(hits)}")
    for f, ln, txt in hits:
        print(f"  [违规] {f}:{ln}  {txt}")
    if hits:
        print("\n修复：默认走 imagegen compose / prompt_pack；"
              "要接外部接口必须由用户明确指定并单独接入。")
        return 1
    print("\n[OK] 代码中没有私接外部生图接口")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
