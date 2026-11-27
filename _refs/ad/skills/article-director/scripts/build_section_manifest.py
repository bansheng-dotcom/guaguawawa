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

from compiler_lib import (
    apply_article_word_budget,
    build_project_dir,
    parse_detailed_outline,
    read_json,
    read_workflow_profile,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic section manifest from detailed outline")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    topic_id = args.topic_id
    outline_path = project_root / "tmp" / f"{topic_id}-detailed-outline.md"
    workflow_profile = read_workflow_profile(project_root, topic_id)
    payload = parse_detailed_outline(outline_path, topic_id, workflow_profile.get("strategy", "knowledge-explainer"))
    project_dir = build_project_dir(project_root, topic_id)
    requirements = read_json(project_dir / "article-requirements.json", {})
    payload = apply_article_word_budget(payload, requirements)
    output_path = project_dir / "section-manifest.json"
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
