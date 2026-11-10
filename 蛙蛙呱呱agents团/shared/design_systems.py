# -*- coding: utf-8 -*-
"""设计系统库（DESIGN.md 解析与令牌契约）。

定位：把 awesome-design-md 的 31 份品牌 DESIGN.md 收进团队资产，让 R10 视觉设计官
能「查库 → 推荐 → 落盘 → 校验」，并把结果转成 R08 组件/令牌门禁认得的
``tokens`` 结构（color / typography / spacing + components）。

只依赖标准库；不联网；不执行模型调用。

对外 API：
    list_systems(category=None, q=None)   列库（含缺失标记）
    get(slug)                             取单个条目（含路径与元数据）
    read(slug)                            读原文
    parse(text)                           解析：章节 / 色板 / 字体 / 组件 / 间距
    audit(parsed)                         九段式硬门禁（PASS/FAIL + 逐项 checks）
    tokens(parsed, slug)                  转 R08 认可的令牌契约
    recommend(project_type)               按项目类型给 3~5 个品牌建议
    write_bundle(slug, out_dir, force)    落盘 DESIGN.md + design_tokens.json
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# 库位置：<repo>/r10-wachengmei-design/references/design-systems
# --------------------------------------------------------------------------- #
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_DIR = os.path.join(
    _REPO_ROOT, "r10-wachengmei-design", "references", "design-systems")

CATEGORY_ZH = {
    "ai": "AI / 模型",
    "devtools": "开发者工具",
    "infra": "基础设施 / 数据",
    "design": "设计 / 生产力",
    "fintech": "金融 / 加密",
    "enterprise": "企业 / 消费",
}

# 31 个品牌（收录自 awesome-design-md），style 为中文气质概括，
# tags 供检索，project 供按项目类型推荐。
CATALOG: Dict[str, Dict[str, Any]] = {
    "airbnb": {"name": "Airbnb", "category": "enterprise", "zh": "暖珊瑚",
               "style": "暖珊瑚强调色、摄影驱动、圆角卡片",
               "tags": ["warm", "coral", "photography", "rounded"]},
    "airtable": {"name": "Airtable", "category": "design", "zh": "彩色结构化",
                 "style": "彩色友好、结构化数据美学",
                 "tags": ["colorful", "friendly", "structured"]},
    "apple": {"name": "Apple", "category": "enterprise", "zh": "高端留白",
              "style": "大留白、SF Pro、电影感图像",
              "tags": ["premium", "whitespace", "sf-pro"]},
    "bmw": {"name": "BMW", "category": "enterprise", "zh": "德系精密",
            "style": "暗色高级面、德系工程精密感",
            "tags": ["dark", "premium", "engineering"]},
    "cal": {"name": "Cal.com", "category": "design", "zh": "中性极简",
            "style": "干净中性、开发者友好的极简",
            "tags": ["neutral", "minimal", "developer"]},
    "claude": {"name": "Claude", "category": "ai", "zh": "赤陶编辑",
               "style": "暖赤陶强调色、编辑式排版",
               "tags": ["warm", "terracotta", "editorial"]},
    "clay": {"name": "Clay", "category": "design", "zh": "有机渐变",
             "style": "有机形状、柔和渐变、艺术指导式版式",
             "tags": ["organic", "gradient", "art-directed"]},
    "clickhouse": {"name": "ClickHouse", "category": "infra", "zh": "黄色技术",
                   "style": "黄色强调、技术文档风格",
                   "tags": ["yellow", "technical", "docs"]},
    "cohere": {"name": "Cohere", "category": "ai", "zh": "渐变数据",
               "style": "高饱和渐变、数据密集型仪表盘",
               "tags": ["gradient", "data", "dashboard"]},
    "coinbase": {"name": "Coinbase", "category": "fintech", "zh": "机构蓝",
                 "style": "干净蓝色识别、信任感、机构气质",
                 "tags": ["blue", "trust", "institutional"]},
    "composio": {"name": "Composio", "category": "infra", "zh": "暗色集成",
                 "style": "现代暗色 + 彩色集成图标",
                 "tags": ["dark", "icons", "integrations"]},
    "cursor": {"name": "Cursor", "category": "devtools", "zh": "暗色渐变",
               "style": "流畅暗色界面、渐变强调",
               "tags": ["dark", "gradient", "editor"]},
    "elevenlabs": {"name": "ElevenLabs", "category": "ai", "zh": "电影暗色",
                   "style": "暗色电影感、声波美学",
                   "tags": ["dark", "cinematic", "audio"]},
    "expo": {"name": "Expo", "category": "devtools", "zh": "紧字距暗色",
             "style": "暗色主题、紧凑字距、代码优先",
             "tags": ["dark", "tight", "code"]},
    "figma": {"name": "Figma", "category": "design", "zh": "多彩活泼",
              "style": "高饱和多彩、活泼但专业",
              "tags": ["colorful", "playful", "professional"],
              "palette_min": 4},
    "framer": {"name": "Framer", "category": "design", "zh": "黑蓝动效",
               "style": "黑蓝大胆、动效优先、设计感强",
               "tags": ["black", "blue", "motion"]},
    "hashicorp": {"name": "HashiCorp", "category": "infra", "zh": "企业黑白",
                  "style": "企业级干净、黑白为主",
                  "tags": ["monochrome", "enterprise", "clean"]},
    "ibm": {"name": "IBM", "category": "enterprise", "zh": "Carbon 蓝",
            "style": "Carbon 设计系统、结构化蓝色体系",
            "tags": ["carbon", "blue", "system"]},
    "intercom": {"name": "Intercom", "category": "design", "zh": "友好蓝",
                 "style": "友好蓝色、对话式 UI",
                 "tags": ["blue", "friendly", "conversational"]},
    "kraken": {"name": "Kraken", "category": "fintech", "zh": "紫色数据台",
               "style": "紫色暗色界面、数据密集型仪表盘",
               "tags": ["purple", "dark", "dashboard"]},
    "linear.app": {"name": "Linear", "category": "devtools", "zh": "极简精准",
                   "style": "超极简、精准、紫色强调",
                   "tags": ["minimal", "precise", "purple"]},
    "lovable": {"name": "Lovable", "category": "devtools", "zh": "活泼渐变",
                "style": "俏皮渐变、友好的开发者气质",
                "tags": ["playful", "gradient", "friendly"]},
    "minimax": {"name": "MiniMax", "category": "ai", "zh": "暗色霓虹",
                "style": "大胆暗色界面 + 霓虹强调",
                "tags": ["dark", "neon", "bold"]},
    "mintlify": {"name": "Mintlify", "category": "devtools", "zh": "绿色文档",
                 "style": "干净、绿色强调、阅读优化",
                 "tags": ["green", "docs", "reading"]},
    "miro": {"name": "Miro", "category": "design", "zh": "亮黄画布",
             "style": "明黄强调、无限画布美学",
             "tags": ["yellow", "canvas", "bright"]},
    "mistral.ai": {"name": "Mistral AI", "category": "ai", "zh": "法式极简",
                   "style": "法式工程极简、紫色调",
                   "tags": ["minimal", "purple", "french"]},
    "mongodb": {"name": "MongoDB", "category": "infra", "zh": "绿叶绿",
                "style": "绿色叶形品牌、开发者文档导向",
                "tags": ["green", "docs", "developer"]},
    "notion": {"name": "Notion", "category": "design", "zh": "暖极简衬线",
               "style": "暖极简、衬线标题、柔和表面",
               "tags": ["warm", "serif", "minimal"]},
    "nvidia": {"name": "NVIDIA", "category": "enterprise", "zh": "绿黑能量",
               "style": "绿黑能量、技术力量感",
               "tags": ["green", "dark", "energy"]},
    "ollama": {"name": "Ollama", "category": "ai", "zh": "终端单色",
               "style": "终端优先、单色极简",
               "tags": ["terminal", "monochrome", "minimal"]},
    "opencode.ai": {"name": "OpenCode AI", "category": "ai", "zh": "开发者暗色",
                    "style": "开发者中心的暗色主题",
                    "tags": ["dark", "developer", "code"]},
}

# 项目类型 → 推荐品牌（只用本库 31 个里的；顺序即推荐优先级）
PROJECT_TYPES: Dict[str, Dict[str, Any]] = {
    "saas": {"zh": "SaaS 官网 / Landing page",
             "brands": ["linear.app", "mintlify", "hashicorp"],
             "why": "经典高转化 SaaS 气质：极简、可信、信息层级清楚"},
    "devtools": {"zh": "开发者工具 / 技术产品",
                 "brands": ["cursor", "expo", "opencode.ai", "composio"],
                 "why": "暗色、代码友好、极客气质，贴近开发者日常工具"},
    "ai": {"zh": "AI 产品 / Chat UI",
           "brands": ["claude", "mistral.ai", "elevenlabs", "minimax"],
           "why": "AI 原生设计语言：温暖可信或未来感，适合对话/多模态"},
    "fintech": {"zh": "Fintech / 金融产品",
                "brands": ["coinbase", "kraken", "ibm"],
                "why": "信任感、精密感、数据密集，机构客户可接受"},
    "productivity": {"zh": "效率工具 / 生产力产品",
                     "brands": ["notion", "linear.app", "cal"],
                     "why": "极简、信息密度高、键盘优先"},
    "ecommerce": {"zh": "电商 / 消费品牌",
                  "brands": ["airbnb", "apple", "figma"],
                  "why": "视觉驱动、大图、情感化，适合卖点与转化"},
    "dashboard": {"zh": "内部后台 / Dashboard",
                  "brands": ["clickhouse", "composio", "nvidia"],
                  "why": "数据密集型深色仪表盘，适合复杂后台"},
    "creative": {"zh": "创意 / 设计工具",
                 "brands": ["figma", "framer", "clay"],
                 "why": "大胆配色、动感十足，适合创意类产品"},
    "enterprise": {"zh": "企业级 / B2B",
                   "brands": ["ibm", "hashicorp", "mongodb"],
                   "why": "稳重、结构化、设计系统成熟，适合 B2B 交付"},
}

_SECTION_RE = re.compile(r"^##\s+(\d+)\.\s*(.+?)\s*$", re.M)
_SUB_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
_HEX_RE = re.compile(r"#([0-9a-fA-F]{6})\b")
_RGB_RE = re.compile(r"rgba?\([^)]{5,60}\)")
_BULLET_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*[：:]\s*(.+?)\s*$")
_TICK_RE = re.compile(r"`([^`]+)`")

# 九段式章节关键字（数字 → 关键词组）
_SECTION_KEYS: Dict[int, Tuple[str, ...]] = {
    1: ("visual theme", "atmosphere", "theme"),
    2: ("color", "palette"),
    3: ("typography",),
    4: ("component",),
    5: ("layout", "grid", "spacing"),
    6: ("depth", "elevation", "shadow"),
    7: ("do", "don't", "dont", "guardrail"),
    8: ("responsive", "breakpoint"),
    9: ("agent prompt", "prompt guide", "quick reference"),
}

DEFAULT_SPACING = [4, 8, 12, 16, 24, 32, 48, 64]
DEFAULT_STATES = ["default", "hover", "focus", "disabled"]


# --------------------------------------------------------------------------- #
# 库检索
# --------------------------------------------------------------------------- #
def library_dir() -> str:
    return LIBRARY_DIR


def path_of(slug: str) -> str:
    return os.path.join(LIBRARY_DIR, f"{slug}.md")


def available() -> List[str]:
    if not os.path.isdir(LIBRARY_DIR):
        return []
    return sorted(os.path.splitext(n)[0] for n in os.listdir(LIBRARY_DIR)
                  if n.endswith(".md") and n != "README.md")


def get(slug: str) -> Optional[Dict[str, Any]]:
    meta = CATALOG.get(slug)
    if meta is None:
        return None
    p = path_of(slug)
    return {**meta, "slug": slug, "path": p, "exists": os.path.isfile(p),
            "category_zh": CATEGORY_ZH.get(meta["category"], meta["category"])}


def list_systems(category: Optional[str] = None,
                 q: Optional[str] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for slug in sorted(CATALOG):
        item = get(slug)
        if item is None:
            continue
        if category and item["category"] != category:
            continue
        if q:
            hay = " ".join([slug, item["name"], item["zh"], item["style"],
                            " ".join(item["tags"])]).lower()
            if q.lower() not in hay:
                continue
        out.append(item)
    return out


def read(slug: str) -> str:
    p = path_of(slug)
    if not os.path.isfile(p):
        raise FileNotFoundError(f"设计系统不存在：{slug}（{p}）")
    with open(p, "r", encoding="utf-8") as fh:
        return fh.read()


def recommend(project_type: str) -> Optional[Dict[str, Any]]:
    spec = PROJECT_TYPES.get(project_type.lower())
    if not spec:
        return None
    picks = []
    for slug in spec["brands"]:
        item = get(slug)
        if item and item["exists"]:
            picks.append(item)
    return {"project_type": project_type.lower(), "zh": spec["zh"],
            "why": spec["why"], "brands": picks,
            "all_types": list(PROJECT_TYPES)}


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #
def _section_text(text: str, number: int) -> str:
    """取第 number 段（## N. ...）的正文，截到下一个 ## 为止。"""
    marks = [(m.start(), int(m.group(1))) for m in _SECTION_RE.finditer(text)]
    for idx, (start, num) in enumerate(marks):
        if num == number:
            end = marks[idx + 1][0] if idx + 1 < len(marks) else len(text)
            return text[start:end]
    return ""


def _subsection(block: str, keywords: Tuple[str, ...]) -> str:
    """取 block 里第一个匹配 keywords 的 ### 小节正文。"""
    lines = block.splitlines()
    start: Optional[int] = None
    for i, line in enumerate(lines):
        m = _SUB_RE.match(line)
        if m:
            if start is not None:
                return "\n".join(lines[start:i])
            if any(k in m.group(1).lower() for k in keywords):
                start = i + 1
    if start is not None:
        return "\n".join(lines[start:])
    return ""


def parse(text: str) -> Dict[str, Any]:
    """把 DESIGN.md 解析成结构化字典（容错：字段缺失不抛异常）。"""
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
    if not fonts:  # 兜底：全文里出现 font-family 的行
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

    return {
        "title": (text.splitlines()[0].lstrip("# ").strip() if text else ""),
        "sections": sections,
        "missing_sections": missing,
        "palette": palette,
        "fonts": fonts,
        "hierarchy_rows": hierarchy_rows,
        "components": components,
        "spacing_px": spacing,
        "prompt_color_count": len(prompt_colors),
        "line_count": len(text.splitlines()),
    }


def audit(parsed: Dict[str, Any], slug: Optional[str] = None) -> Dict[str, Any]:
    """九段式硬门禁：结构 / 色板 / 字体 / 组件 / 反模式 / 响应 / 提示指南。

    ``slug`` 用于读取品牌专属阈值（例如 Figma 是刻意只用黑白双色的系统，
    色板下限放宽到 4），避免把"设计选择"误判为"文档缺陷"。
    """
    checks: List[Dict[str, Any]] = []
    min_colors = int((CATALOG.get(slug or "", {}) or {}).get("palette_min", 6))

    def ck(ok: bool, msg: str, dim: str) -> None:
        checks.append({"ok": bool(ok), "msg": msg, "dim": dim,
                       "sev": "OK" if ok else "BLOCKER"})

    present = {s["number"] for s in parsed["sections"]}
    missing = [n for n in range(1, 10) if n not in present]
    ck(not missing, f"九段式章节齐全（缺 {missing or '无'}）", "doc.sections")

    palette = parsed["palette"]
    ck(len(palette) >= min_colors, f"色令牌 ≥{min_colors}（实际 {len(palette)}）",
       "design.color.tokens")
    ck(bool(parsed["fonts"]), f"字体族 ≥1（实际 {len(parsed['fonts'])}）",
       "design.typography.fonts")
    ck(parsed["hierarchy_rows"] >= 3,
       f"字阶表 ≥3 行（实际 {parsed['hierarchy_rows']}）", "design.typography.scale")
    ck(len(parsed["components"]) >= 2,
       f"组件样式 ≥2（实际 {len(parsed['components'])}）", "design.components")
    ck(7 not in parsed["missing_sections"],
       "Do's & Don'ts 反模式段存在", "design.guardrails")
    ck(8 not in parsed["missing_sections"],
       "响应式断点段存在", "design.responsive")
    ck(parsed["prompt_color_count"] >= 3,
       f"Agent Prompt Guide 含 ≥3 个色值（实际 {parsed['prompt_color_count']}）",
       "design.prompt_guide")

    ok = all(c["ok"] for c in checks)
    return {"checks": checks, "ok": ok, "verdict": "PASS" if ok else "FAIL",
            "palette_count": len(palette), "component_count": len(parsed["components"])}


# --------------------------------------------------------------------------- #
# 令牌契约（R08 s06 design 校验认这个结构）
# --------------------------------------------------------------------------- #
def tokens(parsed: Dict[str, Any], slug: str) -> Dict[str, Any]:
    """把解析结果转成 tokens 契约：{tokens:{color,typography,spacing}, components}。"""
    meta = CATALOG.get(slug, {})
    color = [{"name": p["name"], "value": p["hex"], "role": p["role"]}
             for p in parsed["palette"]]
    typography = [{"name": f"font.{i + 1}", "value": f} for i, f in enumerate(parsed["fonts"])]
    if not typography:
        typography = [{"name": "font.body", "value": "system-ui"}]
    spacing_vals = parsed["spacing_px"] or DEFAULT_SPACING
    spacing = [{"name": f"space.{i + 1}", "value": f"{v}px"} for i, v in enumerate(spacing_vals)]
    components = [{"name": name, "platform": "web", "states": list(DEFAULT_STATES)}
                  for name in (parsed["components"] or
                               ["Buttons", "Cards & Containers", "Inputs & Forms", "Navigation"])]
    return {
        "design_system": {"slug": slug, "name": meta.get("name", slug),
                          "style": meta.get("style", ""), "category": meta.get("category", "")},
        "tokens": {"color": color, "typography": typography, "spacing": spacing},
        "components": components,
        "source": {"kind": "awesome-design-md", "file": f"{slug}.md",
                   "lines": parsed["line_count"]},
    }


# --------------------------------------------------------------------------- #
# 落盘
# --------------------------------------------------------------------------- #
def write_bundle(slug: str, out_dir: str, force: bool = False) -> Dict[str, Any]:
    """把品牌 DESIGN.md 与设计令牌写入目标目录。"""
    text = read(slug)
    parsed = parse(text)
    report = audit(parsed, slug)
    os.makedirs(out_dir, exist_ok=True)
    design_path = os.path.join(out_dir, "DESIGN.md")
    tokens_path = os.path.join(out_dir, "design_tokens.json")
    written: List[str] = []
    skipped: List[str] = []

    header = (f"<!-- 由 R10 视觉设计官从设计系统库落盘：{slug} "
              f"（{CATALOG.get(slug, {}).get('name', slug)}） -->\n")
    for path, payload in ((design_path, header + text),
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
