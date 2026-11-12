# -*- coding: utf-8 -*-
"""S11 Office 交付物（自有实现）。

把结构化内容写成 xlsx / docx：
  probe  探测 openpyxl / python-docx 是否可用
  xlsx   多表工作簿：表头加粗、冻结首行、列宽自适应
  docx   报告文档：标题层级、段落、要点列表

纪律：不覆盖已有文件（除非 --force）；扩展名白名单；缺库返回 blocked。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import _common as c

NAME = "office"
DESC = "Office 交付物：probe/xlsx/docx"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _libs():
    try:
        import openpyxl
        import docx
        return openpyxl, docx
    except Exception:
        return None, None


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    act.add_parser("probe", help="探测 openpyxl / python-docx")
    x = act.add_parser("xlsx", help="生成多表工作簿")
    x.add_argument("--input", required=True)
    x.add_argument("--out", required=True)
    x.add_argument("--force", action="store_true")
    d = act.add_parser("docx", help="生成报告文档")
    d.add_argument("--input", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--force", action="store_true")


def run(args) -> Dict[str, Any]:
    if args.action == "probe":
        openpyxl, docx = _libs()
        checks = [_ck(openpyxl is not None, "openpyxl 可用", "office.openpyxl"),
                  _ck(docx is not None, "python-docx 可用", "office.docx")]
        return c.result(checks, ok=True, verdict="PASS",
                        status="ready" if all(x["ok"] for x in checks) else "blocked")
    data = c.load_json(args.input)
    if args.action == "xlsx":
        return _xlsx(data, args.out, args.force)
    return _docx(data, args.out, args.force)


# --------------------------------------------------------------------------- #
def _guard(out: str, ext: str, force: bool) -> List[Dict[str, Any]]:
    return [_ck(out.lower().endswith(ext), f"输出扩展名 {ext}", "office.ext"),
            _ck(force or not os.path.exists(out), "不覆盖已有文件（需 --force）", "office.overwrite")]


def _xlsx(data: Any, out: str, force: bool) -> Dict[str, Any]:
    openpyxl, _ = _libs()
    checks = _guard(out, ".xlsx", force)
    if openpyxl is None:
        checks.append(_ck(False, "openpyxl 未安装（pip install openpyxl）", "office.openpyxl"))
        return c.result(checks, ok=False, verdict="FAIL", status="blocked")
    sheets = data.get("sheets") if isinstance(data, dict) else None
    checks.append(_ck(isinstance(sheets, list) and len(sheets) >= 1,
                      "至少 1 个工作表", "office.sheets"))
    if not isinstance(sheets, list) or not sheets:
        return c.result(checks, ok=False, verdict="FAIL")
    for i, s in enumerate(sheets):
        headers = s.get("headers") if isinstance(s, dict) else None
        checks.append(_ck(isinstance(headers, list) and len(headers) >= 1,
                          f"工作表[{i}] 表头 ≥1 列", "office.headers"))
        rows = s.get("rows") or []
        checks.append(_ck(all(len(r) == len(headers or []) for r in rows),
                          f"工作表[{i}] 行宽与表头一致", "office.rows"))
    if not all(x["ok"] for x in checks):
        return c.result(checks, ok=False, verdict="FAIL", next="按 checks 修正表格规格")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for s in sheets:
        ws = wb.create_sheet(str(s.get("name") or "Sheet")[:31])
        ws.append(list(s["headers"]))
        for cell in ws[1]:
            cell.font = openpyxl.styles.Font(bold=True)
        for row in s.get("rows") or []:
            ws.append(list(row))
        ws.freeze_panes = "A2"
        for idx, width in enumerate([max(12, min(40, len(str(h)) + 6)) for h in s["headers"]], 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    wb.save(out)
    return c.result(checks + [_ck(os.path.getsize(out) > 0, "文件已生成", "office.out")],
                    ok=True, verdict="PASS", out=out, size_bytes=os.path.getsize(out),
                    sheet_count=len(sheets), next="可直接交付或交 R02 汇总")


def _docx(data: Any, out: str, force: bool) -> Dict[str, Any]:
    _, docx = _libs()
    checks = _guard(out, ".docx", force)
    if docx is None:
        checks.append(_ck(False, "python-docx 未安装（pip install python-docx）", "office.docx"))
        return c.result(checks, ok=False, verdict="FAIL", status="blocked")
    title = str((data or {}).get("title", "")).strip()
    sections = (data or {}).get("sections") or []
    checks.append(_ck(bool(title), "文档标题非空", "office.title"))
    checks.append(_ck(isinstance(sections, list) and len(sections) >= 1,
                      "章节 ≥1", "office.sections"))
    if not all(x["ok"] for x in checks):
        return c.result(checks, ok=False, verdict="FAIL")

    doc = docx.Document()
    doc.add_heading(title, level=0)
    meta = (data or {}).get("meta") or {}
    if meta:
        doc.add_paragraph(" · ".join(f"{k}：{v}" for k, v in meta.items()))
    for s in sections:
        if not isinstance(s, dict):
            continue
        heading = str(s.get("heading", "")).strip()
        if heading:
            doc.add_heading(heading, level=1)
        for p in s.get("paragraphs") or []:
            doc.add_paragraph(str(p))
        for b in s.get("bullets") or []:
            doc.add_paragraph(str(b), style="List Bullet")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    doc.save(out)
    return c.result(checks + [_ck(os.path.getsize(out) > 0, "文件已生成", "office.out")],
                    ok=True, verdict="PASS", out=out, size_bytes=os.path.getsize(out),
                    section_count=len(sections), next="可直接交付或转 PDF")
