# -*- coding: utf-8 -*-
"""charts_pro 门禁：每型都有样例、都能渲染、别名可解析。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.report_theme.charts_pro import spec
from core.report_theme.charts_pro.samples_data import samples  # noqa: E402


def main() -> int:
    kinds = set(spec.kinds())
    missing = sorted(kinds - set(samples.SAMPLE))
    bad = []
    for k in sorted(kinds):
        try:
            svg = spec.render({**samples.SAMPLE[k], "type": k})
            if "<svg" not in svg or "</svg>" not in svg:
                bad.append((k, "empty svg"))
        except Exception as e:  # noqa: BLE001
            bad.append((k, f"{type(e).__name__}: {e}"))
    alias_bad = []
    for a, target in spec.ALIASES.items():
        if target not in kinds:
            alias_bad.append((a, target))
    print(f"kinds {len(kinds)} | samples {len(samples.SAMPLE)} | aliases {len(spec.ALIASES)}")
    if missing:
        print("missing samples:", missing)
    if bad:
        print("render failures:", bad[:5])
    if alias_bad:
        print("bad aliases:", alias_bad[:5])
    return 0 if not (missing or bad or alias_bad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
