# -*- coding: utf-8 -*-
import json
from pathlib import Path

p = Path(r"D:\蛙蛙呱呱\workspace\sec_report\data\aapl_companyfacts.json")
d = json.loads(p.read_text(encoding="utf-8"))
print(d.keys())
print(d["entityName"], d["cik"])
print(list(d["facts"].keys()))
for ns in ("us-gaap",):
    tags = d["facts"][ns]
    keys = [k for k in tags if any(s in k.lower() for s in ["revenue", "sales", "netincome", "operatingincome", "cashprovidedbyusedinoperating", "paymentstoacquireproperty", "dividend", "repurchase", "cashandcashequivalentsatcarrying", "longtermdebt", "commercialpaper", "stockholdersequity", "assets", "liabilities"])]
    print(len(keys))
    for k in keys[:80]:
        print(k)
