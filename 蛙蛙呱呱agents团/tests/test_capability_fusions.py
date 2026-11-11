# -*- coding: utf-8 -*-
"""外部能力「真融合」回归：三个角色里可直接执行的技能（R11/R14/R15）。

这些用例跑的是角色真实 CLI（`agent.py <skill> <action>`），不是只查目录。
全部离线、无外部依赖。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _run(role, args):
    proc = subprocess.run([sys.executable, "agent.py", *args],
                          cwd=os.path.join(ROOT, role), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("__AGENT_RESULT__")), "")
    assert line, f"{role} 未输出结果: {proc.stderr[-500:]}"
    return proc.returncode, json.loads(line.split(" ", 1)[1])


def _note(**over):
    p1 = "上个月我在景区做核销运营，第一周就踩坑：游客排队40分钟，核销率只有30%，现场3个窗口全堵死。"
    p2 = "我复盘了3轮，发现2个关键点：把核销码提前发到短信，把入园和核销合并成1步。改完第2周，核销率从30%涨到72%。"
    p3 = "这套方法在2个景区验证过，最小的一个只有1个窗口也能跑。你如果也在做景区运营，可以先从核销码前置这1步开始。"
    body = "\n\n".join([p1, p2, p3])
    pad = "\n\n我把每周数据都记在表里，连续记了8周，才敢说这个数字是稳定的。"
    while len(body) < 560:
        body += pad
    data = {"title": "景区核销2个月从30%干到72%", "body": body + "\n\n#AI辅助创作",
            "tags": ["景区运营", "核销率", "小红书运营", "文旅"],
            "core_keywords": ["景区", "核销"], "format_type": "story",
            "cta": "你更想先解决排队还是核销？评论区聊聊", "ai_assisted": True}
    data.update(over)
    return data


# --------------------------------------------------------------------------- #
# R11 · xhs
# --------------------------------------------------------------------------- #
def test_r11_note_passes_and_rejects_long_title(tmp_path):
    rc, out = _run("r11-wadianti-copy", ["xhs", "note", "--input", _write(tmp_path, "n.json", _note())])
    assert rc == 0 and out["verdict"] == "PASS", out.get("checks")
    long_title = _note(title="这个标题写得太长了完全超过二十个字的硬性上限所以必须被拦截")
    rc2, out2 = _run("r11-wadianti-copy", ["xhs", "note", "--input", _write(tmp_path, "b.json", long_title)])
    assert out2["verdict"] == "FAIL"
    assert any(c["dim"] == "xhs.title.length" and not c["ok"] for c in out2["checks"])


def test_r11_compliance_blocks_blacklist_cta(tmp_path):
    bad = _note(cta="评论区扣1领取资料，帮你免费诊断", title="全网第一的景区核销秘籍")
    rc, out = _run("r11-wadianti-copy", ["xhs", "compliance", "--input", _write(tmp_path, "bad.json", bad)])
    assert out["verdict"] == "FAIL"
    dims = {c["dim"] for c in out["checks"] if not c["ok"]}
    assert {"xhs.cta.blacklist", "xhs.absolute"} <= dims
    rc2, ok = _run("r11-wadianti-copy", ["xhs", "compliance", "--input", _write(tmp_path, "ok.json", _note())])
    assert ok["verdict"] == "PASS", [c for c in ok["checks"] if not c["ok"]]


def test_r11_score_meets_seven_of_eight(tmp_path):
    rc, out = _run("r11-wadianti-copy", ["xhs", "score", "--input", _write(tmp_path, "s.json", _note())])
    assert out["passed"] >= 7, [c for c in out["checks"] if not c["ok"]]
    assert out["verdict"] == "PASS"
    assert out["ces_reference"]


# --------------------------------------------------------------------------- #
# R14 · selection
# --------------------------------------------------------------------------- #
def _sel(products):
    return {"products": products}


def _product(name, dims, hyp=True, risks=True):
    p = {"name": name, "dims": dims, "source_types": ["检索核实"]}
    if risks:
        p["risks"] = ["同质化"]
    if hyp:
        p["hypothesis"] = {"click_rate": "3%-5%", "cvr": "2%-3%",
                           "margin": "40%-50%", "verify_at": "上架 7 天"}
    return p


GOOD_DIMS = {"capacity": 4, "growth": 5, "entry": 3, "margin": 4, "supply": 4}
WEAK_DIMS = {"capacity": 4, "growth": 3, "entry": 2, "margin": 2, "supply": 2}


def test_r14_selection_normalizes_upstream_weights_and_ranks(tmp_path):
    rc, out = _run("r14-wajiaoyi-commerce", ["selection", "score", "--input",
                                             _write(tmp_path, "s.json", _sel([
                                                 _product("便携水壶", GOOD_DIMS),
                                                 _product("露营桌", WEAK_DIMS)]))])
    assert rc == 0 and out["verdict"] == "PASS", out.get("checks")
    assert out["ranked"][0]["name"] == "便携水壶"
    assert abs(sum(out["weights_used"].values()) - 100) < 0.5


def test_r14_selection_requires_hypothesis_for_recommended(tmp_path):
    rc, out = _run("r14-wajiaoyi-commerce", ["selection", "score", "--input",
                                             _write(tmp_path, "s.json", _sel([
                                                 _product("便携水壶", GOOD_DIMS, hyp=False)]))])
    assert out["verdict"] == "FAIL"
    assert any(c["dim"] == "selection.hypothesis" and not c["ok"] for c in out["checks"])


def test_r14_profit_red_line(tmp_path):
    rc, out = _run("r14-wajiaoyi-commerce", ["selection", "profit", "--input", _write(tmp_path, "p.json", {
        "price": 129, "cost": 40, "shipping": 8, "packaging": 2,
        "platform_fee_pct": 5, "ad_pct": 10, "return_rate_pct": 5})])
    assert out["verdict"] == "PASS" and out["margin_pct"] > 40
    rc2, low = _run("r14-wajiaoyi-commerce", ["selection", "profit", "--input", _write(tmp_path, "l.json", {
        "price": 100, "cost": 92})])
    assert low["verdict"] == "FAIL" and low["margin_pct"] < 15


# --------------------------------------------------------------------------- #
# R15 · tco
# --------------------------------------------------------------------------- #
def test_r15_landed_cost_math_and_ranking(tmp_path):
    quotes = {"annual_rate_pct": 6, "quotes": [
        {"supplier": "A", "unit_price": 12, "qty": 1000, "main_freight": 800,
         "insurance": 100, "duty_pct": 5, "lead_days": 35, "payment_terms_days": 30,
         "defects_pct": 1},
        {"supplier": "B", "unit_price": 11.5, "qty": 1000, "main_freight": 400,
         "insurance": 50, "duty_pct": 5, "lead_days": 75, "payment_terms_days": 60,
         "defects_pct": 3}]}
    rc, out = _run("r15-wagongying-erp", ["tco", "compare", "--input",
                                          _write(tmp_path, "t.json", quotes)])
    assert rc == 0 and out["verdict"] == "PASS"
    best = out["ranked"][0]
    assert best["supplier"] == "B"
    assert abs(best["effective_unit_cost"] - 13.04) < 0.05
    # 交期 75 天与不良率 3% 必须有告警
    assert any(c["sev"] == "WARN" and not c["ok"] for c in out["checks"])


def test_r15_lifecycle_requires_three_components(tmp_path):
    rc, out = _run("r15-wagongying-erp", ["tco", "lifecycle", "--input", _write(tmp_path, "l.json", {
        "acquisition": 120000, "implementation": 20000, "operation": 30000,
        "support": 10000, "residual": 15000})])
    assert out["verdict"] == "PASS" and out["tco"] == 165000
    rc2, thin = _run("r15-wagongying-erp", ["tco", "lifecycle", "--input", _write(tmp_path, "t.json", {
        "acquisition": 100, "main_freight": 10})])
    assert thin["verdict"] == "FAIL"
    assert any(c["dim"] == "tco.lifecycle_components" and not c["ok"] for c in thin["checks"])
