# -*- coding: utf-8 -*-
"""R14 机制单测：交易状态机 + 幂等 + 对账。"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import commerce_fsm as cf  # noqa: E402


def test_three_chains_all_close():
    chains = cf.demo_chains()
    assert [c["chain"] for c in chains] == ["正常成交", "全额退款", "超时重放 + 非法企图"]
    assert all(c["ok"] for c in chains), chains
    assert all(c["status"] == "closed" for c in chains)
    codes = {v["code"] for v in chains[2]["violations"]}
    assert codes == {"T01_ILLEGAL_TRANSITION", "T03_DUPLICATE_CHARGE"}


def test_illegal_transition_rejected():
    book = cf.OrderBook()
    book.create("SO-X", "10.00")
    out = book.fulfill("SO-X", "f1")
    assert out["ok"] is False
    assert out["violations"][0]["code"] == "T01_ILLEGAL_TRANSITION"
    assert book.orders["SO-X"]["status"] == "created"


def test_idempotent_charge_never_double_charges():
    book = cf.OrderBook()
    book.create("SO-Y", "88.00")
    first = book.charge("SO-Y", "88.00", "pay-y")
    second = book.charge("SO-Y", "88.00", "pay-y")
    assert first["ok"] is True and first["charged"] == "88.00"
    assert second["ok"] is True and second["deduplicated"] is True
    assert second["charged"] == "0.00"


def test_same_key_different_amount_is_duplicate_charge():
    book = cf.OrderBook()
    book.create("SO-Z", "88.00")
    book.charge("SO-Z", "88.00", "pay-z")
    out = book.charge("SO-Z", "77.00", "pay-z")
    assert out["ok"] is False
    assert out["violations"][0]["code"] == "T03_DUPLICATE_CHARGE"


def test_missing_idempotency_key_rejected():
    book = cf.OrderBook()
    book.create("SO-K", "10.00")
    out = book.charge("SO-K", "10.00", "")
    assert out["ok"] is False
    assert out["violations"][0]["code"] == "T02_MISSING_IDEMPOTENCY_KEY"


def test_amount_mismatch_and_over_refund():
    book = cf.OrderBook()
    book.create("SO-A", "100.00")
    assert book.charge("SO-A", "90.00", "p1")["violations"][0]["code"] == "T04_AMOUNT_MISMATCH"
    book.charge("SO-A", "100.00", "p2")
    out = book.refund("SO-A", "120.00", "r1")
    assert out["ok"] is False
    assert out["violations"][0]["code"] == "T04_AMOUNT_MISMATCH"


def test_reconciliation_classifies_five_kinds():
    recon = cf.reconcile(cf.RECON_ORDERS, cf.RECON_PAYMENTS)
    assert recon["diff_total"] == 5
    assert recon["counts"] == {
        "R01_MISSING_PAYMENT": 1,
        "R02_ORPHAN_PAYMENT": 1,
        "R03_DUPLICATE_PAYMENT": 1,
        "R04_AMOUNT_MISMATCH": 1,
        "R05_STATUS_MISMATCH": 1,
    }
    assert recon["classes"]["R02_ORPHAN_PAYMENT"][0]["order_id"] == "SO-9999"
    clean = cf.reconcile(
        [{"order_id": "A", "amount": "10.00", "status": "paid"}],
        [{"payment_id": "P", "order_id": "A", "amount": "10.00", "status": "success"}])
    assert clean["ok"] is True and clean["diff_total"] == 0


def test_misuse_cases_are_rejected():
    for name in ("illegal-transition.json", "duplicate-charge.json"):
        out = cf.check_case(os.path.join(HERE, "misuse", name))
        assert out["rejected"] is True, name
        assert out["as_expected"] is True, (name, out["hit"], out["expect"])


def test_golden_html_contract():
    out = cf.build_goldens()
    assert out["ok"] is True
    for name in ("commerce-state-machine.html", "commerce-reconciliation.html"):
        html = open(os.path.join(HERE, "golden", name), encoding="utf-8").read()
        assert "@page" in html and "A4" in html
        assert 'data-theme="light"' in html
        assert html.count("<h1") == 1 and "<thead" in html
        assert "<br" not in html and "italic" not in html
