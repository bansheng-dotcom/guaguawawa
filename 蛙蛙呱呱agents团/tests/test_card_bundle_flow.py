# -*- coding: utf-8 -*-
"""CardBundle 端到端：发卡写 bundle → brief 落项目 → 收卡校验契约。

这一层测试守的是「卡与 brief 不是两份独立产物」：
卡里出现 acceptance 明细、或版本不一致，收卡时必须被拦下。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core import dispatch, project as project_mod


def _make_project(tmp: Path):
    root = tmp / "proj"
    project_mod.init(root, industry="测试", name="测试项目")
    return project_mod.load(root)


def test_write_cards_emits_bundles_and_project_briefs():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = _make_project(tmp)
        out = proj.path("cards")   # 项目内，允许写
        res = dispatch.write_cards("验证卡与 brief 一起下发", str(out),
                                   only=["r06"], project=proj)
        assert res["ok"], res["bundle_problems"]
        assert res["bundles"] == 1

        bundle = json.loads((out / "cards" / "r06" / "bundle.json")
                            .read_text(encoding="utf-8"))
        card, brief = bundle["card"], bundle["brief"]
        assert card["brief_version"] == brief["version"] == "v2"
        assert not card.get("acceptance"), "卡里不得写验收明细"
        assert brief["must_answer"] and brief["acceptance_checks"]
        # brief 落到项目 briefs/，卡里只留相对引用
        assert card["brief_ref"].startswith("briefs/")
        assert (proj.root / card["brief_ref"]).is_file()
        assert card["knowledge_scope"]["industry"] == "测试"
        # TASK.md 要带上 must_answer，执行者才知道该答什么
        task_md = (out / "cards" / "r06" / "TASK.md").read_text(encoding="utf-8")
        assert "专家工作说明书" in task_md and "L0.1" in task_md


def test_collect_rejects_card_with_acceptance_details():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = _make_project(tmp)
        out = proj.path("cards")
        dispatch.write_cards("验证卡里写验收会被拦下", str(out),
                             only=["r06"], project=proj)
        bp = out / "cards" / "r06" / "bundle.json"
        doc = json.loads(bp.read_text(encoding="utf-8"))
        doc["card"]["acceptance"] = ["必须交 3 张图"]
        bp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        merged, problems = dispatch.collect(str(out), allow_legacy=True)
        bc = merged.get("brief_contract") or {}
        assert bc.get("bundles") == 1
        assert any("acceptance" in p for p in bc.get("problems") or [])
        assert any("acceptance" in p for p in problems)


def test_collect_rejects_brief_version_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = _make_project(tmp)
        out = proj.path("cards")
        dispatch.write_cards("验证版本不一致会被拦下", str(out),
                             only=["r06"], project=proj)
        bp = out / "cards" / "r06" / "bundle.json"
        doc = json.loads(bp.read_text(encoding="utf-8"))
        doc["card"]["brief_version"] = "v1"
        bp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        merged, _ = dispatch.collect(str(out), allow_legacy=True)
        probs = (merged.get("brief_contract") or {}).get("problems") or []
        assert any("版本" in p or "brief_version" in p for p in probs)
