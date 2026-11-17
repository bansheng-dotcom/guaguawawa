# -*- coding: utf-8 -*-
"""结果台账（P6）回归测试。"""
from __future__ import annotations

from core import outcome_ledger as ol


def test_add_list_review_summary(tmp_path):
    p = tmp_path / "ledger.json"
    e = ol.add("RPT-1", "structure", "6 涨 6 跌", "哪些品类继续做",
               "2026-12-31", path=p)
    assert e["status"] == "open"
    assert len(ol.list_entries(path=p)) == 1

    # 同一 report/claim 的 open 不重复登记
    e2 = ol.add("RPT-1", "structure", "6 涨 6 跌", "哪些品类继续做",
                "2026-12-31", path=p)
    assert e2["id"] == e["id"]
    assert len(ol.list_entries(path=p)) == 1

    ol.review(e["id"], "hit", "复盘：方向一致", path=p)
    assert ol.list_entries(path=p)[0]["status"] == "hit"
    s = ol.summary(path=p, today="2026-12-01")
    assert s["total"] == 1 and s["hit"] == 1 and s["hit_rate"] == 1.0


def test_overdue_and_due_soon(tmp_path):
    p = tmp_path / "ledger.json"
    ol.add("RPT-1", "a", "A", "D", "2026-11-01", path=p)
    ol.add("RPT-1", "b", "B", "D", "2026-12-10", path=p)
    s = ol.summary(path=p, today="2026-12-01")
    assert s["overdue"] == 1
    assert s["due_soon"] == 1


def test_seed_from_trace(tmp_path):
    p = tmp_path / "ledger.json"
    trace = {"findings": [{"key": "structure", "title": "结构判断"},
                          {"key": "economics", "title": "单位经济"}]}
    seeded = ol.seed_from_trace("RPT-1", "经营分析", trace,
                                deadline="2026-12-31", path=p)
    assert len(seeded) == 2
    assert len(ol.list_entries(path=p)) == 2


def test_review_requires_result(tmp_path):
    p = tmp_path / "ledger.json"
    e = ol.add("RPT-1", "a", "A", "D", "2026-12-31", path=p)
    try:
        ol.review(e["id"], "hit", "", path=p)
    except ValueError as exc:
        assert "result" in str(exc)
    else:
        raise AssertionError("空 result 应报错")


def test_hit_rate_with_hit_miss_void(tmp_path):
    """不等 2027：合成 hit/miss/void，验证命中率分母排除 void。"""
    p = tmp_path / "ledger.json"
    a = ol.add("RPT-1", "a", "A", "D", "2026-12-31", path=p)
    b = ol.add("RPT-1", "b", "B", "D", "2026-12-31", path=p)
    c = ol.add("RPT-1", "c", "C", "D", "2026-12-31", path=p)
    ol.review(a["id"], "hit", "方向一致", path=p)
    ol.review(b["id"], "miss", "方向反了", path=p)
    ol.review(c["id"], "void", "口径变了", path=p)
    s = ol.summary(path=p, today="2026-12-01")
    assert s["hit"] == 1 and s["miss"] == 1 and s["void"] == 1
    assert s["hit_rate"] == 0.5
