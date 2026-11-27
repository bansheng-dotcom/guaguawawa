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
from core.cards import dispatch
from core.report import report_marks
from core import r04_derive
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
    from core.report import report_cli
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


# ====================================================================
# P5 收敛守卫：契约单一出处（P5-1）+ 文笔兜底 fail-closed（P5-2）
# ====================================================================
def test_claims_schema_declared_once():
    """合并后 claims 的 schema 只许在 claims/contract.py 里写一次。"""
    hits = []
    for p in (TEAM / "core").rglob("*.py"):
        if p.parent.name == "claims" and p.name == "contract.py":
            continue
        if '"dsh.agent.claims/v1"' in p.read_text(encoding="utf-8"):
            hits.append(p.relative_to(TEAM).as_posix())
    assert hits == [], hits


def test_claim_consistency_reads_through_contract():
    from core.claims import claim_consistency as cc, contract

    doc = {"numbers": [{"id": "N1", "name": " 规模 ", "value": 1,
                        "period": "2024", "source_file": "S1"}],
           "sources": [{"file": "S1", "grade": "b"}],
           "sections": [], "boundaries": ["仅样本"]}
    assert contract.norm_name(" 规模 ") == "规模"
    assert contract.grades(doc) == {"S1": "B"}
    assert cc.check(doc)["issues"]["C4_no_boundary"] == 0


def test_prose_defaults_match_config():
    """代码兜底值必须与 configs/report_prose.yaml 逐键一致，防止双写漂移。"""
    from core.report.report_contract import PROSE_DEFAULTS
    from core.prose import prose_contract

    pol = prose_contract.load_policy()
    for key, val in PROSE_DEFAULTS.items():
        if key == "banned_phrases":      # 禁用词表本来就只写在配置里
            continue
        if key == "rubric":              # 配置里 rubric 还带 weights 等扩展键
            assert pol[key]["pass"] == val["pass"]
            assert pol[key]["usable"] == val["usable"]
            continue
        assert pol[key] == val, f"{key}: fallback={val!r} config={pol[key]!r}"


def test_prose_fallback_is_fail_closed():
    """配置缺失时不能用宽松默认值放行薄稿。"""
    from core.prose import prose_contract

    pol = prose_contract.load_policy(TEAM / "configs" / "__no_such__.yaml")
    assert pol["chars_hard_min"] >= 800
    assert pol["numbers_per_1000_chars_min"] >= 15


def test_card_orchestration_has_single_entry():
    """P5-3：CLI 与预检只许走 cards.pipeline，不许绕过它调实现模块。"""
    cli = (TEAM / "core/report/report_cli.py").read_text(encoding="utf-8")
    pf = (TEAM / "scripts/preflight.py").read_text(encoding="utf-8")
    for src in (cli, pf):
        assert "report_dispatch." not in src
        assert "dispatch.collect" not in src
        assert "card_issue." not in src
    assert "from core.cards import pipeline" in cli


def test_card_pipeline_forwards(tmp_path, monkeypatch):
    """pipeline 只转发：收卡参数原样传给实现，验卡/发卡的读法不变。"""
    from core.cards import dispatch, pipeline

    assert pipeline.load_issued(str(tmp_path)) is None

    seen = {}

    def fake_collect(out_dir, **kw):
        seen.update({"out": out_dir, "kw": kw})
        return {}, []

    monkeypatch.setattr(dispatch, "collect", fake_collect)
    assert pipeline.collect(str(tmp_path), intent="t") == ({}, [])
    assert seen == {"out": str(tmp_path), "kw": {"intent": "t"}}


# ====================================================================
# P5-4 收敛守卫：映射层并入 claims、契约统一 v4、严格门禁覆盖历史版本
# ====================================================================
def test_claim_mapping_layer_merged_into_claims():
    from core.claims import claims

    for fn in ("detect", "validate_v4", "build_sections", "build_decision",
               "claim_to_section", "encoding_to_chart"):
        assert callable(getattr(claims, fn)), fn
    assert not (TEAM / "core/claims/claims_v4.py").exists()


def test_claim_contract_v4_and_strict_versions():
    from core.claims import contract

    assert contract.CONTRACT == "v4"
    for ver in ("v2", "v3", "v4"):
        assert contract.is_strict({"contract": ver}), ver
    assert not contract.is_strict({})
    assert contract.is_strict({"schema": "dsh.claims/v2"})
