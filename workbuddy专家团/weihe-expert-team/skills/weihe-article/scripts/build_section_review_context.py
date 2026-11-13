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

from compiler_lib import build_project_dir, read_json


def _read_node(project_dir: Path, section_id: str, filename: str, default: object) -> object:
    return read_json(project_dir / "sections" / section_id / filename, default)


def _read_text_node(project_dir: Path, section_id: str, filename: str) -> str:
    path = project_dir / "sections" / section_id / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build section review context for revisers")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    section_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "pass": True,
        "topic_id": args.topic_id,
        "section_id": args.section_id,
        "reviews": {
            "ai_tone": _read_node(project_dir, args.section_id, "review-ai-tone.json", {}),
            "logic": _read_node(project_dir, args.section_id, "review-logic.json", {}),
            "structure": _read_node(project_dir, args.section_id, "review-structure.json", {}),
        },
        "ai_tone": {
            "context_pack": _read_node(project_dir, args.section_id, "ai-tone-context-pack.json", {}),
            "scan": _read_node(project_dir, args.section_id, "ai-tone-scan.json", {}),
            "audit_gate": _read_node(project_dir, args.section_id, "ai-tone-audit-gate.json", {}),
            "repair_plan_path": str(section_dir / "ai-tone-repair-plan.md"),
            "repair_plan": _read_text_node(project_dir, args.section_id, "ai-tone-repair-plan.md"),
        },
        "argument_spine": {
            "path": str(section_dir / "argument-spine.md"),
            "content": _read_text_node(project_dir, args.section_id, "argument-spine.md"),
            "review_rule": "逻辑链和个人文风优先于去 AI 味；修订时不得把完整推理链切碎成连续短判断。",
        },
        "paragraph_tags": _read_node(project_dir, args.section_id, "paragraph-tags.json", {"paragraphs": []}),
        "terms": _read_node(project_dir, args.section_id, "terms.json", {"terms": []}),
        "blocking_issues": [],
        "advisory_issues": [],
    }
    for review in payload["reviews"].values():
        if isinstance(review, dict):
            payload["blocking_issues"].extend(review.get("blocking_issues", []) if isinstance(review.get("blocking_issues"), list) else [])
            payload["advisory_issues"].extend(review.get("advisory_issues", []) if isinstance(review.get("advisory_issues"), list) else [])
    output_path = section_dir / "section-review-context.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
