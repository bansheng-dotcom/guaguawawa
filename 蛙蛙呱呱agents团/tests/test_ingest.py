# -*- coding: utf-8 -*-
"""采集六层：robots / 限速 / 重试 / 字节上限 / 分页 / 失败隔离 / staging 落盘。

用本地 http.server 起一个受控站点，不打外网。
"""
from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import ingest  # noqa: E402
from core.ingest import policy as pol_mod  # noqa: E402

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
def site():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    yield base
    srv.shutdown()


def _pol(**kw):
    p = dict(pol_mod.DEFAULT_POLICY)
    p.update(kw)
    return p


def test_policy_defaults_are_valid():
    assert pol_mod.validate_policy(pol_mod.DEFAULT_POLICY) == []
    assert pol_mod.validate_policy(_pol(rps=0))


def test_robots_blocks_disallowed_path(site):
    res = ingest.http_get(site + "/private/x", _pol(),
                          robots=ingest.fetch.RobotsCache(_pol()))
    assert res.kind == "robots_blocked" and not res.ok


def test_rate_limiter_paces_same_host():
    lim = ingest.RateLimiter(rps=20)          # 间隔 50ms
    t0 = time.monotonic()
    for _ in range(3):
        lim.wait("http://127.0.0.1/x")
    assert time.monotonic() - t0 >= 0.09


def test_retry_until_success(site):
    STATE["flaky"] = 0
    res = ingest.http_get(site + "/flaky", _pol(retries=2, backoff=0.01))
    assert res.ok and res.attempts == 3
    assert "ok" in res.body


def test_max_bytes_marks_too_large(site):
    res = ingest.http_get(site + "/big", _pol(max_bytes=1000))
    assert res.kind == "too_large" and res.nbytes > 1000


def test_pagination_collects_all_pages_and_persists(site, tmp_path):
    spec = {"id": "demo", "source": "local",
            "query": {"url": site + "/list"},
            "pagination": {"param": "page", "start": 1, "stop": 3},
            "extract": {"format": "table", "header": ["name", "price"],
                        "required": ["name"]}}
    out = ingest.run(spec, project_dir=str(tmp_path), persist=True,
                     policy=_pol(rps=1000, backoff=0.01))
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


def test_schema_drift_rows_are_dropped_with_reason(site, tmp_path):
    spec = {"id": "drift", "source": "local",
            "query": {"url": site + "/drift"},
            "extract": {"format": "table", "header": ["name", "price"],
                        "required": ["name"]}}
    out = ingest.run(spec, project_dir=str(tmp_path), policy=_pol(backoff=0.01))
    assert out["rows_out"] == 1
    assert out["drop_reasons"].get("schema_drift") == 1


def test_json_extract_by_path(site, tmp_path):
    spec = {"id": "json", "source": "local",
            "query": {"url": site + "/json"},
            "extract": {"format": "json", "path": "data.items"}}
    out = ingest.run(spec, project_dir=str(tmp_path), policy=_pol(backoff=0.01))
    assert out["rows_out"] == 2


def test_single_source_failure_does_not_kill_batch(site, tmp_path):
    bad = {"id": "bad", "source": "local",
           "query": {"url": site + "/missing"},
           "extract": {"format": "table"}}
    good = {"id": "good", "source": "local",
            "query": {"url": site + "/list"},
            "extract": {"format": "table", "header": ["name", "price"]}}
    out = ingest.run_many([bad, good], project_dir=str(tmp_path),
                          policy=_pol(backoff=0.01))
    assert out["ok_sources"] == 1 and out["total_sources"] == 2
    assert out["results"][0]["ok"] is False
    assert out["results"][0]["pages"][0]["kind"] == "http_404"


def test_staging_inside_team_is_rejected(site):
    spec = {"id": "x", "source": "local", "query": {"url": site + "/list"},
            "extract": {"format": "table", "header": ["name", "price"]}}
    out = ingest.run(spec, project_dir=str(TEAM), persist=True,
                     policy=_pol(backoff=0.01))
    assert out["ok"] is False and out["stage"] == "store"
