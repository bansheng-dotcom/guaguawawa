"""Local-only media file inspection; no upload, transcoding, or external calls."""
from __future__ import annotations
import mimetypes, os
from typing import Any, Dict


def inspect_media(path: str, max_bytes: int = 50_000_000) -> Dict[str, Any]:
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else None
    mime, _ = mimetypes.guess_type(path)
    ok = bool(exists and size is not None and size > 0 and size <= max_bytes and mime and (mime.startswith("image/") or mime.startswith("audio/") or mime.startswith("video/")))
    status = "real" if exists else "blocked"
    return {"ok": ok, "capability_status": status, "capability_evidence": "local file existence/MIME/size inspected", "path": path, "exists": exists, "mime": mime, "size_bytes": size, "max_bytes": max_bytes, "next": "ready for a local media pipeline" if ok else "blocked: local media file is missing, empty, oversized, or unsupported"}
