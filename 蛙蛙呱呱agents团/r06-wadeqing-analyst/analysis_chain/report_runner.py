# -*- coding: utf-8 -*-
"""T8b 编排：material → verify → chart → write → deliver。

输入是 T8a 的链条目录（6 个工件齐全）。输出：
  analysis_material_pack.json / verification.json / chart_spec_pack.json /
  report_text_pack.json / report/report.html + manifest.json + run_events.jsonl
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from . import chart_pack, deliver, material_pack, text_pack, verify
from .common import ck, gate, read_json, write_json


def _load(chain_dir: str) -> Dict[str, Any]:
    return {
        "findings": read_json(os.path.join(chain_dir, "findings.json")),
        "explanation": read_json(os.path.join(chain_dir, "explanation.json")),
        "stats": read_json(os.path.join(chain_dir, "stats.json")),
        "profile": read_json(os.path.join(chain_dir, "data_profile.json")),
    }


def stage_material(chain_dir: str) -> Dict[str, Any]:
    pack = material_pack.build(chain_dir)
    write_json(os.path.join(chain_dir, "analysis_material_pack.json"), pack)
    return pack


def stage_verify(chain_dir: str) -> Dict[str, Any]:
    arts = _load(chain_dir)
    pack = stage_material(chain_dir)
    if not (pack.get("gate") or {}).get("ok"):
        return pack
    ver = verify.build(pack, arts["findings"], arts["explanation"], arts["profile"])
    write_json(os.path.join(chain_dir, "verification.json"), ver)
    return ver


def stage_chart(chain_dir: str) -> Dict[str, Any]:
    arts = _load(chain_dir)
    pack = read_json(os.path.join(chain_dir, "analysis_material_pack.json")) \
        if os.path.exists(os.path.join(chain_dir, "analysis_material_pack.json")) \
        else stage_material(chain_dir)
    ver = read_json(os.path.join(chain_dir, "verification.json")) \
        if os.path.exists(os.path.join(chain_dir, "verification.json")) \
        else stage_verify(chain_dir)
    charts = chart_pack.build(pack, arts["findings"], ver)
    write_json(os.path.join(chain_dir, "chart_spec_pack.json"), charts)
    return charts


def stage_write(chain_dir: str) -> Dict[str, Any]:
    arts = _load(chain_dir)
    pack = read_json(os.path.join(chain_dir, "analysis_material_pack.json")) \
        if os.path.exists(os.path.join(chain_dir, "analysis_material_pack.json")) \
        else stage_material(chain_dir)
    ver = read_json(os.path.join(chain_dir, "verification.json")) \
        if os.path.exists(os.path.join(chain_dir, "verification.json")) \
        else stage_verify(chain_dir)
    charts = read_json(os.path.join(chain_dir, "chart_spec_pack.json")) \
        if os.path.exists(os.path.join(chain_dir, "chart_spec_pack.json")) \
        else stage_chart(chain_dir)
    text = text_pack.build(pack, ver, charts, arts["explanation"], arts["profile"],
                           arts["stats"])
    write_json(os.path.join(chain_dir, "report_text_pack.json"), text)
    return text


def stage_deliver(chain_dir: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
    if not os.path.exists(os.path.join(chain_dir, "report_text_pack.json")):
        stage_write(chain_dir)
    return deliver.build(chain_dir, out_dir)


def run_report(chain_dir: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
    for fn in ("findings.json", "explanation.json", "stats.json", "data_profile.json",
               "frame.json", "analysis_plan.json"):
        if not os.path.exists(os.path.join(chain_dir, fn)):
            return {"ok": False, "artifact": "report_chain", "errors": [f"缺少 {fn}"],
                    "gate": gate([ck(False, f"缺少 {fn}", "existence", "CRITICAL")],
                                 "report_chain")}
    pack = stage_material(chain_dir)
    if not (pack.get("gate") or {}).get("ok"):
        return _fail(pack, "material_pack")
    ver = stage_verify(chain_dir)
    if not (ver.get("gate") or {}).get("ok"):
        return _fail(ver, "verify")
    charts = stage_chart(chain_dir)
    if not (charts.get("gate") or {}).get("ok"):
        return _fail(charts, "chart")
    text = stage_write(chain_dir)
    if not (text.get("gate") or {}).get("ok"):
        return _fail(text, "write")
    report = stage_deliver(chain_dir, out_dir)
    report["artifact"] = "report_chain"
    report["stages"] = {
        "material_pack": pack.get("gate"),
        "verify": ver.get("gate"),
        "chart": charts.get("gate"),
        "write": text.get("gate"),
        "deliver": report.get("gate"),
    }
    report["bounded_modules"] = pack.get("bounded_modules", [])
    return report


def run_all(question: str, data_path: str, out_dir: str, start: str, end: str,
            split: str, **kwargs: Any) -> Dict[str, Any]:
    from . import runner
    manifest = runner.run(question, data_path, out_dir, start, end, split, **kwargs)
    if not manifest.get("ok"):
        return {"ok": False, "artifact": "report_chain", "stage": "analysis_chain",
                "analysis": manifest, "gate": manifest.get("gate"),
                "errors": (manifest.get("gate") or {}).get("errors", [])}
    report = run_report(out_dir, os.path.join(out_dir, "report"))
    report["analysis"] = {"ok": manifest.get("ok"), "stages": manifest.get("stages")}
    return report


def _fail(art: Dict[str, Any], stage: str) -> Dict[str, Any]:
    g = art.get("gate") or {}
    return {"ok": False, "artifact": "report_chain", "stage": stage,
            "gate": g, "errors": g.get("errors", []), "detail": art}
