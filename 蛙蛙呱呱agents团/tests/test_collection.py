# -*- coding: utf-8 -*-
"""collection 域测试（合并自 6 个文件）。

源文件：
    test_collect_schema.py —— P2-5：collect schema --url → 草稿 + 试采 + 质量门。
    test_collection_contract.py —— test_collection_contract —— 采集契约单测。
    test_collectors.py —— test_collectors —— 采集器（离线夹具，不依赖网络）。
    test_ingest.py —— 采集六层：robots / 限速 / 重试 / 字节上限 / 分页 / 失败隔离 / staging 落盘。
    test_coverage_pipeline.py —— 覆盖自动化：TaskFrame / SourceLedger / CoveragePlan / 双门禁。
    test_coverage_wire.py —— test_coverage_wire —— 覆盖矩阵/饱和接进主链路的派生层。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from core import collect_schema
from core import collection_contract as cc
from core.collectors import base
import core.collectors
from core.collectors import web_search as ws
import time
from urllib.parse import parse_qs, urlsplit
from core import ingest
from core.ingest import policy as pol_mod
from core import coverage_plan
from core import coverage_wire


@pytest.fixture(autouse=True)
def _no_system_proxy(monkeypatch):
    """本机 HTTP fixture 不能被系统代理劫持。

    Windows 上 urllib 只读注册表代理、忽略 no_proxy 环境变量，
    所以这里直接把 getproxies 置空，保证 127.0.0.1 走直连。
    """
    import urllib.request
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})



# ====================================================================
# 合并自 test_collect_schema.py：P2-5：collect schema --url → 草稿 + 试采 + 质量门。
# ====================================================================
# -*- coding: utf-8 -*-


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body: str, ctype="text/html; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/table"):
            rows = "".join(f"<tr><td>主体{i}</td><td>{i * 10}</td></tr>"
                           for i in range(1, 9))
            return self._send("<table><tr><th>主体</th><th>金额</th></tr>"
                              + rows + "</table>")
        if self.path.startswith("/json"):
            return self._send(json.dumps({"data": {"items": [
                {"name": f"主体{i}", "value": i * 3} for i in range(1, 8)]}}),
                "application/json")
        if self.path.startswith("/empty"):
            return self._send("<table><tr><th>主体</th><th>金额</th></tr>"
                              "<tr><td></td><td></td></tr></table>")
        self._send("not found")


@pytest.fixture(scope="module")
def site():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()


def _pol():
    from core import ingest
    p = dict(ingest.load_policy("default"))
    p.update({"rps": 1000, "backoff": 0.01, "retries": 0})
    return p


def test_table_draft_has_source_spec_and_quality(site):
    d = collect_schema.draft(site + "/table", policy=_pol())
    assert d["ok"], d
    assert d["source"]["atomic_grain"] == ["主体", "金额"]
    assert d["spec"]["extract"]["format"] == "table"
    assert d["spec"]["mode"] == "raw"
    assert d["spec"]["rollups"][0]["measures"].get("金额")
    assert d["quality"]["ok"] and d["rows"] == 8


def test_json_draft_infers_array_path(site):
    d = collect_schema.draft(site + "/json", policy=_pol())
    assert d["ok"], d
    assert d["spec"]["extract"] == {"format": "json", "path": "data.items"}
    assert d["source"]["fields"][0]["name"] == "name"


def test_quality_gate_blocks_empty_columns(site):
    d = collect_schema.draft(site + "/empty", policy=_pol())
    assert d["ok"] is False and d["stage"] == "quality"
    assert any("空值率" in p or "min_rows" in p for p in d["quality"]["problems"])


def test_cli_writes_project_side_files(site, tmp_path):
    out = tmp_path / "collect"
    rc = collect_schema.main(["--url", site + "/table", "--out", str(out),
                              "--rows", "5"])
    assert rc == 0
    assert list(out.glob("*.source.yaml")) and list(out.glob("*.collection.yaml"))


def test_cli_rejects_team_output(site):
    rc = collect_schema.main(["--url", site + "/table", "--out", str(TEAM)])
    assert rc == 2


# ====================================================================
# 合并自 test_collection_contract.py：test_collection_contract —— 采集契约单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _grid():
    return {"cells": [
        {"cell_id": "Q1.空间.全国", "dim": "空间", "entity": "全国",
         "measure": "retail_sales", "grain": "G_category_year"},
        {"cell_id": "Q1.对象.纸尿裤", "dim": "对象", "entity": "纸尿裤",
         "measure": "share", "grain": "G_category_year"},
    ]}


def _sem():
    return {"case": {
        "entities": [{"id": "category", "levels": ["大类", "子类"]},
                     {"id": "year", "levels": []}],
        "measures": [{"id": "retail_sales", "type": "simple", "unit": "亿元",
                      "caliber": {"scope": "平台内成交额"}},
                     {"id": "share", "type": "ratio", "unit": "%",
                      "expr": "brand_sales/retail_sales"}],
    }}


def test_build_has_required_fields():
    c = cc.build(_grid(), _sem(), {"asks": [{"must": True, "text": "首推哪个品类"}]})
    assert c["apiVersion"] == cc.SCHEMA
    assert c["grain"] == ["category"]
    assert c["rows_expected"] == 2
    assert c["acquisition"]["availability"] in cc.AVAILABILITY


def test_validate_ok():
    c = cc.build(_grid(), _sem())
    assert cc.validate(c) == []


def test_validate_missing_grain():
    c = cc.build(_grid(), _sem())
    c["grain"] = []
    assert any("grain" in e for e in cc.validate(c))


def test_validate_bad_availability():
    c = cc.build(_grid(), _sem())
    c["acquisition"]["availability"] = "maybe"
    assert any("availability" in e for e in cc.validate(c))


def test_availability_percent_is_medium():
    assert cc.availability_estimate(["share"], _sem()) == "medium"


def test_empty_grid_returns_none():
    assert cc.build({"cells": []}, _sem()) is None


# ====================================================================
# 合并自 test_collectors.py：test_collectors —— 采集器（离线夹具，不依赖网络）。
# ====================================================================
# -*- coding: utf-8 -*-


FIX = ROOT / "tests" / "fixtures" / "html" / "search_demo.html"

SEL = {
    "item": "//li[@class='item']",
    "title": ".//h2/a/text()",
    "url": ".//h2/a/@href",
    "price": ".//span[@class='price']/text()",
    "sales": ".//span[@class='sales']/text()",
}


def test_registry_has_three_collectors():
    assert set(base.names()) >= {"csv_manual", "web_search", "platform_search"}


def test_parse_items_offline():
    html = FIX.read_text(encoding="utf-8")
    rows = ws.parse_items(html, SEL)
    assert len(rows) == 3
    assert rows[0]["title"] == "AAA 汽车脚垫 全包围"
    assert rows[0]["url"] == "https://demo.invalid/1"
    assert rows[0]["price"] == "128.0"


def test_parse_requires_item_selector():
    try:
        ws.parse_items("<ul></ul>", {"title": ".//a"})
    except ValueError as exc:
        assert "item" in str(exc)
    else:
        raise AssertionError("缺 item 选择器应当报错")


def test_zero_rows_must_raise():
    # 反爬拦截页会得到 0 行；必须报错，不能静默当成「今天没数据」
    try:
        ws.check_rows([], html_len=2696)
    except ValueError as exc:
        assert "0 行" in str(exc)
    else:
        raise AssertionError("0 行必须报错")


def test_check_rows_passes_through():
    assert ws.check_rows([{"a": 1}], 100) == [{"a": 1}]


def test_fetch_requires_url():
    try:
        base.get("web_search")().fetch({"query": {}})
    except ValueError as exc:
        assert "url" in str(exc)
    else:
        raise AssertionError("缺 url 应当报错")


# ====================================================================
# 合并自 test_ingest.py：采集六层：robots / 限速 / 重试 / 字节上限 / 分页 / 失败隔离 / staging 落盘。
# ====================================================================
# -*- coding: utf-8 -*-


STATE = {"flaky": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 静音
        pass

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        u = urlsplit(self.path)
        if u.path == "/robots.txt":
            return self._send(200, "User-agent: *\nDisallow: /private\n", "text/plain")
        if u.path == "/private/x":
            return self._send(200, "<table><tr><td>a</td></tr></table>")
        if u.path == "/flaky":
            STATE["flaky"] += 1
            if STATE["flaky"] < 3:
                return self._send(500, "boom")
            return self._send(200, "<table><tr><th>name</th></tr><tr><td>ok</td></tr></table>")
        if u.path == "/big":
            return self._send(200, "x" * 5000)
        if u.path == "/list":
            page = int(parse_qs(u.query).get("page", ["1"])[0])
            rows = "".join(
                f"<tr><td>甲{page}-{i}</td><td>{page * 10 + i}</td></tr>"
                for i in (1, 2))
            return self._send(200, f"<table><tr><th>name</th><th>price</th></tr>"
                                   f"{rows}</table>")
        if u.path == "/drift":
            return self._send(200, "<table><tr><th>name</th><th>price</th></tr>"
                                   "<tr><td>甲</td><td>1</td></tr>"
                                   "<tr><td></td><td>2</td></tr></table>")
        if u.path == "/json":
            return self._send(200, json.dumps({"data": {"items": [
                {"name": "a", "v": 1}, {"name": "b", "v": 2}]}}),
                "application/json")
        return self._send(404, "not found")


@pytest.fixture(scope="module")
def site_ingest():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    yield base
    srv.shutdown()


def _pol_ingest(**kw):
    p = dict(pol_mod.DEFAULT_POLICY)
    p.update(kw)
    return p


def test_policy_defaults_are_valid():
    assert pol_mod.validate_policy(pol_mod.DEFAULT_POLICY) == []
    assert pol_mod.validate_policy(_pol_ingest(rps=0))


def test_robots_blocks_disallowed_path(site_ingest):
    res = ingest.http_get(site_ingest + "/private/x", _pol_ingest(),
                          robots=ingest.fetch.RobotsCache(_pol_ingest()))
    assert res.kind == "robots_blocked" and not res.ok


def test_rate_limiter_paces_same_host():
    lim = ingest.RateLimiter(rps=20)          # 间隔 50ms
    t0 = time.monotonic()
    for _ in range(3):
        lim.wait("http://127.0.0.1/x")
    assert time.monotonic() - t0 >= 0.09


def test_retry_until_success(site_ingest):
    STATE["flaky"] = 0
    res = ingest.http_get(site_ingest + "/flaky", _pol_ingest(retries=2, backoff=0.01))
    assert res.ok and res.attempts == 3
    assert "ok" in res.body


def test_max_bytes_marks_too_large(site_ingest):
    res = ingest.http_get(site_ingest + "/big", _pol_ingest(max_bytes=1000))
    assert res.kind == "too_large" and res.nbytes > 1000


def test_pagination_collects_all_pages_and_persists(site_ingest, tmp_path):
    spec = {"id": "demo", "source": "local",
            "query": {"url": site_ingest + "/list"},
            "pagination": {"param": "page", "start": 1, "stop": 3},
            "extract": {"format": "table", "header": ["name", "price"],
                        "required": ["name"]}}
    out = ingest.run(spec, project_dir=str(tmp_path), persist=True,
                     policy=_pol_ingest(rps=1000, backoff=0.01))
    assert out["ok"], out
    assert out["rows_out"] == 6
    d = Path(out["staging"])
    assert (d / "rows.jsonl").is_file()
    assert (d / "_state.json").is_file()
    dq = json.loads((d / "dq_report.json").read_text(encoding="utf-8"))
    assert dq["rows_out"] == 6
    assert set(dq["columns"]) == {"name", "price"}
    rows = ingest.read_staging(tmp_path, "local")
    assert len(rows) == 6


def test_schema_drift_rows_are_dropped_with_reason(site_ingest, tmp_path):
    spec = {"id": "drift", "source": "local",
            "query": {"url": site_ingest + "/drift"},
            "extract": {"format": "table", "header": ["name", "price"],
                        "required": ["name"]}}
    out = ingest.run(spec, project_dir=str(tmp_path), policy=_pol_ingest(backoff=0.01))
    assert out["rows_out"] == 1
    assert out["drop_reasons"].get("schema_drift") == 1


def test_json_extract_by_path(site_ingest, tmp_path):
    spec = {"id": "json", "source": "local",
            "query": {"url": site_ingest + "/json"},
            "extract": {"format": "json", "path": "data.items"}}
    out = ingest.run(spec, project_dir=str(tmp_path), policy=_pol_ingest(backoff=0.01))
    assert out["rows_out"] == 2


def test_single_source_failure_does_not_kill_batch(site_ingest, tmp_path):
    bad = {"id": "bad", "source": "local",
           "query": {"url": site_ingest + "/missing"},
           "extract": {"format": "table"}}
    good = {"id": "good", "source": "local",
            "query": {"url": site_ingest + "/list"},
            "extract": {"format": "table", "header": ["name", "price"]}}
    out = ingest.run_many([bad, good], project_dir=str(tmp_path),
                          policy=_pol_ingest(backoff=0.01))
    assert out["ok_sources"] == 1 and out["total_sources"] == 2
    assert out["results"][0]["ok"] is False
    assert out["results"][0]["pages"][0]["kind"] == "http_404"


def test_staging_inside_team_is_rejected(site_ingest):
    spec = {"id": "x", "source": "local", "query": {"url": site_ingest + "/list"},
            "extract": {"format": "table", "header": ["name", "price"]}}
    out = ingest.run(spec, project_dir=str(TEAM), persist=True,
                     policy=_pol_ingest(backoff=0.01))
    assert out["ok"] is False and out["stage"] == "store"


# ====================================================================
# 合并自 test_coverage_pipeline.py：覆盖自动化：TaskFrame / SourceLedger / CoveragePlan / 双门禁。
# ====================================================================
# -*- coding: utf-8 -*-


def _units():
    return [{"id": f"U{i}", "name": f"单元{i}", "level": "category", "sources": ["S01"]}
            for i in range(1, 4)]


def _dims():
    return [{"id": "D1", "name": "规模", "sources": ["S01"], "required": True},
            {"id": "D2", "name": "链路", "sources": ["S02"], "required": True}]


def _frame():
    # task_frame 模块已删（dispatch 内联产出同结构 artifact），这里用同样的静态结构
    return {
        "schema": "dsh.task_frame/v1", "task_id": "t1", "brief": "测试任务",
        "decision": {"question": "做不做？", "type": "inferred"},
        "units": _units(), "dimensions": _dims(),
        "maps": [{"level": "national", "required": True},
                 {"level": "regional", "required": True}],
        "depth": {"core_units": ["U1", "U2", "U3"],
                  "deep_dimensions": ["D1", "D2"],
                  "long_tail_policy": "context_red"},
    }


def test_pre_gate_core_missing_blocks():
    f = _frame()
    cells = [{"unit": u, "dimension": d, "status": "verified"}
             for u in ("U1", "U2", "U3") for d in ("D1", "D2")]
    cells[0]["status"] = "missing"
    p = coverage_plan.build(f, cells, 21, ["national", "regional"])
    conf = {"plan_hash": coverage_plan.plan_hash(p)}
    r = coverage_plan.pre_gate(f, p, {"cited": 50, "reached": True, "no_new_streak": 15},
                               conf, {"coverage": {"cited_sources_min": 50,
                                                   "maps_required": ["national", "regional"],
                                                   "page_floor": 21}})
    assert r["ok"] is False
    assert "G4_core_missing" in r["hard_fail"]


def test_pre_gate_pass_and_confirm_hash():
    f = _frame()
    cells = [{"unit": u, "dimension": d, "status": "verified"}
             for u in ("U1", "U2", "U3") for d in ("D1", "D2")]
    p = coverage_plan.build(f, cells, 21, ["national", "regional"])
    conf = {"plan_hash": coverage_plan.plan_hash(p)}
    r = coverage_plan.pre_gate(f, p, {"cited": 50, "reached": True, "no_new_streak": 15},
                               conf, {"coverage": {"cited_sources_min": 50,
                                                   "maps_required": ["national", "regional"],
                                                   "page_floor": 21}})
    assert r["ok"] is True
    bad = {"plan_hash": "sha256:bad"}
    r2 = coverage_plan.pre_gate(f, p, {"cited": 50, "reached": True, "no_new_streak": 15},
                                bad, {"coverage": {"cited_sources_min": 50,
                                                   "maps_required": ["national", "regional"],
                                                   "page_floor": 21}})
    assert r2["ok"] is False and "G3_confirmed" in r2["hard_fail"]


def test_data_shape_fit():
    from core import data_shape
    assert data_shape.fits("dumbbell", "pair")
    assert not data_shape.fits("dumbbell", "scalar")
    assert "hbar" in data_shape.candidates("scalar")
    bad = data_shape.audit_sections([{"id": "s1", "chart": "dumbbell", "shape": "scalar"}])
    assert bad["ok"] is False


# ====================================================================
# 合并自 test_coverage_wire.py：test_coverage_wire —— 覆盖矩阵/饱和接进主链路的派生层。
# ====================================================================
# -*- coding: utf-8 -*-


def _w(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _project(tmp_path: Path, filled=True):
    proj = tmp_path / "proj"
    _w(proj / "plan" / "grid.json", {"cells": [
        {"cell_id": "Q1.对象.飞鹤", "qid": "Q1", "dim": "对象",
         "entity": "飞鹤", "measure": "share", "depth_target": 3},
        {"cell_id": "Q1.空间.全国", "qid": "Q1", "dim": "空间",
         "entity": "全国", "measure": "retail_sales"},
        {"cell_id": "Q1.机制.份额变化", "qid": "Q1", "dim": "机制",
         "entity": "飞鹤", "measure": "share", "depth_target": 3},
    ]})
    if filled:
        _w(proj / "out_v3" / "cells_filled.json", {"cells": [
            {"cell_id": "Q1.对象.飞鹤", "status": "filled", "value": 20.0},
            {"cell_id": "Q1.空间.全国", "status": "filled", "value": 100.0},
            {"cell_id": "Q1.机制.份额变化", "status": "open"},
        ]})
    _w(proj / "out" / "claims_merged.json", {"sources": [
        {"file": "S1"}, {"file": "S2"}, {"file": "S2"},
    ]})
    return proj


def test_derive_ok(tmp_path):
    d = coverage_wire.derive(str(_project(tmp_path)))
    assert d["ok"] is True
    assert d["cells"] == 3
    assert d["filled"] == 2
    assert len(d["frame"]["dimensions"]) == 6
    assert "飞鹤" in d["frame"]["depth"]["core_units"]


def test_derive_missing_grid(tmp_path):
    d = coverage_wire.derive(str(tmp_path))
    assert d["ok"] is False
    assert "grid" in d["why"]


def test_derive_marks_missing_cells(tmp_path):
    d = coverage_wire.derive(str(_project(tmp_path)))
    statuses = {(c["unit"], c["dimension"]): c["status"] for c in d["plan"]["cells"]}
    assert statuses[("飞鹤", "对象")] == "verified"
    assert statuses[("飞鹤", "机制")] == "missing"


def test_gate_runs_and_reports(tmp_path):
    g = coverage_wire.gate(str(_project(tmp_path)))
    assert g.get("skipped") is not True
    ids = {c["id"] for c in g["checks"]}
    assert "G4_core_missing" in ids
    assert "G2_saturation" in ids


def test_gate_skipped_without_grid(tmp_path):
    g = coverage_wire.gate(str(tmp_path))
    assert g.get("skipped") is True
    assert g.get("ok") is True
