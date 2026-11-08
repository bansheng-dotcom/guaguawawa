# -*- coding: utf-8 -*-
"""S03 钩子、提纲与立场 —— 能力域 3。

整合自 bzwh321__article-director（topic-architect 的「答案先行」「读者卡点」纪律）。
把「钩子/标题/提纲/立场」从修辞转成确定性校验：钩子类型白名单 + 标题备选 ≥3 +
提纲二级标题 ≥3 + 立场必填（claim/audience/boundary）。立场里的边界必须写清
「不替读者拍板」，否则 FAIL（对齐 R11「不编造、对外发布需授权」边界）。

动作：
  hook    钩子与标题（hook_types 白名单 + 标题备选 ≥3）
  outline 提纲（二级标题 ≥3 + 立场三件套）
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "hook"
DESC = "钩子提纲立场：hook/outline"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    h = act.add_parser("hook", help="校验钩子与标题")
    h.add_argument("--input", required=True)
    o = act.add_parser("outline", help="校验提纲与立场")
    o.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "hook":
        return _validate_hook(data)
    if args.action == "outline":
        return _validate_outline(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_hook(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    hook_type = data.get("hook_type")
    ok_ht = hook_type in th["hook"]["hook_types"]
    checks.append(_ck(ok_ht, f"hook_type={hook_type!r} 在白名单 {th['hook']['hook_types']}",
                      "hook.type"))
    if not ok_ht:
        return c.result(checks, ok=False, verdict="FAIL", hook_type=hook_type,
                        title_count=0)

    titles = data.get("titles")
    ok_titles = isinstance(titles, list) and all(
        isinstance(t, str) and t.strip() for t in titles) and len(titles) >= th["hook"]["title_min"]
    checks.append(_ck(ok_titles,
                      f"标题备选 ≥{th['hook']['title_min']}（实际 {len(titles) if isinstance(titles, list) else 0}）",
                      "hook.titles"))

    ok = ok_ht and ok_titles
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    hook_type=hook_type,
                    title_count=len(titles) if isinstance(titles, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_outline(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    outline_text = str(data.get("outline", ""))
    h2_count = len(re.findall(r"^##\s+", outline_text, re.MULTILINE))
    ok_h2 = h2_count >= th["hook"]["outline_h2_min"]
    checks.append(_ck(ok_h2,
                      f"提纲二级标题 ≥{th['hook']['outline_h2_min']}（实际 {h2_count}）",
                      "hook.outline_h2"))

    # 立场三件套
    stance = data.get("stance")
    ok_stance = isinstance(stance, dict)
    checks.append(_ck(ok_stance, "立场为对象", "hook.stance"))
    if ok_stance:
        for k in th["hook"]["stance_required"]:
            checks.append(_ck(bool(str(stance.get(k, "")).strip()),
                              f"立场字段 {k} 非空", f"hook.stance.{k}"))
        # 边界必须写清「不替读者拍板」
        boundary = str(stance.get("boundary", ""))
        no_decision = any(w in boundary for w in ["不替", "不代表", "仅供参考", "需自行"])
        checks.append(_ck(no_decision, "边界声明「不替读者拍板」", "hook.stance.boundary"))

    ok = ok_h2 and ok_stance and all(
        ch["ok"] for ch in checks if ch["dim"].startswith("hook.stance"))
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    h2_count=h2_count)
