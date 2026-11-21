# -*- coding: utf-8 -*-
"""accepted 只是接单；填格后必须变 delivered。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import card_upgrade as cu  # noqa: E402


def test_reconcile_accepted_to_delivered():
    rows = [{"cell_id": "c1", "status": "filled"},
            {"cell_id": "c2", "status": "open"}]
    reqs = [{"request_id": "R1", "cell_id": "c1", "status": "accepted",
             "elapsed_min": 30},
            {"request_id": "R2", "cell_id": "c2", "status": "accepted",
             "elapsed_min": 30}]
    out = cu.reconcile_requests(reqs, rows)
    assert out[0]["status"] == "delivered" and out[0]["fulfilled"] is True
    assert out[1]["status"] == "accepted" and not out[1].get("fulfilled")
