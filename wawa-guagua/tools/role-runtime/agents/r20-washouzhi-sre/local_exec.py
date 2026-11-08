"""Local backup manifest, content hashes, and isolated restore drill."""
import hashlib, os, shutil, tempfile


def execute(source, destination=None):
    source = os.path.abspath(source)
    if not os.path.isdir(source): return {"ok": False, "capability_status": "blocked", "reason": "backup source unreachable", "side_effects": []}
    entries = []
    for root, dirs, files in os.walk(source):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            digest = hashlib.sha256()
            with open(path, "rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
            entries.append({"relative_path": os.path.relpath(path, source), "sha256": digest.hexdigest(), "size": os.path.getsize(path)})
    target = tempfile.mkdtemp(prefix="r20-restore-drill-")
    try:
        for item in entries:
            src = os.path.join(source, item["relative_path"])
            dst = os.path.join(target, item["relative_path"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            check = hashlib.sha256(open(dst, "rb").read()).hexdigest()
            if check != item["sha256"]: raise ValueError("restore hash mismatch")
        return {"ok": True, "capability_status": "real", "manifest": entries, "restore_drill_directory": target, "restored_count": len(entries), "hashes_verified": True, "production_modified": False, "side_effects": ["temporary directory created"]}
    except Exception as exc:
        shutil.rmtree(target, ignore_errors=True)
        return {"ok": False, "capability_status": "blocked", "reason": str(exc), "side_effects": []}
