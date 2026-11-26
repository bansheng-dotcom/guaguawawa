# -*- coding: utf-8 -*-
"""gates 域测试（合并自 2 个文件）。

源文件：
    test_gate_chain.py —— test_gate_chain —— 四层门禁链单测。
    test_gate_contract.py —— 产线自洽性回归（2026-11-20 事故的四条硬约束）。
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
import argparse
import tempfile
from core import dispatch, report_marks, r04_derive
from core.report_theme import pages



# ====================================================================
# 合并自 test_gate_contract.py：产线自洽性回归（2026-11-20 事故的四条硬约束）。
# ====================================================================
# -*- coding: utf-8 -*-


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="guagua_gate_"))


def _gate(tmp_path: Path, html: str):
    p = tmp_path / "report.html"
    p.write_text(html, encoding="utf-8")
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from check_report_flow import check_html  # noqa: PLC0415
    return check_html(p)


def _base_html(body: str) -> str:
    return ("<!doctype html><html><head><title>t</title></head><body>"
            "<header class='cover'><h1>12 亿元的市场</h1></header>"
            f"{body}</body></html>")


# --------------------------------------------------------------------------- #
# 1. 标记契约：渲染器挂的类，门禁必须认
# --------------------------------------------------------------------------- #
def test_figure_source_class_is_shared():
    frag = pages._chart_html({"chart": {"title": "图", "source": "某某统计局"}}, "图 1")
    assert report_marks.FIGURE_SRC_CLASS in frag
    assert report_marks.FIGURE_SRC_CSS_ALIAS in frag  # 旧 CSS 还认 ex-src


def test_figure_source_without_text_fails():
    # 只有 class、没有来源文字：以前能过（数 class 个数），现在必须拦
    fig = ('<figure class="ex"><svg></svg>'
           f'<div class="{report_marks.FIGURE_SRC_CLASSES}"></div></figure>')
    r = _gate(_tmp(), _base_html(
        f'<section id="summary"><p>结论 12 亿元。</p></section>{fig}'
        '<section><h2>1 节 12 亿元</h2><p>正文 12 亿元。</p></section>'))
    assert "F7_figure_source" in [v["id"] for v in r["violations"]]


# --------------------------------------------------------------------------- #
# 2. 边界：只挂 data-label 不算
# --------------------------------------------------------------------------- #
def test_boundary_attribute_only_fails():
    sec = (f'<section><h2>1 节 12 亿元</h2><p>正文 12 亿元。</p>'
           f'<div class="boundary" data-label="{report_marks.BOUNDARY_LABEL}">'
           f'<b>边界</b></div></section>')
    r = _gate(_tmp(), _base_html(
        f'<section id="summary"><p>结论 12 亿元。</p></section>{sec}'))
    assert "F5_boundary" in [v["id"] for v in r["violations"]]


def test_boundary_with_text_passes_f5():
    txt = "只覆盖 2025 年口径，不含个体工商户与线上外溢。"
    sec = (f'<section><h2>1 节 12 亿元</h2><p>正文 12 亿元。</p>'
           f'<div class="boundary" data-label="{report_marks.BOUNDARY_LABEL}">'
           f'<b>边界</b>{txt}</div></section>')
    r = _gate(_tmp(), _base_html(
        f'<section id="summary"><p>结论 12 亿元。</p></section>{sec}'))
    assert "F5_boundary" not in [v["id"] for v in r["violations"]]


# --------------------------------------------------------------------------- #
# 3. 不许自证门禁
# --------------------------------------------------------------------------- #
def test_self_certified_gate_fails():
    r = _gate(_tmp(), _base_html(
        '<section id="summary"><p>结论 12 亿元，全部门禁通过。</p></section>'))
    assert "F11_self_certified" in [v["id"] for v in r["violations"]]


# --------------------------------------------------------------------------- #
# 4. 来源按唯一 URL 计数 + 降级必须显式授权
# --------------------------------------------------------------------------- #
def _card(role: str, url: str, title: str) -> dict:
    return {
        "meta": {"title": "测试报告"},
        "numbers": [{"id": "N1", "name": "规模", "value": 12, "unit": "亿元",
                     "source_file": "S1"}],
        "sources": [{"file": "S1", "kind": "web", "url": url, "date": "2026-01-01",
                     "quote": "这是一条足够长的原文引文用于字段校验"}],
        "sections": [{"title": f"{title} 12 亿元", "refs": ["N1"],
                      "reading": [{"text": "一"}, {"text": "二"}],
                      "falsifier": "若跌破 10 亿元则作废"}],
    }


def test_min_sources_counts_unique_urls():
    base = _tmp() / "proj"
    for role in ("r05", "r06"):
        d = base / "cards" / role
        d.mkdir(parents=True)
        (d / "TASK.md").write_text("task", encoding="utf-8")
        (d / "claims.json").write_text(
            json.dumps(_card(role, "https://example.com/a?utm_source=x", role),
                       ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(base), min_sources=2)
    assert merged["evidence"]["sources"] == 2
    assert merged["evidence"]["unique_sources"] == 1
    assert merged["evidence"]["duplicate_sources"] == 1
    assert any("唯一来源" in p for p in problems)


def test_collect_refuses_silent_degradation():
    import contextlib
    import io
    from core import report_cli
    ns = argparse.Namespace(dir="x", out="y", intent="", pdf=False,
                            allow_partial=False, min_sources=50,
                            verify_quotes=True, strict_quotes=False,
                            allow_degraded=False)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = report_cli.cmd_collect(ns)
    assert rc == 2
    assert "allow-degraded" in buf.getvalue()


# --------------------------------------------------------------------------- #
# 5. R04 输入必须是派生的
# --------------------------------------------------------------------------- #
def test_r04_inputs_must_be_derived():
    tmp_path = _tmp()
    (tmp_path / "report.html").write_text("<html>12</html>", encoding="utf-8")
    (tmp_path / "report.md").write_text("12", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps({"gate": {"flow": {"ok": True, "verdict": "PASS"}},
                    "evidence": {"files": 1, "unique_sources": 1}}, ensure_ascii=False),
        encoding="utf-8")
    # 手写的输入：没有 derived_from
    (tmp_path / "r04_criteria.json").write_text(
        json.dumps({"criteria": [{"id": "C1", "evidence": "verified: x"}]},
                   ensure_ascii=False), encoding="utf-8")
    bad = r04_derive.check(str(tmp_path))
    assert bad["ok"] is False
    assert any("不是 core.r04_derive 派生" in p for p in bad["problems"])

    # 派生一遍，再核
    r04_derive.derive(str(tmp_path))
    assert r04_derive.check(str(tmp_path))["ok"] is True

    # 产物换了但输入没重派生 → 必须失败
    (tmp_path / "report.html").write_text("<html>变了 13</html>", encoding="utf-8")
    assert r04_derive.check(str(tmp_path))["ok"] is False


# ====================================================================
# 2026-11-26：门禁假绿修复（隔离 glob / 接线真相）
# ====================================================================

def _load_script(name: str):
    import importlib.util
    p = TEAM / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_gate_{name}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_report_isolation_detects_violation(tmp_path):
    """隔离门禁必须能抓到 core/report/ 子包里的越界 import（防假绿）。"""
    iso = _load_script("check_report_isolation")
    bad = tmp_path / "bad.py"
    bad.write_text("from shared.knowledge import brief\n", encoding="utf-8")
    good = tmp_path / "good.py"
    good.write_text("from core import paths\n", encoding="utf-8")
    assert iso.scan([bad])
    assert iso.scan([good]) == []


def test_wiring_truth_state_is_registered():
    """未接线模块必须显式登记；文档不得指向已删模块。"""
    wt = _load_script("wiring_truth")
    data = wt.build()
    problems = wt._check(data)
    assert problems == [], "\n".join(problems)
