# -*- coding: utf-8 -*-
"""charts_pro 门禁：每型都有样例、都能渲染、别名可解析。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.report_theme.charts_pro import spec
from samples import samples  # noqa: E402


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
    # P4-2 / V-1：REQUIRED 与 SAMPLE 必须同源，漂移即失败
    from core.charts import chart_field_contract as _cs
    audit = _cs.contract_audit(samples.SAMPLE)
    from core.report_theme import tokens as _tk
    tbad = _tk.verify_defaults_match_renderer()
    print(f"kinds {len(kinds)} | samples {len(samples.SAMPLE)} | aliases {len(spec.ALIASES)}"
          f" | contract {'OK' if audit['ok'] else 'DRIFT'}"
          f" | tokens {'OK' if not tbad else 'DRIFT'}")
    if tbad:
        print("token drift:", tbad[:3])
    if not audit["ok"]:
        print("contract mismatch:", audit["mismatch"][:5])
    if missing:
        print("missing samples:", missing)
    if bad:
        print("render failures:", bad[:5])
    if alias_bad:
        print("bad aliases:", alias_bad[:5])
    return 0 if not (missing or bad or alias_bad or not audit["ok"] or tbad) else 1


if __name__ == "__main__":
    raise SystemExit(main())
