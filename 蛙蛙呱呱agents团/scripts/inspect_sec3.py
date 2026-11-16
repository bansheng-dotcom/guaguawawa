# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.loads(Path(r"D:\蛙蛙呱呱\workspace\sec_report\data\aapl_companyfacts.json").read_text(encoding="utf-8"))
tags = d["facts"]["us-gaap"]
for tag in ["RevenueFromContractWithCustomerExcludingAssessedTax", "NetIncomeLoss", "NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment", "CashAndCashEquivalentsAtCarryingValue"]:
    print("\n===", tag, "===")
    for e in tags[tag]["units"]["USD"][-8:]:
        print({k: e.get(k) for k in ("start","end","val","accn","fy","fp","form","frame")})
