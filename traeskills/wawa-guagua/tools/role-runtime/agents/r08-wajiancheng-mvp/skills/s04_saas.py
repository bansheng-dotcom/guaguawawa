# -*- coding: utf-8 -*-
"""S04 SaaS 与邮件脚手架 —— 能力域 4。

整合自 makerskills（saas-starter / email-scaffold）。把多页 SaaS 或邮件流程
快速搭出可演示骨架：页面≥2、路由≥1、鉴权方式合法、入口明确；邮件模板带
姓名/主题/正文、预览文字与退订链接齐备。

动作：
  saas   校验 SaaS 脚手架（pages/routes/auth/entry_point）
  email  校验邮件脚手架（templates/preview_text/unsubscribe_link）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "saas"
DESC = "SaaS与邮件脚手架：saas/email"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    s = act.add_parser("saas", help="校验 SaaS 脚手架")
    s.add_argument("--input", required=True)
    e = act.add_parser("email", help="校验邮件脚手架")
    e.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "saas":
        return _validate_saas(data)
    if args.action == "email":
        return _validate_email(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_saas(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    pages_min = th["saas"]["pages_min"]
    auth_types = th["saas"]["auth_types"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    pages = data.get("pages")
    ok_pages = isinstance(pages, list) and len(pages) >= pages_min
    checks.append(_ck(ok_pages,
                      f"pages ≥{pages_min}（实际 {len(pages) if isinstance(pages, list) else 0}）",
                      "saas.pages"))

    routes = data.get("routes")
    ok_routes = isinstance(routes, list) and len(routes) >= 1
    checks.append(_ck(ok_routes,
                      f"routes ≥1（实际 {len(routes) if isinstance(routes, list) else 0}）",
                      "saas.routes"))
    route_ok = ok_routes
    if isinstance(routes, list):
        for i, r in enumerate(routes):
            if not isinstance(r, dict):
                checks.append(_ck(False, f"route[{i}] 非对象", "saas.route"))
                route_ok = False
                continue
            for k in ("path", "page"):
                if not str(r.get(k, "")).strip():
                    checks.append(_ck(False, f"route[{i}] 缺 {k}",
                                      f"saas.route.{k}"))
                    route_ok = False

    auth = str(data.get("auth", "")).strip().lower()
    ok_auth = auth in auth_types
    checks.append(_ck(ok_auth, f"auth={auth or '缺失'}", "saas.auth"))

    entry = str(data.get("entry_point", "")).strip()
    ok_entry = bool(entry)
    checks.append(_ck(ok_entry,
                      "entry_point 非空" if ok_entry else "entry_point 缺失",
                      "saas.entry_point"))

    ok = ok_pages and route_ok and ok_auth and ok_entry
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    page_count=len(pages) if isinstance(pages, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_email(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    templates = data.get("templates")
    ok_t = isinstance(templates, list) and len(templates) >= 1
    checks.append(_ck(ok_t,
                      f"templates ≥1（实际 {len(templates) if isinstance(templates, list) else 0}）",
                      "email.templates"))
    t_ok = ok_t
    if isinstance(templates, list):
        for i, t in enumerate(templates):
            if not isinstance(t, dict):
                checks.append(_ck(False, f"template[{i}] 非对象",
                                  "email.template"))
                t_ok = False
                continue
            for k in ("name", "subject", "body"):
                if not str(t.get(k, "")).strip():
                    checks.append(_ck(False, f"template[{i}] 缺 {k}",
                                      f"email.template.{k}"))
                    t_ok = False

    preview = str(data.get("preview_text", "")).strip()
    ok_p = bool(preview)
    checks.append(_ck(ok_p,
                      "preview_text 非空" if ok_p else "preview_text 缺失",
                      "email.preview_text"))

    unsub = str(data.get("unsubscribe_link", "")).strip()
    ok_u = bool(unsub)
    checks.append(_ck(ok_u,
                      "unsubscribe_link 非空" if ok_u else "unsubscribe_link 缺失",
                      "email.unsubscribe_link"))

    ok = t_ok and ok_p and ok_u
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    template_count=len(templates) if isinstance(templates, list) else 0)