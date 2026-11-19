# -*- coding: utf-8 -*-
"""共享渲染桥（core 层）：contract → HTML / MD / PDF。

2026-11-15 产线收敛后，本模块只保留**渲染能力**，不再负责「result → contract」
（那是 R01 s09 解读 + core/report_flow 的事），也不再区分 kernel/legacy 引擎。

保留的四个函数：
    render_html(contract, out_html, chart_dir=None, theme=None)
    write_markdown(contract, out_md)
    render_pdf(html_path, pdf_path)
    _stamp_page_numbers(pdf_path)

唯一渲染器仍然是 core/report_renderer.py；这里只是它的薄调用层。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_RENDERER = os.path.join(AGENTS_ROOT, "core", "report_renderer.py")
# 共享 48 型图表库（原 R06 私有，已上收为全角色共用）。
SHARED_CHART_DIR = os.path.join(AGENTS_ROOT, "core", "charts")

# 子进程强制 UTF-8，避免 Windows 控制台 GBK 编码污染 JSON。
_CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8",
                  PYTHONUTF8="1", PYTHONPATH=AGENTS_ROOT)


def render_html(contract: Dict[str, Any], out_html: str,
                chart_dir: Optional[str] = None,
                theme: Optional[str] = None) -> Dict[str, Any]:
    """contract → core 渲染器 → HTML。返回 {ok, output?, errors?}。

    theme: "paper"（白纸研究风，默认）/ "sticker"（历史主题）。
    """
    tmp = out_html + ".contract.json"
    os.makedirs(os.path.dirname(os.path.abspath(tmp)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(contract, f, ensure_ascii=False, indent=2)
    argv = [sys.executable, CORE_RENDERER, "--contract", tmp, "--output", out_html]
    if theme:
        argv += ["--theme", theme]
    chart_dir = chart_dir or SHARED_CHART_DIR
    if chart_dir and os.path.exists(os.path.join(chart_dir, "chart_lib.py")):
        argv += ["--chart-dir", os.path.abspath(chart_dir)]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=_CHILD_ENV,
                              timeout=300)
        out = (proc.stdout or "").strip()
        try:
            return json.loads(out) if out.startswith("{") else {
                "ok": proc.returncode == 0, "output": out_html,
                "errors": [out or proc.stderr or "渲染失败"]}
        except json.JSONDecodeError:
            return {"ok": proc.returncode == 0, "output": out_html,
                    "errors": [out or proc.stderr or "渲染失败"]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "errors": ["渲染子进程超时（300s）"]}
    finally:
        # 中间契约文件不留在产物目录里
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _md_cell(c: Any) -> str:
    """markdown 表格单元格：兼容 {"text":...} / {"lines":[...]} / 裸字符串。"""
    if isinstance(c, dict):
        if c.get("text") not in (None, ""):
            return str(c["text"])
        if c.get("lines"):
            return " / ".join(str(x.get("text", "")) if isinstance(x, dict) else str(x)
                              for x in c["lines"])
        return ""
    return str(c)


_SENT_END = ("。", "；", "！", "？", "：", "，", "、")


def _reading_texts(s: Dict[str, Any]) -> List[str]:
    """把一个 section 的 reading 归一化成纯文本句子列表（去掉 strong 标签）。"""
    out: List[str] = []
    for r in (s.get("reading") or []):
        t = str(r.get("text", "")).strip() if isinstance(r, dict) else str(r).strip()
        if t:
            out.append(t)
    return out


def _join_prose(texts: List[str]) -> str:
    """把有序句子拼成一个连贯段落：缺句末标点时补句号，不产生 `。。`。"""
    parts = [t for t in (x.strip() for x in texts) if t]
    if not parts:
        return ""
    out = parts[0]
    for t in parts[1:]:
        if out.endswith(_SENT_END) or t.startswith(_SENT_END):
            out += t
        else:
            out += "。" + t
    if not out.endswith(_SENT_END):
        out += "。"
    return out


def write_markdown(contract: Dict[str, Any], out_md: str) -> None:
    """从 contract 落一份「结论先行」的 .md 快读摘要（非 JSON 裸转）。"""
    L: List[str] = []
    L.append(f"# {contract['title_lines'][0]}")
    if len(contract["title_lines"]) > 1:
        L.append(f"> {contract['title_lines'][1]}")
    L.append("")
    if contract.get("summary"):
        L.append("**结论**：" + contract["summary"][0]["text"])
        L.append("")
    if contract.get("metric_strip"):
        L.append("## 关键指标")
        L.append("")
        L.append("| 指标 | 值 | 说明 |")
        L.append("|---|---|---|")
        for m in contract["metric_strip"]:
            L.append(f"| {m['label']} | **{m['value']}** | {m.get('note', '')} |")
        L.append("")
    for s in contract.get("sections", []):
        L.append(f"## {s['index']}. {s['title']}")
        L.append("")
        for p in (s.get("intro") or []):
            L.append(str(p.get("text", "")))
            L.append("")
        for b in (s.get("blocks") or []):
            t = b.get("type")
            if t == "subhead":
                L.append(f"### {b.get('text', '')}")
                L.append("")
            elif t == "bullets":
                for it in (b.get("items") or []):
                    L.append(f"- {it}")
                L.append("")
            elif t == "table" and b.get("table"):
                tb = b["table"]
                cols = tb.get("columns", [])
                L.append("| " + " | ".join(_md_cell(c) for c in cols) + " |")
                L.append("|" + "---|" * len(cols))
                for row in tb.get("rows", []):
                    L.append("| " + " | ".join(_md_cell(c) for c in row) + " |")
                L.append("")
            elif t == "callout":
                L.append(f"> {b.get('text', '')}")
                L.append("")
            else:
                L.append(str(b.get("text", "")))
                L.append("")
        if s.get("reading"):
            reading_style = s.get("reading_style") or "prose"
            if reading_style == "prose":
                L.append(_join_prose(_reading_texts(s)))
                L.append("")
            else:
                for t in _reading_texts(s):
                    L.append(f"- {t}")
                L.append("")
        sec_tables = list(s.get("tables") or [])
        if s.get("table"):
            sec_tables.insert(0, s["table"])
        for tb in sec_tables:
            L.append("")
            cols = tb["columns"]
            L.append("| " + " | ".join(_md_cell(c) for c in cols) + " |")
            L.append("|" + "---|" * len(cols))
            for row in tb["rows"]:
                L.append("| " + " | ".join(_md_cell(cell) for cell in row) + " |")
        L.append("")
    if contract.get("notes"):
        # 用 notes.summary 作标题：与 HTML 同一处措辞，避免出现「口径与分数」
        # 之后又跟一个「口径与边界」，读者分不清是不是两件事。
        L.append("## " + str(contract["notes"].get("summary") or "证据包与回溯"))
        L.append("")
        for it in contract["notes"].get("items", []):
            L.append(str(it.get("text", "")))
        L.append("")
    os.makedirs(os.path.dirname(os.path.abspath(out_md)), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def render_pdf(html_path: str, pdf_path: str) -> Dict[str, Any]:
    """Render PDF via installed Chrome/Edge headless; unavailable is blocked."""
    candidates = [shutil.which(x) for x in ("chrome", "google-chrome", "msedge", "microsoft-edge")]
    candidates += [r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                   r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"]
    browser = next((p for p in candidates if p and os.path.exists(p)), None)
    if not browser:
        return {"ok": False, "status": "blocked",
                "errors": ["Chrome/Edge headless executable not found"]}
    os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
    try:
        uri = Path(html_path).resolve().as_uri()
        proc = subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer",
             "--print-to-pdf=" + os.path.abspath(pdf_path), uri],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180)
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": "timeout", "output": None,
                "errors": ["PDF 渲染超时（180s）"]}
    ok = proc.returncode == 0 and os.path.exists(pdf_path)
    if ok:
        _stamp_page_numbers(pdf_path)
    return {"ok": ok, "status": "created" if ok else "failed",
            "output": pdf_path if ok else None,
            "errors": [] if ok else [proc.stderr or "PDF rendering failed"]}


def _stamp_page_numbers(pdf_path: str) -> None:
    """给 PDF 逐页加「第 x / y 页」页脚。Chrome 的 @page margin box 不支持，只能后处理。"""
    try:
        import pymupdf  # PyMuPDF
    except Exception:  # noqa: BLE001
        return
    try:
        doc = pymupdf.open(pdf_path)
        n = doc.page_count
        for i, page in enumerate(doc):
            w, h = page.rect.width, page.rect.height
            label = f"{i + 1} / {n}"
            page.insert_text((w / 2 - 14, h - 16), label, fontsize=8,
                             color=(0.45, 0.45, 0.42), fontname="helv")
        tmp = pdf_path + ".tmp"
        doc.save(tmp)
        doc.close()
        os.replace(tmp, pdf_path)
    except Exception:  # noqa: BLE001
        return
