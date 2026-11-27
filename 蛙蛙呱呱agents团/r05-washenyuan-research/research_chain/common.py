# -*- coding: utf-8 -*-
"""研究链公共件：阶段顺序、门禁结构、确定性哈希与读写。

设计口径（对齐 r06 analysis_chain）：
- 每个阶段只产出一个 JSON 工件，工件内含 `gate`（逐条 check）；
- 门禁 id 形如 `stage:rule`，报告与测试都按 id 断言，避免“只返回 ok=false”无法定位；
- 全部计算确定性：无随机、无联网、无时间依赖（时间戳只进 manifest）。
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Iterable, List

STAGE_ORDER: List[str] = [
    "scope", "source", "collect", "verify", "triangulate", "size", "compete", "report",
]

STAGE_TITLES: Dict[str, str] = {
    "scope": "拆解决策问题（5–8 子问题 + MECE）",
    "source": "源地图（一手/二手/三手 × 载体 × 可访问性）",
    "collect": "证据台账（claim/value/unit/period/url/date/quote）",
    "verify": "逐条验证（回抓/复算/偏见/时效）",
    "triangulate": "三角验证（置信度 + 矛盾记录）",
    "size": "市场测算（top-down + bottom-up + p10/p50/p90）",
    "compete": "竞争格局（5 家 × 8 维 + battlecard + 五力 + 份额）",
    "report": "研究简报（结论先行 + 证据附录 + 边界）",
}

STAGE_FILES: Dict[str, str] = {s: "%s.json" % s for s in STAGE_ORDER}
REPORT_MD = "research_report.md"
REPORT_HTML = "research_report.html"
MANIFEST_FILE = "research_manifest.json"


def ck(cid: str, ok: bool, detail: str = "") -> Dict[str, Any]:
    """构造一条门禁检查。"""
    return {"id": cid, "ok": bool(ok), "detail": str(detail)}


def gate(checks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """把逐条 check 汇总成门禁对象；失败清单按 id 稳定排序。"""
    rows = list(checks)
    failed = sorted([r["id"] for r in rows if not r["ok"]])
    return {
        "ok": not failed,
        "passed": len(rows) - len(failed),
        "total": len(rows),
        "failed": failed,
        "checks": rows,
    }


def now_iso() -> str:
    """仅用于 manifest 的时间戳（研究结论本身不依赖时间）。"""
    import datetime

    return datetime.datetime.now().replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: str, data: Any) -> str:
    """写 JSON（UTF-8、不转义中文），返回文件 sha256。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False).encode("utf-8")
    with open(path, "wb") as f:
        f.write(payload)
    return sha256_bytes(payload)


def write_text(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = text.encode("utf-8")
    with open(path, "wb") as f:
        f.write(payload)
    return sha256_bytes(payload)


def file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def nonempty(value: Any) -> bool:
    """字符串/数字/列表的非空判定（0 视为有效数字）。"""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def as_number(value: Any) -> float:
    """严格数值化：布尔与空串不算数字。"""
    if isinstance(value, bool):
        raise ValueError("布尔值不是有效数值")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("无法数值化: %r" % (value,))


def sort_ids(ids: Iterable[str]) -> List[str]:
    """按自然序号排序（S2 < S10，E1 < E10），保证输出稳定。"""
    def key(x: str):
        head = "".join(ch for ch in x if ch.isalpha())
        tail = "".join(ch for ch in x if ch.isdigit())
        return (head, int(tail) if tail else -1, x)

    return sorted({str(i) for i in ids}, key=key)


def confidence_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(str(value), 3)
