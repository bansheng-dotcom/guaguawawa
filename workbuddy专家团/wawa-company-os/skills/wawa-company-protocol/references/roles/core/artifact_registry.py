"""Artifact 注册与审计记录（纯标准库）。"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def _atomic_write(path: str, data: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ArtifactRegistry:
    """JSONL append log plus atomically maintained JSON index."""
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.jsonl_path = os.path.join(self.root, "artifacts.jsonl")
        self.json_path = os.path.join(self.root, "artifacts.json")
        os.makedirs(self.root, exist_ok=True)

    def register(self, artifact_ref: str, sha256: str = "", schema_version: str = "1",
                 producer: str = "", inputs: Optional[Iterable[Any]] = None,
                 status: str = "created", created_at: Optional[str] = None,
                 **extra: Any) -> Dict[str, Any]:
        if not sha256 and extra.get("path") and os.path.isfile(str(extra["path"])):
            sha256 = sha256_file(str(extra["path"]))
        record = {"artifact_ref": artifact_ref, "sha256": sha256,
                  "schema_version": schema_version, "producer": producer,
                  "inputs": list(inputs or []), "status": status,
                  "created_at": created_at or datetime.now(timezone.utc).isoformat()}
        record.update(extra)
        # Serialize once, then replace index and append log under the same process lock.
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        old = self.records()
        old.append(record)
        _atomic_write(self.jsonl_path, "".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in old))
        _atomic_write(self.json_path, json.dumps(old, ensure_ascii=False, indent=2) + "\n")
        return record

    def records(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.jsonl_path):
            return []
        out = []
        with open(self.jsonl_path, encoding="utf-8") as f:
            for line in f:
                if line.strip(): out.append(json.loads(line))
        return out

    def get(self, artifact_ref: str) -> Optional[Dict[str, Any]]:
        found = [r for r in self.records() if r.get("artifact_ref") == artifact_ref]
        return found[-1] if found else None


def register_artifact(root: str, **fields: Any) -> Dict[str, Any]:
    return ArtifactRegistry(root).register(**fields)
