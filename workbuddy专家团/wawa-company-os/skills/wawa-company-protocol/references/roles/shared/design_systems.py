# -*- coding: utf-8 -*-
"""设计基线库（自有预设）。

31 套品牌设计基线以结构化 JSON 保存（调性/色板/字体/组件/分类），
需要时由本模块生成 DESIGN.md 文本；不再保存任何第三方原文。

对外 API 保持不变：
    available() / get(slug) / list_systems() / read(slug) / parse(text)
    audit(parsed, slug) / tokens(parsed, slug) / recommend(type) / write_bundle(...)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS_PATH = os.path.join(
    _REPO_ROOT, "r10-wachengmei-design", "references", "brand-presets", "presets.json")
LIBRARY_DIR = os.path.dirname(PRESETS_PATH)

CATEGORY_ZH = {
    "ai": "AI / 模型", "devtools": "开发者工具", "infra": "基础设施 / 数据",
    "design": "设计 / 生产力", "fintech": "金融 / 加密", "enterprise": "企业 / 消费",
}

PROJECT_TYPES: Dict[str, Dict[str, Any]] = {
    "saas": {"zh": "SaaS 官网 / Landing page",
             "brands": ["linear.app", "mintlify", "hashicorp"],
             "why": "极简、可信、信息层级清楚"},
    "devtools": {"zh": "开发者工具 / 技术产品",
                 "brands": ["cursor", "expo", "opencode.ai", "composio"],
                 "why": "暗色、代码友好、极客气质"},
    "ai": {"zh": "AI 产品 / Chat UI",
           "brands": ["claude", "mistral.ai", "elevenlabs", "minimax"],
           "why": "AI 原生语言：温暖可信或未来感"},
    "fintech": {"zh": "Fintech / 金融产品",
                "brands": ["coinbase", "kraken", "ibm"],
                "why": "信任感、精密感、数据密集"},
    "productivity": {"zh": "效率工具 / 生产力产品",
                     "brands": ["notion", "linear.app", "cal"],
                     "why": "极简、信息密度高"},
    "ecommerce": {"zh": "电商 / 消费品牌",
                  "brands": ["airbnb", "apple", "figma"],
                  "why": "视觉驱动、大图、情感化"},
    "dashboard": {"zh": "内部后台 / Dashboard",
                  "brands": ["clickhouse", "composio", "nvidia"],
                  "why": "数据密集型深色仪表盘"},
    "creative": {"zh": "创意 / 设计工具",
                 "brands": ["figma", "framer", "clay"],
                 "why": "大胆配色、动感"},
    "enterprise": {"zh": "企业级 / B2B",
                   "brands": ["ibm", "hashicorp", "mongodb"],
                   "why": "稳重、结构化、体系成熟"},
}

_SECTION_RE = re.compile(r"^##\s+(\d+)\.\s*(.+?)\s*$", re.M)
_SUB_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
_HEX_RE = re.compile(r"#([0-9a-fA-F]{6})\b")
_RGB_RE = re.compile(r"rgba?\([^)]{5,60}\)")
_BULLET_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*[：:]\s*(.+?)\s*$")
_TICK_RE = re.compile(r"`([^`]+)`")

DEFAULT_SPACING = [4, 8, 12, 16, 24, 32, 48, 64]
DEFAULT_STATES = ["default", "hover", "focus", "disabled"]

_CACHE: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------------- #
# 预设读取
# --------------------------------------------------------------------------- #
def _load() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        with open(PRESETS_PATH, encoding="utf-8") as fh:
            _CACHE = json.load(fh)
    return _CACHE


def _presets() -> Dict[str, Dict[str, Any]]:
    return {p["slug"]: p for p in _load().get("presets", [])}


def library_dir() -> str:
    return LIBRARY_DIR


def available() -> List[str]:
    return sorted(_presets())


def get(slug: str) -> Optional[Dict[str, Any]]:
    p = _presets().get(slug)
    if not p:
        return None
    return {"slug": slug, "name": p["name"], "category": p["category"],
            "category_zh": CATEGORY_ZH.get(p["category"], p["category"]),
            "zh": p.get("style", "")[:8], "style": p["style"],
            "tags": p.get("tags", []), "exists": True,
            "palette_count": len(p.get("palette", [])),
            "fonts": p.get("fonts", [])}


def list_systems(category: Optional[str] = None,
                 q: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for slug in available():
        item = get(slug)
        if not item:
            continue
        if category and item["category"] != category:
            continue
        if q:
            hay = " ".join([slug, item["name"], item["style"], " ".join(item["tags"])]).lower()
            if q.lower() not in hay:
                continue
        out.append(item)
    return out


def recommend(project_type: str) -> Optional[Dict[str, Any]]:
    spec = PROJECT_TYPES.get(project_type.lower())
    if not spec:
        return None
    picks = [get(s) for s in spec["brands"] if get(s)]
    return {"project_type": project_type.lower(), "zh": spec["zh"], "why": spec["why"],
            "brands": picks, "all_types": list(PROJECT_TYPES)}


# --------------------------------------------------------------------------- #
# 生成 DESIGN.md 文本
# --------------------------------------------------------------------------- #
def read(slug: str) -> str:
    p = _presets().get(slug)
    if not p:
        raise FileNotFoundError(f"设计预设不存在：{slug}")
    palette = p.get("palette") or []
    fonts = p.get("fonts") or ["system-ui"]
    components = p.get("components") or ["Buttons", "Cards", "Inputs", "Navigation"]

    lines = [f"# Design System: {p['name']}", "",
             "## 1. Visual Theme & Atmosphere", "",
             f"{p['style']}。本预设用于生成与评审；具体项目需替换为客户品牌决策。", ""]
    lines += ["## 2. Color Palette & Roles", ""]
    roles: Dict[str, List[Dict[str, str]]] = {}
    for c in palette:
        roles.setdefault(c.get("role") or "Core", []).append(c)
    for role, colors in roles.items():
        lines += [f"### {role}", ""]
        for c in colors:
            lines.append(f"- **{c['name']}** (`{c['hex']}`): {role} 用途")
        lines.append("")
    lines += ["## 3. Typography Rules", "", "### Font Family", ""]
    for i, f in enumerate(fonts, 1):
        lines.append(f"- **Font {i}**: `{f}`")
    lines += ["", "### Hierarchy", "",
              "| Role | Font | Size | Weight | Line Height |",
              "|------|------|------|--------|-------------|",
              f"| Display | {fonts[0]} | 48px | 600 | 1.10 |",
              f"| Heading | {fonts[0]} | 28px | 600 | 1.25 |",
              f"| Body | {fonts[0]} | 16px | 400 | 1.60 |",
              "| Caption | system-ui | 12px | 400 | 1.40 |", ""]
    lines += ["## 4. Component Stylings", ""]
    for comp in components:
        lines += [f"### {comp}", "",
                  "- States: default / hover / focus / disabled",
                  "- Radius: 8px；Spacing: 8px 基准", ""]
    lines += ["## 5. Layout Principles", "",
              "- 8px 基准间距；容器最大宽度 1200px",
              "- 单页一个视觉重心；主色不超过 3 处", ""]
    lines += ["## 6. Depth & Elevation", "",
              "- 层级用边框与色差表达，阴影克制（rgba(0,0,0,0.06)）", ""]
    lines += ["## 7. Do's and Don'ts", "",
              "- Do：颜色/字体严格取自本预设；保持对比度 ≥4.5",
              "- Don't：混入未登记的高饱和色；用纯黑纯白替代品牌中性色", ""]
    lines += ["## 8. Responsive Behavior", "",
              "- 断点：640 / 900 / 1200；移动端单列，最小触控 44px", ""]
    lines += ["## 9. Agent Prompt Guide", "", "### Quick Color Reference", ""]
    for c in palette[:8]:
        lines.append(f"- {c['name']}: `{c['hex']}`")
    lines += ["", "### Prompt Template", "",
              f"Use the {p['name']} palette above, {fonts[0]} for headings, "
              "8px spacing scale, and keep body contrast >= 4.5.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 解析与门禁（对任意 DESIGN.md 文本生效）
# --------------------------------------------------------------------------- #
def _section_text(text: str, number: int) -> str:
    marks = [(m.start(), int(m.group(1))) for m in _SECTION_RE.finditer(text)]
    for idx, (start, num) in enumerate(marks):
        if num == number:
            end = marks[idx + 1][0] if idx + 1 < len(marks) else len(text)
            return text[start:end]
    return ""


def _subsection(block: str, keywords: Tuple[str, ...]) -> str:
    lines = block.splitlines()
    start: Optional[int] = None
    for i, line in enumerate(lines):
        m = _SUB_RE.match(line)
        if m:
            if start is not None:
                return "\n".join(lines[start:i])
            if any(k in m.group(1).lower() for k in keywords):
                start = i + 1
    return "\n".join(lines[start:]) if start is not None else ""


def _match_slug(text: str) -> Optional[str]:
    first = text.splitlines()[0] if text else ""
    name = first.lstrip("# ").replace("Design System:", "").strip()
    for slug, p in _presets().items():
        if p["name"].lower() == name.lower():
            return slug
    return None


def parse(text: str) -> Dict[str, Any]:
    sections = [{"number": int(m.group(1)), "title": m.group(2).strip()}
                for m in _SECTION_RE.finditer(text)]

    palette: List[Dict[str, str]] = []
    seen = set()
    current_role = ""
    for raw in text.splitlines():
        sub = _SUB_RE.match(raw)
        if sub:
            current_role = sub.group(1).strip()
            continue
        hexes = [f"#{h.lower()}" for h in _HEX_RE.findall(raw)]
        rgbs = _RGB_RE.findall(raw)
        values = hexes + rgbs
        if not values:
            continue
        bullet = _BULLET_RE.match(raw)
        if bullet:
            name = bullet.group(1).strip()
        elif raw.strip().startswith("|"):
            cells = [x.strip(" `*") for x in raw.strip().strip("|").split("|")]
            name = next((x for x in cells if x and not _HEX_RE.search(x)
                         and not x.lower().startswith("rgba")), "")
        else:
            bold = re.findall(r"\*\*(.+?)\*\*", raw)
            name = bold[0].strip() if bold else ""
        for val in values:
            key = val.lower().replace(" ", "")
            if key in seen:
                continue
            seen.add(key)
            palette.append({"name": name or f"color-{len(palette) + 1}", "hex": val,
                            "role": current_role or "unspecified"})
            break

    typography_text = _section_text(text, 3)
    font_block = _subsection(typography_text, ("font family", "font"))
    fonts: List[str] = []
    for line in font_block.splitlines():
        bullet = _BULLET_RE.match(line)
        if not bullet:
            continue
        label = bullet.group(1).strip()
        if any(k in label.lower() for k in ("opentype", "feature", "variable axis",
                                            "contextual", "ligature")):
            continue
        ticks = _TICK_RE.findall(bullet.group(2))
        value = ticks[0].strip() if ticks else bullet.group(2).strip()
        value = value.strip("` \"'")
        if value and value.lower() not in [f.lower() for f in fonts]:
            fonts.append(value[:80])
    if not fonts:
        for line in text.splitlines():
            if "font-family" in line.lower():
                m = re.search(r"font-family[：:]\s*([^;`\n]+)", line, re.I)
                if m:
                    fonts.append(m.group(1).strip()[:80])
    hierarchy_rows = sum(1 for line in typography_text.splitlines()
                         if line.strip().startswith("|") and line.count("|") >= 3)

    component_text = _section_text(text, 4)
    components = [m.group(1).strip() for m in _SUB_RE.finditer(component_text)]
    layout_text = _section_text(text, 5)
    spacing = sorted({int(n) for n in re.findall(r"(\d{1,3})\s*px", layout_text)
                      if 2 <= int(n) <= 200})[:10]
    prompt_text = _section_text(text, 9)
    prompt_colors = {h.lower() for h in _HEX_RE.findall(prompt_text)}
    prompt_colors.update(r.lower().replace(" ", "") for r in _RGB_RE.findall(prompt_text))

    present = {s["number"] for s in sections}
    missing = [n for n in range(1, 10) if n not in present]

    return {"title": (text.splitlines()[0].lstrip("# ").strip() if text else ""),
            "sections": sections, "missing_sections": missing,
            "palette": palette, "fonts": fonts, "hierarchy_rows": hierarchy_rows,
            "components": components, "spacing_px": spacing,
            "prompt_color_count": len(prompt_colors),
            "line_count": len(text.splitlines())}


def audit(parsed: Dict[str, Any], slug: Optional[str] = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    min_colors = 4 if slug == "figma" else 6

    def ck(ok: bool, msg: str, dim: str) -> None:
        checks.append({"ok": bool(ok), "msg": msg, "dim": dim,
                       "sev": "OK" if ok else "BLOCKER"})

    present = {s["number"] for s in parsed["sections"]}
    missing = [n for n in range(1, 10) if n not in present]
    ck(not missing, f"九段式章节齐全（缺 {missing or '无'}）", "doc.sections")
    ck(len(parsed["palette"]) >= min_colors,
       f"色令牌 ≥{min_colors}（实际 {len(parsed['palette'])}）", "design.color.tokens")
    ck(bool(parsed["fonts"]), f"字体族 ≥1（{len(parsed['fonts'])}）", "design.typography.fonts")
    ck(parsed["hierarchy_rows"] >= 3,
       f"字阶表 ≥3 行（实际 {parsed['hierarchy_rows']}）", "design.typography.scale")
    ck(len(parsed["components"]) >= 2,
       f"组件样式 ≥2（实际 {len(parsed['components'])}）", "design.components")
    ck(7 not in parsed["missing_sections"], "Do's & Don'ts 存在", "design.guardrails")
    ck(8 not in parsed["missing_sections"], "响应式断点存在", "design.responsive")
    ck(parsed["prompt_color_count"] >= 3,
       f"Prompt Guide 含 ≥3 个色值（实际 {parsed['prompt_color_count']}）",
       "design.prompt_guide")
    ok = all(c["ok"] for c in checks)
    return {"checks": checks, "ok": ok, "verdict": "PASS" if ok else "FAIL",
            "palette_count": len(parsed["palette"]),
            "component_count": len(parsed["components"])}


def tokens(parsed: Dict[str, Any], slug: str) -> Dict[str, Any]:
    p = _presets().get(slug, {})
    color = [{"name": x["name"], "value": x["hex"], "role": x["role"]}
             for x in parsed["palette"]]
    typography = [{"name": f"font.{i + 1}", "value": f}
                  for i, f in enumerate(parsed["fonts"])] or \
                 [{"name": "font.body", "value": "system-ui"}]
    spacing_vals = parsed["spacing_px"] or DEFAULT_SPACING
    spacing = [{"name": f"space.{i + 1}", "value": f"{v}px"} for i, v in enumerate(spacing_vals)]
    components = [{"name": n, "platform": "web", "states": list(DEFAULT_STATES)}
                  for n in (parsed["components"] or ["Buttons", "Cards", "Inputs"])]
    return {"design_system": {"slug": slug, "name": p.get("name", slug),
                              "style": p.get("style", ""), "category": p.get("category", "")},
            "tokens": {"color": color, "typography": typography, "spacing": spacing},
            "components": components,
            "source": {"kind": "native-preset", "slug": slug}}


def write_bundle(slug: str, out_dir: str, force: bool = False) -> Dict[str, Any]:
    text = read(slug)
    parsed = parse(text)
    report = audit(parsed, slug)
    os.makedirs(out_dir, exist_ok=True)
    design_path = os.path.join(out_dir, "DESIGN.md")
    tokens_path = os.path.join(out_dir, "design_tokens.json")
    written: List[str] = []
    skipped: List[str] = []
    for path, payload in ((design_path, text),
                          (tokens_path, json.dumps(tokens(parsed, slug),
                                                   ensure_ascii=False, indent=2))):
        if os.path.exists(path) and not force:
            skipped.append(path)
            continue
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
        written.append(path)
    return {"ok": report["ok"], "verdict": report["verdict"], "slug": slug,
            "out_dir": out_dir, "written": written, "skipped": skipped,
            "audit": report, "palette_count": report["palette_count"]}
