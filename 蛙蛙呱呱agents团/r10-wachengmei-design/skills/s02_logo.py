# -*- coding: utf-8 -*-
"""S02 Logo、图标与品牌 VI —— 能力域 2。

整合自 kaankiziltug__logo-design-skill（8 类 mark type、测试阶梯、光学修正）
+ jgerton__brand-toolkit(brand-visual-identity)。
把「logo 不能只在 512px 好看」落成确定性校验：mark_type 白名单、多尺寸测试、
单色测试、16px 底线、商标排查、主/次色 hex 合法且对比度达标。

动作：
  logo   校验 logo 设计包（mark_type/concepts/tests/color）
  favicon 校验 favicon/app-icon 变体包（variants ≥3 + sizes）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "logo"
DESC = "Logo图标与品牌VI：logo/favicon"


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "OK") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": sev if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    lg = act.add_parser("logo", help="校验 logo 设计包")
    lg.add_argument("--input", required=True)
    fv = act.add_parser("favicon", help="校验 favicon/app-icon 变体")
    fv.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "logo":
        return _validate_logo(data)
    if args.action == "favicon":
        return _validate_favicon(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_logo(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    mark_type = data.get("mark_type")
    ok_mt = mark_type in th["logo"]["mark_types"]
    checks.append(_ck(ok_mt,
                      f"mark_type={mark_type!r} 在白名单 {th['logo']['mark_types']}",
                      "logo.mark_type"))

    # concepts：至少 3 个不同方向（样式寻路阶段）
    concepts = data.get("concepts")
    ok_cc = isinstance(concepts, list) and len(concepts) >= 3
    checks.append(_ck(ok_cc,
                      f"concepts ≥3（实际 {len(concepts) if isinstance(concepts, list) else 0}）",
                      "logo.concepts"))
    cc_ok = ok_cc
    if isinstance(concepts, list):
        for i, co in enumerate(concepts):
            if not isinstance(co, dict) or not str(co.get("name", "")).strip():
                checks.append(_ck(False, f"concept[{i}] 缺 name",
                                  "logo.concepts"))
                cc_ok = False
            elif not str(co.get("idea", "")).strip():
                checks.append(_ck(False, f"concept[{i}] 缺 idea（一句话想法）",
                                  "logo.concepts"))
                cc_ok = False

    # 测试矩阵：多尺寸 + 单色 + 16px 底线
    tests = data.get("tests")
    if not isinstance(tests, dict):
        checks.append(_ck(False, "tests 缺失或非对象", "logo.tests"))
        test_ok = False
        passed = 0
    else:
        ladder = th["logo"]["test_ladders"]
        missing = [s for s in ladder if str(s) not in tests]
        checks.append(_ck(not missing, f"尺寸测试覆盖 {ladder}（缺 {missing or '无'}）",
                          "logo.tests.sizes"))
        one_color = tests.get("one_color")
        if not isinstance(one_color, dict) or not one_color.get("readable"):
            checks.append(_ck(False, "单色测试缺失或不可读", "logo.tests.one_color"))
        else:
            checks.append(_ck(True, "单色测试可读", "logo.tests.one_color"))
        px16 = tests.get("16px")
        ok_px = isinstance(px16, dict) and px16.get("legible") is True
        checks.append(_ck(ok_px, "16px 小尺寸可辨识（legible=true）",
                          "logo.tests.16px"))
        passed = sum(1 for s in ladder if str(s) in tests and tests[str(s)])
        test_ok = (not missing) and isinstance(one_color, dict) \
            and one_color.get("readable") and ok_px

    # 商标排查：至少 1 条筛查记录
    trademark = data.get("trademark_check")
    ok_tm = isinstance(trademark, list) and len(trademark) >= th["logo"]["trademark_min"]
    checks.append(_ck(ok_tm,
                      f"trademark_check ≥{th['logo']['trademark_min']} 条（实际 {len(trademark) if isinstance(trademark, list) else 0}）",
                      "logo.trademark_check"))

    # 颜色：主/次色 hex 合法 + 对比度达标（文字与背景）
    colors = data.get("colors")
    if not isinstance(colors, dict):
        checks.append(_ck(False, "colors 缺失或非对象", "logo.colors"))
        color_ok = False
    else:
        primary = colors.get("primary")
        secondary = colors.get("secondary")
        ok_hex = c.is_hex_color(primary) and c.is_hex_color(secondary)
        checks.append(_ck(ok_hex, f"primary/secondary 为合法 hex（{primary}/{secondary}）",
                          "logo.colors.hex"))
        contrast_ok = ok_hex and c.contrast(primary, secondary) >= 3.0
        checks.append(_ck(contrast_ok,
                          f"主/次色对比度 ≥3.0（实际 {c.contrast(primary, secondary):.2f}）" if ok_hex
                          else "主/次色对比度无法计算",
                          "logo.colors.contrast"))
        color_ok = ok_hex and contrast_ok

    ok = ok_mt and cc_ok and test_ok and ok_tm and color_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    mark_type=mark_type,
                    concept_count=len(concepts) if isinstance(concepts, list) else 0,
                    tests_passed=passed)


# --------------------------------------------------------------------------- #
def _validate_favicon(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    variants = data.get("variants")
    ok_v = isinstance(variants, list) and len(variants) >= 3
    checks.append(_ck(ok_v,
                      f"variants ≥3（favicon/app-icon/可缩放）（实际 {len(variants) if isinstance(variants, list) else 0}）",
                      "favicon.variants"))
    v_ok = ok_v
    sizes: List[str] = []
    if isinstance(variants, list):
        for i, v in enumerate(variants):
            if not isinstance(v, dict) or not str(v.get("name", "")).strip():
                checks.append(_ck(False, f"variant[{i}] 缺 name", "favicon.variant"))
                v_ok = False
                continue
            sizes.append(str(v.get("name")))
    if "favicon" not in sizes or not any("app" in s for s in sizes):
        checks.append(_ck(False, "变体需含 favicon 与 app-icon 类", "favicon.coverage"))
        v_ok = False

    source = data.get("source")
    ok_src = bool(source) and str(source).endswith(".svg")
    checks.append(_ck(ok_src,
                      f"source 为 svg（{source}）",
                      "favicon.source"))

    ok = v_ok and ok_src
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    variant_count=len(variants) if isinstance(variants, list) else 0,
                    source=source)
