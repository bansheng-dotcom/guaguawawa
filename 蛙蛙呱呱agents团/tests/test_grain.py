# -*- coding: utf-8 -*-
"""test_grain —— 采集层 v3（S0–S6）：源画像 / 粒度校验 / rollup / 三业务回归。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import collection_spec as cs  # noqa: E402
from core import grain as g  # noqa: E402
from core import source_profile as sp  # noqa: E402


def _src(**kw):
    base = {
        "schema": sp.SCHEMA, "id": "s1", "kind": "csv_manual",
        "atomic_grain": ["row_id"], "history": "historical",
        "fields": [
            {"name": "row_id", "type": "string"},
            {"name": "snapshot_date", "type": "date"},
            {"name": "title", "type": "string"},
            {"name": "price", "type": "number"},
            {"name": "volume", "type": "number"},
        ],
    }
    base.update(kw)
    return base


def _rollup(**kw):
    base = {
        "id": "r1",
        "grain": ["brand", "month"],
        "derive": {"brand": "token:title:0", "month": "substr:snapshot_date:0:7"},
        "measures": {"asp": {"agg": "mean", "expr": "price"}},
    }
    base.update(kw)
    return base


# ---------------- S0 源画像 ----------------

def test_source_valid():
    assert sp.validate(_src()) == []


def test_source_requires_atomic_grain():
    assert any("atomic_grain" in e for e in sp.validate(_src(atomic_grain=[])))


def test_source_history_enum():
    assert any("history" in e for e in sp.validate(_src(history="whatever")))


def test_source_field_type():
    s = _src()
    s["fields"][0]["type"] = "nope"
    assert any("type" in e for e in sp.validate(s))


def test_source_atomic_grain_must_be_field():
    assert any("不在 fields" in e for e in sp.validate(_src(atomic_grain=["nope"])))


# ---------------- S1 粒度校验 ----------------

def test_grain_ok():
    assert g.check(_src(), _rollup()) == []


def test_grain_g_a_missing_atomic():
    errs = g.check(_src(atomic_grain=[]), _rollup())
    assert any("G-A" in e for e in errs)


def test_grain_g_b_undeducible():
    r = _rollup(grain=["brand", "unknown_dim"])
    assert any("G-B" in e for e in g.check(_src(), r))


def test_grain_g_c_bad_expr_column():
    r = _rollup(measures={"asp": {"agg": "mean", "expr": "nope"}})
    assert any("G-C" in e for e in g.check(_src(), r))


def test_grain_g_d_missing_grain():
    r = _rollup(grain=[])
    assert any("G-D" in e for e in g.check(_src(), r))


def test_grain_g_e_needs_history():
    # 源只能采当下 + rollup 要序列 → 必须被拦
    errs = g.check(_src(history="snapshot_only"), _rollup(series=True))
    assert any("G-E" in e for e in errs)


def test_grain_g_e_ok_with_history():
    assert g.check(_src(history="historical"), _rollup(series=True)) == []


# ---------------- S1 rollup 运算 ----------------

def _rows():
    return [
        {"row_id": "1", "snapshot_date": "2025-01-15", "title": "AAA 脚垫",
         "price": 100, "volume": 2},
        {"row_id": "2", "snapshot_date": "2025-01-20", "title": "AAA 脚垫",
         "price": 200, "volume": 3},
        {"row_id": "3", "snapshot_date": "2025-02-10", "title": "BBB 脚垫",
         "price": 150, "volume": 1},
    ]


def test_rollup_rows_mean_sum():
    out = g.rollup_rows(_rows(), _rollup())
    by = {(r["brand"], r["month"]): r for r in out}
    assert by[("AAA", "2025-01")]["asp"] == 150.0
    assert by[("AAA", "2025-01")]["_rows"] == 2
    assert by[("BBB", "2025-02")]["asp"] == 150.0


def test_rollup_rows_arithmetic_expr():
    r = _rollup(measures={"revenue": {"agg": "sum", "expr": "price * volume"}})
    out = g.rollup_rows(_rows(), r)
    by = {(x["brand"], x["month"]): x for x in out}
    assert by[("AAA", "2025-01")]["revenue"] == 800.0


def test_rollup_bucket():
    r = _rollup(grain=["price_band", "month"],
                derive={"price_band": "bucket:price:120,180:低,中,高",
                        "month": "substr:snapshot_date:0:7"})
    out = g.rollup_rows(_rows(), r)
    assert {x["price_band"] for x in out} == {"低", "中", "高"}


def test_safe_eval_rejects_calls():
    try:
        g._safe_eval("__import__('os').system('x')", {})
    except Exception:
        return
    raise AssertionError("应该拒绝函数调用")


# ---------------- S3 采集规格 + S6 三业务回归 ----------------

def test_three_businesses_same_code():
    """同一套代码，三套 YAML，都合法——这就是「适配各种业务」的证据。

    业务 YAML 放在 tests/fixtures/，**不进 configs/**：
    源码里不许有业务线，业务只活在项目目录（或测试夹具）里。
    """
    for name in ("auto_interior", "demo_maternal", "demo_vegetable"):
        spec = cs.load(str(ROOT / "tests" / "fixtures" / "collections"
                           / (name + ".yaml")))
        assert spec, name
        errs = cs.validate(spec)
        assert not errs, (name, errs)


def test_spec_rejects_unknown_dataset():
    spec = {
        "schema": cs.SCHEMA, "id": "x", "source": "manual_csv",
        "query": {"path": "a.csv"},
        "rollups": [_rollup()],
        "claims": [{"id": "c1", "dataset": "nope",
                    "query": {"group_by": ["brand"], "metrics": ["asp"]},
                    "min_rows": 5}],
    }
    assert any("不在 rollups" in e for e in cs.validate(spec, _src()))


def test_spec_rejects_bad_claim_query():
    spec = {
        "schema": cs.SCHEMA, "id": "x", "source": "manual_csv",
        "query": {"path": "a.csv"},
        "rollups": [_rollup()],
        "claims": [{"id": "c1", "dataset": "r1",
                    "query": {"group_by": ["nope"], "metrics": ["asp"]},
                    "min_rows": 5}],
    }
    assert any("group_by" in e for e in cs.validate(spec, _src()))
