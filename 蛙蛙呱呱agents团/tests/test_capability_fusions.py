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


# --------------------------------------------------------------------------- #
# R08 · deck
# --------------------------------------------------------------------------- #
def _deck(**over):
    slides = [
        {"title": "Q4 复盘", "message": "营收 +18%，利润只 +4%", "is_cover": True},
        {"title": "结论先行", "message": "增长来自复购", "bullets": ["复购 62%"]},
        {"title": "流量结构", "message": "自然流量升、转化降"},
        {"title": "履约成本", "message": "单均履约是最大漏点"},
        {"title": "三个动作", "message": "先修履约再加复购"},
        {"title": "验证方式", "message": "每项动作 4 周验证"},
        {"title": "下一步", "message": "本周定责任人", "is_closing": True},
    ]
    data = {"title": "2026 Q4 增长复盘", "slides": slides}
    data.update(over)
    return data


def test_r08_deck_plan_and_html(tmp_path):
    src = _write(tmp_path, "deck.json", _deck())
    rc, out = _run("r08-wajiancheng-mvp", ["deck", "plan", "--input", src])
    assert rc == 0 and out["verdict"] == "PASS", out.get("checks")
    target = str(tmp_path / "deck.html")
    rc2, html_out = _run("r08-wajiancheng-mvp", ["deck", "html", "--input", src, "--out", target])
    assert html_out["verdict"] == "PASS", html_out.get("checks")
    body = open(target, encoding="utf-8").read()
    assert body.startswith("<!doctype html>") and "page-break-after" in body

    bad = _deck(slides=_deck()["slides"][:3])
    rc3, bad_out = _run("r08-wajiancheng-mvp", ["deck", "plan", "--input", _write(tmp_path, "bad.json", bad)])
    assert bad_out["verdict"] == "FAIL"


# --------------------------------------------------------------------------- #
# R10 · brandcheck
# --------------------------------------------------------------------------- #
def test_r10_brandcheck_against_design_md(tmp_path):
    good = {"colors": ["#0F172A", "#22D3EE"], "fonts": ["system-ui"],
            "text_pairs": [{"fg": "#F8FAFC", "bg": "#0F172A"}]}
    rc, out = _run("r10-wachengmei-design", ["brandcheck", "check",
                                             "--input", _write(tmp_path, "b.json", good)])
    assert out["verdict"] == "PASS", [c for c in out["checks"] if not c["ok"]]

    bad = {"colors": ["#FF00FF"], "fonts": ["Comic Sans"]}
    rc2, out2 = _run("r10-wachengmei-design", ["brandcheck", "check",
                                               "--input", _write(tmp_path, "bad.json", bad)])
    assert out2["verdict"] == "FAIL"
    dims = {c["dim"] for c in out2["checks"] if not c["ok"]}
    assert "brand.colors.known" in dims and "brand.fonts" in dims


# --------------------------------------------------------------------------- #
# R07 · prdguard / R08 · htmlreport / miniapp / R10 · imgops
# --------------------------------------------------------------------------- #
def _prd():
    return {
        "title": "会员券分层",
        "product_contract": {"user": "复购 2 次以上", "trigger": "订单完成 7 天",
                             "job": "把复购周期压到 21 天", "completion": "券核销并二次下单"},
        "p0_features": [
            {"name": "分层发券", "trigger": "订单完成 7 天", "rule": "按客单分 3 档",
             "result": "收到券", "state": "待核销", "source": "judgment"},
            {"name": "核销提醒", "trigger": "到期前 48h", "rule": "未核销推 1 次",
             "result": "推送成功", "state": "已提醒", "source": "evidence"},
        ],
        "non_goals": ["不做全场折扣", "不做新客首单"],
        "edge_cases": ["券库存不足降档", "通知失败重试 2 次"],
        "assumptions": ["21 天可达"], "open_questions": ["券成本上限"],
    }


def test_r07_prd_guard_and_render(tmp_path):
    src = _write(tmp_path, "prd.json", _prd())
    rc, out = _run("r07-wademing-pm", ["prdguard", "check", "--input", src])
    assert rc == 0 and out["ok"], [c for c in out["checks"] if not c["ok"]]
    target = str(tmp_path / "prd.md")
    rc2, out2 = _run("r07-wademing-pm", ["prdguard", "render", "--input", src, "--out", target])
    assert out2["ok"] and os.path.isfile(target)
    assert "产品契约" in open(target, encoding="utf-8").read()

    bad = _prd()
    bad["p0_features"][0].pop("state")
    bad["non_goals"] = ["只有一条"]
    rc3, out3 = _run("r07-wademing-pm", ["prdguard", "check", "--input",
                                         _write(tmp_path, "bad.json", bad)])
    assert not out3["ok"]


def test_r08_html_report(tmp_path):
    report = {"title": "Q4 复盘", "meta": {"audience": "管理层", "purpose": "决定加投"},
              "chapters": [{"title": "结论", "summary": "复购是主因", "paragraphs": ["+18%"]},
                           {"title": "流量", "summary": "自然升转化降"},
                           {"title": "动作", "summary": "先修履约"}],
              "thesis": ["复购 62%", "履约漏点", "只投 ROI>2"],
              "sources": [{"label": "生意参谋"}, {"label": "财务月报"}, {"label": "履约系统"}]}
    target = str(tmp_path / "report.html")
    rc, out = _run("r08-wajiancheng-mvp", ["htmlreport", "html", "--input",
                                           _write(tmp_path, "r.json", report), "--out", target])
    assert out["verdict"] == "PASS", out.get("checks")
    body = open(target, encoding="utf-8").read()
    assert body.startswith("<!doctype html>") and "http" not in body


def test_r08_miniapp_scaffold(tmp_path):
    spec = {"name": "wawa-shop", "pages": [{"path": "pages/home/index", "title": "首页"},
                                           {"path": "pages/cart/index", "title": "购物车"}],
            "tabbar": [{"page": "pages/home/index"}, {"page": "pages/cart/index"}]}
    src = _write(tmp_path, "mini.json", spec)
    rc, out = _run("r08-wajiancheng-mvp", ["miniapp", "plan", "--input", src])
    assert out["verdict"] == "PASS"
    target = str(tmp_path / "app")
    rc2, out2 = _run("r08-wajiancheng-mvp", ["miniapp", "scaffold", "--input", src, "--out", target])
    assert out2["verdict"] == "PASS" and out2["file_count"] >= 9
    assert os.path.isfile(os.path.join(target, "package.json"))


def test_r10_imgops_resize_and_overwrite_guard(tmp_path):
    from PIL import Image
    src = tmp_path / "src.png"
    Image.new("RGB", (800, 600), (15, 23, 42)).save(src)
    out = str(tmp_path / "out.jpg")
    rc, data = _run("r10-wachengmei-design", ["imgops", "resize", "--input", str(src),
                                              "--out", out, "--width", "400"])
    assert data["verdict"] == "PASS" and data["width"] == 400
    rc2, bad = _run("r10-wachengmei-design", ["imgops", "resize", "--input", str(src),
                                              "--out", str(src), "--width", "100"])
    assert bad["verdict"] == "FAIL"
    assert any(c["dim"] == "img.overwrite" and not c["ok"] for c in bad["checks"])
