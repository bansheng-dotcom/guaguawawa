# -*- coding: utf-8 -*-
"""设计 token（P4-4）：颜色 / 字号 / 间距 / 数值精度。

默认值 = 现状（与 `charts_pro/prokit_helpers.py` 的模块常量一致），
所以换 token 文件不会改变默认产出；项目可在 `<PROJECT>/theme.yaml` 覆盖。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

#: 与 prokit_helpers 现有常量保持一致（改这里必须同步那边，门禁会比对）
DEFAULT_TOKENS: Dict[str, Any] = {
    "color": {"ink": "#1F2A37", "ink2": "#33424F", "muted": "#66737F",
              "faint": "#98A2AC", "line": "#E3E5E8", "line2": "#C9D0D6",
              "accent": "#C0392B", "blue": "#2E6F9E", "white": "#FFFFFF"},
    "font": {"family": '"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif',
             "size_sm": 7.2, "size_base": 8.6, "size_lg": 12.0},
    "space": {"pad": 20, "gap": 8, "radius": 1.5},
    "format": {"decimals": 1, "threshold_sci": 1e8},
}


def _deep_merge(base: Dict[str, Any], got: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (got or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def load(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """读主题文件（yaml/json）；缺文件返回默认 token。"""
    if not path:
        return {k: (dict(v) if isinstance(v, dict) else v)
                for k, v in DEFAULT_TOKENS.items()}
    p = Path(path)
    if not p.is_file():
        return {k: (dict(v) if isinstance(v, dict) else v)
                for k, v in DEFAULT_TOKENS.items()}
    try:
        if p.suffix.lower() == ".json":
            import json
            doc = json.loads(p.read_text(encoding="utf-8"))
        else:
            import yaml
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 主题坏了退回默认，不阻断开报告
        doc = {}
    return _deep_merge(DEFAULT_TOKENS, doc if isinstance(doc, dict) else {})


def css_vars(tokens: Optional[Dict[str, Any]] = None) -> str:
    """输出 `--chart-ink: …;` 形式，供 HTML 报告卡片挂主题。"""
    tk = tokens or DEFAULT_TOKENS
    lines = [":root{"]
    for k, v in (tk.get("color") or {}).items():
        lines.append("  --chart-%s:%s;" % (k, v))
    for k, v in (tk.get("font") or {}).items():
        if isinstance(v, str):
            lines.append("  --chart-%s:%s;" % (k, v))
    lines.append("}")
    return "\n".join(lines)


def verify_defaults_match_renderer() -> list[str]:
    """门禁用：token 默认值必须与渲染器常量一致（否则换 token 会静默改产出）。"""
    from core.report_theme.charts_pro import prokit_helpers as ph
    pairs = {"ink": ph.INK, "ink2": ph.INK2, "muted": ph.MUTED, "faint": ph.FAINT,
             "line": ph.LINE, "line2": ph.LINE2, "accent": ph.ACCENT,
             "blue": ph.BLUE, "white": ph.WHITE}
    bad = []
    for k, v in pairs.items():
        if DEFAULT_TOKENS["color"].get(k) != v:
            bad.append("%s: token=%s renderer=%s" % (k, DEFAULT_TOKENS["color"].get(k), v))
    return bad
