# -*- coding: utf-8 -*-
"""S11 设计系统库 —— 品牌 DESIGN.md 的检索、推荐、落盘与九段式门禁。

把 awesome-design-md 的 31 份品牌 DESIGN.md 变成 R10 的可调用资产：
  - 查库：按分类/关键词检索，或按项目类型要 3~5 个推荐；
  - 落盘：把品牌规范写成项目的 DESIGN.md + design_tokens.json；
  - 门禁：九段式结构 / 色板 / 字阶 / 组件 / 反模式 / 响应 / 提示指南确定性校验；
  - 交接：design_tokens.json 的 tokens.color/typography/spacing + components
    正是 R08 组件与设计实现（s06 design/token）认得的结构，可直接过 R08 门禁。

动作：
  list       列出库内设计系统（可按分类/关键词过滤）
  recommend  按项目类型推荐 3~5 个品牌（--list-types 看全部类型）
  show       查看单个品牌的元数据、色板、字体与组件清单
  apply      落盘 DESIGN.md + design_tokens.json 到目标目录
  audit      对给定 DESIGN.md（或库内品牌）跑九段式门禁
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

from . import _common as c

try:  # 正常由 agent.py 把仓库根放进 sys.path
    from shared import design_systems as ds
except ImportError:  # pragma: no cover - 直接单文件运行时的兜底
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from shared import design_systems as ds

NAME = "designsys"
DESC = "设计系统库：list/recommend/show/apply/audit"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    ls = act.add_parser("list", help="列出库内设计系统")
    ls.add_argument("--category", default=None,
                    help="过滤分类：ai/devtools/infra/design/fintech/enterprise")
    ls.add_argument("--q", default=None, help="关键词（名称/气质/标签）")

    rc = act.add_parser("recommend", help="按项目类型推荐设计系统")
    rc.add_argument("--project", default=None,
                    help="saas/devtools/ai/fintech/productivity/ecommerce/dashboard/creative/enterprise")
    rc.add_argument("--list-types", action="store_true", help="列出全部项目类型")

    sh = act.add_parser("show", help="查看单个品牌")
    sh.add_argument("--brand", required=True, help="品牌 slug，如 linear.app")

    ap = act.add_parser("apply", help="落盘 DESIGN.md 与 design_tokens.json")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--out", default=None,
                    help="目标目录（默认 workspace/design-systems/<brand>）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在文件")

    au = act.add_parser("audit", help="九段式门禁校验")
    au.add_argument("--input", default=None, help="DESIGN.md 路径")
    au.add_argument("--brand", default=None, help="库内品牌 slug（与 --input 二选一）")


def run(args) -> Dict[str, Any]:
    action = args.action
    if action == "list":
        return _list(args)
    if action == "recommend":
        return _recommend(args)
    if action == "show":
        return _show(args)
    if action == "apply":
        return _apply(args)
    if action == "audit":
        return _audit(args)
    return {"error": f"未知动作: {action}"}


# --------------------------------------------------------------------------- #
def _list(args) -> Dict[str, Any]:
    items = ds.list_systems(category=args.category, q=args.q)
    rows = [{"slug": i["slug"], "name": i["name"], "category": i["category"],
             "category_zh": i["category_zh"], "zh": i["zh"], "style": i["style"],
             "exists": i["exists"]} for i in items]
    return c.result([_ck(True, f"库内命中 {len(rows)} 个设计系统", "designsys.list")],
                    verdict="PASS", count=len(rows), systems=rows,
                    library=ds.library_dir(),
                    categories=ds.CATEGORY_ZH)


def _recommend(args) -> Dict[str, Any]:
    if args.list_types or not args.project:
        return c.result([_ck(True, f"共 {len(ds.PROJECT_TYPES)} 种项目类型", "designsys.types")],
                        verdict="PASS",
                        types=[{"type": k, "zh": v["zh"], "why": v["why"],
                                "brands": v["brands"]}
                               for k, v in ds.PROJECT_TYPES.items()])
    rec = ds.recommend(args.project)
    if not rec:
        return c.result([_ck(False, f"未知项目类型：{args.project}", "designsys.project")],
                        verdict="FAIL", ok=False,
                        valid_types=list(ds.PROJECT_TYPES))
    picks = [{"slug": i["slug"], "name": i["name"], "zh": i["zh"], "style": i["style"]}
             for i in rec["brands"]]
    return c.result([_ck(len(picks) >= 3,
                         f"推荐 ≥3 个（实际 {len(picks)}）", "designsys.recommend")],
                    verdict="PASS", project_type=rec["project_type"], zh=rec["zh"],
                    why=rec["why"], brands=picks)


def _show(args) -> Dict[str, Any]:
    item = ds.get(args.brand)
    if not item:
        return c.result([_ck(False, f"品牌不在库内：{args.brand}", "designsys.brand")],
                        verdict="FAIL", ok=False,
                        available=ds.available())
    parsed = ds.parse(ds.read(args.brand))
    report = ds.audit(parsed, args.brand)
    palette = [{"name": p["name"], "value": p["hex"], "role": p["role"]}
               for p in parsed["palette"][:12]]
    return c.result([_ck(report["ok"], f"九段式门禁 {report['verdict']}", "designsys.audit")],
                    verdict=report["verdict"], brand=item,
                    sections=[s["title"] for s in parsed["sections"]],
                    palette=palette, palette_count=len(parsed["palette"]),
                    fonts=parsed["fonts"], components=parsed["components"],
                    missing_sections=parsed["missing_sections"])


def _apply(args) -> Dict[str, Any]:
    item = ds.get(args.brand)
    if not item:
        return c.result([_ck(False, f"品牌不在库内：{args.brand}", "designsys.brand")],
                        verdict="FAIL", ok=False, available=ds.available())
    out = args.out or os.path.join("workspace", "design-systems", args.brand)
    report = ds.write_bundle(args.brand, out, force=args.force)
    checks = [_ck(report["ok"], f"九段式门禁 {report['verdict']}", "designsys.audit"),
              _ck(len(report["written"]) > 0 or bool(report["skipped"]),
                  f"产物写入/跳过（写入 {len(report['written'])}，已存在 {len(report['skipped'])}）",
                  "designsys.files")]
    return c.result(checks, verdict=report["verdict"],
                    brand=item["slug"], out_dir=report["out_dir"],
                    written=report["written"], skipped=report["skipped"],
                    palette_count=report["palette_count"],
                    next="产物可直接交给 R08 做组件/令牌门禁，或交给 R09 实现前端")


def _audit(args) -> Dict[str, Any]:
    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            text = fh.read()
        parsed = ds.parse(text)
        report = ds.audit(parsed)
        source = args.input
    elif args.brand:
        parsed = ds.parse(ds.read(args.brand))
        report = ds.audit(parsed, args.brand)
        source = ds.path_of(args.brand)
    else:
        return c.result([_ck(False, "需要 --input 或 --brand", "designsys.input")],
                        verdict="FAIL", ok=False)
    return c.result(report["checks"], verdict=report["verdict"],
                    source=source,
                    palette_count=report["palette_count"],
                    component_count=report["component_count"])
