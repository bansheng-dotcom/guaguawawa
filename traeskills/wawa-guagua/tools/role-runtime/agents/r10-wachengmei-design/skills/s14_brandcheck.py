# -*- coding: utf-8 -*-
"""S14 品牌一致性检查（自有实现）。

拿产物的颜色/字体/对比度去对 `DESIGN.md` 令牌：
  check  颜色是否在令牌内、字体是否是令牌字体、正文对比度是否达标、单页用色是否过多

不依赖任何外部服务；令牌来源就是本角色维护的 DESIGN.md。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from . import _common as c

try:
    from shared import design_systems as ds
except ImportError:  # pragma: no cover
    import sys
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from shared import design_systems as ds

NAME = "brandcheck"
DESC = "品牌一致性检查：check（颜色/字体/对比度）"

_ROLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DESIGN = os.path.join(_ROLE, "DESIGN.md")
CONTRAST_MIN = 4.5
MAX_COLORS = 8


def _ck(ok: bool, msg: str, dim: str = "", warn: bool = False) -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim,
            "sev": "OK" if ok else ("WARN" if warn else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ck = act.add_parser("check", help="对产物做品牌一致性检查")
    ck.add_argument("--input", required=True, help="产物描述 JSON")
    ck.add_argument("--design", default=DEFAULT_DESIGN, help="DESIGN.md 路径")


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    return _check(data, args.design)


# --------------------------------------------------------------------------- #
def _hex(value: str) -> Optional[str]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(value).strip())
    return f"#{m.group(1).lower()}" if m else None


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


GENERIC_FONTS = {"system-ui", "-apple-system", "sans-serif", "serif", "monospace",
                 "arial", "helvetica", "pingfang sc", "microsoft yahei", "segoe ui"}


def _tokens(design_path: str) -> Dict[str, Any]:
    with open(design_path, encoding="utf-8") as fh:
        text = fh.read()
    parsed = ds.parse(text)
    palette = {p["hex"].lower() for p in parsed["palette"]}
    fonts = [f.lower() for f in parsed["fonts"]]
    if not fonts:  # 团队账本用 `font.xxx` 令牌写法，不是九段式的 Font Family 小节
        for m in re.finditer(r"`?(font\.[a-z0-9_.]+)`?\s*[:：]\s*([^，,。;；\n]+)", text):
            fonts.append(m.group(2).strip().lower())
    return {"palette": palette, "fonts": fonts}


def _check(data: Any, design_path: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    if not os.path.isfile(design_path):
        return c.result([_ck(False, f"DESIGN.md 不存在：{design_path}", "brand.design")],
                        verdict="FAIL")
    tok = _tokens(design_path)
    checks: List[Dict[str, Any]] = []

    colors = [_hex(x) for x in (data.get("colors") or [])]
    known = [x for x in colors if x]
    checks.append(_ck(bool(known), "至少提供 1 个颜色", "brand.colors"))
    outside = [x for x in known if x not in tok["palette"]]
    checks.append(_ck(not outside,
                      f"颜色均在令牌内（越界：{outside or '无'}，令牌 {len(tok['palette'])} 个）",
                      "brand.colors.known"))
    distinct = len(set(known))
    checks.append(_ck(distinct <= MAX_COLORS,
                      f"单页主色 ≤{MAX_COLORS}（实际 {distinct}）",
                      "brand.colors.count", warn=(distinct > MAX_COLORS)))

    fonts = [str(f).strip() for f in (data.get("fonts") or []) if str(f).strip()]
    bad_fonts = [f for f in fonts
                 if f.lower() not in GENERIC_FONTS
                 and not any(f.lower() in t or t in f.lower() for t in tok["fonts"])]
    checks.append(_ck(not bad_fonts,
                      f"字体均为令牌字体（越界：{bad_fonts or '无'}）", "brand.fonts"))

    for i, pair in enumerate(data.get("text_pairs") or []):
        if not isinstance(pair, dict):
            continue
        fg, bg = _hex(pair.get("fg", "")), _hex(pair.get("bg", ""))
        if not fg or not bg:
            checks.append(_ck(False, f"text_pairs[{i}] 颜色格式错误", "brand.contrast.format"))
            continue
        ratio = _contrast(fg, bg)
        checks.append(_ck(ratio >= CONTRAST_MIN,
                          f"对比度 ≥{CONTRAST_MIN}（{fg} on {bg} = {ratio:.2f}）",
                          "brand.contrast"))

    ok = all(x["ok"] for x in checks if x["sev"] != "WARN")
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    design=design_path, palette_size=len(tok["palette"]),
                    outside_colors=outside,
                    next=("一致，可交付" if ok else "按越界颜色/字体/对比度修正后重检"))
