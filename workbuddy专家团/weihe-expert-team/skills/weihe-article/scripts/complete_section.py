import argparse
import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark a section as completed after the fixed revision chain")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    source = section_dir / "revision-logic.md"
    final = section_dir / "final.md"
    required_ai_tone = [
        section_dir / "ai-tone-context-pack.json",
        section_dir / "ai-tone-scan.json",
        section_dir / "review-ai-tone.json",
        section_dir / "ai-tone-audit-gate.json",
        section_dir / "ai-tone-repair-plan.md",
        section_dir / "revision-de-ai.md",
        section_dir / "ai-tone-regression.json",
    ]
    issues = [f"missing {path.name} for {args.section_id}" for path in required_ai_tone if not path.exists()]
    audit_gate = _read_json(section_dir / "ai-tone-audit-gate.json")
    regression = _read_json(section_dir / "ai-tone-regression.json")
    if audit_gate and audit_gate.get("pass") is not True:
        issues.append(f"ai-tone audit gate failed for {args.section_id}")
    if regression and regression.get("pass") is not True:
        issues.append(f"ai-tone regression failed for {args.section_id}")
    if not source.exists():
        issues.append(f"missing revision-logic.md for {args.section_id}")
    if issues:
        payload = {"pass": False, "issues": issues, "file": str(final)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    shutil.copyfile(source, final)
    payload = {"pass": True, "issues": [], "passed": [f"{args.section_id} completed"], "file": str(final)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
