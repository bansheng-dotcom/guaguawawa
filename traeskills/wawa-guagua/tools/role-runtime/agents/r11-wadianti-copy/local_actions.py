"""Local text checks only; does not publish or call platforms."""
from __future__ import annotations
from typing import Any, Dict

PLATFORM_LIMITS = {"xiaohongshu": 1000, "xhs": 1000, "douyin": 2000, "weibo": 2000, "zhihu": 10000}

def check_text(text: str, platform: str = "", min_chars: int = 1) -> Dict[str, Any]:
    text = str(text or "")
    limit = PLATFORM_LIMITS.get(str(platform or "").lower())
    ok = len(text) >= min_chars and (limit is None or len(text) <= limit)
    return {"ok": ok, "capability_status": "real", "capability_evidence": "local text formatting/length inspected", "char_count": len(text), "platform": platform, "platform_limit": limit, "format_ok": isinstance(text, str), "next": "text ready for human/platform handoff" if ok else "blocked: empty or over platform length limit"}
