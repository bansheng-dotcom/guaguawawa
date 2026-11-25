# -*- coding: utf-8 -*-
"""P2-5：collect schema --url → 草稿 + 试采 + 质量门。"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import collect_schema  # noqa: E402


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
