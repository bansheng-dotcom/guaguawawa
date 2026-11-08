# -*- coding: utf-8 -*-
"""S04 品牌 VI 与设计令牌 —— 能力域 4（品牌 VI 归并进本域）。

整合自 jgerton__brand-toolkit(brand-visual-identity / brand-audit / brand-voice)
+ mae616__design-skills 的 token 纪律。
把「视觉身份必须策略驱动」落成确定性校验：
  - vi：Stylescapes 三方向、每方向四要素（色彩/字体/图像/叙事）、反陈词滥调
  - token：色彩/排版/间距三类 token 全部 name+value

动作：
  vi    校验品牌视觉身份（3 方向 Stylescape）
  token 校验设计令牌（三类 token + 主色）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "brand"
DESC = "品牌VI与设计令牌：vi/token"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    vi = act.add_parser("vi", help="校验品牌视觉身份")
    vi.add_argument("--input", required=True)
    tk = act.add_parser("token", help="校验设计令牌")
    tk.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "vi":
        return _validate_vi(data)
    if args.action == "token":
        return _validate_token(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_vi(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    directions = data.get("directions")
    ok_d = isinstance(directions, list) and len(directions) >= th["brand"]["stylescape_dirs_min"]
    checks.append(_ck(ok_d,
                      f"directions ≥{th['brand']['stylescape_dirs_min']}（实际 {len(directions) if isinstance(directions, list) else 0}）",
                      "brand.directions"))
    d_ok = ok_d
    if isinstance(directions, list):
        for i, d in enumerate(directions):
            if not isinstance(d, dict):
                checks.append(_ck(False, f"direction[{i}] 非对象", "brand.directions"))
                d_ok = False
                continue
            for key in ("name", "palette", "typography", "imagery", "narrative"):
                if not str(d.get(key, "")).strip():
                    checks.append(_ck(False, f"direction[{i}] 缺 {key}",
                                      f"brand.directions.{key}"))
                    d_ok = False
            # 反陈词滥调：narrative 不允许出现通用空话
            narrative = str(d.get("narrative", ""))
            for cliche in ("因为蓝色代表信任", "看起来专业", "显得高端", "lorem"):
                if cliche in narrative:
                    checks.append(_ck(False, f"direction[{i}] narrative 含陈词滥调「{cliche}」",
                                      "brand.anti_slop"))
                    d_ok = False

    # 品牌语调四维（voice dimensions）
    voice = data.get("voice")
    if not isinstance(voice, dict):
        checks.append(_ck(False, "voice 缺失或非对象", "brand.voice"))
        v_ok = False
    else:
        missing = [d for d in th["brand"]["voice_dimensions"] if not str(voice.get(d, "")).strip()]
        checks.append(_ck(not missing,
                          f"voice 四维齐备（缺 {missing or '无'}）",
                          "brand.voice"))
        v_ok = not missing

    ok = d_ok and v_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    direction_count=len(directions) if isinstance(directions, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_token(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    tokens = data.get("tokens")
    ok = True
    token_count = 0
    if not isinstance(tokens, dict):
        checks.append(_ck(False, "tokens 缺失或非对象", "brand.tokens"))
        ok = False
    else:
        groups = ("color", "typography", "spacing")
        for g in groups:
            grp = tokens.get(g)
            if not isinstance(grp, list) or len(grp) < 1:
                checks.append(_ck(False, f"tokens.{g} 缺失或为空", f"brand.tokens.{g}"))
                ok = False
            else:
                token_count += len(grp)
                for i, item in enumerate(grp):
                    if not isinstance(item, dict):
                        checks.append(_ck(False, f"tokens.{g}[{i}] 非对象",
                                          f"brand.tokens.{g}"))
                        ok = False
                        continue
                    for k in ("name", "value"):
                        if not str(item.get(k, "")).strip():
                            checks.append(_ck(False, f"tokens.{g}[{i}] 缺 {k}",
                                              f"brand.tokens.{g}"))
                            ok = False

    primary = str(data.get("primary", "")).strip()
    checks.append(_ck(c.is_hex_color(primary),
                      f"primary 为合法 hex（{primary or '缺失'}）",
                      "brand.primary"))

    ok = ok and c.is_hex_color(primary)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    token_count=token_count,
                    primary=primary if c.is_hex_color(primary) else None)
