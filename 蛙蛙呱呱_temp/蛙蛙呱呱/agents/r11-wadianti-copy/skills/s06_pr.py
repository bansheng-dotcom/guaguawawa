# -*- coding: utf-8 -*-
"""S06 广告、公关与新闻稿 —— 能力域 6。

整合自 bzwh321__article-director 的边界纪律 + R11「对外发布需授权」红线。
把「广告创意/新闻稿/对外口径」转成确定性校验：广告三件套 + 禁词（绝对化用语）+
CTA 白名单 + 新闻稿六段结构。发布需授权 → 广告文案含发布意图但无 authorized
即 FAIL（对齐 R01 irreversible_gate 思路，但这里是「对外发布」授权而非不可逆操作）。

动作：
  ad     广告文案（headline/benefit/cta + 绝对化禁词）
  press  新闻稿（headline/dateline/lead/body/boilerplate/contact）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "pr"
DESC = "广告公关新闻稿：ad/press"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("ad", help="校验广告文案")
    a.add_argument("--input", required=True)
    pr = act.add_parser("press", help="校验新闻稿")
    pr.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "ad":
        return _validate_ad(data)
    if args.action == "press":
        return _validate_press(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "", **ev) -> Dict[str, Any]:
    d = {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}
    d.update(ev)
    return d


# --------------------------------------------------------------------------- #
def _validate_ad(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["pr"]["ad_required"]:
        checks.append(_ck(bool(str(data.get(k, "")).strip()),
                          f"广告字段 {k} 非空", f"pr.ad.{k}"))

    cta = data.get("cta")
    ok_cta = cta in th["pr"]["cta_types"]
    checks.append(_ck(ok_cta, f"cta={cta!r} 在白名单 {th['pr']['cta_types']}",
                      "pr.ad.cta"))

    # 绝对化禁词（广告法红线）
    body = " ".join(str(v) for v in [data.get("headline"), data.get("benefit")])
    banned = [w for w in th["pr"]["ad_forbidden"] if w in body]
    checks.append(_ck(not banned, f"无绝对化禁词（命中 {banned[:5] or '无'}）",
                      "pr.ad.banned", hits=banned))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    banned_count=len(banned))


# --------------------------------------------------------------------------- #
def _validate_press(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["pr"]["press_required"]:
        checks.append(_ck(bool(str(data.get(k, "")).strip()),
                          f"新闻稿字段 {k} 非空", f"pr.press.{k}"))

    # dateline 格式：城市 + 日期
    dateline = str(data.get("dateline", ""))
    ok_dl = bool(dateline) and (("20" in dateline) or ("—" in dateline or "-" in dateline))
    checks.append(_ck(ok_dl, "dateline 含城市与日期", "pr.press.dateline"))

    # 导语不得含广告绝对化禁词
    lead = str(data.get("lead", ""))
    banned = [w for w in th["pr"]["ad_forbidden"] if w in lead]
    checks.append(_ck(not banned, f"导语无绝对化禁词（命中 {banned or '无'}）",
                      "pr.press.banned"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    section_count=len(th["pr"]["press_required"]))
