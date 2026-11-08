"""Safe local project scaffold inspection for R08."""
from __future__ import annotations
import os
from typing import Any, Dict


def inspect_scaffold(data: Dict[str, Any], base_dir: str = ".") -> Dict[str, Any]:
    root = os.path.realpath(os.path.join(base_dir, str(data.get("root", "."))))
    files = data.get("files", [])
    checked = []
    errors = []
    for item in files:
        rel = str(item.get("path", ""))
        target = os.path.realpath(os.path.join(root, rel))
        if not rel or os.path.commonpath([root, target]) != root:
            errors.append({"path": rel, "reason": "invalid or escaping path"})
            continue
        exists = os.path.isfile(target)
        checked.append({"path": rel, "exists": exists, "size_bytes": os.path.getsize(target) if exists else None})
        if item.get("required", True) and not exists:
            errors.append({"path": rel, "reason": "required file missing"})
    return {"ok": not errors, "capability_status": "real", "capability_evidence": "local project paths checked without writing", "root": root, "checked": checked, "errors": errors}
