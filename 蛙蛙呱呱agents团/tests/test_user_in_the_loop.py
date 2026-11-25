# -*- coding: utf-8 -*-
"""2026-11-22：意图必须问用户、卡片必须给用户看；封面取 meta 不取首节。"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from core import report_flow, report_editorial

# 临时目录必须在团外：写团内会让"项目边界门禁"变红（且污染工具仓）
TMP = Path(tempfile.gettempdir()) / "guagua_test_user_in_the_loop"


def _setup(by: str = "agent", ack: bool = False):
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    (TMP / "clarify.json").write_text(json.dumps({
        "status": "confirmed", "confirmed_by": by,
        "user_said": "用户说：按这个做" if by == "user" else "",
        "asks": [{"id": f"Q{i}", "text": "问句", "must": True} for i in range(1, 11)],
    }, ensure_ascii=False), encoding="utf-8")
    (TMP / "intake.json").write_text(json.dumps({
        "answers": {f"I{i}": "答案" for i in range(1, 13)},
        "answered_by": {f"I{i}": by for i in range(1, 13)},
        "user_answers": 12 if by == "user" else 0,
        "status": "complete",
    }, ensure_ascii=False), encoding="utf-8")
    plan = {"status": "confirmed",
            "cards": [{"role": "r06", "questions": ["Q1"]}]}
    if ack:
        plan["acknowledged_at"] = "2026-11-22T10:00:00"
    (TMP / "plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    (TMP / "semantic_layer.yaml").write_text("measures:\n- id: m\n", encoding="utf-8")
    return TMP


def test_preflight_blocks_agent_confirmed_intent():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pf", Path("scripts/preflight.py").resolve())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.run(str(_setup(by="agent")), 0)
    fails = {c["id"] for c in r["checks"] if not c["ok"]}
    assert "P8" in fails, r
    r2 = mod.run(str(_setup(by="user", ack=True)), 0)
    assert not {c["id"] for c in r2["checks"] if not c["ok"]} & {"P8", "P9"}, r2


def test_cover_title_comes_from_meta_not_first_section():
    secs = [{"index": 1, "title": "首节结论 42%",
             "reading": [{"strong": "事实　", "text": "42%"},
                         {"strong": "所以　", "text": "所以先做 A"}],
             "refs": ["N1"], "headline": "42%", "falsifier": "跌破 30% 作废"}]
    pack = {"meta": {"title": "小码女装市场研究",
                     "subtitle": "人群 · 竞争 · 价盘",
                     "metrics": [{"label": "女装大盘", "value": "12311亿元"}]},
            "numbers": [{"id": "N1", "value": 42, "unit": "%", "name": "占比"}]}
    dec = report_flow._build_decision(secs, pack)
    assert dec["title"] == "小码女装市场研究", dec
    assert dec["subtitle"] == "人群 · 竞争 · 价盘"
    strip = report_editorial._metrics({"decision": dec}, pack)
    assert strip and strip[0]["value"] == "12311亿元", strip


def test_evidence_pack_carries_meta():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "car", Path("scripts/compile_agent_report.py").resolve())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pack = mod.build_pack({"meta": {"title": "T", "subtitle": "S"},
                           "sources": [], "numbers": []})
    assert pack["meta"]["title"] == "T"
    assert pack["meta"]["subtitle"] == "S"
