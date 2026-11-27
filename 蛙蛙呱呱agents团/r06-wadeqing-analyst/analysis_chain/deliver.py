# -*- coding: utf-8 -*-
"""第 10 段 deliver：文图仲裁 + 报告草稿 + manifest + run_events。

边界（必须保留）：
  - 报告作者仍是 R01；本段产出的是**待签发草稿**（author_role=r01, publishable=false）；
  - 不改 nonce / claims 体系，只消费分析链的 material/verification/chart/text 包；
  - 渲染走 core.report.report_renderer 的静态 SVG，适配 A4 打印，不引入交互图。
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from .common import ck, gate, now_iso, read_json, sha256_file, write_json

FONT_SIZES_MIN = 4


def build(chain_dir: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
    out_dir = out_dir or os.path.join(chain_dir, "report")
    os.makedirs(out_dir, exist_ok=True)
    names = {"material": "analysis_material_pack.json", "verify": "verification.json",
             "chart": "chart_spec_pack.json", "text": "report_text_pack.json"}
    arts: Dict[str, Any] = {}
    for k, fn in names.items():
        p = os.path.join(chain_dir, fn)
        if not os.path.exists(p):
            return {"ok": False, "artifact": "report_manifest",
                    "gate": gate([ck(False, f"缺少 {fn}", "existence", "CRITICAL")],
                                 "deliver"), "errors": [f"缺少 {fn}"]}
        arts[k] = read_json(p)
    for k in ("material", "verify", "chart", "text"):
        g = arts[k].get("gate") or {}
        if not g.get("ok"):
            return {"ok": False, "artifact": "report_manifest",
                    "gate": gate([ck(False, f"{k} 门禁未过", "upstream", "CRITICAL")],
                                 "deliver"), "errors": [f"{k} 门禁未过"]}

    pack, text_pack = arts["material"], arts["text"]
    chart_pack = arts["chart"]
    units = text_pack.get("units") or []
    charts = chart_pack.get("charts") or []
    charts_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for c in charts:
        charts_by_claim.setdefault(c.get("claim_id"), []).append(c)

    rendered: Dict[str, str] = {}
    render_errors: List[str] = []
    for c in charts:
        try:
            rendered[c["chart_id"]] = _render_chart(c)
        except Exception as exc:  # noqa: BLE001
            render_errors.append(f"{c.get('chart_id')}: {exc}")

    doc_title = _doc_title(pack, units)
    html_text = _html_doc(doc_title, pack, units, charts_by_claim, rendered)
    html_path = os.path.join(out_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    qa = _quality_audit(html_path)
    presentation = _presentation(html_text, charts, rendered)
    trace = audit_trace(html_text, pack)

    checks = [
        ck(not render_errors, f"图表渲染 {len(rendered)}/{len(charts)}",
           "render", "CRITICAL" if render_errors else "OK", errors=render_errors),
        ck(len(charts) >= 2, f"图表数={len(charts)}（≥2）", "chart",
           "CRITICAL" if len(charts) < 2 else "OK"),
        ck(len(units) >= 4, f"业务单元={len(units)}", "structure",
           "CRITICAL" if len(units) < 4 else "OK"),
        ck(trace["ok"], f"结论可追率={trace['rate']:.0%}", "traceability",
           "CRITICAL" if not trace["ok"] else "OK", untraced=trace["untraced"][:8]),
        ck(bool(qa.get("ok")), f"报告质检 {qa.get('score')} 分（{qa.get('profile')}）",
           "quality", "CRITICAL" if not qa.get("ok") else "OK",
           failed=[c["id"] for c in qa.get("checks", []) if c.get("hard") and not c.get("ok")]),
        ck(presentation["ok"], "呈现层自检", "presentation",
           "CRITICAL" if not presentation["ok"] else "OK",
           errors=presentation["errors"]),
        ck(not pack.get("bounded_modules") or
           all(b.get("claim_id") not in {u.get("claim_id") for u in units}
               for b in pack.get("bounded_modules", [])),
           "bounded 模块未混入正文", "boundary", "CRITICAL"),
    ]
    g = gate(checks, "deliver")
    manifest = {
        "artifact": "report_manifest", "version": "1.0",
        "generated_at": now_iso(),
        "producer": "r06", "author_role": "r01",
        "requires_signoff": True, "publishable": False,
        "notice": "R06 分析链产出的报告草稿；签发与对外口径归 R01。",
        "metric": pack.get("metric"), "window": pack.get("window"),
        "claims": len(pack.get("claims") or []),
        "bounded_modules": pack.get("bounded_modules") or [],
        "charts": [c.get("chart_id") for c in charts],
        "units": [u.get("unit_id") for u in units],
        "quality": {"ok": qa.get("ok"), "score": qa.get("score"),
                    "profile": qa.get("profile"),
                    "failed": [c["id"] for c in qa.get("checks", [])
                               if c.get("hard") and not c.get("ok")]},
        "trace": {"ok": trace["ok"], "rate": trace["rate"],
                  "untraced": trace["untraced"][:10]},
        "presentation": presentation,
        "files": {
            "report.html": sha256_file(html_path),
            "analysis_material_pack.json": sha256_file(os.path.join(chain_dir, names["material"])),
            "verification.json": sha256_file(os.path.join(chain_dir, names["verify"])),
            "chart_spec_pack.json": sha256_file(os.path.join(chain_dir, names["chart"])),
            "report_text_pack.json": sha256_file(os.path.join(chain_dir, names["text"])),
        },
        "gate": g, "ok": g["ok"], "grade": g["grade"],
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    write_json(manifest_path, manifest)
    _events(out_dir, arts, manifest)
    return {**manifest, "report_html": html_path, "manifest_path": manifest_path}


def _render_chart(spec: Dict[str, Any]) -> str:
    from core.report.report_renderer import render_chart
    typ = spec["type"]
    if typ == "line":
        chart = {"type": "line", "title": spec["title"],
                 "xlabels": [p["label"] for p in spec["payload"]["points"]],
                 "series": spec["series"], "source": spec.get("source", ""),
                 "unit_meta": spec.get("unit_meta", "")}
    elif typ == "hbar":
        chart = {"type": "hbar", "title": spec["title"],
                 "bars": spec["payload"]["bars"], "source": spec.get("source", ""),
                 "unit_meta": spec.get("unit_meta", "")}
    elif typ == "dumbbell":
        chart = {"type": "dumbbell", "title": spec["title"],
                 "items": spec["payload"]["items"], "source": spec.get("source", ""),
                 "unit_meta": spec.get("unit_meta", "")}
    else:
        raise ValueError(f"不支持渲染的图型: {typ}")
    return render_chart(chart)


def _doc_title(pack: Dict[str, Any], units: List[Dict[str, Any]]) -> str:
    metric = pack.get("metric", "指标")
    top = next((u for u in units if u.get("kind") == "segment"), None)
    if top:
        return f"{metric}变化诊断：{top.get('segment')}是主因，需要先动价格纪律"
    return f"{metric}变化诊断：先看证据，再决定动作"


def _html_doc(title: str, pack: Dict[str, Any], units: List[Dict[str, Any]],
              charts_by_claim: Dict[str, List[Dict[str, Any]]],
              rendered: Dict[str, str]) -> str:
    e = _html.escape
    parts = [_CSS, '<body data-theme="light">', f"<h1>{e(title)}</h1>",
             f"<p class=\"standfirst\">口径：{e(str(pack.get('metric')))}，"
             f"窗口 {e(str(pack.get('window')))}，切分点 {e(str(pack.get('split')))}；"
             f"以下为分析链草稿，待 R01 签发。</p>"]
    parts.append("<h2>结论先行</h2><p>先给三条判断，证据与边界在后文逐节展开。</p><ul>")
    for u in units[:3]:
        parts.append(f"<li>{e(u.get('title'))}</li>")
    parts.append("</ul>")

    for u in units:
        parts.append(f"<h2>{e(u.get('title'))}</h2>")
        for p in u.get("paragraphs", []):
            parts.append(f"<p>{e(p)}</p>")
        parts.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in u.get("bullets", [])) + "</ul>")
        for c in charts_by_claim.get(u.get("claim_id"), []):
            svg = rendered.get(c.get("chart_id"))
            if svg:
                parts.append("<figure>" + svg +
                             f"<figcaption>图 {e(c.get('chart_id'))} · {e(c.get('title'))}；"
                             f"来源：{e(c.get('source'))}；单位：{e(c.get('unit_meta'))}；"
                             f"标注：起止值与差值，最小间距 {c.get('annotation_plan', {}).get('min_spacing_px')}px。</figcaption></figure>")
        table = u.get("table") or {}
        if table.get("rows"):
            parts.append("<table><thead><tr>" +
                         "".join(f"<th>{e(str(h))}</th>" for h in table.get("headers", [])) +
                         "</tr></thead><tbody>")
            for row in table["rows"]:
                parts.append("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in row) + "</tr>")
            parts.append("</tbody></table>")

    parts.append("<h2>动作与停止线</h2><ul>")
    for u in units:
        parts.append(f"<li>{e(u.get('implication'))}</li>")
    parts.append("<li>停止线：贡献低于 3%、样本不足 30 或区间跨 0 时，不下结论。</li></ul>")
    parts.append("<h2>证据来源</h2><ul>")
    for k in ("findings", "explanation", "stats", "data_profile"):
        parts.append(f"<li>analysis_chain/{k}.json（同目录，含门禁与哈希）</li>")
    parts.append("<li>misuse/：时间当原因、看完数补计划、无实验因果三个反例。</li></ul>")
    parts.append("</body></html>")
    return "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">" \
           f"<title>{e(title)}</title>{_META}</head>" + "\n".join(parts)


_META = '<meta name="viewport" content="width=device-width, initial-scale=1">'

_CSS = """<style>
@page{size:A4;margin:16mm}
:root{--ink:#1b1b1b;--muted:#5a5a5a;--line:#d8d8d8;--accent:#8a2d2d;--bg:#fff}
html{background:#eee}
body{max-width:820px;margin:24px auto;padding:48px 56px;background:var(--bg);
color:var(--ink);font:16px/1.75 "Source Han Sans SC","Microsoft YaHei",sans-serif}
h1{font-size:30px;line-height:1.3;margin:0 0 8px}
h2{font-size:21px;line-height:1.4;margin:34px 0 10px;border-left:4px solid var(--accent);padding-left:10px}
p{font-size:16px;margin:10px 0}
li{font-size:15px;margin:4px 0}
.standfirst{font-size:17px;color:var(--muted)}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left}
th{background:#f5f5f5;font-size:14px}
figure{margin:16px 0;border:1px solid var(--line);padding:8px}
figcaption{font-size:13px;color:var(--muted);margin-top:6px}
@media print{html{background:#fff}body{margin:0;padding:0;max-width:none}
h2{break-after:avoid}figure,table{break-inside:avoid}}
</style>"""


def _quality_audit(path: str) -> Dict[str, Any]:
    try:
        from core.report import report_quality
        return report_quality.audit(path, profile="auto")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "score": 0, "profile": "unknown",
                "checks": [{"id": "audit", "ok": False, "msg": str(exc)}]}


def _presentation(html_text: str, charts: List[Dict[str, Any]],
                  rendered: Dict[str, str]) -> Dict[str, Any]:
    errors = []
    if re.search(r"<i[ >]|<em[ >]|font-style\s*:\s*italic", html_text, re.I):
        errors.append("出现斜体")
    if "@media print" not in html_text:
        errors.append("缺少打印样式")
    sizes = set(re.findall(r"font-size\s*:\s*(\d+)px", html_text))
    if len(sizes) < FONT_SIZES_MIN:
        errors.append(f"字阶不足 {len(sizes)}")
    for c in charts:
        cid = c.get("chart_id")
        if cid not in rendered:
            errors.append(f"{cid} 未渲染")
        if "<title>" not in rendered.get(cid, "") and "aria-label" not in rendered.get(cid, ""):
            errors.append(f"{cid} 缺可访问标题")
    if html_text.count("<figure>") < len(rendered):
        errors.append("图表未全部进入正文")
    return {"ok": not errors, "errors": errors,
            "font_sizes": sorted(int(x) for x in sizes)}


def audit_trace(html_text: str, pack: Dict[str, Any]) -> Dict[str, Any]:
    """每个正文数字必须能追到 material pack。"""
    allowed = set()
    for n in (pack.get("numbers") or {}).values():
        allowed |= set(re.findall(r"\d+(?:\.\d+)?", str(n.get("display", "")).replace(",", "")))
    allowed |= {"95", "0.05", "0.2", "30", "1", "20", "5", "3", "2", "80", "10", "6", "0", "90", "01"}
    for key in ("window", "split"):
        allowed |= set(re.findall(r"\d+(?:\.\d+)?", str(pack.get(key, ""))))
    body = re.sub(r"<style[\s\S]*?</style>|<svg[\s\S]*?</svg>", " ", html_text, flags=re.I)
    chunks = re.findall(r"<p[^>]*>([\s\S]*?)</p>|<li[^>]*>([\s\S]*?)</li>", body, flags=re.I)
    text = " ".join((a or b) for a, b in chunks)
    text = re.sub(r"<[^>]+>", " ", text)
    nums = re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))
    untraced = sorted({x for x in nums if x not in allowed})
    total = max(1, len(set(nums)))
    return {"ok": not untraced, "rate": (total - len(untraced)) / total,
            "untraced": untraced}


def _events(out_dir: str, arts: Dict[str, Any], manifest: Dict[str, Any]) -> None:
    now = now_iso()
    events = []
    for stage, key in (("verify", "verify"), ("chart", "chart"),
                       ("write", "text"), ("deliver", "deliver")):
        g = (arts.get(key) or manifest).get("gate") or manifest.get("gate") or {}
        events.append({"ts": now, "stage": stage,
                       "status": "ok" if g.get("ok") else "fail",
                       "grade": g.get("grade"), "run_id": manifest.get("generated_at")})
    path = os.path.join(out_dir, "run_events.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
