# -*- coding: utf-8 -*-
"""S01 AI 生图与插画 —— 能力域 1。

整合自 mae616__design-skills(creative-coder) + nlr-2007__illustrations
（illustration/diagram/hybrid 三技能的 style locks 纪律）。
把「生图提示词」从口头模板转成确定性校验：输出媒体白名单、风格枚举、
正/负向提示词必填、风格锁（style locks）不得被负向提示词自我推翻。

动作：
  prompt  校验生图提示词包（media/style/prompt/negative_prompt/style_locks）
  style   校验风格探索（style 枚举 + 构图控制项）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "imagegen"
DESC = "AI生图与插画：prompt/style"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    pr = act.add_parser("prompt", help="校验生图提示词包")
    pr.add_argument("--input", required=True)
    st = act.add_parser("style", help="校验风格探索")
    st.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "prompt":
        return _validate_prompt(data)
    if args.action == "style":
        return _validate_style(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_prompt(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    media = data.get("media")
    ok_media = media in th["imagegen"]["output_media"]
    checks.append(_ck(ok_media,
                      f"media={media!r} 在白名单 {th['imagegen']['output_media']}",
                      "imagegen.media"))
    if not ok_media:
        return c.result(checks, ok=False, verdict="FAIL",
                        media=media, style=data.get("style"))

    style = data.get("style")
    ok_style = style in th["imagegen"]["style_types"]
    checks.append(_ck(ok_style,
                      f"style={style!r} 在白名单 {th['imagegen']['style_types']}",
                      "imagegen.style"))

    prompt = str(data.get("prompt", "")).strip()
    checks.append(_ck(bool(prompt), f"prompt 非空（{len(prompt)} 字）",
                      "imagegen.prompt"))

    negative = str(data.get("negative_prompt", "")).strip()
    neg_min = th["imagegen"]["negative_min"]
    checks.append(_ck(bool(negative), f"negative_prompt 非空（≥{neg_min} 项）",
                      "imagegen.negative_prompt"))

    locks = data.get("style_locks")
    ok_locks = isinstance(locks, list) and len(locks) >= 1
    checks.append(_ck(ok_locks,
                      f"style_locks ≥1（实际 {len(locks) if isinstance(locks, list) else 0}）",
                      "imagegen.style_locks"))

    # 风格锁自洽：锁条目不得在负向提示词中被否定（自我推翻）
    contradiction = []
    if ok_locks and negative:
        for lock in locks:
            if isinstance(lock, str) and lock.strip():
                # 负向提示词中命中锁原文（或其否定式）即矛盾
                if lock in negative or f"不{lock}" in negative or f"无{lock}" in negative:
                    contradiction.append(lock)
    ok_lock = not contradiction
    checks.append(_ck(ok_lock,
                      f"风格锁不被负向提示词推翻（矛盾 {contradiction or '无'}）",
                      "imagegen.lock_consistency"))

    ok = ok_media and ok_style and bool(prompt) and bool(negative) and ok_locks and ok_lock
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    media=media, style=style,
                    lock_count=len(locks) if isinstance(locks, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_style(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    style = data.get("style")
    ok_style = style in th["imagegen"]["style_types"]
    checks.append(_ck(ok_style,
                      f"style={style!r} 在白名单 {th['imagegen']['style_types']}",
                      "style.type"))

    composition = data.get("composition")
    ok_comp = isinstance(composition, list) and len(composition) >= 1
    checks.append(_ck(ok_comp,
                      f"composition ≥1（实际 {len(composition) if isinstance(composition, list) else 0}）",
                      "style.composition"))
    comp_ok = ok_comp
    if isinstance(composition, list):
        for i, item in enumerate(composition):
            if not isinstance(item, str) or not item.strip():
                checks.append(_ck(False, f"composition[{i}] 非字符串",
                                  "style.composition"))
                comp_ok = False

    palette = data.get("palette")
    ok_pal = isinstance(palette, list) and all(
        isinstance(p, str) and c.is_hex_color(p) for p in palette) if isinstance(palette, list) else False
    checks.append(_ck(ok_pal, f"palette 为 hex 色列表（{palette!r}）",
                      "style.palette"))

    ok = ok_style and comp_ok and ok_pal
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    style=style,
                    comp_count=len(composition) if isinstance(composition, list) else 0,
                    palette=palette if isinstance(palette, list) else [])
