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

from compiler_lib import build_project_dir, read_json, score_article_sections, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Score article workload deterministically")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest_path = project_dir / "section-manifest.json"
    manifest = read_json(manifest_path, {"topic_id": args.topic_id, "sections": []})
    scored = score_article_sections(manifest)
    write_json(manifest_path, scored)
    print(json.dumps(scored, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
