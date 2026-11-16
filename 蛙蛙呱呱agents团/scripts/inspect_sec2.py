# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.loads(Path(r"D:\蛙蛙呱呱\workspace\sec_report\data\aapl_companyfacts.json").read_text(encoding="utf-8"))
tags = d["facts"]["us-gaap"]
for k in sorted(tags):
    kl = k.lower()
    if any(s in kl for s in ["revenue", "netincome", "operatingincome", "cashprovidedbyusedinoperating", "paymentstoacquireproperty", "dividend", "repurchase", "cashandcashequivalentsatcarrying", "longtermdebt", "commercialpaper", "stockholdersequity", "assets", "liabilities", "incometaxexpense", "grossprofit", "costofrevenue"]):
        units = list(tags[k]["units"].keys())
        print(k, units, len(tags[k]["units"][units[0]]))
