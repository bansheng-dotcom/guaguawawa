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
        {"id": "A3", "name": "今年增速", "value": 0.5, "unit": "%", "period": "2026Q3",
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
        "boundaries": [
            "只对本次输入的三组社零数据成立，不外推到全国",
            "2025 年口径与 2024 年一致，若口径变了本节作废",
            "增速 0.5% 是同比，不是环比",
            "社零 5375.5 亿元未扣价格因素",
            "若下季度增速超过百分之一，减速判断作废",
        ],
        "sections": [
            {"title": "大盘：社零 5375.5 亿元，比上一年少 239.8 亿元",
             "question": "盘子有多大？",
             "refs": ["A1", "A2"],
             "falsifier": "若社零超过 5615.3 亿元，本节作废",
             "chart": {"type": "hbar", "title": "两年社零：5375.5 vs 5615.3",
                       "unit_meta": "亿元", "source": "A1/A2",
                       "refs": ["A1", "A2"],
                       "bars": [{"label": "2025", "value": 5375.5},
                                {"label": "2024", "value": 5615.3}]},
             "reading": [
                 {"text": "2025 年社零 5375.5 亿元，比上一年多 239.8 亿元的降幅；因为基数 5615.3 亿元更高，所以同比少 239.8 亿元。判别方法：看 2025 与 2024 的绝对额差。",
                  "refs": ["A1", "A2"]},
                 {"text": f"补充口径：{x}；因为口径未变，所以两年可比。判别方法：核对来源与期次。",
                  "refs": ["A1", "A2"]},
             ]},
            {"title": "增速：三季度只有 0.5%", "question": "还在不在增长？",
             "refs": ["A3"],
             "falsifier": "若增速超过 1 个百分点，本节作废",
             "reading": [
                 {"text": "2026 年三季度增速不到一个百分点，基本停住；因为基数高，所以增速掉到不到一个百分点。判别方法：看同比增速是否连续两个季度低于百分之一。",
                  "refs": ["A3"]},
                 {"text": "增速口径是同比，不是环比；因为季调不同，所以不能拿环比替代。判别方法：核对报告期，并核对同比基期与本期口径是否一致，若基期被修订则本节结论只保留方向、不保留点位。",
                  "refs": ["A3"]},
                 {"text": "这一段只交代阅读方式：先看方向，再看幅度，最后看口径；方向由同比给出，幅度由绝对额差给出，口径由来源期次给出，三者缺一就不下结论。",
                  "refs": ["A3"]},
             ]},
            {"title": "判断：先保存量，3 条动作", "question": "做什么？",
             "refs": ["A1"],
             "falsifier": "若存量跌破 5000 亿元，本节作废",
             "reading": [
                 {"text": "盘子 5375.5 亿元，先保存量；因为增量只剩不到一个百分点，所以先守住 5375.5 亿元的存量。判别方法：看季度社零是否守住 5375.5 亿元。",
                  "refs": ["A1"]},
                 {"text": "动作按季度验收；因为回款滞后，所以按季度而不是按月验收。判别方法：看季度回款、看季度库存周转、看季度新增投入是否超过当季增量，三项有一项不达标就停手重排。",
                  "refs": ["A1"]},
                 {"text": "预算先按 5375.5 亿元的不到一个百分点增量安排；因为增量薄，所以不扩新品类。判别方法：看新增品类是否超过 239.8 亿元。",
                  "refs": ["A1", "A2"]},
             ]},
            {"title": "风险：0.5% 增速下的三个停手条件", "question": "什么情况下停？",
             "refs": ["A1", "A3"],
             "falsifier": "若增速回到 1 个百分点以上，本节作废",
             "reading": [
                 {"text": "社零 5375.5 亿元、增速不到一个百分点，先设停手线；因为增速薄，所以任何一个月低于百分之一就停。判别方法：看月度同比。",
                  "refs": ["A1", "A3"]},
                 {"text": "库存周转超过两个月就停；因为 5375.5 亿元的盘子不允许压货。判别方法：看周转天数。",
                  "refs": ["A1"]},
                 {"text": "新增投入超过 239.8 亿元就停；因为增量只有 239.8 亿元，投入不能超过增量。判别方法：看投入/增量比。",
                  "refs": ["A1", "A2"]},
             ]},
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
                          out_dir=str(out), prose_hard=False)
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
