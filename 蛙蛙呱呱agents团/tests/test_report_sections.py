# -*- coding: utf-8 -*-
"""调研级报告（章节稿 + 证据包逐节过账）的回归测试。

钉住：pack 可寻址、章节校验会拦编造数字、渲染后门禁可过。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
REPO = TEAM.parent
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from core import evidence_pack, report_flow  # noqa: E402


def _pack(tmp_path):
    numbers = [
        {"id": "A1", "name": "社零", "value": 5375.5, "unit": "亿元", "period": "2025",
         "source_file": "obs.json", "org": "统计局"},
        {"id": "A2", "name": "上年社零", "value": 5615.3, "unit": "亿元", "period": "2024",
         "source_file": "obs.json", "org": "统计局"},
        {"id": "A3", "name": "今年增速", "value": 0.005, "unit": "%", "period": "2026Q3",
         "source_file": "obs.json", "org": "统计局"},
    ]
    pack = {"schema": "dsh.evidence_pack/v1", "project": "t", "root": str(tmp_path),
            "numbers": numbers,
            "sources": [{"file": "obs.json", "kind": "json", "hash": "abc", "numbers": 3}],
            "counts": {"files": 1, "numbers": 3}}
    p = tmp_path / "evidence_pack.json"
    p.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    return pack, str(p)


def _draft(bad_number: bool = False):
    x = 9999 if bad_number else 239.8
    return {
        "profile": "market_research",
        "title_lines": ["测试市场：5375.5 亿元的盘子在减速"],
        "standfirst": "2025 年社零 5375.5 亿元，增速掉到 0.5%。",
        "metrics": [{"label": "社零", "value": "5375.5 亿", "note": "A1"}],
        "summary": ["盘子还在，但增速只剩 0.5%。"],
        "sections": [
            {"title": "大盘：社零 5375.5 亿元，比上一年少 239.8 亿元",
             "question": "盘子有多大？",
             "refs": ["A1", "A2"],
             "chart": {"type": "hbar", "title": "两年社零：5375.5 vs 5615.3",
                       "unit_meta": "亿元", "source": "A1/A2",
                       "refs": ["A1", "A2"],
                       "bars": [{"label": "2025", "value": 5375.5},
                                {"label": "2024", "value": 5615.3}]},
             "reading": [
                 {"text": "2025 年社零 5375.5 亿元，比上一年多 239.8 亿元的降幅。",
                  "refs": ["A1", "A2"]},
                 {"text": f"补充口径：{x}。", "refs": ["A1", "A2"]},
             ]},
            {"title": "增速：三季度只有 0.5%", "question": "还在不在增长？",
             "refs": ["A3"],
             "reading": [{"text": "2026 年三季度增速 0.5%，基本停住。", "refs": ["A3"]},
                         {"text": "增速口径是同比，不是环比。", "refs": ["A3"]}]},
            {"title": "判断：先保存量，3 条动作", "question": "做什么？",
             "refs": ["A1"],
             "reading": [{"text": "盘子 5375.5 亿元，先保存量。", "refs": ["A1"]},
                         {"text": "动作按季度验收。", "refs": ["A1"]}]},
        ],
        "boundary": ["只对本次输入成立"],
    }


def test_pack_is_addressable(tmp_path):
    pack, path = _pack(tmp_path)
    assert pack["counts"]["numbers"] == 3
    assert evidence_pack.load(path)["numbers"][0]["id"] == "A1"
    ids = {n["id"] for n in evidence_pack.values(pack)}
    assert ids == {"A1", "A2", "A3"}


def test_sections_validate_and_render(tmp_path):
    _, path = _pack(tmp_path)
    out = tmp_path / "out"
    res = report_flow.run(intent="测试", evidence=path, draft=_draft(),
                          out_dir=str(out))
    assert res["ok"], res
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["producer"] == "r01" and man["branch"] == "sections"
    assert man["section_check"]["ok"] is True
    c = json.loads((out / "contract.json").read_text(encoding="utf-8"))
    assert c["sections"][-1]["title"] == "口径与分数"
    assert any(s.get("appendix") for s in c["sections"])
    assert (out / "report.html").stat().st_size > 15000


def test_fabricated_number_is_rejected(tmp_path):
    _, path = _pack(tmp_path)
    with pytest.raises(report_flow.FlowError) as e:
        report_flow.run(intent="测试", evidence=path, draft=_draft(bad_number=True),
                        out_dir=str(tmp_path / "bad"))
    assert "239.8" in str(e.value) or "9999" in str(e.value) or "无法" in str(e.value)
