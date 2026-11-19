#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三方许可状态门禁。

背景：
    `r10-wachengmei-design/references/design-library/` 有 31 份公开设计系统的
    事实性摘录，`vendor/aihive/imagegen.py` 是上游客户端脚本的本地适配。
    它们能不能随包分发，取决于上游许可——目前全部登记为 `unknown`。

用法：
    python scripts/check_third_party_licenses.py            # 出状态报告（默认不阻塞）
    python scripts/check_third_party_licenses.py --strict   # 有 unknown 即退出 1（打包/分发前用）
    python scripts/check_third_party_licenses.py --json

清单：r10-wachengmei-design/references/design-library/LICENSE_STATUS.json
说明：THIRD_PARTY_NOTICES.md 是给人看的摘要，本清单是给机器看的唯一状态源。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVENTORY = os.path.join(ROOT, "r10-wachengmei-design", "references",
                         "design-library", "LICENSE_STATUS.json")


def load():
    if not os.path.isfile(INVENTORY):
        return None
    with open(INVENTORY, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_third_party_licenses")
    ap.add_argument("--strict", action="store_true",
                    help="存在 unknown / 不可再分发条目时退出 1")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    data = load()
    if data is None:
        print(f"[FAIL] 找不到清单：{INVENTORY}", file=sys.stderr)
        return 2

    entries = data.get("entries", [])
    unknown = [e for e in entries if str(e.get("license", "")).lower() in ("", "unknown")]
    blocked = [e for e in entries if not e.get("redistributable", False)]
    missing_url = [e for e in entries if not e.get("upstream_url")]

    if args.json:
        print(json.dumps({"total": len(entries), "unknown": len(unknown),
                          "not_redistributable": len(blocked),
                          "missing_upstream_url": len(missing_url),
                          "entries": entries}, ensure_ascii=False, indent=2))
        return 1 if (args.strict and (unknown or blocked)) else 0

    print("第三方许可状态（清单：" +
          os.path.relpath(INVENTORY, ROOT).replace(os.sep, "/") + "）")
    print("=" * 74)
    print(f"登记 {len(entries)} 项｜许可未知 {len(unknown)} 项｜"
          f"不可再分发 {len(blocked)} 项｜缺上游 URL {len(missing_url)} 项")
    for e in entries[:8]:
        print(f"  - {e.get('file')}: license={e.get('license')} "
              f"url={e.get('upstream_url') or '—'}")
    if len(entries) > 8:
        print(f"  … 其余 {len(entries) - 8} 项见清单")
    if unknown or blocked:
        print("\n[WARN] 存在许可未确认资产：可以内部使用，**不得进入对外分发包**。")
        print("       打包前：补齐 upstream_url 与 license，或从分发包排除。")
    if args.strict and (unknown or blocked):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
