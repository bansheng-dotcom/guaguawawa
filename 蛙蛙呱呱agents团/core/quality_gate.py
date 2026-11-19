# -*- coding: utf-8 -*-
"""core/quality_gate —— 三层质检：证据 / 编辑 / 呈现（v11 / P5）。

为什么要有这一层：
    改造前门禁是散的——`check_sections`（R01 子进程）、`report_quality`（HTML 深度）、
    `check_report_flow`（九条）、`report_model`（语义层）、`check_report_presentation`（呈现）。
    散着的问题不是「不够严」，是**没有一处能回答「这份报告到底能不能发」**：
    每道门各说各话，manifest 里 `ok` 由调用方随手拼。

本模块把三层收成一个判定：

    evidence      数字能不能复算、来源齐不齐、有没有编造
    editorial     有没有先答用户的问题、每节有机理与证伪、跨节不复读
    presentation  斜体 / 打印 / 对比度 / 字阶 / 图四件套 / 主题

纪律：
1. **三层全过才 ok**；任何一层 fail 都 block（不是 warn）。
2. 复用已有实现，不重写判据：evidence 用 `report_flow.check_sections` 的结果，
   editorial 用 `report_quality.audit`，presentation 用 `check_report_presentation`。
3. 本模块只做「聚合 + 解释」，不新增阈值。阈值仍在上游各自的 PROFILES 里。

用法：
    python -m core.quality_gate --draft <draft_sections.json> --pack <evidence_pack.json> \
        --html <report.html>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "dsh.quality_gate/v1"


def _evidence(draft: Dict[str, Any], pack: Dict[str, Any],
              section_check: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """证据层：数字可复算 + 来源齐 + 无编造。

    `section_check` 是 R01 s09 的逐节过账结果（report_flow 已跑过就传进来，避免跑两遍）；
    没传就现跑一次。
    """
    from core import report_flow
    if section_check is None:
        try:
            section_check = report_flow.check_sections(draft, pack)
        except Exception as exc:  # noqa: BLE001
            return {"layer": "evidence", "ok": False,
                    "detail": {"error": f"{type(exc).__name__}: {exc}"}}
    checks = section_check.get("checks") or []
    failed = [c.get("id") for c in checks if not c.get("ok")]
    return {
        "layer": "evidence",
        "ok": bool(section_check.get("ok")) and not failed,
        "detail": {
            "checks": len(checks),
            "failed": failed,
            "sections": section_check.get("sections"),
            "pack_numbers": len(pack.get("numbers") or []),
        },
    }


def _editorial(html_path: str) -> Dict[str, Any]:
    """编辑层：先答问题 + 每节有机理与证伪 + 不复读。"""
    from core import report_quality
    qa = report_quality.audit(html_path)
    hard_fail = [c["id"] for c in (qa.get("checks") or [])
                 if c.get("hard") and not c.get("ok")]
    return {
        "layer": "editorial",
        "ok": bool(qa.get("ok")) and not hard_fail,
        "detail": {
            "profile": qa.get("profile"),
            "score": qa.get("score"),
            "sections": qa.get("sections"),
            "density": qa.get("density"),
            "hard_failed": hard_fail,
        },
    }


def _presentation(html_path: str) -> Dict[str, Any]:
    """呈现层：斜体 / 打印 / 对比度 / 字阶 / 图四件套 / 主题串色。"""
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_report_presentation import check_html
    pres = check_html(Path(html_path))
    return {
        "layer": "presentation",
        "ok": bool(pres.get("ok")),
        "detail": {
            "figures": pres.get("figures"),
            "type_steps": len(pres.get("type_steps") or []),
            "violations": [v.get("id") for v in (pres.get("violations") or [])],
            "contrast": pres.get("contrast"),
        },
    }


def _contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """契约呈现层：标题带数字 / 图下来源与口径 / B 页 rail 够数。"""
    from core import report_editorial
    res = report_editorial.check_contract(contract)
    return {"layer": "contract", "ok": bool(res.get("ok")),
            "detail": {"hard": res.get("hard") or [], "warn": res.get("warn") or [],
                       "sections": res.get("sections")}}


def _pages(html_path: str) -> Dict[str, Any]:
    """consulting 页式：封面/节页/页码/图表 aria；旧 DOM 判据不适用。"""
    from pathlib import Path
    h = Path(html_path).read_text(encoding="utf-8", errors="replace")
    pages = h.count('class="page')
    charts = h.count("<svg")
    bad = []
    if pages < 5:
        bad.append(f"页数过少（{pages}）")
    if 'class="page cover"' not in h:
        bad.append("缺封面")
    if "rail-float" in h and 'class="page sec rail-layout"' not in h:
        bad.append("rail 未落在 B 页")
    return {"layer": "pages", "ok": not bad,
            "detail": {"pages": pages, "charts": charts, "bad": bad}}


def _coverage(coverage: Dict[str, Any]) -> Dict[str, Any]:
    """覆盖层：R04 五项（覆盖/数据/图表/版式/文笔）的完整审计。"""
    from core import r04_audit
    res = r04_audit.audit(
        coverage.get("frame") or {}, coverage.get("plan") or {},
        coverage.get("sources") or {}, coverage.get("html") or "",
        int(coverage.get("min_pages", 21)),
        bool(coverage.get("prose_hard", True)),
        coverage.get("pdf"))
    return {"layer": "coverage", "ok": bool(res.get("ok")), "detail": res}


def check(draft: Optional[Dict[str, Any]] = None, pack: Optional[Dict[str, Any]] = None,
          html: Optional[str] = None,
          section_check: Optional[Dict[str, Any]] = None,
          contract: Optional[Dict[str, Any]] = None,
          coverage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """三层全过才 ok。缺输入的那层记 skipped（不算过，也不算不过）。"""
    layers: List[Dict[str, Any]] = []
    if draft and pack:
        layers.append(_evidence(draft, pack, section_check))
    if contract:
        layers.append(_contract(contract))
    if coverage:
        layers.append(_coverage(coverage))
    if html is not None:
        # 传了 HTML 就必须存在：缺文件 = 编辑/呈现两层没跑，不能当成「跳过而通过」
        if not Path(html).exists():
            layers.append({"layer": "presentation", "ok": False,
                           "detail": {"bad": [f"HTML 不存在：{html}"]}})
        elif contract and str(contract.get("theme") or "") == "consulting":
            layers.append(_pages(html))
        else:
            layers.append(_editorial(html))
            layers.append(_presentation(html))
    if not layers:
        return {"schema": SCHEMA, "ok": False, "layers": [],
                "error": "没有任何可检的输入"}
    ran = [l for l in layers if l.get("ok") is not None]
    ok = bool(ran) and all(l["ok"] for l in ran)
    return {
        "schema": SCHEMA,
        "ok": ok,
        "verdict": "PASS" if ok else "BLOCK",
        "layers": ran,
        "failed": [l["layer"] for l in ran if not l["ok"]],
        "note": "三层全过才放行；LLM 裁判只写诊断，不参与本判定",
    }


def describe(result: Dict[str, Any]) -> str:
    marks = {"evidence": "证据", "editorial": "编辑", "presentation": "呈现",
             "contract": "契约", "pages": "页式", "coverage": "覆盖"}
    parts = []
    for l in result.get("layers") or []:
        parts.append(f"{marks.get(l['layer'], l['layer'])}={'过' if l['ok'] else '不过'}")
    return ("三层质检：" + " / ".join(parts) +
            ("" if result.get("ok") else f"（卡在 {'、'.join(result.get('failed') or [])}）"))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="quality_gate", description="三层质检：证据/编辑/呈现")
    ap.add_argument("--draft", default=None, help="draft_sections.json")
    ap.add_argument("--pack", default=None, help="evidence_pack.json")
    ap.add_argument("--section-check", default=None, help="section_check.json（可选）")
    ap.add_argument("--html", default=None, help="report.html")
    ap.add_argument("--contract", default=None, help="contract.json（可选，查标题/图/rail）")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    draft = json.loads(Path(a.draft).read_text(encoding="utf-8-sig")) if a.draft else None
    pack = json.loads(Path(a.pack).read_text(encoding="utf-8-sig")) if a.pack else None
    sc = (json.loads(Path(a.section_check).read_text(encoding="utf-8-sig"))
          if a.section_check else None)
    contract = (json.loads(Path(a.contract).read_text(encoding="utf-8-sig"))
                if a.contract else None)
    res = check(draft, pack, a.html, sc, contract)
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
