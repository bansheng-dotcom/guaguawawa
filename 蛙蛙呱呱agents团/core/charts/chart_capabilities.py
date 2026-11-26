# -*- coding: utf-8 -*-
"""core/chart_capabilities.py —— 48 型图表能力注册表。

不是“报告里用了几种就算几种”，而是核心必须完整持有 48 型：
- CHART_INDEX：48 个图型的 id/key/title/group/use_when；
- RENDERERS：48 个可调用渲染器；
- has_chart / render_chart：给选择器和报告层调用；
- check()：启动/CI 时验证 48/48，缺一即失败。

用法：
    python -m core.chart_capabilities --check
    python -m core.chart_capabilities --list
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

CHART_DIR = Path(__file__).resolve().parent
if str(CHART_DIR) not in sys.path:
    sys.path.insert(0, str(CHART_DIR))

import chart_lib  # noqa: E402

CATALOG: List[Dict[str, Any]] = list(chart_lib.CHART_INDEX)
RENDERERS: Dict[str, Any] = dict(chart_lib.RENDERERS)
EXPECTED = 48


def check() -> Dict[str, Any]:
    keys = {c["key"] for c in CATALOG}
    errors = []
    if len(CATALOG) != EXPECTED:
        errors.append(f"CHART_INDEX {len(CATALOG)}/{EXPECTED}")
    if len(RENDERERS) != EXPECTED:
        errors.append(f"RENDERERS {len(RENDERERS)}/{EXPECTED}")
    missing = sorted(keys - set(RENDERERS))
    extra = sorted(set(RENDERERS) - keys)
    if missing:
        errors.append("缺渲染器: " + ",".join(missing))
    if extra:
        errors.append("多渲染器: " + ",".join(extra))
    not_callable = sorted(k for k, v in RENDERERS.items() if not callable(v))
    if not_callable:
        errors.append("不可调用: " + ",".join(not_callable))
    return {"ok": not errors, "count": len(CATALOG), "renderers": len(RENDERERS),
            "errors": errors, "keys": sorted(keys)}


def has_chart(key: str) -> bool:
    return key in RENDERERS and callable(RENDERERS[key])


def render_chart(key: str, chart: Dict[str, Any]) -> str:
    if not has_chart(key):
        raise KeyError(f"未知图型: {key}")
    return RENDERERS[key](chart)


def catalog_json() -> str:
    return json.dumps({"count": len(CATALOG), "items": CATALOG}, ensure_ascii=False, indent=2)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    r = check()
    if a.list:
        print(catalog_json())
    else:
        print(json.dumps({k: v for k, v in r.items() if k != "keys"}, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
