# -*- coding: utf-8 -*-
"""S04 文案与长文 —— 能力域 4。

整合自 bzwh321__article-director 的 harness/article_validator.py（终稿校验）。
把「可发布成稿」从口头判断转成确定性门禁：正文字数下限、AI 味禁词（中文+英文）、
结论先行（摘要含数字）、必要结构（延伸阅读）。这是 R11 最核心的「成品门禁」，
对齐上游 article_validator 的「错误累积、不 raise、区分 hard error 与 warning」。

动作：
  article  文案终稿（字数/禁词/结论先行/必要结构）
  script   脚本类（对话/口播，字数门槛略低，禁词同源）
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "copy"
DESC = "文案与长文：article/script"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("article", help="校验文案终稿")
    a.add_argument("--input", required=True)
    s = act.add_parser("script", help="校验脚本类（对话/口播）")
    s.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "article":
        return _validate_article(data)
    if args.action == "script":
        return _validate_script(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "", **ev) -> Dict[str, Any]:
    d = {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}
    d.update(ev)
    return d


def _forbidden_hits(text: str, th: Dict[str, Any]) -> List[str]:
    """AI 味确定性证据词命中（中文子串 + 英文词边界），排除软连接词。"""
    hits: List[str] = []
    soft = set(th["copy"]["soft_connectives"])
    for w in th["copy"]["forbidden_zh"]:
        if w in soft:
            continue
        if w in text:
            hits.append(f"[中]{w}")
    for w in th["copy"]["forbidden_en"]:
        if re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE):
            hits.append(f"[英]{w}")
    return hits


def _validate(text: str, min_chars: int, profile: str) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not text or not text.strip():
        return c.result([_ck(False, "正文为空", "copy.empty")],
                        ok=False, verdict="FAIL", char_count=0)

    # 标题
    checks.append(_ck(text.lstrip().startswith("#"), "以 # 标题开头", "copy.title"))

    # 字数
    n = c.clean_len(text)
    checks.append(_ck(n >= min_chars, f"字数 {n} ≥ {min_chars}", "copy.length"))

    # 禁词
    hits = _forbidden_hits(text, th)
    checks.append(_ck(not hits, f"无 AI 味禁词（命中 {hits[:5] or '无'}）",
                      "copy.forbidden", hits=hits))

    # 结论先行：摘要段含数字
    summary = re.search(r"(?:摘要|总结|结论)[：:]\s*(.+?)(?:\n\n|\Z)", text, re.DOTALL)
    has_num = bool(summary and re.search(r"\d", summary.group(1)))
    checks.append(_ck(has_num, "摘要/结论段含具体数字", "copy.summary"))

    # 必要结构
    has_more = any(s in text for s in th["copy"]["required_sections"])
    checks.append(_ck(has_more, "含延伸阅读/后续阅读", "copy.structure"))

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    char_count=n, profile=profile, forbidden_count=len(hits))


# --------------------------------------------------------------------------- #
def _validate_article(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")
    text = str(data.get("text", data.get("content", "")))
    return _validate(text, th["copy"]["min_chars"], "article")


def _validate_script(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")
    text = str(data.get("text", data.get("content", "")))
    # 脚本类字数门槛略低：对话/口播按 min_chars 的 0.5 计
    return _validate(text, max(1, th["copy"]["min_chars"] // 2), "script")
