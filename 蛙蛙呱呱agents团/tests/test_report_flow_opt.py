# -*- coding: utf-8 -*-
"""SOP 优化项的回归测试（2026-11-16）。

钉住四件事：
1. compose 的「边界」不再丢失，落到末节「口径与分数」；
2. 契约中转不丢 `charts` / intro / why / refs；
3. 门禁不过就不落盘（不产生半份报告）；
4. 附录 id 单独编号，不与正文章节号冲突；表格裸字符串单元格可渲染。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
REPO = TEAM.parent
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import evidence_pack, report_flow, report_renderer  # noqa: E402


def _pack(tmp_path) -> dict:
    return {
        "schema": "dsh.evidence_pack/v1", "project": "t", "root": str(tmp_path),
        "numbers": [{"id": "A1", "name": "社零", "value": 1.0, "unit": "亿元"}],
        "sources": [{"file": "obs.json", "kind": "json", "hash": "abc", "numbers": 1}],
        "counts": {"files": 1, "numbers": 1},
    }


def _draft() -> dict:
    return {
        "standfirst": "测试用结论 12",
        "summary": ["测试用结论 12"],
        "sections": [{
            "title": "1 测试节：有数字 12",
            "question": "q",
            "reading": [{"text": "证据 12", "refs": ["A1"]}],
            "chart": {"type": "hbar", "title": "图 12", "unit_meta": "亿元",
                      "source": "obs.json",
                      "bars": [{"label": "a", "value": 1}]},
            "charts": [{"type": "hbar", "title": "第二张 3", "unit_meta": "亿元",
                        "source": "obs.json", "bars": [{"label": "b", "value": 2}]}],
            "intro": [{"text": "导语 12"}],
            "why": "为什么做 12",
            "refs": ["A1"],
        }],
        "boundaries": ["只对样本成立 1", "不含税 2"],
    }


def test_boundaries_reach_final_section(tmp_path):
    contract = report_flow.build_sections_contract(_draft(), _pack(tmp_path))
    tail = contract["sections"][-1]
    assert tail["title"] == "口径与分数"
    joined = " ".join(r.get("text", "") for r in tail["reading"])
    assert "只对样本成立 1" in joined and "不含税 2" in joined


def test_charts_and_section_fields_pass_through(tmp_path):
    contract = report_flow.build_sections_contract(_draft(), _pack(tmp_path))
    sec = contract["sections"][0]
    assert sec["charts"][0]["title"] == "第二张 3"
    assert sec["intro"][0]["text"] == "导语 12"
    assert sec["why"].startswith("为什么做")
    assert sec["refs"] == ["A1"]


def test_gate_blocks_render(tmp_path, monkeypatch):
    monkeypatch.setattr(report_flow, "check_sections",
                        lambda *a, **k: {"ok": True, "sections": 1, "checks": {}})
    monkeypatch.setattr(report_flow, "layout_errors", lambda *a, **k: ["forced"])
    monkeypatch.setattr(evidence_pack, "load", lambda *a, **k: _pack(tmp_path))
    out = tmp_path / "out"
    res = report_flow.run("测试", out_dir=str(out), draft=_draft(), evidence=str(tmp_path))
    assert res["ok"] is False
    assert not (out / "report.html").exists(), "门禁不过时不许落盘"


def test_appendix_ids_unique_and_string_cells(tmp_path):
    contract = report_flow.build_sections_contract(_draft(), _pack(tmp_path))
    # 追加一张表，单元格用裸字符串（手写 draft 的常见写法）
    contract["sections"][0]["table"] = {
        "caption": "表 1", "columns": ["列 A", "列 B"],
        "rows": [["x", "1"], ["y", "2"]],
        "total_row": ["合计", "3"],
    }
    html = report_renderer.render(contract)
    ids = re.findall(r'id="(s-[^"]+)"', html)
    assert len(ids) == len(set(ids)), f"section id 重复: {ids}"
    assert "s-A1" in ids
    assert "<td>x</td>" in html
