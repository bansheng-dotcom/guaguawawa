# -*- coding: utf-8 -*-
"""pm_workflows 公共层：工件读写、确定性门禁结构、哈希。

与 skills/_common 保持同构，但本包不依赖 skills 包，避免
`skills/__init__ -> s11_workflows -> pm_workflows` 的循环导入。
门禁严重度沿用 R07 约定：BLOCKER 阻断、MAJOR 记录不阻断、OK 通过。
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from typing import Any, Dict, List, Optional


def read_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: str, data: Any) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def write_text(path: str, text: str) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **evidence: Any) -> Dict[str, Any]:
    item: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    item.update(evidence)
    return item


def _grade(checks: List[Dict[str, Any]]) -> str:
    if not checks:
        return "EMPTY"
    if all(x.get("ok") for x in checks):
        return "PASS"
    if any(x.get("sev") == "BLOCKER" and not x.get("ok") for x in checks):
        return "FAIL"
    return "WARN"


def gate(checks: List[Dict[str, Any]], stage: str = "") -> Dict[str, Any]:
    """把判据压成统一门禁：只有 BLOCKER 失败才阻断。"""
    failed = [x for x in checks if not x.get("ok")]
    blockers = [x for x in failed if x.get("sev") == "BLOCKER"]
    return {
        "ok": not blockers,
        "grade": _grade(checks),
        "stage": stage,
        "checks": checks,
        "errors": [f"{x.get('dim')}: {x.get('msg')}" for x in failed],
        "blockers": [f"{x.get('dim')}: {x.get('msg')}" for x in blockers],
        "warnings": [f"{x.get('dim')}: {x.get('msg')}" for x in failed
                     if x.get("sev") != "BLOCKER"],
    }


def result_ok(pack: Dict[str, Any]) -> bool:
    return bool((pack.get("gate") or {}).get("ok"))


def blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def as_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def evidence_backlink(kind: str, ref: str) -> Dict[str, str]:
    """交接回链：kind=上游包类型，ref=包内锚点。"""
    return {"kind": kind, "ref": ref}


def emit_pack(pack: Dict[str, Any], path: str) -> Dict[str, Any]:
    """统一包外壳：OK/checks/gate + 路径与 sha256。"""
    g = pack.get("gate") or {}
    return {
        "ok": bool(g.get("ok")),
        "stage": pack.get("stage", ""),
        "artifact": pack.get("artifact", ""),
        "artifact_path": os.path.abspath(path),
        "sha256": sha256_file(path) if os.path.exists(path) else "",
        "checks": g.get("checks", []),
        "grade": g.get("grade"),
        "gate": g,
        "data": pack,
    }
