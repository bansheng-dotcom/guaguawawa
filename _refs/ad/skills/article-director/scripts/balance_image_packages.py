import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_image_packages, build_project_dir, read_json, score_image_manifest, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Balance image packages deterministically")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    image_manifest = read_json(project_dir / "image-manifest-source.json", {"topic_id": args.topic_id, "images": []})
    if image_manifest.get("images") and "total_score" not in image_manifest["images"][0]:
        image_manifest = score_image_manifest(image_manifest)
        write_json(project_dir / "image-manifest-source.json", image_manifest)
    payload = build_image_packages(image_manifest)
    output_path = project_dir / "image-packages.json"
    write_json(output_path, payload)
    print(output_path)


if __name__ == "__main__":
    main()
