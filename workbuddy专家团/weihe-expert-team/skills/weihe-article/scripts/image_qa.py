import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, write_json


SVG_SIZE_PATTERN = re.compile(r'viewBox="0 0 (\d+) (\d+)"')


def image_size(path: Path) -> tuple[int, int]:
    if path.suffix.lower() == ".svg":
        match = SVG_SIZE_PATTERN.search(path.read_text(encoding="utf-8"))
        if match:
            return int(match.group(1)), int(match.group(2))
    return 0, 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic QA over generated image assets")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "image-manifest-source.json", {"images": []})

    passed: list[str] = []
    issues: list[str] = []
    details: list[dict] = []

    for image in manifest.get("images", []):
        payload = read_json(project_dir / f"image-compositor-{image['image_id']}" / "output.json", {})
        file_path = Path(payload.get("file", ""))
        if not file_path.exists():
            issues.append(f"missing rendered file: {image['image_id']}")
            continue
        width, height = image_size(file_path)
        if width < 1200 or height < 700:
            issues.append(f"image too small: {file_path.name} {width}x{height}")
        if not payload.get("components"):
            issues.append(f"component list missing: {image['image_id']}")
        if not payload.get("design_notes"):
            issues.append(f"design notes missing: {image['image_id']}")
        details.append(
            {
                "image_id": image["image_id"],
                "file": str(file_path),
                "width": width,
                "height": height,
                "code_qa": {"exists": file_path.exists(), "size_ok": width >= 1200 and height >= 700},
                "heuristic_ai_qa": {
                    "has_purpose": bool(payload.get("design_notes")),
                    "has_components": bool(payload.get("components")),
                    "precise_numbers_supported": (not image.get("requires_precise_numbers")) or "experiment" in file_path.name or "cost" in file_path.name,
                },
            }
        )
        passed.append(f"qa passed: {file_path.name}")

    output_path = project_dir / "image-qa-01" / "output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pass": not issues,
        "passed": passed,
        "issues": issues,
        "file": str(project_root / "assets" / "publish-ready" / args.topic_id),
        "images": details,
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
