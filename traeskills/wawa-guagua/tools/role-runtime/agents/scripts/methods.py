# -*- coding: utf-8 -*-
"""方法库 CLI：把「20 角色深度地图」里的方法做成可跑命令。

用法：
  python scripts/methods.py matched --treat a.csv --control b.csv --col price
  python scripts/methods.py did --input did.csv --y sales --treat treated --post post
  python scripts/methods.py elasticity --input e.csv --price price --qty qty
  python scripts/methods.py mmm --input m.csv --y sales --channels tv,search,social
  python scripts/methods.py rdd --input r.csv --y score --running x --cutoff 60
  python scripts/methods.py fulfill --demand 100 --sd 20 --lead 3 --capacity 500
  python scripts/methods.py safety-stock --sigma 2 --lead 9
  python scripts/methods.py ltv-cac --arpu 60 --gm 0.3 --churn 0.05 --cac 120
  python scripts/methods.py runway --cash 3000000 --burn 550000
  python scripts/methods.py little --arrival 200 --cycle 1.2
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.methods import advanced, core  # noqa: E402


def col(path: str, name: str) -> list[float]:
    with open(path, encoding="utf-8-sig") as fh:
        return [float(r[name]) for r in csv.DictReader(fh) if r.get(name) not in (None, "")]


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("matched")
    m.add_argument("--treat", required=True)
    m.add_argument("--control", required=True)
    m.add_argument("--col", required=True)

    d = sub.add_parser("did")
    d.add_argument("--input", required=True)
    d.add_argument("--y", required=True)
    d.add_argument("--treat", required=True)
    d.add_argument("--post", required=True)

    e = sub.add_parser("elasticity")
    e.add_argument("--input", required=True)
    e.add_argument("--price", required=True)
    e.add_argument("--qty", required=True)

    mm = sub.add_parser("mmm")
    mm.add_argument("--input", required=True)
    mm.add_argument("--y", required=True)
    mm.add_argument("--channels", required=True, help="逗号分隔的渠道列")

    r = sub.add_parser("rdd")
    r.add_argument("--input", required=True)
    r.add_argument("--y", required=True)
    r.add_argument("--running", required=True)
    r.add_argument("--cutoff", type=float, required=True)
    r.add_argument("--bandwidth", type=float, default=None)

    f = sub.add_parser("fulfill")
    f.add_argument("--demand", type=float, required=True)
    f.add_argument("--sd", type=float, required=True)
    f.add_argument("--lead", type=float, required=True)
    f.add_argument("--capacity", type=float, required=True)
    f.add_argument("--days", type=int, default=30)
    f.add_argument("--sims", type=int, default=1000)

    s = sub.add_parser("safety-stock")
    s.add_argument("--sigma", type=float, required=True)
    s.add_argument("--lead", type=float, required=True)
    s.add_argument("--z", type=float, default=1.65)

    l = sub.add_parser("ltv-cac")
    l.add_argument("--arpu", type=float, required=True)
    l.add_argument("--gm", type=float, required=True)
    l.add_argument("--churn", type=float, required=True)
    l.add_argument("--cac", type=float, required=True)

    w = sub.add_parser("runway")
    w.add_argument("--cash", type=float, required=True)
    w.add_argument("--burn", type=float, required=True)
    w.add_argument("--growth", type=float, default=0.0)

    li = sub.add_parser("little")
    li.add_argument("--arrival", type=float, required=True)
    li.add_argument("--cycle", type=float, required=True)

    ns = ap.parse_args()
    if ns.cmd == "matched":
        out = core.matched_diff(col(ns.treat, ns.col), col(ns.control, ns.col))
    elif ns.cmd == "did":
        with open(ns.input, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        out = core.did([float(r[ns.y]) for r in rows],
                       [int(r[ns.treat]) for r in rows], [int(r[ns.post]) for r in rows])
    elif ns.cmd == "elasticity":
        out = core.elasticity(col(ns.input, ns.price), col(ns.input, ns.qty))
    elif ns.cmd == "mmm":
        chans = [c.strip() for c in ns.channels.split(",") if c.strip()]
        with open(ns.input, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        y = [float(r[ns.y]) for r in rows]
        X = [[float(r[c]) for c in chans] for r in rows]
        out = advanced.mmm(X, y, chans)
    elif ns.cmd == "rdd":
        with open(ns.input, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        out = advanced.rdd([float(r[ns.y]) for r in rows],
                           [float(r[ns.running]) for r in rows], ns.cutoff, ns.bandwidth)
    elif ns.cmd == "fulfill":
        out = advanced.fulfillment_sim(ns.demand, ns.sd, ns.lead, ns.capacity, ns.days, ns.sims)
    elif ns.cmd == "safety-stock":
        out = core.safety_stock(ns.sigma, ns.lead, ns.z)
    elif ns.cmd == "ltv-cac":
        out = core.ltv_cac(ns.arpu, ns.gm, ns.churn, ns.cac)
    elif ns.cmd == "runway":
        out = core.runway(ns.cash, ns.burn, ns.growth)
    else:
        out = core.littles_law(ns.arrival, ns.cycle)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
