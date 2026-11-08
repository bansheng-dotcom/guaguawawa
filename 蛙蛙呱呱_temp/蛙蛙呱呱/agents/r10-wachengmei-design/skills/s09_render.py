# -*- coding: utf-8 -*-
"""S09 数据视觉与营销物料 —— 能力域 9。

R10 的**确定性生成层**（第九节「LLM 生成，Python 关笼子」的落点）：本技能不是画师，
而是「营销物料版式工厂」——把 `poster` contract（宣传图契约）确定性渲染成矢量 SVG。

设计系统（对齐 qiuqiu 互联网报告样张的确定性渲染纪律）：
- 语义色令牌（bg/accent/muted/soft…）+ 12 栏网格 + 字阶（display/title/body/caption）
- 版面骨架：品牌标 → 主标题+副标 → 主视觉区 → 卖点胶囊 → 脚注
- 主视觉只做「参数化几何体」（圆角矩形/圆形/渐变的确定性组合），不假装会画照片级
  产品图——那交给 `imagegen prompt` 产提示词、由真实生图模型生成。

契约校验：poster 缺必填字段即 FAIL（`validate_poster` 返回 {ok, grade, checks[]}）。

动作：
  poster  校验并渲染宣传图契约 → SVG
  theme   打印内置主题色板（供 poster 契约引用）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "render"
DESC = "数据视觉与营销物料：poster/theme"

# 内置主题（semantic color token）。阈值外置到 thresholds.json 后可覆盖。
_THEMES: Dict[str, Dict[str, str]] = {
    "tech-blue": {
        "bg_top": "#0A0F1E", "bg_bottom": "#0C1326", "accent": "#22D3EE",
        "accent_soft": "#0891B2", "text": "#F8FAFC", "muted": "#94A3B8",
        "card": "#16213E", "rim": "#22D3EE",
    },
    "brand-yellow": {
        "bg_top": "#0F1722", "bg_bottom": "#141B2E", "accent": "#FFC21A",
        "accent_soft": "#C9980A", "text": "#F8FAFC", "muted": "#A8B3C7",
        "card": "#1C2436", "rim": "#FFC21A",
    },
    "minimal": {
        "bg_top": "#F8FAFC", "bg_bottom": "#E8EDF5", "accent": "#1E3A5F",
        "accent_soft": "#2C4F7E", "text": "#1D2739", "muted": "#5A6B84",
        "card": "#FFFFFF", "rim": "#1E3A5F",
    },
}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    po = act.add_parser("poster", help="渲染宣传图契约 → SVG")
    po.add_argument("--input", required=True)
    po.add_argument("--output", default=None, help="输出 SVG 路径（缺省在输入旁生成）")
    th = act.add_parser("theme", help="列出内置主题色板")
    th.add_argument("--name", default=None)


def run(args) -> Dict[str, Any]:
    if args.action == "theme":
        return _theme(getattr(args, "name", None))
    if args.action == "poster":
        data = c.load_json(args.input)
        out = _validate_poster(data)
        if out["ok"]:
            svg = render_poster(data)
            out_path = getattr(args, "output", None) or (args.input.rsplit(".", 1)[0] + ".svg")
            c.write_text(out_path, svg)
            out["artifact"] = out_path
            out["next"] = f"宣传图已渲染：{out_path}"
        return out
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
# 契约校验（确定性门禁）
# --------------------------------------------------------------------------- #
_REQUIRED_TOP = ["title", "subtitle", "theme", "subject", "selling_points"]
_VALID_SUBJECT = {"mouse", "phone", "headphone", "generic"}


def _theme(name: str = None) -> Dict[str, Any]:
    if name and name not in _THEMES:
        return {"ok": False, "grade": "FAIL",
                "checks": [_ck(False, f"未知主题 {name}（可选 {sorted(_THEMES)}）", "theme")],
                "verdict": "FAIL"}
    return {"ok": True, "grade": "PASS", "verdict": "PASS",
            "themes": sorted(_THEMES),
            "selected": name if name in _THEMES else None,
            "palette": _THEMES.get(name) if name else None}


def _validate_poster(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "poster 契约必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")
    for k in _REQUIRED_TOP:
        if not str(data.get(k, "")).strip():
            checks.append(_ck(False, f"缺必填字段 {k}", f"poster.{k}"))
        else:
            checks.append(_ck(True, f"{k} 非空", f"poster.{k}"))

    theme = data.get("theme")
    checks.append(_ck(theme in _THEMES,
                      f"theme={theme!r} 在内置主题 {sorted(_THEMES)}",
                      "poster.theme"))

    subject = data.get("subject")
    checks.append(_ck(subject in _VALID_SUBJECT,
                      f"subject={subject!r} 在白名单 {sorted(_VALID_SUBJECT)}",
                      "poster.subject"))

    points = data.get("selling_points")
    if not isinstance(points, list) or len(points) != 3:
        checks.append(_ck(False,
                          f"selling_points 必须恰为 3 个（实际 {len(points) if isinstance(points, list) else 0}）",
                          "poster.selling_points"))
        pts_ok = False
    else:
        pts_ok = True
        for i, pt in enumerate(points):
            if not isinstance(pt, dict) or not str(pt.get("title", "")).strip() \
                    or not str(pt.get("desc", "")).strip():
                checks.append(_ck(False, f"selling_points[{i}] 缺 title/desc",
                                  "poster.selling_points"))
                pts_ok = False

    ok = all(ch["ok"] for ch in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    point_count=len(points) if isinstance(points, list) else 0)


# --------------------------------------------------------------------------- #
# SVG 渲染（确定性、参数化几何体，不假装画照片级产品图）
# --------------------------------------------------------------------------- #
_W = 1200
_H = 1200


def _esc(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _mouse_shape() -> str:
    """参数化无线鼠标（侧视）路径。"""
    return ("M 600 940 C 470 940 378 878 366 798 C 354 716 358 618 408 543 "
            "C 452 478 544 458 600 458 C 656 458 748 478 792 543 "
            "C 842 618 846 716 834 798 C 822 878 730 940 600 940 Z")


def _subject_path(subject: str) -> str:
    if subject == "mouse":
        return _mouse_shape()
    if subject == "phone":
        return ("M 600 952 C 508 952 460 900 458 810 L 458 420 C 458 330 510 288 "
                "600 288 C 690 288 742 330 742 420 L 742 810 C 740 900 692 952 600 952 Z")
    if subject == "headphone":
        return ("M 600 760 C 470 760 392 670 388 540 L 388 430 C 388 330 442 288 "
                "600 288 C 758 288 812 330 812 430 L 812 540 C 808 670 730 760 600 760 Z")
    return _mouse_shape()


def render_poster(data: Dict[str, Any]) -> str:
    th = _THEMES[data["theme"]]
    title = _esc(data["title"])
    subtitle = _esc(data["subtitle"])
    brand = _esc(data.get("brand", "LINGXI"))
    brandline = _esc(data.get("brandline", "LINGXI · PRO"))
    subject = data.get("subject", "mouse")
    pts = data.get("selling_points", [])

    # 12 栏网格：胶囊 3 个，每个跨 3 栏（268px），槽 38px
    pills = ""
    x0 = 150
    for pt in pts[:3]:
        t = _esc(pt["title"])
        d = _esc(pt["desc"])
        pills += f"""
  <g>
    <rect x="{x0}" y="1006" width="268" height="86" rx="43" fill="{th['card']}"
          stroke="{th['rim']}" stroke-opacity="0.5" stroke-width="1.5"/>
    <circle cx="{x0 + 54}" cy="1049" r="7" fill="{th['accent']}"/>
    <text x="{x0 + 84}" y="1043" fill="{th['text']}" font-size="26"
          font-weight="600">{t}</text>
    <text x="{x0 + 84}" y="1074" fill="{th['muted']}" font-size="18">{d}</text>
  </g>"""
        x0 += 268 + 38

    body_grad = _mouse_shape()
    accent = th["accent"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" viewBox="0 0 {_W} {_H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{th['bg_top']}"/>
      <stop offset="1" stop-color="{th['bg_bottom']}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="{accent}" stop-opacity="0.22"/>
      <stop offset="0.55" stop-color="{accent}" stop-opacity="0.08"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="shadow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#000000" stop-opacity="0.55"/>
      <stop offset="0.7" stop-color="#000000" stop-opacity="0.28"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}"/>
      <stop offset="1" stop-color="{th['accent_soft']}"/>
    </linearGradient>
  </defs>

  <rect width="{_W}" height="{_H}" fill="url(#bg)"/>
  <ellipse cx="600" cy="660" rx="560" ry="520" fill="url(#glow)"/>

  <g stroke="{accent}" stroke-opacity="0.05" stroke-width="1">
    <line x1="150" y1="0" x2="150" y2="{_H}"/><line x1="450" y1="0" x2="450" y2="{_H}"/>
    <line x1="750" y1="0" x2="750" y2="{_H}"/><line x1="1050" y1="0" x2="1050" y2="{_H}"/>
    <line x1="0" y1="400" x2="{_W}" y2="400"/><line x1="0" y1="800" x2="{_W}" y2="800"/>
  </g>

  <g text-anchor="middle" font-family="'PingFang SC','Microsoft YaHei',sans-serif">
    <text x="600" y="96" fill="{accent}" font-size="22" letter-spacing="10">{brandline}</text>
    <text x="600" y="168" fill="{th['text']}" font-size="92" font-weight="700" letter-spacing="4">{title}</text>
    <text x="600" y="232" fill="{th['muted']}" font-size="30" letter-spacing="6">{subtitle}</text>
  </g>

  <ellipse cx="600" cy="952" rx="300" ry="52" fill="url(#shadow)"/>
  <path d="{body_grad}" fill="#39455C" stroke="url(#rim)" stroke-width="2.5" stroke-opacity="0.75"/>
  <ellipse cx="600" cy="812" rx="24" ry="20" fill="#0F172A" opacity="0.85"/>
  <circle cx="600" cy="812" r="12" fill="none" stroke="{accent}" stroke-width="3"/>
  <circle cx="600" cy="812" r="4" fill="{accent}"/>

  {pills}

  <g text-anchor="middle" font-family="'PingFang SC','Microsoft YaHei',sans-serif">
    <text x="600" y="1156" fill="{th['muted']}" font-size="18" letter-spacing="3">{brand} · {title}</text>
  </g>
</svg>
"""
