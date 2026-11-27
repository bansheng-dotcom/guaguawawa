import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize publish-ready image manifest")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    source_manifest = read_json(project_dir / "image-manifest-source.json", {"images": []})
    qa_payload = read_json(project_dir / "image-qa-01" / "output.json", {"images": []})
    qa_map = {item["image_id"]: item for item in qa_payload.get("images", [])}

    images: list[dict] = []
    for image in source_manifest.get("images", []):
        compositor = read_json(project_dir / f"image-compositor-{image['image_id']}" / "output.json", {})
        qa_item = qa_map.get(image["image_id"], {})
        images.append(
            {
                "image_id": image["image_id"],
                "filename": compositor.get("filename", ""),
                "file": compositor.get("file", ""),
                "kind": image.get("kind", ""),
                "insert_after_heading": image.get("insert_after_heading", ""),
                "target_section_id": image.get("target_section_id", ""),
                "data_source": image.get("source", ""),
                "component_list": compositor.get("components", []),
                "design_notes": compositor.get("design_notes", image.get("purpose", "")),
                "qa_status": "pass" if qa_item.get("code_qa", {}).get("exists") else "fail",
                "qa_detail": qa_item,
            }
        )

    payload = {
        "topic_id": args.topic_id,
        "generated_at": datetime.now().isoformat(),
        "total_score": source_manifest.get("total_score", 0.0),
        "images": images,
    }

    asset_dir = project_root / "assets" / "publish-ready" / args.topic_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    write_json(project_dir / "image-manifest-final.json", payload)
    write_json(asset_dir / "image-manifest.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
