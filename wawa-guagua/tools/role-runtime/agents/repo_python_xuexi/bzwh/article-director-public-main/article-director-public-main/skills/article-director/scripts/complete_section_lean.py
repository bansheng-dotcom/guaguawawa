import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir


def _display_path(project_root: Path, path: Path) -> str:
    try:
        value = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        value = path
    return value.as_posix()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark a lean-v1 section complete after editor materialization and gates")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    required = [
        section_dir / "draft.md",
        section_dir / "review-source.md",
        section_dir / "final.md",
        section_dir / "section-editor-output.json",
        section_dir / "section-editor-materialize.json",
        section_dir / "ai-tone-context-pack.json",
        section_dir / "ai-tone-scan.json",
        section_dir / "review-ai-tone.json",
        section_dir / "ai-tone-audit-gate.json",
        section_dir / "ai-tone-repair-plan.md",
        section_dir / "ai-tone-regression.json",
    ]
    issues = [f"missing {path.name}" for path in required if not path.exists()]
    for path in (section_dir / "section-editor-materialize.json", section_dir / "ai-tone-audit-gate.json", section_dir / "ai-tone-regression.json"):
        payload = _read_json(path)
        if payload and payload.get("pass") is not True:
            issues.append(f"{path.name} failed")
    output_path = section_dir / "complete.json"
    result = {
        "pass": not issues,
        "issues": issues,
        "passed": [f"{args.section_id} completed in lean-v1"] if not issues else [],
        "file": _display_path(project_root, section_dir / "final.md"),
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
