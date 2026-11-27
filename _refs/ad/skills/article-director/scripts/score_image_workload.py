import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, score_image_manifest, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Score image workload deterministically")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest_path = project_dir / "image-manifest-source.json"
    payload = read_json(manifest_path, {"topic_id": args.topic_id, "images": []})
    scored = score_image_manifest(payload)
    write_json(manifest_path, scored)
    print(manifest_path)


if __name__ == "__main__":
    main()
