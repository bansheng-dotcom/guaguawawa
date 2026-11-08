# -*- coding: utf-8 -*-
"""S02 SEO/AEO 与搜索发现 —— 能力域 2。

整合自 alirezarezvani__aeo-box（answer-engine-optimization 的 ContentAnalyzer：
E-E-A-T 四维打分 + 结构 + 引用）。把「AEO 就绪度」从营销话术转成确定性实算：
关键词表必填字段 + 搜索意图枚举 + E-E-A-T 四维信号实算（权威域、数据点、
一手经验、禁 hype）。不做外链/排名抓取（需 API，如实降级），只做离线文本审计。

动作：
  keyword  关键词表（primary/longtail/intent/difficulty/aeo_opportunity）
  audit    内容 AEO 就绪度审计（E-E-A-T + 结构 + 引用）
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "seo"
DESC = "SEO/AEO 与搜索发现：keyword/audit"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    k = act.add_parser("keyword", help="校验关键词表")
    k.add_argument("--input", required=True)
    a = act.add_parser("audit", help="内容 AEO 就绪度审计")
    a.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "keyword":
        return _validate_keyword(data)
    if args.action == "audit":
        return _validate_audit(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "", **ev) -> Dict[str, Any]:
    d = {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}
    d.update(ev)
    return d


# --------------------------------------------------------------------------- #
def _validate_keyword(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    for k in th["seo"]["keywords_required"]:
        checks.append(_ck(bool(str(data.get(k, "")).strip()),
                          f"关键词字段 {k} 非空", f"seo.keyword.{k}"))

    intent = data.get("intent")
    ok_intent = intent in th["seo"]["intent_enum"]
    checks.append(_ck(ok_intent, f"intent={intent!r} 在枚举 {th['seo']['intent_enum']}",
                      "seo.intent"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    keyword_count=1)


# --------------------------------------------------------------------------- #
def _validate_audit(data: Any) -> Dict[str, Any]:
    """AEO 就绪度审计：E-E-A-T 四维实算 + 结构 + 引用，阈值外置。"""
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    content = str(data.get("content", ""))
    if not content.strip():
        return c.result([_ck(False, "content 为空", "seo.content")],
                        ok=False, verdict="FAIL",
                        h2_count=0, external_links=0)

    # 权威域引用（authoritativeness/trustworthiness）
    auth_domains = th["seo"]["authoritative_domains"]
    auth_hits = [d for d in auth_domains if d in content.lower()]
    checks.append(_ck(True, f"权威域命中 {len(auth_hits)} 个", "seo.eeat_auth",
                      hits=auth_hits))

    # 一手经验信号（experience）：第一人称
    first_person = bool(re.search(r"\b(我|我们|我们的|我的|本人)\b", content))
    checks.append(_ck(True, f"一手经验信号：{'有' if first_person else '无'}",
                      "seo.eeat_exp", first_person=first_person))

    # 数据点（experience/expertise）
    data_points = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b", content)
    checks.append(_ck(True, f"数据点 {len(data_points)} 个", "seo.eeat_data",
                      data_points=len(data_points)))

    # 标题层级（structure）
    h2_count = len(re.findall(r"^##\s+", content, re.MULTILINE))
    ok_h2 = h2_count >= 2
    checks.append(_ck(ok_h2, f"二级标题 ≥2（实际 {h2_count}）", "seo.structure_h2"))

    # hype 词（trustworthiness 反向）
    hype = ["guaranteed", "miracle", "secret", "100%有效", "保证有效", "永不失败"]
    hype_hits = [h for h in hype if h.lower() in content.lower()]
    ok_nohype = not hype_hits
    checks.append(_ck(ok_nohype, f"无 hype 词（命中 {hype_hits or '无'}）",
                      "seo.eeat_hype"))

    # 时效信息（trustworthiness）
    has_date = bool(re.search(r"(更新|最后修改|发布|20\d{2})", content))
    checks.append(_ck(True, f"时效信息：{'有' if has_date else '无'}", "seo.eeat_date",
                      has_date=has_date))

    # 引用计数（citations）：Markdown 外链
    links = re.findall(r"\[[^\]]*\]\((https?://[^)]+)\)", content)
    external = [u for u in links if not u.startswith("#")]
    ok_links = len(external) >= th["seo"]["min_external_links"]
    checks.append(_ck(ok_links,
                      f"外链 ≥{th['seo']['min_external_links']}（实际 {len(external)}）",
                      "seo.citations"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    h2_count=h2_count, external_links=len(external),
                    data_points=len(data_points), auth_hits=auth_hits)
