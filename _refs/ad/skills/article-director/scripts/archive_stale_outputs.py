import argparse
import json
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
OUTPUTS_DIR = SKILL_ROOT / "outputs"
ARCHIVE_DIR = OUTPUTS_DIR / "_archive-bad-runs"

ARCHIVE_NAME_PATTERNS = (
    "post-review-revision",
    "gate-check",
    "gate-shrink-check",
    "interaction-check",
    "flow-check",
    "shape-check",
    "strict-",
    "mock-approval",
)

KEEP_EXACT = {
    "_archive-bad-runs",
    "_rerun-backups",
    "workflow-shape-check-20260524",
}


def should_archive_dir(path: Path) -> tuple[bool, str]:
    name = path.name
    if name in KEEP_EXACT:
        return False, ""
    lowered = name.lower()
    for pattern in ARCHIVE_NAME_PATTERNS:
        if pattern in lowered:
            return True, f"name matched pattern: {pattern}"
    if lowered.endswith("-v2") or lowered.endswith("-v3"):
        return True, "name matched generated version suffix"
    bootstrap_run = path / f"run_{name}.py"
    if "check" in lowered and not bootstrap_run.exists():
        return True, "check-only directory without bootstrap run script"
    run_files = list(path.glob("run_*_expanded.py"))
    if not run_files and (path / "workflow-profile.json").exists() and not any(path.glob("run_*.py")):
        return True, "profile-only directory without runnable bootstrap script"
    return False, ""


def collect_candidates() -> list[dict]:
    candidates: list[dict] = []
    if not OUTPUTS_DIR.exists():
        return candidates
    for path in OUTPUTS_DIR.iterdir():
        if not path.is_dir():
            continue
        archive, reason = should_archive_dir(path)
        if archive:
            candidates.append({"type": "dir", "path": path, "reason": reason})
    for pycache in OUTPUTS_DIR.rglob("__pycache__"):
        try:
            top_level = pycache.relative_to(OUTPUTS_DIR).parts[0]
        except Exception:
            top_level = ""
        if top_level in KEEP_EXACT:
            continue
        candidates.append({"type": "pycache", "path": pycache, "reason": "stale runtime cache under outputs"})
    return candidates


def move_candidate(item: dict) -> dict:
    source: Path = item["path"]
    if item["type"] == "dir":
        target = ARCHIVE_DIR / source.name
        if target.exists():
            suffix = 2
            while (ARCHIVE_DIR / f"{source.name}--{suffix}").exists():
                suffix += 1
            target = ARCHIVE_DIR / f"{source.name}--{suffix}"
        shutil.move(str(source), str(target))
        return {"action": "moved", "source": str(source), "target": str(target), "reason": item["reason"]}
    shutil.rmtree(source, ignore_errors=True)
    return {"action": "deleted", "source": str(source), "target": "", "reason": item["reason"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive stale article-director output directories")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    candidates = collect_candidates()
    payload = {
        "apply": args.apply,
        "archive_dir": str(ARCHIVE_DIR),
        "candidate_count": len(candidates),
        "candidates": [
            {"type": item["type"], "path": str(item["path"]), "reason": item["reason"]}
            for item in candidates
        ],
    }
    if not args.apply:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    moved = [move_candidate(item) for item in candidates]
    print(
        json.dumps(
            {
                **payload,
                "moved_count": len(moved),
                "moved": moved,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
