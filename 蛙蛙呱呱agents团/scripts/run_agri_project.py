# -*- coding: utf-8 -*-
"""真实项目：内蒙古肉蛋 + 蔬菜 市场调研（r05 真实技能 → 内核三层 → L2/L3）。

跑法：python scripts/run_agri_project.py
产物：projects/agri_2026q4/out/{meat_egg,veggie}_report.html + L2 + L3
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import report_bridge, report_renderer  # noqa: E402
from core.report_kernel import aggregate, layers, spec as kspec  # noqa: E402

MEAT_LEDGER = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12\data\证据台账_底稿.json")
MEAT_CSV = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12\底稿版\data_daily.csv")
VEG_LEDGER = Path(r"D:\蛙蛙呱呱\内蒙古蔬菜调研_2026-11-11\data\证据台账_veggie_ledger.json")
VEG_CSV = Path(r"D:\蛙蛙呱呱\内蒙古蔬菜调研_2026-11-11\data\品类四周明细_乌兰察布15种蔬菜.csv")

OUT = ROOT / "projects" / "agri_2026q4"


def run_skill(*args: str) -> dict:
    p = subprocess.run([sys.executable, "guagua.py", "call", "r05", *args],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    mark = "__AGENT_RESULT__ "
    for line in (p.stdout or "").splitlines():
        if line.startswith(mark):
            return json.loads(line[len(mark):])
    raise RuntimeError(f"skill 无输出: {' '.join(args)}\n{(p.stderr or '')[:300]}")


def meat_dataset() -> list[dict]:
    rows = []
    for r in csv.DictReader(MEAT_CSV.open(encoding="utf-8-sig")):
        for item, val in r.items():
            if item == "date" or not val:
                continue
            rows.append({"date": r["date"][:10], "item": item, "value": float(val),
                         "unit": "元/公斤", "source": "farm_daily"})
    return rows


def veg_dataset() -> list[dict]:
    weeks = ["2026-10-15", "2026-10-22", "2026-10-29", "2026-11-05"]
    rows = []
    for r in csv.DictReader(VEG_CSV.open(encoding="utf-8-sig")):
        for i, w in enumerate(["10月第三周", "10月第四周", "10月第五周", "11月第一周"]):
            v = (r.get(w) or "").strip()
            if not v:
                continue
            try:
                val = float(v)
            except ValueError:
                continue
            rows.append({"date": weeks[i], "item": r["品种"], "value": val,
                         "unit": "元/斤", "source": "nmg_veg"})
    return rows


def build_one(role: str, title: str, ledger: Path, dataset: list[dict], outdir: Path):
    res = run_skill("research", "report", "--input", str(ledger))
    s = kspec.load(role)
    contract, fid = layers.build_contract(role, "蛙深远", title, res, s,
                                          "research", "report", title, dataset=dataset)
    verrs = report_renderer.validate_contract(contract)
    serrs = layers.spec_compliance(contract, s)
    report_bridge.render_html(contract, str(outdir / f"{title}.html"))
    report_bridge.write_markdown(contract, str(outdir / f"{title}.md"))
    print(f"  L1 {title}: sections={len(contract['sections'])} "
          f"obs={fid.get('obs_total')} retention={fid.get('retention')} "
          f"contract_errs={len(verrs)} spec_errs={len(serrs)}")
    return {"role": role, "title": title, "contract": contract, "fid": fid, "spec_errors": serrs}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    outdir = OUT / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    items = []
    spec_errors = {}
    for title, ledger, ds in (("肉蛋市场调研", MEAT_LEDGER, None),
                              ("蔬菜市场调研", VEG_LEDGER, None)):
        data = meat_dataset() if "肉蛋" in title else veg_dataset()
        item = build_one("r05", title, ledger, data, outdir)
        items.append(item)
        spec_errors[f"r05#{title}"] = item["spec_errors"]

    l2 = aggregate.build_l2("agri_2026q4", items)
    report_bridge.render_html(l2, str(outdir / "L2_report.html"))
    report_bridge.write_markdown(l2, str(outdir / "L2_report.md"))
    l3 = aggregate.build_l3("agri_2026q4", l2, spec_errors)
    report_bridge.render_html(l3, str(outdir / "L3_review.html"))
    report_bridge.write_markdown(l3, str(outdir / "L3_review.md"))

    man = {"project": "agri_2026q4",
           "l1": [{"role": i["role"], "title": i["title"], "fid": i["fid"],
                   "spec_errors": i["spec_errors"]} for i in items]}
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"l1": len(items), "spec_fail": sum(1 for v in spec_errors.values() if v)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
