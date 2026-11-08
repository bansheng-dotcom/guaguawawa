import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json


TAIL_PATTERNS = [
    "如果你要",
    "我下一步可以",
    "我可以继续",
    "你要的话",
    "如果需要我可以",
    "接下来我可以",
]


def split_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def strip_heading(block: str) -> str:
    lines = block.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[1:]).strip()


def trim_tail(text: str) -> str:
    cut = None
    for pattern in TAIL_PATTERNS:
        idx = text.find(pattern)
        if idx != -1:
            cut = idx if cut is None else min(cut, idx)
    if cut is None:
        return text.strip()
    return text[:cut].rstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair style harmonizer output while preserving canonical section headings")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    output_path = project_dir / "style-harmonizer-01" / "output.md"
    draft_path = project_root / "tmp" / f"{args.topic_id}-draft.md"

    if not output_path.exists() or not draft_path.exists():
        raise SystemExit("style harmonizer output or draft source is missing")

    expected_headings = [section.get("heading", "").strip() for section in manifest.get("sections", []) if section.get("heading")]
    harmonized_blocks = split_blocks(output_path.read_text(encoding="utf-8"))
    draft_blocks = split_blocks(draft_path.read_text(encoding="utf-8"))

    repaired_blocks: list[str] = []
    for index, heading in enumerate(expected_headings):
        if index < len(harmonized_blocks):
            body = strip_heading(harmonized_blocks[index])
        elif index < len(draft_blocks):
            body = strip_heading(draft_blocks[index])
        else:
            body = ""
        if index == len(expected_headings) - 1:
            body = trim_tail(body)
        repaired = f"## {heading}".rstrip()
        if body:
            repaired += f"\n\n{body.strip()}"
        repaired_blocks.append(repaired.strip())

    output_path.write_text("\n\n".join(repaired_blocks).strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
