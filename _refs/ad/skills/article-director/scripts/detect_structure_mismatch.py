import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from article_quality_gates import (
    evaluate_structure_mismatch,
    package_output_path,
    render_gate_payload,
    resolve_package_sections,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect structure mismatch for a package output")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--stage", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    output_path = package_output_path(project_root, args.topic_id, args.package_id, args.stage)
    sections, package = resolve_package_sections(project_root, args.topic_id, args.package_id)

    if not package:
        payload = render_gate_payload(False, output_path, [], [f"package not found: {args.package_id}"], package_id=args.package_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)
    if not output_path.exists():
        payload = render_gate_payload(False, output_path, [], [f"package output missing: {output_path}"], package_id=args.package_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)

    text = output_path.read_text(encoding="utf-8")
    passed, issues = evaluate_structure_mismatch(text, sections)
    payload = render_gate_payload(not issues, output_path, passed, issues, package_id=args.package_id, stage=args.stage or "latest")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if not issues else 1)


if __name__ == "__main__":
    main()
