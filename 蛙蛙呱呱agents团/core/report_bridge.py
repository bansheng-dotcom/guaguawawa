# -*- coding: utf-8 -*-
"""共享「结果 → 报告」桥（core 层，全 20 角色通用）。

解决现状问题（见 REPORT-STANDARD.md 开篇）：多数角色把 result JSON 直接拍成
markdown（`## ok` + 代码块），没有结论、没有排版——那是日志，不是汇报。

本模块把一次技能真实运行结果（result JSON）翻译成《REPORT-STANDARD.md》规定的
report contract，交给 core/report_renderer.py 确定性渲染 HTML，同时落一份
「结论先行」的 .md 快读摘要。双格式：.html（正式）+ .md（快读）。

用法（各角色 agent.py 的 run_task 末尾，替换原 _write_report）：

    from core import report_bridge
    ports = report_bridge.emit(
        role="r06", name="蛙得清", title="数据分析师",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, md_name="analysis_report",
        specialist=my_recon,   # 可选：本角色 result→contract 精细映射
        chart_dir=HERE,        # 可选：含 chart_lib.py 的目录（出图用）
    )
    outputs.extend(ports)

specialist 签名：specialist(result, skill, action, intent) -> dict | None；
返回 None 时回退到通用映射（generic_contract）。与 R03 report.py 的
recon_contract 模式一致。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
import shutil
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

AGENTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_RENDERER = os.path.join(AGENTS_ROOT, "core", "report_renderer.py")
# 共享 48 型图表库（原 R06 私有，已上收为全角色共用）。
SHARED_CHART_DIR = os.path.join(AGENTS_ROOT, "core", "charts")

# 子进程强制 UTF-8，避免 Windows 控制台 GBK 编码污染 JSON。
_CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8",
                  PYTHONUTF8="1", PYTHONPATH=AGENTS_ROOT)

# result 的元字段：不进正文 section（避免把 runtime_ms/task_id 拍进报告）。
_META_KEYS = {
    "ok", "checks", "runtime_ms", "task_id", "skill", "action",
    "type", "note", "advice_authorized", "verdict", "error", "raw",
    "status", "caveats", "provenance", "contract_warnings",
}

# 已经是「人话结论」的字段：优先直接放进 summary，不再摊成 section。
_CONCLUSION_KEYS = ("conclusion", "next", "summary", "insight", "finding",
                    "recommendation", "result_note", "message", "answer")


# ---------------------------------------------------------------- kernel 接入
from pathlib import Path as _Path
LEGACY_LIST = _Path(__file__).resolve().parent.parent / "configs" / "legacy_roles.txt"


def _use_kernel(role: str) -> bool:
    """角色是否走新内核：在 legacy 名单里 → 否；否则看有没有 spec。"""
    if LEGACY_LIST.exists():
        names = {x.strip() for x in LEGACY_LIST.read_text(encoding="utf-8").splitlines() if x.strip()}
        if role in names:
            return False
    from core.report_kernel import spec as _spec
    return _spec.role_spec_path(role).exists()


# 公开别名：shared/role_runtime.py 据此判断该角色走内核还是 REP-001 旧引擎
use_kernel = _use_kernel


def build_kernel_contract(role, name, title, result, skill, action, intent,
                          dataset=None, doc_type="角色报告", data=None):
    """data：技能的输入 JSON（PRD 类角色内容在输入不在 result，必须透传）。"""
    from core.report_kernel import layers as _layers, spec as _spec
    s = _spec.load(role)
    return _layers.build_contract(role, name, title, result, s, skill, action, intent,
                                  dataset=dataset, data=data)


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return f"{v:,.2f}"
    if v is None:
        return "—"
    return str(v)


def _first_scalar(obj: Any, keys: Sequence[str]) -> Optional[str]:
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and not isinstance(obj[k], (dict, list)):
                return f"{k}={_fmt(obj[k])}"
    return None


def _rows_from_list(lst: List[Any]) -> List[List[Dict[str, Any]]]:
    """把 list[dict] 摊平成证据表：列 = 键并集，行 = 逐项。"""
    if not lst or not isinstance(lst[0], dict):
        return []
    cols = []
    for it in lst:
        for k in it.keys():
            if k not in cols:
                cols.append(k)
    rows = [[{"text": _fmt(it.get(k, ""))} for k in cols] for it in lst]
    return [{"text": c} for c in cols], rows


# --------------------------------------------------------------------------- #
# 通用映射：任何 result → 可读 contract（不吐字段名和 JSON）
# --------------------------------------------------------------------------- #
def generic_contract(result: Dict[str, Any], role: str, name: str, title: str,
                     skill: str, action: str, intent: str,
                     doc_type: str = "角色报告") -> Dict[str, Any]:
    ok = bool(result.get("ok", True))
    checks = result.get("checks", [])
    if not isinstance(checks, list):
        checks = []

    passed = sum(1 for c in checks if isinstance(c, dict) and c.get("ok"))
    failed = [c for c in checks if isinstance(c, dict) and not c.get("ok")]

    # 结论先行：优先取人话字段，否则用门禁汇总合成
    concl_text = _first_scalar(result, _CONCLUSION_KEYS) or (
        f"门禁通过：{passed}/{len(checks)} 项检查全部通过，可交付。"
        if ok else f"门禁未通过：{len(failed)}/{len(checks)} 项检查失败。")

    # 关键指标：门禁 + 检查计数 + 1~2 个顶层标量
    metric_strip = [
        {"label": "门禁", "value": "PASS" if ok else "FAIL",
         "note": f"{passed}/{len(checks)} 项", "status": "healthy" if ok else "critical"},
    ]
    _st = str(result.get("status") or "").lower()
    if _st in ("warn", "unavailable", "blocked"):
        metric_strip.append({"label": "技能状态", "value": _st,
                             "note": "见报告边界", "status": "critical" if _st == "blocked" else "watch"})
    n_scalar = 0
    for k, v in result.items():
        if k in _META_KEYS or isinstance(v, (dict, list)):
            continue
        if n_scalar >= 3:
            break
        metric_strip.append({"label": k, "value": _fmt(v),
                             "note": "输出字段", "status": "none"})
        n_scalar += 1

    # 正文：每个非元字段一个 section（list[dict] 摊成表，标量摊成 reading）
    sections: List[Dict[str, Any]] = []
    idx = 0
    for k, v in result.items():
        if k in _META_KEYS or k in _CONCLUSION_KEYS:
            continue
        if k == "advice_authorized":
            continue
        idx += 1
        sec: Dict[str, Any] = {
            "index": idx,
            "title": k,
            "question": f"{k} 的判定与证据是什么？",
        }
        if isinstance(v, list) and v and isinstance(v[0], dict):
            cols, rows = _rows_from_list(v)
            sec["table"] = {"caption": k, "columns": cols, "rows": rows}
        elif isinstance(v, (dict, list)):
            sec["reading"] = [{"text": _fmt(v)}]
        else:
            sec["reading"] = [{"strong": k + "：", "text": _fmt(v)}]
        sections.append(sec)

    if result.get("caveats") and sections:
        _boundary = {"title": "证据边界",
                     "text": "；".join(str(x) for x in result["caveats"])}
        for _sec in sections:
            if not _sec.get("appendix"):
                _sec.setdefault("boundary", _boundary)
    if not sections:
        sections = [{
            "index": 1, "title": "执行结果",
            "question": "本次技能执行的判定与证据是什么？",
            "reading": [{"text": concl_text}],
        }]

    return {
        "doc_type": f"{doc_type} · {name}",
        "title_lines": [f"{name} · {skill}/{action}", intent or title],
        "standfirst": concl_text,
        "meta": [f"角色 {role} {name}（{title}）",
                 f"生成日期 {date.today().isoformat()}",
                 "渲染器 core/report_renderer.py"]
                + ([f"技能状态 {result['status']}"] if result.get("status") and result["status"] != "ok" else []),
        "metric_strip": metric_strip,
        "summary": [
            {"label": "结论：", "text": concl_text},
            {"label": "说明：", "text": "本报告由一次技能真实运行结果确定性生成；"
             "每个数字可回溯到 result JSON。"},
        ],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": ([
                      {"label": "来源：", "text": f"技能 {skill}/{action} 的确定性输出（无 LLM）。"},
                      {"label": "边界：", "text": "结论仅基于本次输入的产出；未纳入的输入不参与判断。"},
                  ] + ([{"label": "已知边界：", "text": "；".join(str(x) for x in result["caveats"])}]
                       if result.get("caveats") else [])
                    + ([{"label": "状态：", "text": str(result["status"])}]
                       if result.get("status") and result["status"] != "ok" else []))},
        "footer": [f"{name} · {title}", "core/report_renderer.py 确定性渲染"],
    }


# --------------------------------------------------------------------------- #
# 渲染 + 落盘
# --------------------------------------------------------------------------- #
def render_html(contract: Dict[str, Any], out_html: str,
                chart_dir: Optional[str] = None, theme: Optional[str] = None) -> Dict[str, Any]:
    """contract → core 渲染器 → HTML。返回 {ok, output?, errors?}。

    theme: "sticker"（墨绿封面 + 粗黑描边 + 贴纸卡片，默认）/ "paper"（白纸研究风）。
    """
    tmp = out_html + ".contract.json"
    os.makedirs(os.path.dirname(os.path.abspath(tmp)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(contract, f, ensure_ascii=False, indent=2)
    argv = [sys.executable, CORE_RENDERER, "--contract", tmp, "--output", out_html]
    if theme:
        argv += ["--theme", theme]
    # 全角色共用 48 型图表库：未显式指定时回落到 core/charts。
    chart_dir = chart_dir or SHARED_CHART_DIR
    if chart_dir and os.path.exists(os.path.join(chart_dir, "chart_lib.py")):
        argv += ["--chart-dir", os.path.abspath(chart_dir)]
    proc = subprocess.run(argv, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=_CHILD_ENV)
    out = (proc.stdout or "").strip()
    try:
        return json.loads(out) if out.startswith("{") else {
            "ok": proc.returncode == 0, "output": out_html,
            "errors": [out or proc.stderr or "渲染失败"]}
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "output": out_html,
                "errors": [out or proc.stderr or "渲染失败"]}


def write_markdown(contract: Dict[str, Any], out_md: str) -> None:
    """从 contract 落一份「结论先行」的 .md 快读摘要（非 JSON 裸转）。"""
    L: List[str] = []
    L.append(f"# {contract['title_lines'][0]}")
    if len(contract["title_lines"]) > 1:
        L.append(f"> {contract['title_lines'][1]}")
    L.append("")
    # 结论
    L.append("**结论**：" + contract["summary"][0]["text"])
    L.append("")
    # 关键指标
    if contract.get("metric_strip"):
        L.append("## 关键指标")
        L.append("")
        L.append("| 指标 | 值 | 说明 |")
        L.append("|---|---|---|")
        for m in contract["metric_strip"]:
            L.append(f"| {m['label']} | **{m['value']}** | {m.get('note', '')} |")
        L.append("")
    # 各节
    for s in contract.get("sections", []):
        L.append(f"## {s['index']}. {s['title']}")
        if s.get("question"):
            L.append(f"> {s['question']}")
        L.append("")
        if s.get("reading"):
            for r in s["reading"]:
                strong = f"**{r['strong']}**" if r.get("strong") else ""
                L.append(f"- {strong}{r['text']}")
        if s.get("table"):
            cols = s["table"]["columns"]
            L.append("| " + " | ".join(c["text"] for c in cols) + " |")
            L.append("|" + "---|" * len(cols))
            for row in s["table"]["rows"]:
                L.append("| " + " | ".join(cell["text"] for cell in row) + " |")
        L.append("")
    # 边界
    if contract.get("notes"):
        L.append("## 口径与边界")
        L.append("")
        for it in contract["notes"].get("items", []):
            label = f"**{it['label']}**" if it.get("label") else ""
            L.append(f"- {label}{it['text']}")
        L.append("")
    os.makedirs(os.path.dirname(os.path.abspath(out_md)), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def render_pdf(html_path: str, pdf_path: str) -> Dict[str, Any]:
    """Render PDF via installed Chrome/Edge headless; unavailable is blocked."""
    candidates = [shutil.which(x) for x in ("chrome", "google-chrome", "msedge", "microsoft-edge")]
    candidates += [r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"]
    browser = next((p for p in candidates if p and os.path.exists(p)), None)
    if not browser:
        return {"ok": False, "status": "blocked", "errors": ["Chrome/Edge headless executable not found"]}
    os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
    proc = subprocess.run([browser, "--headless", "--disable-gpu", "--no-sandbox", "--print-to-pdf=" + os.path.abspath(pdf_path), "file:///" + os.path.abspath(html_path).replace('\\\\', '/')], capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = proc.returncode == 0 and os.path.exists(pdf_path)
    return {"ok": ok, "status": "created" if ok else "failed", "output": pdf_path if ok else None, "errors": [] if ok else [proc.stderr or "PDF rendering failed"]}



def emit(role: str, name: str, title: str, result: Dict[str, Any],
         skill: str, action: str, intent: str, out_dir: str,
         md_name: str, html_name: Optional[str] = None,
         specialist: Optional[Callable[..., Optional[Dict[str, Any]]]] = None,
         chart_dir: Optional[str] = None,
         data: Optional[Dict[str, Any]] = None,
         doc_type: str = "角色报告", pdf: bool = True,
         dataset: Optional[List[Dict[str, Any]]] = None,
         legacy: bool = False) -> List[Any]:
    """dataset: 观测集（可选）；legacy=True 强制走老路径。"""
    """把 result 变成 html + md 两份报告，返回 Port 列表。

    data：可选，技能的输入 JSON（部分角色如 R07 PRD，其内容在输入而非 result）。
    """
    contract = None
    if not legacy and _use_kernel(role):
        contract, _fid = build_kernel_contract(role, name, title, result,
                                               skill, action, intent,
                                               dataset=dataset, doc_type=doc_type,
                                               data=data)
    if contract is None and specialist is not None:
        try:
            contract = specialist(result, skill, action, intent, data)
        except TypeError:
            # specialist 不接受 data 参数时退回四参
            try:
                contract = specialist(result, skill, action, intent)
            except Exception:
                contract = None
        except Exception:
            contract = None
    if contract is None:
        contract = generic_contract(result, role, name, title,
                                    skill, action, intent, doc_type)

    html_name = html_name or (md_name + ".html")
    out_html = os.path.join(out_dir, html_name)
    out_md = os.path.join(out_dir, md_name + ".md")
    render_html(contract, out_html, chart_dir=chart_dir)
    write_markdown(contract, out_md)
    out_pdf = os.path.join(out_dir, md_name + ".pdf")
    pdf_result = render_pdf(out_html, out_pdf) if pdf else {"ok": False, "status": "skipped"}

    # 延迟导入避免循环；protocol 是纯数据结构
    from core import protocol
    ports = [protocol.Port(md_name + ".md", "report", "text/markdown"),
             protocol.Port(html_name, "report", "text/html")]
    # PDF is exposed as a port even when blocked, with receipt metadata attached.
    ports.append(protocol.Port(md_name + ".pdf", "report", "application/pdf",
                               note=json.dumps(pdf_result, ensure_ascii=False)))
    return ports
