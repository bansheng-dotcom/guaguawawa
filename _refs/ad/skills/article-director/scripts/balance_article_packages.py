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

from compiler_lib import build_article_packages, build_project_dir, read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Balance article packages deterministically")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"topic_id": args.topic_id, "sections": []})
    packages = build_article_packages(manifest)
    output_path = project_dir / "article-packages.json"
    write_json(output_path, packages)
    print(json.dumps(packages, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
